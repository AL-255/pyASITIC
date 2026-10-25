// All independently captured x87 formatter instruction states in Pyodide.
import{readFileSync,writeFileSync}from'node:fs';import{pathToFileURL}from'node:url';
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL('../dist/reasitic.zip',import.meta.url))),'zip');
const root='/x87-formatter-state';py.FS.mkdirTree(root+'/tools');py.FS.mkdirTree(root+'/tests/fixtures');
for(const name of['capture_x87_formatter_instructions_native.py','audit_x87_formatter_instructions_native.py'])py.FS.writeFile(root+'/tools/'+name,readFileSync(new URL(name,import.meta.url)));
py.FS.writeFile(root+'/tests/fixtures/x87_formatter_instructions_native.json.gz',readFileSync(new URL('../tests/fixtures/x87_formatter_instructions_native.json.gz',import.meta.url)));
py.FS.writeFile(root+'/tests/test_x87_formatter_instructions_native.py',readFileSync(new URL('../tests/test_x87_formatter_instructions_native.py',import.meta.url)));
let passed;
try{passed=py.runPython(`
import os,sys,unittest
sys.path[:0]=['${root}/tools','${root}/tests']
os.environ['PYASITIC_X87_FORMAT_STATE_REPORT']='${root}/report.json'
import test_x87_formatter_instructions_native as tests
unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(tests)).wasSuccessful()
`);}catch(error){console.error(String(error));process.exit(1);}
if(process.argv[3])writeFileSync(process.argv[3],py.FS.readFile(root+'/report.json'));
process.exitCode=passed?0:1;
