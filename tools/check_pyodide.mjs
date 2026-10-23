// Execute the exact Pages source archive in the pinned WebAssembly runtime.
// Usage: node tools/check_pyodide.mjs /absolute/path/to/pyodide/pyodide.mjs
import { readFileSync } from "node:fs";
import { pathToFileURL } from "node:url";
import assert from "node:assert/strict";
const { loadPyodide } = await import(pathToFileURL(process.argv[2]).href);
const py = await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL("../dist/reasitic.zip",import.meta.url))),"zip");
py.runPython("from reasitic.bridge import request_json");
const call=py.globals.get("request_json");
function request(data) {
  const result=JSON.parse(call(JSON.stringify(data)));
  if(result.error)throw new Error(result.error);
  return result.result;
}
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
const networkCases=JSON.parse(readFileSync(new URL("../tests/fixtures/network.json",import.meta.url))).cases;
for(const fixture of networkCases){
  const result=request({action:"pi2",kind:fixture.kind,parameters:fixture.parameters,technology:fixture.technology,
    frequency_hz:fixture.frequency_hz,mesh:fixture.mesh,ground:fixture.ground});
  for(const key of ["admittance_matrix","scattering_matrix"]){
    assert.equal(result[key].length,2);
    result[key].forEach((row,i)=>row.forEach((value,j)=>value.forEach((component,k)=>{
      const expected=fixture[key][i][j][k];
      assert.ok(Math.abs(component-expected)<=Math.max(1e-10,Math.abs(expected)*1e-8),`PI2 ${fixture.process} ${fixture.kind} ${key} [${i},${j}]`);
    })));
  }
  assert.equal(result.eddy,false);
  assert.ok(Number.isFinite(result.pi.q_first));
  assert.ok(Number.isFinite(result.pi.inductance_h));
  if(fixture.kind==="wire" && !fixture.ground)assert.equal(result.pi.shunt_differential_ohm,null);
}
console.log("Eight native distributed Pi2 Y/S matrices passed in WebAssembly.");
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
call.destroy();
console.log("Pinned Pyodide archive smoke test passed.");
