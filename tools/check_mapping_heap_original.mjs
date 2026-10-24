// Actual packaged Python mmap allocator, historical inputs and native probes.
import{readFileSync}from'node:fs';import{gunzipSync}from'node:zlib';import{pathToFileURL}from'node:url';
import{installNumericalKernels}from'../web/numeric-kernels.mjs';
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL('../dist/reasitic.zip',import.meta.url))),'zip');
await installNumericalKernels(py,readFileSync(new URL('../dist/numeric.wasm',import.meta.url)));
py.FS.mkdirTree('/mapping/tests/fixtures');py.FS.mkdirTree('/mapping/tools');
const fixture=JSON.parse(gunzipSync(readFileSync(new URL('../tests/fixtures/allocator_mappings_original.json.gz',import.meta.url))));
for(const name of['allocator_mappings_original.json.gz','mmap_sequences_native.json.gz','allocator_state_original.json.gz','trailing_via_heap_original.json.gz',...Object.keys(fixture.parents)])py.FS.writeFile('/mapping/tests/fixtures/'+name,readFileSync(new URL('../tests/fixtures/'+name,import.meta.url)));
for(const name of['capture_allocator_original','capture_mapping_allocator_original','capture_mmap_sequences_native','capture_trailing_via_heap_original','capture_original_symmetric','audit_allocator_original','audit_trailing_via_heap'])py.FS.writeFile('/mapping/tools/'+name+'.py',readFileSync(new URL('../tools/'+name+'.py',import.meta.url)));
py.FS.writeFile('/mapping/tests/test_mapping_heap_original.py',readFileSync(new URL('../tests/test_mapping_heap_original.py',import.meta.url)));
py.runPython(`
import sys,unittest
sys.path[:0]=['/mapping/tests','/mapping/tools']
from reasitic.filament import _compiled_filaments
assert _compiled_filaments is not None
import test_mapping_heap_original
assert unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(test_mapping_heap_original)).wasSuccessful()
`);
console.log('Packaged mmap allocator matches all 3,117 ASITIC allocation addresses and 58 independent native history events. Running strict audit; native damaged lists remain required.');
const status=py.runPython(`
sys.argv=['audit_allocator_original','--fixture','/mapping/tests/fixtures/allocator_mappings_original.json.gz']
from audit_allocator_original import main
status=0
try:main()
except SystemExit as error:status=error.code
status
`);
process.exitCode=Number(status);
