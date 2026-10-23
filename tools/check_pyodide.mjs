// Execute the exact Pages source archive in the pinned WebAssembly runtime.
// Usage: node tools/check_pyodide.mjs /absolute/path/to/pyodide/pyodide.mjs
// Optional baseline/dependencies/resonance select disjoint validation groups.
// "resonance-rules" runs only the primitive native SELFRES search traces.
import { readFileSync } from "node:fs";
import { pathToFileURL } from "node:url";
import assert from "node:assert/strict";
const { loadPyodide } = await import(pathToFileURL(process.argv[2]).href);
const siteVersion=JSON.parse(readFileSync(new URL("../dist/version.json",import.meta.url))).version;
for(const [file,references] of [["index.html",["app.js","style.css"]],["app.js",["analysis-views.mjs","worker.js"]],["worker.js",["reasitic.zip"]]]){
  const body=readFileSync(new URL("../dist/"+file,import.meta.url),"utf8");
  for(const reference of references)assert.ok(body.includes(`${reference}?v=${siteVersion}`),`Coherent release asset ${reference}`);
}
const py = await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL("../dist/reasitic.zip",import.meta.url))),"zip");
py.runPython("from reasitic.bridge import request_json");
const call=py.globals.get("request_json");
const dependenciesOnly=process.argv[3]==="dependencies";
const resonanceOnly=["resonance","resonance-rules"].includes(process.argv[3]);
const baselineOnly=process.argv[3]==="baseline";
if(process.argv[3]&&!['dependencies','resonance','resonance-rules','baseline'].includes(process.argv[3]))throw Error("Unknown validation group");
function request(data,onProgress) {
  const result=JSON.parse(onProgress?call(JSON.stringify(data),onProgress):call(JSON.stringify(data)));
  if(result.error)throw new Error(result.error);
  return result.result;
}
if(!resonanceOnly){
if(!dependenciesOnly){
const init=request({action:"init"});
assert.equal(init.technology.metals.length,5);
for(const kind of init.generators) {
  const input={kind,parameters:{name:"WASM",metal:"M4",exit_metal:"M3"}};
  const shape=request({action:"build",...input});
  assert.ok(shape.polygons.length>0,kind);
  const simulation=request({action:"simulate",...input,frequency_hz:2e9});
  assert.ok(Number.isFinite(simulation.inductance_nh),kind);
  const gds=request({action:"gds",...input});
  assert.ok(Buffer.from(gds.base64,"base64").length>100,kind);
  console.log(`${kind}: ${shape.segments.length} segments, L=${simulation.inductance_nh} nH, GDS OK`);
}
const sweep=request({action:"sweep",first_hz:1e8,last_hz:2e10,count:31});
assert.equal(sweep.rows.length,31);
const pair=request({action:"build",kind:"transformer",parameters:{length:100,width:3,spacing:2,turns:1.5,secondary_turns:1.25,metal:"M4",exit_metal:"M3"}});
assert.equal(pair.windings.length,2);
assert.ok(pair.polygons.length>pair.segments.length);
const cases=JSON.parse(readFileSync(new URL("../tests/fixtures/analysis.json",import.meta.url))).cases;
for (const fixture of cases) {
  // Keyword angles cross a native binary32 boundary before entering geometry.
  const parameters={...fixture.parameters};
  for (const key of ["gap","angle"]) if(key in parameters) parameters[key]=Math.fround(parameters[key]*Math.PI/180)*180/Math.PI;
  if(fixture.kind==="wire" && fixture.parameters.angle){
    const shape=request({action:"build",kind:fixture.kind,parameters});
    assert.deepEqual(shape.segments.map(segment=>[...segment.start,...segment.end]),fixture.geometry_endpoints,"Native rotated-wire endpoint doubles");
  }
  for(const [frequency_hz,mesh,key] of [[1e9,{},"matrix_1ghz"],[2e9,{length_cell:50,width_cell:3,thickness_cell:.5},"matrix_fine_2ghz"],[1e9,{length_cell:20,capacitance_length_cell:50},"matrix_unequal_1ghz"]]) {
    const result=request({action:"lmat",kind:fixture.kind,parameters,frequency_hz,mesh});
    const expected=fixture[key];
    assert.equal(result.matrix.length,expected.length,`${fixture.kind} ${key} mesh dimensions`);
    result.matrix.forEach((row,i)=>row.forEach((z,j)=>z.forEach((value,component)=>assert.ok(Math.abs(value-expected[i][j][component])<1e-8,`${fixture.kind} ${key} [${i},${j}]`))));
  }
}
console.log("36 reference LMAT matrices passed in WebAssembly.");
const cases3d=JSON.parse(readFileSync(new URL("../tests/fixtures/transformer3d.json",import.meta.url))).cases;
for(const fixture of cases3d){
  for(const [winding,name] of [[0,"P"],[1,"S"]]){
    const input={kind:"transformer3d",parameters:fixture.parameters,winding};
    const geometry=request({action:"build",...input});
    const reference=fixture.geometry[name];
    assert.equal(geometry.segments.length,reference.length);
    geometry.segments.forEach((segment,i)=>{
      for(const [field,point] of [["AX",segment.outer_start],["BX",segment.outer_end],["CX",segment.inner_start],["DX",segment.inner_end],["PORT1X",segment.start],["PORT2X",segment.end]]){
        assert.ok(Math.abs(point[0]-reference[i][field])<5.1e-7);
        assert.ok(Math.abs(point[1]-reference[i][field.replace(/X$/,"Y")])<5.1e-7);
      }
    });
    const matrix=request({action:"lmat",...input,frequency_hz:1e9}).matrix;
    const expected=fixture.matrices[name];
    assert.equal(matrix.length,expected.length);
    matrix.forEach((row,i)=>row.forEach((value,j)=>value.forEach((component,k)=>assert.ok(Math.abs(component-expected[i][j][k])<1e-8,`3D ${name} matrix [${i},${j}]`))));
  }
}
console.log("Seven 3D geometry sessions and 14 winding matrices passed in WebAssembly.");
const potentialCases=JSON.parse(readFileSync(new URL("../tests/fixtures/potential.json",import.meta.url))).cases;
for(const fixture of potentialCases){
  const result=request({action:"capacitance",kind:fixture.kind,parameters:fixture.parameters,technology:fixture.technology,
    frequency_hz:fixture.frequency_hz,mesh:{length_cell:fixture.length_cell,width_cell:fixture.width_cell},
    ground:fixture.ground?{kind:"wire",parameters:fixture.ground}:null});
  assert.equal(result.matrix.length,fixture.matrix.length);
  result.matrix.forEach((row,i)=>row.forEach((value,j)=>value.forEach((component,k)=>{
    const expected=fixture.matrix[i][j][k];
    assert.ok(Math.abs(component-expected)<=Math.max(1e-16,Math.abs(expected)*1e-8),`CAP ${fixture.process} ${fixture.kind} [${i},${j}]`);
  })));
}
console.log("Eight native layered-substrate capacitance matrices passed in WebAssembly.");
const networkCases=[...JSON.parse(readFileSync(new URL("../tests/fixtures/network.json",import.meta.url))).cases,
  ...JSON.parse(readFileSync(new URL("../tests/fixtures/network_eddy.json",import.meta.url))).cases];
for(const fixture of networkCases){
  const result=request({action:"pi2",kind:fixture.kind,parameters:fixture.parameters,technology:fixture.technology,
    frequency_hz:fixture.frequency_hz,mesh:fixture.mesh,ground:fixture.ground,eddy:fixture.eddy||false});
  for(const key of ["admittance_matrix","scattering_matrix"]){
    assert.equal(result[key].length,2);
    result[key].forEach((row,i)=>row.forEach((value,j)=>value.forEach((component,k)=>{
      const expected=fixture[key][i][j][k];
      assert.ok(Math.abs(component-expected)<=Math.max(1e-10,Math.abs(expected)*1e-8),`PI2 ${fixture.process} ${fixture.kind} ${key} [${i},${j}]`);
    })));
  }
  assert.equal(result.eddy,fixture.eddy||false);
  assert.ok(Number.isFinite(result.pi.q_first));
  assert.ok(Number.isFinite(result.pi.inductance_h));
  if(fixture.kind==="wire" && !fixture.ground)assert.equal(result.pi.shunt_differential_ohm,null);
}
console.log("16 native distributed Pi2 Y/S models passed in WebAssembly, eddy off/on.");
const piModelCases=[...JSON.parse(readFileSync(new URL("../tests/fixtures/pi_models.json",import.meta.url))).cases,
  ...JSON.parse(readFileSync(new URL("../tests/fixtures/pi_models_eddy.json",import.meta.url))).cases];
for(const fixture of piModelCases){
  const result=request({action:fixture.model,kind:fixture.kind,parameters:fixture.parameters,technology:fixture.technology,
    ground:fixture.ground,first_pad:fixture.first_pad,second_pad:fixture.second_pad,frequency_hz:fixture.frequency_hz,eddy:fixture.eddy||false});
  for(const key of ["admittance_matrix","scattering_matrix"]){
    result[key].forEach((row,i)=>row.forEach((value,j)=>value.forEach((component,k)=>{
      const expected=fixture[key][i][j][k];
      assert.ok(Math.abs(component-expected)<=Math.max(1e-10,Math.abs(expected)*1e-8),`${fixture.model} ${fixture.kind} ${key}`);
    })));
  }
  if(fixture.model==="pi4")assert.ok(result.filaments>=19);
}
assert.throws(()=>request({action:"pi"}),/native fast Pi/);
assert.throws(()=>request({action:"pi3"}),/explicit ground/);
console.log("16 native Pi3/Pi4 models and explicit fast-Pi limitation passed in WebAssembly, eddy off/on.");
}
if(baselineOnly){call.destroy();console.log("Pinned Pyodide baseline checks passed.");process.exit(0);}
py.runPython(`
from dataclasses import asdict
import json,math
from reasitic.quadrature import integrate_infinite,infinite_rule
def quadrature_probe(payload):
    case=json.loads(payload)
    kind,scale=case.pop("kind"),case.pop("scale")
    case.pop("result")
    callback=[lambda x:1/((1+x)*(1+x)),lambda x:1/(1+x*x),lambda x:math.exp(-scale*x),
              lambda x:math.exp(-x*x),lambda x:math.sin(x)/(1+x*x),lambda x:1.,
              lambda x:math.exp(-x)/math.sqrt(x)][kind]
    solver=infinite_rule if "a" in case else integrate_infinite
    return json.dumps(asdict(solver(callback,**case)),allow_nan=False)
`);
const quadratureProbe=py.globals.get("quadrature_probe");
const quadratureFixture=JSON.parse(readFileSync(new URL("../tests/fixtures/quadrature.json",import.meta.url)));
for(const fixture of [...quadratureFixture.cases,...quadratureFixture.rules]){
  const result=JSON.parse(quadratureProbe(JSON.stringify(fixture)));
  for(const [key,expected] of Object.entries(fixture.result)){
    if(["status","evaluations","intervals"].includes(key))assert.equal(result[key],expected,`QUADPACK ${key}`);
    else assert.ok(Math.abs(result[key]-expected)<=Math.max(1e-13,Math.abs(expected)*1e-12),`QUADPACK ${key} kind=${fixture.kind}`);
  }
}
quadratureProbe.destroy();
console.log("60 native infinite integrations and 36 transformed rules passed in WebAssembly.");
py.runPython(`
from reasitic.green import (GreenLayers,propagation_constant,complex_tanh,reflection_imag,
                            oscillating_integrand,propagation_integrand,oscillating_kernel,reflection_kernel)
def green_probe(payload):
    case=json.loads(payload)
    k,f=case["k"],case["frequency"]
    layers=GreenLayers(case["layer1"],case["layer2"],case["depth"])
    a,b=propagation_constant(k,f,layers.layer1),propagation_constant(k,f,layers.layer2)
    t=complex_tanh(complex(layers.depth*a.real,layers.depth*a.imag))
    result=dict(gamma_first=[a.real,a.imag],gamma_second=[b.real,b.imag],tanh=[t.real,t.imag],
                reflection_imag=reflection_imag(k,f,layers.layer1),oscillating_integrand=oscillating_integrand(k,f,layers),
                propagation_integrand=propagation_integrand(f,layers),
                oscillating_kernel=oscillating_kernel(k,f,layers,case["height"],case["separation"]),
                reflection_kernel=reflection_kernel(k,case["height"]))
    def finite(value):
        if isinstance(value,list):return [finite(v) for v in value]
        return value if math.isfinite(value) else "nan" if math.isnan(value) else "inf" if value>0 else "-inf"
    return json.dumps({key:finite(value) for key,value in result.items()},allow_nan=False)
`);
const greenProbe=py.globals.get("green_probe");
const greenCases=JSON.parse(readFileSync(new URL("../tests/fixtures/green.json",import.meta.url))).cases;
for(const fixture of greenCases){
  const result=JSON.parse(greenProbe(JSON.stringify(fixture)));
  for(const [key,value] of Object.entries(result)){
    const actual=Array.isArray(value)?value:[value],expected=Array.isArray(fixture[key])?fixture[key]:[fixture[key]];
    actual.forEach((v,i)=>{
      const reference=expected[i];
      if(typeof reference==="string")assert.equal(v,reference,`Green ${key}`);
      else if(reference===0)assert.ok(v===0,`Green ${key} exact zero`);
      else {
        const floor=key==="reflection_kernel" || fixture.height===1?1e-300:1e-14;
        assert.ok(Math.abs(v-reference)<=Math.max(floor,Math.abs(reference)*1e-12),`Green ${key} k=${fixture.k}`);
      }
    });
  }
}
greenProbe.destroy();
console.log("186 native Green-kernel cases passed in WebAssembly, including cutoff and nonfinite classifications.");
py.runPython(`
from reasitic.oscillatory import (MomentCache,weighted_rule,chebyshev_transform,solve_tridiagonal,
                                  oscillatory_rule,integrate_oscillatory,integrate_fourier)
from reasitic.quadrature import _d
def oscillatory_probe(payload):
    case=json.loads(payload)
    group=case.pop("group")
    kind=case.get("kind",0)
    callback=[lambda x:1/(1+x*x),lambda x:math.exp(-x),lambda x:1/(1+x),lambda x:1.,
              lambda x:x*x*x,lambda x:abs(x-.37)][kind]
    if group=="rules":
        cache=MomentCache(case["rows"])
        value=oscillatory_rule(callback,case["a"],case["b"],case["frequency"],case["selector"],0,False,cache)
        result=asdict(value.value)
        result.update(evaluations=value.evaluations,computed=cache.computed,moments=cache.data[0])
    elif group=="weighted":
        weight=lambda x:(math.sin if case["selector"]==2 else math.cos)(float(_d(case["frequency"])*_d(x)))
        result=asdict(weighted_rule(callback,weight,case["a"],case["b"]))
    elif group=="chebyshev":
        samples=case["samples"].copy()
        y,z=chebyshev_transform(samples)
        result=dict(overwritten=samples,degree12=y,degree24=z)
    elif group=="tridiagonal":
        arrays=[case[key].copy() for key in ("c","d","e","rhs")]
        result=dict(status=solve_tridiagonal(*arrays),overwritten=arrays)
    else:
        args={k:v for k,v in case.items() if k not in ("kind","rows","result","cycle_integrals","cycle_errors","cycle_statuses","history")}
        if group=="oscillatory":
            cache=MomentCache(case["rows"])
            result=asdict(integrate_oscillatory(callback,cache=cache,**args))
            result["computed"]=cache.computed
        else:result=asdict(integrate_fourier(callback,**args))
    return json.dumps(result,allow_nan=False)
`);
const oscillatoryProbe=py.globals.get("oscillatory_probe");
const oscillatoryFixture=JSON.parse(readFileSync(new URL("../tests/fixtures/oscillatory.json",import.meta.url)));
function compareOscillatory(actual,expected,label){
  if(Array.isArray(expected)){
    assert.equal(actual.length,expected.length,label);
    actual.forEach((v,i)=>compareOscillatory(v,expected[i],`${label}[${i}]`));
  } else if(/evaluations|status|intervals|computed|cycles/.test(label))assert.equal(actual,expected,label);
  else {
    const floor=label.includes("error")?1e-12:1e-13,relative=label.includes("error")?1e-10:1e-12;
    assert.ok(Math.abs(actual-expected)<=Math.max(floor,Math.abs(expected)*relative),label);
  }
}
for(const group of ["rules","weighted","chebyshev","tridiagonal","oscillatory","fourier"]){
  for(const fixture of oscillatoryFixture[group]){
    const result=JSON.parse(oscillatoryProbe(JSON.stringify({...fixture,group})));
    for(const [key,value] of Object.entries(result))compareOscillatory(value,key in fixture?fixture[key]:fixture.result[key],`${group} ${key}`);
  }
}
oscillatoryProbe.destroy();
console.log("524 native weighted/Chebyshev/moment/adaptive/Fourier cases passed in WebAssembly.");
py.runPython(`
from reasitic.green_integration import GreenIntegrationState,green_integral
def green_integral_probe(payload):
    case=json.loads(payload)
    state=GreenIntegrationState(GreenLayers(case["layer1"],case["layer2"],case["depth"]),case["kernel"])
    points=[]
    value=green_integral(case["frequency"],case["separation"],case["height"],case["z_offset"],state,observer=points.append)
    result=dict(value=value.value,status=value.status,observations=value.observations,first_point=points[0],last_point=value.last_point,
                state=[state.frequency,state.separation,state.height,state.z_offset],history=state.history)
    if not math.isfinite(result["value"]):result["value"]=str(result["value"])
    return json.dumps(result,allow_nan=False)
`);
const greenIntegralProbe=py.globals.get("green_integral_probe");
const greenIntegralCases=JSON.parse(readFileSync(new URL("../tests/fixtures/green_integration.json",import.meta.url))).cases;
for(const fixture of greenIntegralCases){
  const result=JSON.parse(greenIntegralProbe(JSON.stringify(fixture)));
  function compare(actual,expected,label){
    if(Array.isArray(expected)){
      assert.equal(actual.length,expected.length,label);
      actual.forEach((value,i)=>compare(value,expected[i],`${label}[${i}]`));
    }else if(typeof expected==="string" || ["status","observations"].includes(label))assert.equal(actual,expected,label);
    else if(expected===0)assert.ok(actual===0,label);
    else assert.ok(Math.abs(actual-expected)<=Math.max(1e-12,Math.abs(expected)*1e-12),`Green integral ${label}`);
  }
  for(const [key,value] of Object.entries(result))compare(value,fixture[key],key);
}
greenIntegralProbe.destroy();
console.log("58 complete native Green integrations passed in WebAssembly, including selector boundaries and callback traces.");
const eddyCases=JSON.parse(readFileSync(new URL("../tests/fixtures/eddy.json",import.meta.url))).cases;
for(const fixture of eddyCases){
  for(const [frequency_hz,mesh,key] of [[1e9,{},"matrix_1ghz"],[2e9,{length_cell:50,width_cell:3,thickness_cell:.5},"matrix_fine_2ghz"]]){
    const result=request({action:"lmat",kind:fixture.kind,parameters:fixture.parameters,technology:fixture.technology,frequency_hz,mesh,eddy:true});
    assert.equal(result.eddy,true);
    assert.equal(result.matrix.length,fixture[key].length);
    result.matrix.forEach((row,i)=>row.forEach((value,j)=>value.forEach((component,k)=>{
      const expected=fixture[key][i][j][k];
      assert.ok(Math.abs(component-expected)<=Math.max(1e-8,Math.abs(expected)*1e-8),`EDDY ${fixture.kind} ${fixture.process} ${key} [${i},${j}]`);
    })));
  }
}
console.log("16 complete native EDDY ON LMAT matrices passed in WebAssembly.");
}
if(dependenciesOnly){call.destroy();console.log("Pinned Pyodide dependency checks passed.");process.exit(0);}
py.runPython(`
import json,math
from reasitic.resonance import search_self_resonance
def resonance_probe(payload):
    case=json.loads(payload)
    def analyze(frequency,fast):
        imag=(frequency-case["target"])*case["scale"] if case["kind"]==0 else float(case["fixed"])
        return dict(y11=1+.5j,y12=.01+.02j,y21=.01+.02j,y22=complex(0 if case["kind"]==2 else 1,imag))
    result=search_self_resonance(analyze,case["first"],case["second"],case["step"],differential=case["differential"],fast=case["fast"],iteration_limit=case["iteration_limit"])
    for point in result["trace"]:
        if not math.isfinite(point["imaginary_impedance_ohm"]):point["imaginary_impedance_ohm"]=str(point["imaginary_impedance_ohm"])
    return json.dumps(result,allow_nan=False)
`);
const resonanceProbe=py.globals.get("resonance_probe");
const resonanceSearchCases=JSON.parse(readFileSync(new URL("../tests/fixtures/resonance_search.json",import.meta.url))).cases;
for(const fixture of resonanceSearchCases){
  const result=JSON.parse(resonanceProbe(JSON.stringify(fixture)));
  assert.equal(result.native_result_hz,fixture.native_result_hz,"Native SELFRES stopping frequency");
  assert.equal(result.evaluations,fixture.evaluations,"Native SELFRES solve count");
  assert.deepEqual(result.analysis_frequencies_hz,fixture.analyses.map(row=>row[0]));
  assert.equal(result.trace.length,fixture.progress.length);
  result.trace.forEach((point,i)=>{
    const actual=[point.lower_hz/1e9,point.upper_hz/1e9,point.frequency_hz/1e9,point.imaginary_impedance_ohm];
    actual.forEach((value,j)=>{
      const expected=fixture.progress[i][j];
      if(expected==="nan")assert.equal(value,"nan");
      else assert.ok(Math.abs(value-expected)<=Math.max(1e-12,Math.abs(expected)*1e-12),`SELFRES progress ${i}/${j}`);
    });
  });
}
resonanceProbe.destroy();
console.log("184 native SELFRES search traces passed in WebAssembly, including strict tolerance, quantization and 101-solve exhaustion.");
if(process.argv[3]!=="resonance-rules"){
const resonancePhysicalCases=JSON.parse(readFileSync(new URL("../tests/fixtures/resonance_physical.json",import.meta.url))).cases;
for(const [index,fixture] of resonancePhysicalCases.entries()){
  console.log(`SELFRES case ${index+1}/${resonancePhysicalCases.length}: ${fixture.process} · ${fixture.kind} · ${fixture.first_hz/1e9}–${fixture.last_hz/1e9} GHz`);
  const progress=[];
  const result=request({action:"selfres",kind:fixture.kind,parameters:fixture.parameters,technology:fixture.technology,ground:fixture.ground,
    eddy:fixture.eddy,mesh:fixture.mesh,first_hz:fixture.first_hz,last_hz:fixture.last_hz,step_hz:fixture.step_hz,differential:fixture.differential},point=>progress.push(JSON.parse(point)));
  assert.deepEqual(progress,result.trace,"Live worker progress matches the result trace");
  assert.equal(result.trace.length,fixture.progress.length);
  assert.ok(Math.abs(result.frequency_hz/1e9-fixture.frequency_ghz)<1e-10,"Physical SELFRES stopping frequency");
  assert.equal(result.model.frequency_hz,result.last_evaluated_frequency_hz);
  result.trace.forEach((point,i)=>{
    const actual=[point.lower_hz/1e9,point.upper_hz/1e9,point.frequency_hz/1e9,point.imaginary_impedance_ohm];
    actual.forEach((value,j)=>assert.ok(Math.abs(value-fixture.progress[i][j])<=Math.max(1e-8,Math.abs(fixture.progress[i][j])*1e-8),`Physical SELFRES progress ${i}/${j}`));
  });
}
console.log("12 complete native SELFRES SLOW sessions and live progress callbacks passed in WebAssembly.");
}
call.destroy();
console.log("Pinned Pyodide archive smoke test passed.");
