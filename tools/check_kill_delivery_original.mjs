// Once-initialized native kill -> handler on the packaged Pages Python.
import{readFileSync,readdirSync,writeFileSync}from'node:fs';import{gunzipSync}from'node:zlib';import{pathToFileURL}from'node:url';
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL('../dist/reasitic.zip',import.meta.url))),'zip');
const root='/kill-delivery';py.FS.mkdirTree(root+'/tools');py.FS.mkdirTree(root+'/tests/fixtures');
const fixture=JSON.parse(gunzipSync(readFileSync(new URL('../tests/fixtures/kill_delivery_original.json.gz',import.meta.url))));
for(const name of new Set(['kill_delivery_original.json.gz','square_original.json','unjoin_sessions_original.json.gz',...Object.keys(fixture.parents)]))py.FS.writeFile(root+'/tests/fixtures/'+name,readFileSync(new URL('../tests/fixtures/'+name,import.meta.url)));
for(const name of readdirSync(new URL('.',import.meta.url)).filter(n=>n.endsWith('.py')))py.FS.writeFile(root+'/tools/'+name,readFileSync(new URL(name,import.meta.url)));
py.FS.writeFile(root+'/tests/test_kill_delivery_original.py',readFileSync(new URL('../tests/test_kill_delivery_original.py',import.meta.url)));
let passed;
try{passed=py.runPython(`
import json,sys,unittest
from pathlib import Path
sys.path[:0]=['${root}/tools','${root}/tests']
from test_kill_delivery_original import KillDeliveryTests
from audit_kill_delivery_original import run
passed=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(KillDeliveryTests)).wasSuccessful()
Path('${root}/report.json').write_text(json.dumps(run(KillDeliveryTests.fixture),indent=2)+'\\n')
passed
`);}catch(error){console.error(String(error));process.exit(1);}
if(process.argv[3])writeFileSync(process.argv[3],py.FS.readFile(root+'/report.json'));
process.exitCode=passed?0:1;
