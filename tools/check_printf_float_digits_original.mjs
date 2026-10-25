// Decimal text/extraction component only. Complete native ABI gates stay separate.
import{readFileSync,writeFileSync}from'node:fs';import{pathToFileURL}from'node:url';
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL('../dist/reasitic.zip',import.meta.url))),'zip');
const root='/printf-float-digits';py.FS.mkdirTree(root+'/tools');py.FS.mkdirTree(root+'/tests/fixtures');
for(const name of['capture_printf_integer_original.py','capture_printf_float_digits_original.py','audit_printf_float_digits_original.py'])py.FS.writeFile(root+'/tools/'+name,readFileSync(new URL(name,import.meta.url)));
py.FS.writeFile(root+'/tests/fixtures/printf_float_digits_original.json.gz',readFileSync(new URL('../tests/fixtures/printf_float_digits_original.json.gz',import.meta.url)));
py.FS.writeFile(root+'/tests/test_printf_float_digits_original.py',readFileSync(new URL('../tests/test_printf_float_digits_original.py',import.meta.url)));
let passed;
try{passed=py.runPython(`
import os,sys,unittest
sys.path[:0]=['${root}/tools','${root}/tests']
os.environ['PYASITIC_PRINTF_FLOAT_DIGITS_REPORT']='${root}/report.json'
import test_printf_float_digits_original as tests
unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(tests)).wasSuccessful()
`);}catch(error){console.error(String(error));process.exit(1);}
if(process.argv[3])writeFileSync(process.argv[3],py.FS.readFile(root+'/report.json'));
process.exitCode=passed?0:1;
