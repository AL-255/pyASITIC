// Earlier contact/cache allocator state, carried through both regenerated matrices.
import{readFileSync,writeFileSync}from'node:fs';import{gunzipSync}from'node:zlib';import{pathToFileURL}from'node:url';
import{installNumericalKernels}from'../web/numeric-kernels.mjs';
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL('../dist/reasitic.zip',import.meta.url))),'zip');
await installNumericalKernels(py,readFileSync(new URL('../dist/numeric.wasm',import.meta.url)));
py.FS.mkdirTree('/prelude/tests/fixtures');py.FS.mkdirTree('/prelude/tools');
const names=new Set(['cap_prelude_original.json.gz','cap_prelude_shared_original.json.gz','cap_prelude_modes_original.json.gz','contact_storage_original.json.gz','allocator_mappings_original.json.gz','shared_heap_original.json.gz']);
for(const name of ['cap_prelude_original.json.gz','cap_prelude_shared_original.json.gz']){
 const fixture=JSON.parse(gunzipSync(readFileSync(new URL('../tests/fixtures/'+name,import.meta.url))));
 for(const parent of Object.keys(fixture.parents))names.add(parent);
}
for(const name of names)py.FS.writeFile('/prelude/tests/fixtures/'+name,readFileSync(new URL('../tests/fixtures/'+name,import.meta.url)));
for(const name of['capture_allocator_original','capture_mapping_allocator_original','capture_shared_memory_original','capture_cap_prelude_original','capture_cap_prelude_shared_original','capture_cap_prelude_modes_original','capture_contact_storage_original','capture_trailing_via_heap_original','capture_original_symmetric','audit_cap_prelude_original','audit_cap_prelude_shared_original','audit_contact_storage_original','audit_cache_stores_original','audit_shared_heap_original','audit_allocator_original'])py.FS.writeFile('/prelude/tools/'+name+'.py',readFileSync(new URL('../tools/'+name+'.py',import.meta.url)));
for(const name of['test_cap_prelude_original','test_contact_storage_original','test_cache_stores_original'])py.FS.writeFile('/prelude/tests/'+name+'.py',readFileSync(new URL('../tests/'+name+'.py',import.meta.url)));
py.runPython(`
import sys,unittest
sys.path[:0]=['/prelude/tests','/prelude/tools']
from reasitic.filament import _compiled_filaments
assert _compiled_filaments is not None
from test_cap_prelude_original import CapPreludeTests
from test_contact_storage_original import ContactStorageTests
from test_cache_stores_original import CacheStoreTests
assert unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(cls)for cls in (CapPreludeTests,ContactStorageTests,CacheStoreTests))).wasSuccessful()
`);
const contactStatus=py.runPython(`
sys.argv=['audit_contact_storage_original','--output','/prelude/contact-storage-audit.json']
from audit_contact_storage_original import main as contact_main
contact_status=0
try:contact_main()
except SystemExit as error:contact_status=error.code
contact_status
`);
const status=py.runPython(`
sys.argv=['audit_cap_prelude_shared_original','--ported','--output','/prelude/audit.json']
from audit_cap_prelude_shared_original import main
status=0
try:main()
except SystemExit as error:status=error.code
status
`);
if(process.argv[3])writeFileSync(process.argv[3],py.FS.readFile('/prelude/audit.json'));
if(process.argv[4])writeFileSync(process.argv[4],py.FS.readFile('/prelude/contact-storage-audit.json'));
process.exitCode=Math.max(Number(status),Number(contactStatus));
