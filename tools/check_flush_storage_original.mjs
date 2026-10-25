// Every native successful fflush region, register, FP byte and write effect.
import{readFileSync,readdirSync,writeFileSync}from'node:fs';import{gunzipSync}from'node:zlib';import{pathToFileURL}from'node:url';
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL('../dist/reasitic.zip',import.meta.url))),'zip');
py.FS.mkdirTree('/flush/tools');py.FS.mkdirTree('/flush/tests/fixtures');
const fixture=JSON.parse(gunzipSync(readFileSync(new URL('../tests/fixtures/flush_storage_original.json.gz',import.meta.url))));
for(const name of new Set(['flush_storage_original.json.gz','square_original.json','unjoin_sessions_original.json.gz',...Object.keys(fixture.parents)]))py.FS.writeFile('/flush/tests/fixtures/'+name,readFileSync(new URL('../tests/fixtures/'+name,import.meta.url)));
for(const name of readdirSync(new URL('.',import.meta.url)).filter(n=>n.endsWith('.py')))py.FS.writeFile('/flush/tools/'+name,readFileSync(new URL(name,import.meta.url)));
py.FS.writeFile('/flush/tests/test_flush_storage_original.py',readFileSync(new URL('../tests/test_flush_storage_original.py',import.meta.url)));
let status;
try{status=py.runPython(`
import sys,unittest
sys.path[:0]=['/flush/tools','/flush/tests']
from test_flush_storage_original import FlushStorageTests
from audit_flush_storage_original import main
assert unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(FlushStorageTests)).wasSuccessful()
sys.argv=['audit_flush_storage_original','--output','/flush/report.json']
try:main()
except SystemExit as error:status=error.code
status
`);}catch(error){console.error(String(error));process.exit(1);}
if(process.argv[3])writeFileSync(process.argv[3],py.FS.readFile('/flush/report.json'));
process.exitCode=Number(status);
