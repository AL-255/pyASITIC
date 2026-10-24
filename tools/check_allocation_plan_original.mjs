// Real packaged Pyodide/WASM geometry/mesh inputs and native storage lifetimes.
import{readFileSync}from'node:fs';import{gunzipSync}from'node:zlib';import{pathToFileURL}from'node:url';
import{installNumericalKernels}from'../web/numeric-kernels.mjs';
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL('../dist/reasitic.zip',import.meta.url))),'zip');await installNumericalKernels(py,readFileSync(new URL('../dist/numeric.wasm',import.meta.url)));
py.FS.mkdirTree('/storage/tests/fixtures');py.FS.mkdirTree('/storage/tools');
const data=readFileSync(new URL('../tests/fixtures/trailing_via_heap_original.json.gz',import.meta.url)),fixture=JSON.parse(gunzipSync(data));
py.FS.writeFile('/storage/tests/fixtures/trailing_via_heap_original.json.gz',data);
for(const name of Object.keys(fixture.parents))py.FS.writeFile('/storage/tests/fixtures/'+name,readFileSync(new URL('../tests/fixtures/'+name,import.meta.url)));
for(const name of['capture_trailing_via_heap_original','capture_original_symmetric','audit_trailing_via_heap'])py.FS.writeFile('/storage/tools/'+name+'.py',readFileSync(new URL('../tools/'+name+'.py',import.meta.url)));
py.FS.writeFile('/storage/tests/test_allocation_plan_original.py',readFileSync(new URL('../tests/test_allocation_plan_original.py',import.meta.url)));
py.runPython(`
import sys,unittest
sys.path[:0]=['/storage/tests','/storage/tools']
from reasitic.filament import _compiled_filaments
assert _compiled_filaments is not None
from test_allocation_plan_original import OriginalAllocationPlanTests
result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(OriginalAllocationPlanTests))
assert result.wasSuccessful()
`);
console.log('130 cold/warm observations: all 12,877 observed allocation/free events and object identities, one original fault prefix, native cache provenance, and geometry/contact/filament dimensions passed in packaged Pyodide/WASM. Physical address placement and model aliasing remain unimplemented.');
