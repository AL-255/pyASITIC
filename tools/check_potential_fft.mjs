// Exact native FFT output checks in the deployable WebAssembly source archive.
// Usage: node tools/check_potential_fft.mjs /absolute/path/to/pyodide.mjs
import {readFileSync} from "node:fs";
import {pathToFileURL} from "node:url";
import assert from "node:assert/strict";
import {installNumericalKernels} from "../web/numeric-kernels.mjs";
const {loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL("../dist/reasitic.zip",import.meta.url))),"zip");
await installNumericalKernels(py,readFileSync(new URL("../dist/numeric.wasm",import.meta.url)));
py.runPython(`
import json
from reasitic.potential import _fft,_transform_grid
from reasitic.fft import _compiled_transform
assert _compiled_transform is not None
def potential_fft_probe(payload):
    c=json.loads(payload);values=[complex(*z) for z in c["input"]]
    if c["grid"]:_transform_grid(values,c["nx"],c["ny"])
    else:_fft(values)
    return json.dumps([[z.real,z.imag] for z in values],allow_nan=False)
`);
function nativeJSON(value){
  if(typeof value==="number"&&Object.is(value,-0))return "-0.0";
  if(Array.isArray(value))return "["+value.map(nativeJSON).join(",")+"]";
  if(value&&typeof value==="object")return "{"+Object.entries(value).map(([key,v])=>JSON.stringify(key)+":"+nativeJSON(v)).join(",")+"}";
  return JSON.stringify(value);
}
const probe=py.globals.get("potential_fft_probe");
const cases=JSON.parse(readFileSync(new URL("../tests/fixtures/potential_fft.json",import.meta.url))).cases;
let components=0;
for(const [i,c] of cases.entries()){
  const actual=JSON.parse(probe(nativeJSON(c)));
  assert.deepEqual(actual,c.output,`Native FFT bits ${i}: ${c.nx}×${c.ny}, grid=${c.grid}`);
  components+=2*c.output.length;
}
probe.destroy();
console.log(`${cases.length} native potential FFT/grid cases passed exactly in WebAssembly (${components} binary64 components, including signed zeros and subnormals).`);
py.runPython(`
from reasitic.x87_math import cosh_argument,tanh_argument,_native_cosh,_native_tanh
assert _native_cosh is not None and _native_tanh is not None
def potential_math_probe(kind,payload):
    values=json.loads(payload)
    return cosh_argument(1.,float(values),0.) if kind=="cosh" else tanh_argument(*values)
`);
const mathProbe=py.globals.get("potential_math_probe");
const scalarCases=JSON.parse(readFileSync(new URL("../tests/fixtures/potential_math.json",import.meta.url)));
for(const [kind,rows] of [["cosh",scalarCases.cosh],["tanh",scalarCases.tanh]]){
  for(const [input,expected] of rows)assert.equal(mathProbe(kind,nativeJSON(input)),Number(expected),`Original ${kind} ${input}`);
}
mathProbe.destroy();
console.log(`${scalarCases.cosh.length+scalarCases.tanh.length} original-binary cosh/tanh cases passed bit for bit in compiled WebAssembly.`);
