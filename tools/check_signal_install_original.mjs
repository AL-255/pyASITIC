// Native signal-wrapper ABI; every return byte comes from earlier call state.
import{readFileSync,readdirSync,writeFileSync}from'node:fs';import{gunzipSync}from'node:zlib';import{pathToFileURL}from'node:url';
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL('../dist/reasitic.zip',import.meta.url))),'zip');
py.FS.mkdirTree('/install/tools');py.FS.mkdirTree('/install/tests/fixtures');
const fixture=JSON.parse(gunzipSync(readFileSync(new URL('../tests/fixtures/signal_install_original.json.gz',import.meta.url))));
const names=new Set(['signal_install_original.json.gz','square_original.json','unjoin_sessions_original.json.gz',...Object.keys(fixture.parents)]);
for(const name of names)py.FS.writeFile('/install/tests/fixtures/'+name,readFileSync(new URL('../tests/fixtures/'+name,import.meta.url)));
for(const name of readdirSync(new URL('.',import.meta.url)).filter(n=>n.endsWith('.py')))py.FS.writeFile('/install/tools/'+name,readFileSync(new URL(name,import.meta.url)));
py.FS.writeFile('/install/tests/test_signal_install_original.py',readFileSync(new URL('../tests/test_signal_install_original.py',import.meta.url)));
let status;
try{status=py.runPython(`
import sys,unittest
sys.path[:0]=['/install/tools','/install/tests']
from test_signal_install_original import SignalInstallTests
from audit_signal_install_original import main
assert unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(SignalInstallTests)).wasSuccessful()
sys.argv=['audit_signal_install_original','--output','/install/report.json']
try:main()
except SystemExit as error:status=error.code
status
`);}catch(error){console.error(String(error));process.exit(1);}
if(process.argv[3])writeFileSync(process.argv[3],py.FS.readFile('/install/report.json'));
process.exitCode=Number(status);
