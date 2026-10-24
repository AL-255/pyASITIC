// Native pre-CAP FFT scratch and stream-buffer stores in the packaged solver.
import{readFileSync,writeFileSync}from'node:fs';import{gunzipSync}from'node:zlib';import{pathToFileURL}from'node:url';
import{installNumericalKernels}from'../web/numeric-kernels.mjs';
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL('../dist/reasitic.zip',import.meta.url))),'zip');
await installNumericalKernels(py,readFileSync(new URL('../dist/numeric.wasm',import.meta.url)));
py.FS.mkdirTree('/prestorage/tests/fixtures');py.FS.mkdirTree('/prestorage/tools');
const names=new Set(['prelude_storage_original.json.gz','prelude_storage_extended_original.json.gz','geometry_setup_original.json.gz']);
for(const name of [...names]){
 const fixture=JSON.parse(gunzipSync(readFileSync(new URL('../tests/fixtures/'+name,import.meta.url))));
 for(const parent of Object.keys(fixture.parents))names.add(parent);
}
for(const name of names)py.FS.writeFile('/prestorage/tests/fixtures/'+name,readFileSync(new URL('../tests/fixtures/'+name,import.meta.url)));
for(const name of['capture_allocator_original','capture_mapping_allocator_original','capture_cap_prelude_original','capture_trailing_via_heap_original','capture_original_symmetric','capture_geometry_setup_original','capture_prelude_storage_original','capture_prelude_storage_extended_original','project_prelude_storage_original','audit_allocator_original','audit_cap_prelude_original','audit_prelude_storage_original'])py.FS.writeFile('/prestorage/tools/'+name+'.py',readFileSync(new URL('../tools/'+name+'.py',import.meta.url)));
py.FS.writeFile('/prestorage/tests/test_prelude_storage_original.py',readFileSync(new URL('../tests/test_prelude_storage_original.py',import.meta.url)));
let status;
try{status=py.runPython(`
import sys,unittest
sys.path[:0]=['/prestorage/tools','/prestorage/tests']
from reasitic.table_kernel import _compiled_tables
assert _compiled_tables is not None
from test_prelude_storage_original import PreludeStorageTests
assert unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(PreludeStorageTests)).wasSuccessful()
from audit_prelude_storage_original import main
status=0
for name in ('prelude_storage_original','prelude_storage_extended_original'):
    sys.argv=['audit_prelude_storage_original','--fixture','/prestorage/tests/fixtures/'+name+'.json.gz','--output','/prestorage/'+name+'-audit.json']
    try:main()
    except SystemExit as error:status|=error.code
status
`);}catch(error){console.error(String(error));process.exit(1);}
for(const [i,name]of['prelude_storage_original','prelude_storage_extended_original'].entries())if(process.argv[i+3])writeFileSync(process.argv[i+3],py.FS.readFile('/prestorage/'+name+'-audit.json'));
process.exitCode=Number(status);
