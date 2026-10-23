// Complete original filament records through the shipped Python batch bridge.
import {readFileSync} from "node:fs";
import {pathToFileURL} from "node:url";
import {installNumericalKernels} from "../web/numeric-kernels.mjs";
const {loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL("../dist/reasitic.zip",import.meta.url))),"zip");
await installNumericalKernels(py,readFileSync(new URL("../dist/numeric.wasm",import.meta.url)));
py.globals.set("fixture_text",readFileSync(new URL("../tests/fixtures/filaments.json",import.meta.url),"utf8"));
py.runPython(`
import json,struct,math,copy
from array import array
from reasitic.filament import filament_records,_compiled_filaments
assert _compiled_filaments is not None
fixture=json.loads(fixture_text);records=[c['input'] for c in fixture['cases']];before=copy.deepcopy(records)
actual=filament_records(records)
assert actual and len(actual)==len(records) and records==before
for i,(row,c) in enumerate(zip(actual,fixture['cases'])):
 assert len(row)==9
 for j,(value,bits) in enumerate(zip(row,c['output_bits'])):
  expected=struct.unpack('<d',bytes.fromhex(bits))[0]
  assert math.isnan(value) if math.isnan(expected) else struct.pack('<d',value).hex()==bits,(i,j,value,expected)
for data,output in [(array('d',[0.]),array('d',[0.])*9),(array('d',records[0]),array('d',[0.]))]:
 try:_compiled_filaments(data,output)
 except Exception:pass
 else:raise AssertionError('Invalid filament buffer accepted')
print(len(actual),'original filament records passed:',len(actual)*9,'exact finite components/nonfinite classifications, all adaptive edge branches and immutable inputs.')
`);
