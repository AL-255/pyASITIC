// Actual packaged runtime, unchanged native histories, all strict targets retained.
import{readFileSync,readdirSync,writeFileSync}from'node:fs';
import{gunzipSync}from'node:zlib';import{pathToFileURL}from'node:url';
import{installNumericalKernels}from'../web/numeric-kernels.mjs';
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL('../dist/reasitic.zip',import.meta.url))),'zip');
await installNumericalKernels(py,readFileSync(new URL('../dist/numeric.wasm',import.meta.url)));
const root='/shunt-exit';py.FS.mkdirTree(root+'/tools');py.FS.mkdirTree(root+'/tests/fixtures');
const testsOnly=process.argv.includes('--tests-only');
const names=new Set(['shunt_exit_original.json.gz','shunt_cleanup_original.json.gz','shunt_malloc_original.json.gz','shunt_repl_original.json.gz','shunt_shutdown_original.json.gz','shunt_port_tail_original.json.gz','shunt_node_history_original.json.gz','shunt_second_driver_original.json.gz']);
// External banks are complete byte dictionaries, not captures with parent fields.
for(const name of [...names]){
 const raw=readFileSync(new URL('../tests/fixtures/'+name,import.meta.url));
 const f=JSON.parse(gunzipSync(raw));
 for(const parent of Object.keys(f.parents??{}))names.add(parent);
 for(const info of Object.values(f.external_banks??{}))names.add(info.file);
}
for(const name of names)py.FS.writeFile(root+'/tests/fixtures/'+name,readFileSync(new URL('../tests/fixtures/'+name,import.meta.url)));
for(const name of readdirSync(new URL('.',import.meta.url)).filter(n=>n.endsWith('.py')))py.FS.writeFile(root+'/tools/'+name,readFileSync(new URL(name,import.meta.url)));
py.FS.writeFile(root+'/tests/test_shunt_exit_original.py',readFileSync(new URL('../tests/test_shunt_exit_original.py',import.meta.url)));
const status=py.runPython(`
import sys,json,unittest
from pathlib import Path
sys.path[:0]=['${root}/tools','${root}/tests']
from reasitic.linear import _compiled_general
assert _compiled_general is not None
from audit_shunt_exit_original import run
from test_shunt_exit_original import ShuntExitTests
passed=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ShuntExitTests)).wasSuccessful()
report=run(ShuntExitTests.fixture) if not ${testsOnly?'True':'False'} else dict(tests_only=True)
Path('${root}/report.json').write_text(json.dumps(report,indent=2)+'\\n')
int(bool(report.get('differences',0))or not passed)
`);
if(process.argv[3]&&!process.argv[3].startsWith('--'))writeFileSync(process.argv[3],py.FS.readFile(root+'/report.json'));
process.exitCode=Number(status);
