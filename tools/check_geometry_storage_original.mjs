// Full native geometry bytes, pooled COPY names and continuous CAP placement.
import{readFileSync,writeFileSync}from'node:fs';import{gunzipSync}from'node:zlib';import{pathToFileURL}from'node:url';
import{installNumericalKernels}from'../web/numeric-kernels.mjs';
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL('../dist/reasitic.zip',import.meta.url))),'zip');
await installNumericalKernels(py,readFileSync(new URL('../dist/numeric.wasm',import.meta.url)));
py.FS.mkdirTree('/geometry/tests/fixtures');py.FS.mkdirTree('/geometry/tools');
const names=new Set(['geometry_setup_original.json.gz','geometry_setup_extended_original.json.gz','cap_prelude_original.json.gz']);
for(const name of [...names]){
 const fixture=JSON.parse(gunzipSync(readFileSync(new URL('../tests/fixtures/'+name,import.meta.url))));
 for(const parent of Object.keys(fixture.parents))names.add(parent);
}
for(const name of names)py.FS.writeFile('/geometry/tests/fixtures/'+name,readFileSync(new URL('../tests/fixtures/'+name,import.meta.url)));
for(const name of['capture_allocator_original','capture_mapping_allocator_original','capture_cap_prelude_original','capture_trailing_via_heap_original','capture_original_symmetric','capture_geometry_setup_original','capture_geometry_setup_extended_original','audit_allocator_original','audit_cap_prelude_original','audit_geometry_setup_original'])py.FS.writeFile('/geometry/tools/'+name+'.py',readFileSync(new URL('../tools/'+name+'.py',import.meta.url)));
py.FS.writeFile('/geometry/tests/test_geometry_storage_original.py',readFileSync(new URL('../tests/test_geometry_storage_original.py',import.meta.url)));
let status;
try{status=py.runPython(`
import sys,unittest
sys.path[:0]=['/geometry/tools','/geometry/tests']
from reasitic.filament import _compiled_filaments
assert _compiled_filaments is not None
from test_geometry_storage_original import GeometryStorageTests
assert unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(GeometryStorageTests)).wasSuccessful()
from audit_geometry_setup_original import main
status=0
for name in ('geometry_setup_original','geometry_setup_extended_original'):
    sys.argv=['audit_geometry_setup_original','--fixture','/geometry/tests/fixtures/'+name+'.json.gz','--output','/geometry/'+name+'-audit.json']
    try:main()
    except SystemExit as error:status|=error.code
status
`);}catch(error){console.error(String(error));process.exit(1);}
for(const [i,name]of['geometry_setup_original','geometry_setup_extended_original'].entries())if(process.argv[i+3])writeFileSync(process.argv[i+3],py.FS.readFile('/geometry/'+name+'-audit.json'));
process.exitCode=Number(status);
