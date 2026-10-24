import{readFileSync,writeFileSync}from'node:fs';import{gunzipSync}from'node:zlib';import{pathToFileURL}from'node:url';
import{installNumericalKernels}from'../web/numeric-kernels.mjs';
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL('../dist/reasitic.zip',import.meta.url))),'zip');
await installNumericalKernels(py,readFileSync(new URL('../dist/numeric.wasm',import.meta.url)));
py.FS.mkdirTree('/workspaces/tests/fixtures');py.FS.mkdirTree('/workspaces/tools');
const fixture=JSON.parse(gunzipSync(readFileSync(new URL('../tests/fixtures/workspace_storage_original.json.gz',import.meta.url))));
for(const name of new Set(['workspace_storage_original.json.gz','cap_prelude_original.json.gz',...Object.keys(fixture.parents)]))py.FS.writeFile('/workspaces/tests/fixtures/'+name,readFileSync(new URL('../tests/fixtures/'+name,import.meta.url)));
for(const name of['capture_allocator_original','capture_mapping_allocator_original','capture_cap_prelude_original','capture_workspace_storage_original','capture_trailing_via_heap_original','capture_original_symmetric','audit_allocator_original','audit_cap_prelude_original','audit_cap_storage_original','audit_shared_heap_original','audit_workspace_storage_original'])py.FS.writeFile('/workspaces/tools/'+name+'.py',readFileSync(new URL('../tools/'+name+'.py',import.meta.url)));
py.FS.writeFile('/workspaces/tests/test_workspace_storage_original.py',readFileSync(new URL('../tests/test_workspace_storage_original.py',import.meta.url)));
let status;
try{status=py.runPython(`
import sys,unittest
sys.path[:0]=['/workspaces/tools','/workspaces/tests']
from test_workspace_storage_original import WorkspaceStorageTests
assert unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(WorkspaceStorageTests)).wasSuccessful()
sys.argv=['audit_workspace_storage_original','--output','/workspaces/audit.json']
from audit_workspace_storage_original import main
status=0
try:main()
except SystemExit as error:status=error.code
status
`);}catch(error){console.error(String(error));process.exit(1);}
if(process.argv[3])writeFileSync(process.argv[3],py.FS.readFile('/workspaces/audit.json'));
process.exitCode=Number(status);
