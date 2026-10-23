// Exact original transfer/regional kernels and complete generated tables.
import {readFileSync} from "node:fs";
import {pathToFileURL} from "node:url";
import assert from "node:assert/strict";
import {installNumericalKernels} from "../web/numeric-kernels.mjs";
const {loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL("../dist/reasitic.zip",import.meta.url))),"zip");
await installNumericalKernels(py,readFileSync(new URL("../dist/numeric.wasm",import.meta.url)));
py.runPython(`
import json,hashlib,struct
from array import array
from reasitic.table_kernel import configuration,generate_tables,_compiled_tables
from _reasitic_numeric import spectral_probe
assert _compiled_tables is not None

def spectral_check(payload):
    c=json.loads(payload);coefficients=[complex(float(z[0]),float(z[1])) for z in c["coefficients"]];depths=[float(v) for v in c["depths"]]
    config=configuration(c["source"],c["target"],c["nx"],c["ny"],c["width"],c["height"],c["metals"],coefficients,depths)
    before=config.tobytes();assert hashlib.sha256(before).hexdigest()==c["input_sha256"],"Original spectral input bits differ"
    if "requests" in c:
        values=[]
        for kind,source,target,last,k,sh,th in c["requests"]:
            output=array("d",[0.])*(len(coefficients)+3)
            assert spectral_probe(config,output,kind,source,target,last,float(k),float(sh),float(th))==0
            assert output[2:].tobytes()==array("d",depths).tobytes(),"Compiled source helper did not restore native depth bits"
            values.extend(output[:2])
    else:
        tables=generate_tables(c["source"],c["target"],c["nx"],c["ny"],c["width"],c["height"],c["metals"],coefficients,depths)
        values=[v for table in tables for z in table for v in (z.real,z.imag)]
    assert config.tobytes()==before,"Spectral input metadata changed"
    binary=array("d",values).tobytes()
    return json.dumps(dict(sha256=hashlib.sha256(binary).hexdigest())) if "output_sha256" in c else json.dumps([binary[i:i+8].hex() for i in range(0,len(binary),8)])
`);
function nativeJSON(value){
  if(typeof value==="number"&&Object.is(value,-0))return "-0.0";
  if(Array.isArray(value))return "["+value.map(nativeJSON).join(",")+"]";
  if(value&&typeof value==="object")return "{"+Object.entries(value).map(([k,v])=>JSON.stringify(k)+":"+nativeJSON(v)).join(",")+"}";
  return JSON.stringify(value);
}
const fixture=JSON.parse(readFileSync(new URL("../tests/fixtures/spectral.json",import.meta.url))),probe=py.globals.get("spectral_check");
let components=0;
for(const [index,c] of [...fixture.scalar,...fixture.tables].entries()){
  const actual=JSON.parse(probe(nativeJSON(c)));
  if(c.output_sha256){assert.equal(actual.sha256,c.output_sha256,`Original complete table bits ${index}: ${c.nx}×${c.ny} pair ${c.source},${c.target}`);components+=2*(2*c.nx+2*c.ny+Math.max((c.nx+1)*(c.ny+1),c.nx*(c.nx+1)+c.ny+1));continue;}
  assert.equal(actual.length,c.output.length);
  for(const [i,expected] of c.output.entries()){
    const bytes=Buffer.from(actual[i],"hex"),value=bytes.readDoubleLE();
    if(expected==="nan")assert.ok(Number.isNaN(value),`Original spectral NaN ${index} component ${i}`);
    else if(expected==="inf"||expected==="-inf")assert.equal(value,expected==="inf"?Infinity:-Infinity,`Original spectral infinity ${index} component ${i}`);
    else{const target=Buffer.alloc(8);target.writeDoubleLE(expected);assert.equal(bytes.toString("hex"),target.toString("hex"),`Original spectral finite bits ${index} component ${i}`);}
    components++;
  }
}
assert.equal(components,fixture.components);probe.destroy();
console.log(`${fixture.scalar.reduce((n,c)=>n+c.requests.length,0)} original transfer/regional calls and ${fixture.tables.length} complete tables passed (${components} output components), finite bits and nonfinite classifications, including rectangular and 256×256 tables.`);
py.runPython(`
from reasitic.table_kernel import _coefficient_records,_compiled_coefficients
assert _compiled_coefficients is not None
def coefficient_probe(payload):
    c=json.loads(payload)
    zs=_coefficient_records([(float(r),float(e)) for r,e in c["records"]],float(c["frequency"]))
    return json.dumps([struct.pack("<d",v).hex() for z in zs for v in (z.real,z.imag)])
`);
const coefficients=JSON.parse(readFileSync(new URL("../tests/fixtures/layer_coefficients.json",import.meta.url))),coefficientProbe=py.globals.get("coefficient_probe");
for(const [index,c] of coefficients.cases.entries()){
  const actual=JSON.parse(coefficientProbe(nativeJSON(c)));
  assert.equal(actual.length,c.output.length);
  for(const [i,expected] of c.output.entries()){
    const bytes=Buffer.from(actual[i],"hex"),value=bytes.readDoubleLE();
    if(expected==="nan")assert.ok(Number.isNaN(value),`Original coefficient NaN ${index} component ${i}`);
    else if(expected==="inf"||expected==="-inf")assert.equal(value,expected==="inf"?Infinity:-Infinity);
    else{const target=Buffer.alloc(8);target.writeDoubleLE(expected);assert.equal(bytes.toString("hex"),target.toString("hex"),`Original coefficient bits ${index} component ${i}`);}
  }
}
coefficientProbe.destroy();
console.log(`${coefficients.cases.length} original CAP coefficient groups passed (${coefficients.components} exact finite components/nonfinite classifications), including native scalar division and frequency-weight rounding.`);
