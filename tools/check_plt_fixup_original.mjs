// Original lazy PLT caller, symbol lookup, IFUNC and complete target entry.
import{readFileSync,readdirSync,writeFileSync}from'node:fs';import{gunzipSync}from'node:zlib';import{pathToFileURL}from'node:url';
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL('../dist/reasitic.zip',import.meta.url))),'zip');
py.FS.mkdirTree('/plt/tools');py.FS.mkdirTree('/plt/tests/fixtures');
const fixture=JSON.parse(gunzipSync(readFileSync(new URL('../tests/fixtures/plt_fixup_original.json.gz',import.meta.url))));
const names=new Set(['plt_fixup_original.json.gz','square_original.json','unjoin_sessions_original.json.gz',...Object.keys(fixture.parents)]);
for(const name of names)py.FS.writeFile('/plt/tests/fixtures/'+name,readFileSync(new URL('../tests/fixtures/'+name,import.meta.url)));
for(const name of readdirSync(new URL('.',import.meta.url)).filter(n=>n.endsWith('.py')))py.FS.writeFile('/plt/tools/'+name,readFileSync(new URL(name,import.meta.url)));
py.FS.writeFile('/plt/tests/test_plt_fixup_original.py',readFileSync(new URL('../tests/test_plt_fixup_original.py',import.meta.url)));
let status;
try{status=py.runPython(`
import sys,unittest
sys.path[:0]=['/plt/tools','/plt/tests']
from test_plt_fixup_original import PltFixupTests
from audit_plt_fixup_original import main
assert unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(PltFixupTests)).wasSuccessful()
sys.argv=['audit_plt_fixup_original','--output','/plt/report.json']
try:main()
except SystemExit as error:status=error.code
status
`);}catch(error){console.error(String(error));process.exit(1);}
if(process.argv[3])writeFileSync(process.argv[3],py.FS.readFile('/plt/report.json'));
process.exitCode=Number(status);
