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
call.destroy();
console.log("Pinned Pyodide archive smoke test passed.");
