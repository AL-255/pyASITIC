// All continuing stdin histories and targets. Unfinished differences stay failures.
import{readFileSync,readdirSync,writeFileSync}from'node:fs';import{gunzipSync}from'node:zlib';import{pathToFileURL}from'node:url';
import{installNumericalKernels}from'../web/numeric-kernels.mjs';
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL('../dist/reasitic.zip',import.meta.url))),'zip');
await installNumericalKernels(py,readFileSync(new URL('../dist/numeric.wasm',import.meta.url)));
py.FS.mkdirTree('/input/tools');py.FS.mkdirTree('/input/tests/fixtures');
const fixture=JSON.parse(gunzipSync(readFileSync(new URL('../tests/fixtures/input_transition_original.json.gz',import.meta.url))));
const names=new Set(['input_transition_original.json.gz','plt_fixup_original.json.gz','square_original.json','unjoin_sessions_original.json.gz','stdio_transition_original.json.gz',...Object.keys(fixture.parents)]);
for(const name of names)py.FS.writeFile('/input/tests/fixtures/'+name,readFileSync(new URL('../tests/fixtures/'+name,import.meta.url)));
for(const name of readdirSync(new URL('.',import.meta.url)).filter(n=>n.endsWith('.py')))py.FS.writeFile('/input/tools/'+name,readFileSync(new URL(name,import.meta.url)));
py.FS.writeFile('/input/tests/test_input_transition_original.py',readFileSync(new URL('../tests/test_input_transition_original.py',import.meta.url)));
let status;
try{status=py.runPython(`
import sys,unittest
sys.path[:0]=['/input/tools','/input/tests']
from test_input_transition_original import InputTransitionTests
from audit_command_transition_original import main
assert unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(InputTransitionTests)).wasSuccessful()
sys.argv=['audit_command_transition_original','--fixture','/input/tests/fixtures/input_transition_original.json.gz','--output','/input/report.json']
try:main()
except SystemExit as error:status=error.code
status
`);}catch(error){console.error(String(error));process.exit(1);}
if(process.argv[3])writeFileSync(process.argv[3],py.FS.readFile('/input/report.json'));
process.exitCode=Number(status);
