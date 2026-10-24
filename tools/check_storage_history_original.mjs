// Continuous source stores from earlier free-heap bytes, no via-entry seed.
import{readFileSync,writeFileSync}from'node:fs';import{pathToFileURL}from'node:url';
import{installNumericalKernels}from'../web/numeric-kernels.mjs';
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL('../dist/reasitic.zip',import.meta.url))),'zip');
await installNumericalKernels(py,readFileSync(new URL('../dist/numeric.wasm',import.meta.url)));
py.FS.mkdirTree('/history/tests/fixtures');py.FS.mkdirTree('/history/tools');
for(const name of['cap_prelude_shared_original.json.gz','initial_storage_memory_original.json.gz'])py.FS.writeFile('/history/tests/fixtures/'+name,readFileSync(new URL('../tests/fixtures/'+name,import.meta.url)));
for(const name of['audit_allocator_original','audit_cap_prelude_original','audit_cap_storage_original','audit_contact_storage_original','audit_shared_heap_original','audit_storage_history_original','project_initial_storage_memory_original'])py.FS.writeFile('/history/tools/'+name+'.py',readFileSync(new URL('../tools/'+name+'.py',import.meta.url)));
py.FS.writeFile('/history/tests/test_storage_history_original.py',readFileSync(new URL('../tests/test_storage_history_original.py',import.meta.url)));
let status;
try{status=py.runPython(`
import sys,unittest
sys.path[:0]=['/history/tools','/history/tests']
from reasitic.linear import _compiled_general
assert _compiled_general is not None
from test_storage_history_original import StorageHistoryTests
assert unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(StorageHistoryTests)).wasSuccessful()
sys.argv=['audit_storage_history_original','--output','/history/audit.json']
from audit_storage_history_original import main
status=0
try:main()
except SystemExit as error:status=error.code
status
`);}catch(error){console.error(String(error));process.exit(1);}
if(process.argv[3])writeFileSync(process.argv[3],py.FS.readFile('/history/audit.json'));
process.exitCode=Number(status);
