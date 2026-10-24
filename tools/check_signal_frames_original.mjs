// Independent Linux/i386 signal ABI, using earlier CPU and stack inputs only.
import{readFileSync,readdirSync,writeFileSync}from'node:fs';import{gunzipSync}from'node:zlib';import{pathToFileURL}from'node:url';
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL('../dist/reasitic.zip',import.meta.url))),'zip');
py.FS.mkdirTree('/signals/tools');py.FS.mkdirTree('/signals/tests/fixtures');
const fixture=JSON.parse(gunzipSync(readFileSync(new URL('../tests/fixtures/signal_frames_original.json.gz',import.meta.url))));
const names=new Set(['signal_frames_original.json.gz','square_original.json','unjoin_sessions_original.json.gz',...Object.keys(fixture.parents)]);
for(const name of names)py.FS.writeFile('/signals/tests/fixtures/'+name,readFileSync(new URL('../tests/fixtures/'+name,import.meta.url)));
for(const name of readdirSync(new URL('.',import.meta.url)).filter(n=>n.endsWith('.py')))py.FS.writeFile('/signals/tools/'+name,readFileSync(new URL(name,import.meta.url)));
py.FS.writeFile('/signals/tests/test_signal_frames_original.py',readFileSync(new URL('../tests/test_signal_frames_original.py',import.meta.url)));
let status;
try{status=py.runPython(`
import sys,unittest
sys.path[:0]=['/signals/tools','/signals/tests']
from test_signal_frames_original import SignalFrameTests
from audit_signal_frames_original import main
assert unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(SignalFrameTests)).wasSuccessful()
sys.argv=['audit_signal_frames_original','--output','/signals/report.json']
try:main()
except SystemExit as error:status=error.code
status
`);}catch(error){console.error(String(error));process.exit(1);}
if(process.argv[3])writeFileSync(process.argv[3],py.FS.readFile('/signals/report.json'));
process.exitCode=Number(status);
