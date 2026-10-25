// Complete independent stat/allocation caller operations and native assertions.
import{readFileSync,readdirSync,writeFileSync}from'node:fs';import{gunzipSync}from'node:zlib';import{pathToFileURL}from'node:url';
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL('../dist/reasitic.zip',import.meta.url))),'zip');
py.FS.mkdirTree('/filealloc/tools');py.FS.mkdirTree('/filealloc/tests/fixtures');
const fixture=JSON.parse(gunzipSync(readFileSync(new URL('../tests/fixtures/file_allocation_original.json.gz',import.meta.url))));
for(const name of new Set(['file_allocation_original.json.gz','square_original.json','unjoin_sessions_original.json.gz',...Object.keys(fixture.parents)]))py.FS.writeFile('/filealloc/tests/fixtures/'+name,readFileSync(new URL('../tests/fixtures/'+name,import.meta.url)));
for(const name of readdirSync(new URL('.',import.meta.url)).filter(n=>n.endsWith('.py')))py.FS.writeFile('/filealloc/tools/'+name,readFileSync(new URL(name,import.meta.url)));
py.FS.writeFile('/filealloc/tests/test_file_allocation_original.py',readFileSync(new URL('../tests/test_file_allocation_original.py',import.meta.url)));
let status;
try{status=py.runPython(`
import sys,unittest
sys.path[:0]=['/filealloc/tools','/filealloc/tests']
from test_file_allocation_original import FileAllocationTests
from audit_file_allocation_original import main
assert unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(FileAllocationTests)).wasSuccessful()
sys.argv=['audit_file_allocation_original','--output','/filealloc/report.json']
try:main()
except SystemExit as error:status=error.code
status
`);}catch(error){console.error(String(error));process.exit(1);}
if(process.argv[3])writeFileSync(process.argv[3],py.FS.readFile('/filealloc/report.json'));
process.exitCode=Number(status);
