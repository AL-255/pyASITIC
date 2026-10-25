// All independently captured integer instructions/flags through the actual flow.
import{readFileSync,writeFileSync}from'node:fs';import{pathToFileURL}from'node:url';
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL('../dist/reasitic.zip',import.meta.url))),'zip');
const root='/printf-instruction-flags';py.FS.mkdirTree(root+'/tools');py.FS.mkdirTree(root+'/tests/fixtures');
for(const name of['capture_printf_integer_flags_native.py','audit_printf_integer_flags_native.py','lift_printf_fp_original.py'])py.FS.writeFile(root+'/tools/'+name,readFileSync(new URL(name,import.meta.url)));
py.FS.writeFile(root+'/tests/fixtures/printf_integer_flags_native.json.gz',readFileSync(new URL('../tests/fixtures/printf_integer_flags_native.json.gz',import.meta.url)));
py.FS.writeFile(root+'/tests/test_printf_integer_flags_native.py',readFileSync(new URL('../tests/test_printf_integer_flags_native.py',import.meta.url)));
// The provenance test reads source directly as well as its installed package.
py.FS.mkdirTree(root+'/src/reasitic');py.FS.writeFile(root+'/src/reasitic/printf_fp_program.json',readFileSync(new URL('../src/reasitic/printf_fp_program.json',import.meta.url)));
let passed;
try{passed=py.runPython(`
import os,sys,unittest
sys.path[:0]=['${root}/tools','${root}/tests']
os.environ['PYASITIC_PRINTF_INSTRUCTION_FLAGS_REPORT']='${root}/report.json'
import test_printf_integer_flags_native as tests
unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(tests)).wasSuccessful()
`);}catch(error){console.error(String(error));process.exit(1);}
if(process.argv[3])writeFileSync(process.argv[3],py.FS.readFile(root+'/report.json'));
process.exitCode=passed?0:1;
