// Packaged Python allocator and strict native physical-placement comparison.
import{readFileSync}from'node:fs';import{gunzipSync}from'node:zlib';import{pathToFileURL}from'node:url';
import{installNumericalKernels}from'../web/numeric-kernels.mjs';
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL('../dist/reasitic.zip',import.meta.url))),'zip');
await installNumericalKernels(py,readFileSync(new URL('../dist/numeric.wasm',import.meta.url)));
py.FS.mkdirTree('/heap/tests/fixtures');py.FS.mkdirTree('/heap/tools');
const data=readFileSync(new URL('../tests/fixtures/allocator_state_original.json.gz',import.meta.url)),fixture=JSON.parse(gunzipSync(data));
py.FS.writeFile('/heap/tests/fixtures/allocator_state_original.json.gz',data);
for(const name of['trailing_via_heap_original.json.gz',...Object.keys(fixture.parents)])py.FS.writeFile('/heap/tests/fixtures/'+name,readFileSync(new URL('../tests/fixtures/'+name,import.meta.url)));
for(const name of['capture_allocator_original','capture_trailing_via_heap_original','capture_original_symmetric','audit_allocator_original','audit_trailing_via_heap'])py.FS.writeFile('/heap/tools/'+name+'.py',readFileSync(new URL('../tools/'+name+'.py',import.meta.url)));
py.FS.writeFile('/heap/tests/test_heap_original.py',readFileSync(new URL('../tests/test_heap_original.py',import.meta.url)));
py.runPython(`
import sys,unittest
sys.path[:0]=['/heap/tests','/heap/tools']
from reasitic.filament import _compiled_filaments
assert _compiled_filaments is not None
from test_heap_original import OriginalHeapTests
assert unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(OriginalHeapTests)).wasSuccessful()
`);
console.log('Packaged allocator provenance and all 130 supported-prefix comparisons passed. Running the full strict placement audit; mmap and native damaged lists remain required.');
const status=py.runPython(`
sys.argv=['audit_allocator_original']
from audit_allocator_original import main
status=0
try:main()
except SystemExit as error:status=error.code
status
`);
process.exitCode=Number(status);
