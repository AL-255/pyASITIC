// Execute the native PiX numerical fixtures in the exact static-site archive.
// Usage: node tools/check_extended.mjs /absolute/path/to/pyodide.mjs [rules]
import {readFileSync} from "node:fs";
import {pathToFileURL} from "node:url";
import assert from "node:assert/strict";
import {installNumericalKernels} from "../web/numeric-kernels.mjs";
const {loadPyodide}=await import(pathToFileURL(process.argv[2]).href);
const py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL("../dist/reasitic.zip",import.meta.url))),"zip");
await installNumericalKernels(py,readFileSync(new URL("../dist/numeric.wasm",import.meta.url)));
const fixture=name=>JSON.parse(readFileSync(new URL(`../tests/fixtures/${name}.json`,import.meta.url)));
// JSON.stringify(-0) emits 0. Primitive native fixtures intentionally contain
// signed-zero inputs, so preserve those bits on the trip into Python.
function nativeJSON(value){
  if(typeof value==="number"&&Object.is(value,-0))return "-0.0";
  if(Array.isArray(value))return "["+value.map(nativeJSON).join(",")+"]";
  if(value&&typeof value==="object")return "{"+Object.entries(value).map(([key,v])=>JSON.stringify(key)+":"+nativeJSON(v)).join(",")+"}";
  return JSON.stringify(value);
}
function near(actual,expected,label,floor=1e-12,relative=1e-10){
  if(Array.isArray(expected)){
    assert.equal(actual.length,expected.length,label);
    expected.forEach((v,i)=>near(actual[i],v,`${label}[${i}]`,floor,relative));
  }else if(typeof expected==="string")assert.equal(actual,expected,label);
  else{
    assert.equal(typeof actual,"number",label);assert.ok(Number.isFinite(actual),label);
    assert.ok(Math.abs(actual-expected)<=Math.max(floor,Math.abs(expected)*relative),`${label}: ${actual} versus ${expected}`);
  }
}
py.runPython(`
import json,math
from reasitic.extended import stamp_extended_node_columns,solve_extended_node_equations
from reasitic.symmetric import factor_symmetric_upper,inverse_symmetric,_eigen2
from reasitic.parallel import segment_self_inductance,cross_section_log_integral,effective_separation,parallel_segment_mutual
from reasitic.inductance import segment_mutual
from reasitic.network import _pairs,_complex_matrix
from reasitic.green import _guard
from reasitic.bridge import request_json
def clean(value):
    if isinstance(value,float) and not math.isfinite(value):return str(value)
    if isinstance(value,dict):return {k:clean(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [clean(v) for v in value]
    return value
def extended_probe(payload):
    request=json.loads(payload);group,case=request["group"],request["case"]
    if group=="nodes":
        cap,ind=_complex_matrix(case["cap"]),_complex_matrix(case["ind"])
        result=dict(SC=_pairs(stamp_extended_node_columns(cap)),SZ=_pairs(stamp_extended_node_columns(ind)))
        if not case["stamp_only"]:
            y,state=solve_extended_node_equations(cap,ind);n=len(cap)
            result.update(Y=[[y[k].real,y[k].imag] for k in ("y22","y21","y12","y11")],
                V=[[z.real,z.imag] for z in state["solutions"][0][:n+1]],I=[[z.real,z.imag] for z in state["solutions"][0][n+1:]])
    elif group=="symmetric":
        a=_complex_matrix(case["matrix"])
        if case["S"]:
            try:inverse_symmetric(a);result=dict(singular=False)
            except ValueError:result=dict(singular=True)
        else:
            factor,pivots=factor_symmetric_upper(a);inverse=inverse_symmetric(a)
            result=dict(P=pivots,F=_pairs([row[i:] for i,row in enumerate(factor)]),I=_pairs([row[i:] for i,row in enumerate(inverse)]))
    elif group=="eigen":
        values=_guard(_eigen2)(*(complex(*z) for z in case["input"]))
        result=[[z.real,z.imag] for z in values]
    else:
        mode,args=case["mode"],case["input"]
        if mode<3:result=dict(status=0,value=float((segment_self_inductance,cross_section_log_integral,effective_separation)[mode](*args)))
        elif mode==3:
            status,value=parallel_segment_mutual(args[:8],args[8:16],args[16]);result=dict(status=status,value=value)
        else:result=dict(status=0,value=segment_mutual(args[:8],args[8:16]))
    return json.dumps(clean(result),allow_nan=False)
`);
const probe=py.globals.get("extended_probe");
for(const c of fixture("extended_nodes").cases){
  assert.equal(c.padding_untouched,true,"Native noncontiguous output canaries");
  const result=JSON.parse(probe(nativeJSON({group:"nodes",case:c})));
  for(const key of ["SC","SZ"])assert.deepEqual(result[key],c[key],`Exact native column stamps ${key}`);
  if(!c.stamp_only)for(const key of ["Y","V","I"])near(result[key],c[key],`Extended nodes ${c.cap.length} ${key}`);
}
console.log("68 native extended-node cases passed in WebAssembly, including blocked LU and exact column stamps.");
const symmetric=fixture("symmetric");
for(const c of symmetric.cases){
  const result=JSON.parse(probe(nativeJSON({group:"symmetric",case:c})));
  if(c.S)assert.equal(result.singular,true);
  else{
    assert.deepEqual(result.P,c.P,"Native symmetric pivots");
    for(const key of ["F","I"])near(result[key],c[key].map((row,i)=>row.slice(i)),`Symmetric ${c.matrix.length} ${key}`);
  }
}
for(const c of symmetric.eigen)near(JSON.parse(probe(nativeJSON({group:"eigen",case:c}))),c.result,"Native eigen2");
console.log(`${symmetric.cases.length} native symmetric factors/inverses and ${symmetric.eigen.length} eigen rotations passed in WebAssembly.`);
for(const c of fixture("parallel").cases){
  const result=JSON.parse(probe(nativeJSON({group:"parallel",case:c})));
  assert.equal(result.status,c.status,"Native parallel status");
  if(c.status)assert.equal(result.value,null,"Rejected parallel output is undefined");
  else if(c.value===0)assert.ok(result.value===0,"Exact native zero");
  else near(result.value,c.value,`Retained parallel mode ${c.mode}`,1e-300,1e-12);
}
probe.destroy();
console.log("175 native retained self/separation/parallel cases passed in WebAssembly.");
if(process.argv[3]!=="rules"){
  const call=py.globals.get("request_json");
  for(const c of fixture("pix").cases){
    const payload={action:"pix",kind:c.kind,parameters:c.parameters,technology:c.technology,ground:c.ground,
      frequency_hz:c.frequency_hz,mesh:c.mesh,eddy:c.eddy,include_matrices:true};
    const response=JSON.parse(call(JSON.stringify(payload)));assert.ok(!response.error,response.error);
    const r=response.result;
    for(const [key,floor] of [["capacitance_matrix",1e-16],["inductive_impedance_matrix",1e-8],["currents_first",1e-10],["voltages_first",1e-10]])near(r[key],c[key],`PiX ${c.kind} ${key}`,floor,1e-8);
    near(r.filament_impedance_diagonal,c.filament_impedance_diagonal,"Native filament self impedance",1e-14,1e-13);
    near(r.admittance_matrix,c.direct_admittance_matrix,"Native PIX RHS Y",1e-12,1e-8);
    if(c.admittance_matrix){
      near(r.admittance_matrix,c.admittance_matrix,"Native 2PORTX Y",1e-10,1e-8);
      near(r.scattering_matrix,c.scattering_matrix,"Native 2PORTX S",1e-10,1e-8);
    }
    for(const [i,key] of ["q_first","q_second","q_differential"].entries()){
      if(typeof c.qualities[i]==="string")assert.equal(r.pi[key],null,key);
      else near(r.pi[key],c.qualities[i],key,1e-9,1e-8);
    }
    const metrics=[["inductance_h",1e9],["resistance_ohm",1],["capacitance_first_f",1e15],["resistance_first_ohm",1],["capacitance_second_f",1e15],["resistance_second_ohm",1],["resonant_frequency_hz",1e-9]];
    metrics.forEach(([key,scale],i)=>{
      if(typeof c.metrics[i]==="string")assert.equal(r.pi[key],null,key);
      else{assert.notEqual(r.pi[key],null,key);near(r.pi[key]*scale,c.metrics[i],key,1e-9,1e-8);}
    });
    ["input_impedance_first_ohm","input_impedance_second_ohm","differential_impedance_ohm"].forEach((key,i)=>near(r[key],c.input_impedances[i],key,1e-8,1e-8));
  }
  call.destroy();
  console.log("10 complete native PIX sessions passed in WebAssembly with full-precision circuit/ZIN and matrix/vector checks.");
}
