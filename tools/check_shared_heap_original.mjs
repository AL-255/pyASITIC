// Real packaged byte-backed cache + via formulas; full native reinversion.
import{readFileSync,writeFileSync}from'node:fs';import{gunzipSync}from'node:zlib';import{pathToFileURL}from'node:url';
import{installNumericalKernels}from'../web/numeric-kernels.mjs';
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL('../dist/reasitic.zip',import.meta.url))),'zip');
await installNumericalKernels(py,readFileSync(new URL('../dist/numeric.wasm',import.meta.url)));
py.FS.mkdirTree('/shared/tests/fixtures');py.FS.mkdirTree('/shared/tools');
const fixture=JSON.parse(gunzipSync(readFileSync(new URL('../tests/fixtures/shared_heap_original.json.gz',import.meta.url))));
for(const name of['shared_heap_original.json.gz','allocator_mappings_original.json.gz','vias_original.json',...Object.keys(fixture.parents)])py.FS.writeFile('/shared/tests/fixtures/'+name,readFileSync(new URL('../tests/fixtures/'+name,import.meta.url)));
for(const name of['capture_allocator_original','capture_mapping_allocator_original','capture_shared_memory_original','capture_trailing_via_heap_original','capture_original_symmetric','audit_shared_heap_original','audit_allocator_original'])py.FS.writeFile('/shared/tools/'+name+'.py',readFileSync(new URL('../tools/'+name+'.py',import.meta.url)));
py.FS.writeFile('/shared/tests/test_shared_heap_original.py',readFileSync(new URL('../tests/test_shared_heap_original.py',import.meta.url)));
py.runPython(`
import sys,unittest
sys.path[:0]=['/shared/tests','/shared/tools']
from reasitic.filament import _compiled_filaments
assert _compiled_filaments is not None
from test_shared_heap_original import SharedHeapTests
assert unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(SharedHeapTests)).wasSuccessful()
`);
const status=py.runPython(`
sys.argv=['audit_shared_heap_original','--inverse','--ported-cap',*(['--ported-ind']if ${process.argv.includes('--ported-ind')?'True':'False'} else []),'--output','/shared/audit.json']
from audit_shared_heap_original import main
status=0
try:main()
except SystemExit as error:status=error.code
status
`);
process.exitCode=Number(status);
const outputPath=process.argv.slice(3).find(value=>!value.startsWith('--'));
if(outputPath)writeFileSync(outputPath,py.FS.readFile('/shared/audit.json'));
