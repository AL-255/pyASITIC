// Every native scalar getline search/copy region, register and FP byte.
import{readFileSync,readdirSync,writeFileSync}from'node:fs';import{gunzipSync}from'node:zlib';import{pathToFileURL}from'node:url';
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL('../dist/reasitic.zip',import.meta.url))),'zip');
py.FS.mkdirTree('/getline/tools');py.FS.mkdirTree('/getline/tests/fixtures');
const fixture=JSON.parse(gunzipSync(readFileSync(new URL('../tests/fixtures/getline_bytes_original.json.gz',import.meta.url))));
for(const name of new Set(['getline_bytes_original.json.gz','square_original.json','unjoin_sessions_original.json.gz',...Object.keys(fixture.parents)]))py.FS.writeFile('/getline/tests/fixtures/'+name,readFileSync(new URL('../tests/fixtures/'+name,import.meta.url)));
for(const name of readdirSync(new URL('.',import.meta.url)).filter(n=>n.endsWith('.py')))py.FS.writeFile('/getline/tools/'+name,readFileSync(new URL(name,import.meta.url)));
py.FS.writeFile('/getline/tests/test_getline_bytes_original.py',readFileSync(new URL('../tests/test_getline_bytes_original.py',import.meta.url)));
let status;
try{status=py.runPython(`
import sys,unittest
sys.path[:0]=['/getline/tools','/getline/tests']
from test_getline_bytes_original import GetlineBytesTests
from audit_getline_bytes_original import main
assert unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(GetlineBytesTests)).wasSuccessful()
sys.argv=['audit_getline_bytes_original','--output','/getline/report.json']
try:main()
except SystemExit as error:status=error.code
status
`);}catch(error){console.error(String(error));process.exit(1);}
if(process.argv[3])writeFileSync(process.argv[3],py.FS.readFile('/getline/report.json'));
process.exitCode=Number(status);
