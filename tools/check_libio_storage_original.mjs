// Complete pre-CAP storage replay with earlier libio/cache header inputs.
import{readFileSync,writeFileSync}from'node:fs';import{gunzipSync}from'node:zlib';import{pathToFileURL}from'node:url';
import{installNumericalKernels}from'../web/numeric-kernels.mjs';
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL('../dist/reasitic.zip',import.meta.url))),'zip');
await installNumericalKernels(py,readFileSync(new URL('../dist/numeric.wasm',import.meta.url)));
py.FS.mkdirTree('/libio/tests/fixtures');py.FS.mkdirTree('/libio/tools');
const names=new Set(['libio_storage_original.json.gz','libio_storage_extended_original.json.gz','libio_binding_ambiguous_original.json.gz','libio_binding_pilot_original.json.gz','prelude_storage_original.json.gz','prelude_storage_extended_original.json.gz']);
for(const name of [...names]){
 const fixture=JSON.parse(gunzipSync(readFileSync(new URL('../tests/fixtures/'+name,import.meta.url))));
 for(const parent of Object.keys(fixture.parents))names.add(parent);
}
for(const name of names)py.FS.writeFile('/libio/tests/fixtures/'+name,readFileSync(new URL('../tests/fixtures/'+name,import.meta.url)));
for(const name of['audit_geometry_setup_original','audit_contact_storage_original','audit_shared_heap_original','audit_cap_prelude_original','audit_allocator_original','project_prelude_storage_original','audit_libio_storage_original','capture_libio_storage_original','capture_geometry_setup_original','capture_prelude_storage_original','capture_prelude_storage_extended_original','capture_cap_prelude_original','capture_allocator_original','capture_mapping_allocator_original','capture_trailing_via_heap_original','capture_original_symmetric'])py.FS.writeFile('/libio/tools/'+name+'.py',readFileSync(new URL('../tools/'+name+'.py',import.meta.url)));
py.FS.writeFile('/libio/tests/test_libio_storage_original.py',readFileSync(new URL('../tests/test_libio_storage_original.py',import.meta.url)));
let status;
try{status=py.runPython(`
import sys,unittest,json
sys.path[:0]=['/libio/tools','/libio/tests']
from reasitic.table_kernel import _compiled_tables
assert _compiled_tables is not None
from audit_libio_storage_original import main
from test_libio_storage_original import LibioStorageTests
assert unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(LibioStorageTests)).wasSuccessful()
status=0
for name in ('libio_storage_original','libio_storage_extended_original'):
    sys.argv=['audit_libio_storage_original','--fixture','/libio/tests/fixtures/'+name+'.json.gz','--output','/libio/'+name+'-audit.json']
    try:main()
    except SystemExit as error:status|=error.code
# Earlier ambiguous GDB inputs must fail exactly at every FILE chain word.
# Never repair those explicit caller values from a later observed FILE record.
sys.argv=['audit_libio_storage_original','--fixture','/libio/tests/fixtures/libio_binding_ambiguous_original.json.gz','--output','/libio/binding-audit.json']
try:main()
except SystemExit as error:assert error.code==1
else:assert False,'The wrong symbol input was silently accepted'
binding=json.load(open('/libio/binding-audit.json'))
assert binding['differences']==195
assert all(d['kind']=='bytes'and d['offset']==52 and d['name'].endswith('.file')for r in binding['results']for d in r['differences'])
status
`);}catch(error){console.error(String(error));process.exit(1);}
for(const [i,name]of['libio_storage_original','libio_storage_extended_original','binding'].entries())if(process.argv[i+3])writeFileSync(process.argv[i+3],py.FS.readFile('/libio/'+name+'-audit.json'));
process.exitCode=Number(status);
