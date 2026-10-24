// Direct-script / next-command preparation in the continuous complete heap.
import{readFileSync,writeFileSync}from'node:fs';import{gunzipSync}from'node:zlib';import{pathToFileURL}from'node:url';
import{installNumericalKernels}from'../web/numeric-kernels.mjs';
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL('../dist/reasitic.zip',import.meta.url))),'zip');
await installNumericalKernels(py,readFileSync(new URL('../dist/numeric.wasm',import.meta.url)));
py.FS.mkdirTree('/driver/tests/fixtures');py.FS.mkdirTree('/driver/tools');
const names=new Set(['command_transition_original.json.gz','command_transition_extended_original.json.gz','node_history_original.json.gz','node_history_extended_original.json.gz','console_storage_original.json.gz','console_storage_extended_original.json.gz','driver_history_original.json.gz','driver_history_extended_original.json.gz','cache_storage_original.json.gz','cache_storage_extended_original.json.gz']);
for(const name of [...names]){
 const fixture=JSON.parse(gunzipSync(readFileSync(new URL('../tests/fixtures/'+name,import.meta.url))));
 for(const parent of Object.keys(fixture.parents))names.add(parent);
}
for(const name of names)py.FS.writeFile('/driver/tests/fixtures/'+name,readFileSync(new URL('../tests/fixtures/'+name,import.meta.url)));
for(const name of ['port_timestamp_writers_original.json','command_catalog_reference.inc'])py.FS.writeFile('/driver/tests/fixtures/'+name,readFileSync(new URL('../tests/fixtures/'+name,import.meta.url)));
for(const name of['audit_command_transition_original','capture_command_transition_original','capture_command_transition_extended_original','audit_node_history_original','capture_node_history_original','capture_node_history_extended_original','audit_console_storage_original','capture_console_storage_original','capture_console_storage_extended_original','audit_driver_history_original','audit_storage_history_original','audit_cache_storage_original','audit_cap_storage_original','audit_libio_storage_original','audit_geometry_setup_original','audit_contact_storage_original','audit_shared_heap_original','audit_cap_prelude_original','audit_allocator_original','project_prelude_storage_original','capture_driver_history_original','capture_driver_history_extended_original','capture_cache_storage_original','capture_libio_storage_original','capture_workspace_storage_original','capture_prelude_storage_original','capture_prelude_storage_extended_original','capture_geometry_setup_original','capture_allocator_original','capture_mapping_allocator_original','capture_cap_prelude_original','capture_trailing_via_heap_original','capture_original_symmetric'])py.FS.writeFile('/driver/tools/'+name+'.py',readFileSync(new URL('../tools/'+name+'.py',import.meta.url)));
py.FS.writeFile('/driver/tests/test_command_transition_original.py',readFileSync(new URL('../tests/test_command_transition_original.py',import.meta.url)));
let status;
try{status=py.runPython(`
import sys,unittest
sys.path[:0]=['/driver/tools','/driver/tests']
from reasitic.table_kernel import _compiled_samples
assert _compiled_samples is not None
from audit_command_transition_original import main
from test_command_transition_original import CommandTransitionTests
assert unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(CommandTransitionTests)).wasSuccessful()
status=0
for name in ('command_transition_original','command_transition_extended_original'):
    sys.argv=['audit_command_transition_original','--fixture','/driver/tests/fixtures/'+name+'.json.gz','--output','/driver/'+name+'-audit.json']
    try:main()
    except SystemExit as error:status|=error.code
status
`);}catch(error){console.error(String(error));process.exit(1);}
for(const[i,name]of['command_transition_original','command_transition_extended_original'].entries())if(process.argv[i+3])writeFileSync(process.argv[i+3],py.FS.readFile('/driver/'+name+'-audit.json'));
process.exitCode=Number(status);
