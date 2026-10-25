// Complete select64/VDSO states and independent edge cases on Pages Python.
import{readFileSync,readdirSync,writeFileSync}from'node:fs';import{gunzipSync}from'node:zlib';import{pathToFileURL}from'node:url';
import{installNumericalKernels}from'../web/numeric-kernels.mjs';
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL('../dist/reasitic.zip',import.meta.url))),'zip');
await installNumericalKernels(py,readFileSync(new URL('../dist/numeric.wasm',import.meta.url)));
const root='/select-dispatch';py.FS.mkdirTree(root+'/tools');py.FS.mkdirTree(root+'/tests/fixtures');
const names=new Set(['select_dispatch_original.json.gz','select_dispatch_probe.json.gz','printf_transition_original.json.gz','square_original.json','unjoin_sessions_original.json.gz']);
for(const file of ['select_dispatch_original.json.gz','printf_transition_original.json.gz']){const f=JSON.parse(gunzipSync(readFileSync(new URL('../tests/fixtures/'+file,import.meta.url))));for(const name of Object.keys(f.parents))names.add(name);}
for(const name of names)py.FS.writeFile(root+'/tests/fixtures/'+name,readFileSync(new URL('../tests/fixtures/'+name,import.meta.url)));
for(const name of readdirSync(new URL('.',import.meta.url)).filter(n=>n.endsWith('.py')))py.FS.writeFile(root+'/tools/'+name,readFileSync(new URL(name,import.meta.url)));
py.FS.writeFile(root+'/tests/test_select_dispatch_original.py',readFileSync(new URL('../tests/test_select_dispatch_original.py',import.meta.url)));
let passed;
try{passed=py.runPython(`
import gzip,json,sys,unittest
from pathlib import Path
sys.path[:0]=['${root}/tools','${root}/tests']
from test_select_dispatch_original import SelectDispatchTests
from audit_select_dispatch_original import run
from audit_poll_storage_original import compare
passed=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(SelectDispatchTests)).wasSuccessful()
f=SelectDispatchTests.fixture
Path('${root}/report.json').write_text(json.dumps(run(f),indent=2)+'\\n')
f=SelectDispatchTests.probe;c=f['cases'][0]
report=compare(f,c,phases=[('dispatch','entry','after')])
helpers=dict(c,poll_calls=[dict(call,syscall=call['after'])for call in c['poll_calls']if call['boundary']=='syscall'])
report['helper_report']=compare(f,helpers,phases=[('syscall','syscall','vdso')])
Path('${root}/probe-report.json').write_text(json.dumps(report,indent=2)+'\\n')
passed
`);}catch(error){console.error(String(error));process.exit(1);}
if(process.argv[3]){writeFileSync(process.argv[3],py.FS.readFile(root+'/report.json'));writeFileSync(process.argv[3]+'.probe.json',py.FS.readFile(root+'/probe-report.json'));}
process.exitCode=passed?0:1;
