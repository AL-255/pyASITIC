// Real printf continuation on the exact Pages source; no later-state inputs.
import{readFileSync,readdirSync,writeFileSync}from'node:fs';import{gunzipSync}from'node:zlib';import{pathToFileURL}from'node:url';import assert from'node:assert/strict';
import{installNumericalKernels}from'../web/numeric-kernels.mjs';
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL('../dist/reasitic.zip',import.meta.url))),'zip');
await installNumericalKernels(py,readFileSync(new URL('../dist/numeric.wasm',import.meta.url)));
const root='/printf-transition';py.FS.mkdirTree(root+'/tools');py.FS.mkdirTree(root+'/tests/fixtures');
const fixture=JSON.parse(gunzipSync(readFileSync(new URL('../tests/fixtures/printf_transition_original.json.gz',import.meta.url))));
const shard=Number(process.argv[4]??1),shards=Number(process.argv[5]??1);assert.ok(Number.isInteger(shard)&&Number.isInteger(shards)&&1<=shard&&shard<=shards&&shards<=fixture.cases.length);
const names=new Set(['printf_transition_original.json.gz','square_original.json','unjoin_sessions_original.json.gz',...Object.keys(fixture.parents)]);
for(const name of names)py.FS.writeFile(root+'/tests/fixtures/'+name,readFileSync(new URL('../tests/fixtures/'+name,import.meta.url)));
for(const name of readdirSync(new URL('.',import.meta.url)).filter(n=>n.endsWith('.py')))py.FS.writeFile(root+'/tools/'+name,readFileSync(new URL(name,import.meta.url)));
py.FS.writeFile(root+'/tests/test_printf_transition_original.py',readFileSync(new URL('../tests/test_printf_transition_original.py',import.meta.url)));
py.globals.set('printf_transition_shard',shard);py.globals.set('printf_transition_shards',shards);
let passed;
try{passed=py.runPython(`
import os,sys,unittest
sys.path[:0]=['${root}/tools','${root}/tests']
os.environ['PYASITIC_PRINTF_TRANSITION_SHARD']=str(printf_transition_shard)
os.environ['PYASITIC_PRINTF_TRANSITION_SHARDS']=str(printf_transition_shards)
os.environ['PYASITIC_PRINTF_TRANSITION_REPORT']='${root}/report.json'
from test_printf_transition_original import PrintfTransitionTests
unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(PrintfTransitionTests)).wasSuccessful()
`);}catch(error){console.error(String(error));process.exit(1);}
if(process.argv[3])writeFileSync(process.argv[3],py.FS.readFile(root+'/report.json'));
process.exitCode=passed?0:1;
