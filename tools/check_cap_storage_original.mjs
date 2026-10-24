// Every source-generated CAP buffer, at predicted native guest allocations.
import{readFileSync,writeFileSync}from'node:fs';import{gunzipSync}from'node:zlib';import{pathToFileURL}from'node:url';
import{installNumericalKernels}from'../web/numeric-kernels.mjs';
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL('../dist/reasitic.zip',import.meta.url))),'zip');
await installNumericalKernels(py,readFileSync(new URL('../dist/numeric.wasm',import.meta.url)));
py.FS.mkdirTree('/capstorage/tests/fixtures');py.FS.mkdirTree('/capstorage/tools');
const fixture=JSON.parse(gunzipSync(readFileSync(new URL('../tests/fixtures/cap_storage_original.json.gz',import.meta.url))));
for(const name of new Set(['cap_storage_original.json.gz','cap_prelude_original.json.gz',...Object.keys(fixture.parents)]))py.FS.writeFile('/capstorage/tests/fixtures/'+name,readFileSync(new URL('../tests/fixtures/'+name,import.meta.url)));
for(const name of['capture_allocator_original','capture_mapping_allocator_original','capture_cap_prelude_original','capture_cap_storage_original','capture_trailing_via_heap_original','capture_original_symmetric','audit_cap_prelude_original','audit_cap_storage_original','audit_shared_heap_original','audit_allocator_original'])py.FS.writeFile('/capstorage/tools/'+name+'.py',readFileSync(new URL('../tools/'+name+'.py',import.meta.url)));
py.FS.writeFile('/capstorage/tests/test_cap_storage_original.py',readFileSync(new URL('../tests/test_cap_storage_original.py',import.meta.url)));
py.runPython(`
import sys,unittest
sys.path[:0]=['/capstorage/tests','/capstorage/tools']
from reasitic.linear import _compiled_general
assert _compiled_general is not None
from test_cap_storage_original import CapStorageTests
assert unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(CapStorageTests)).wasSuccessful()
sys.argv=['audit_cap_storage_original','--output','/capstorage/audit.json']
`);
const status=py.runPython(`
from audit_cap_storage_original import main
status=0
try:main()
except SystemExit as error:status=error.code
status
`);
if(process.argv[3])writeFileSync(process.argv[3],py.FS.readFile('/capstorage/audit.json'));
process.exitCode=Number(status);
