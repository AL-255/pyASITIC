// Both source solves, actual S record and fclose in one packaged guest memory.
import{readFileSync,readdirSync,writeFileSync}from'node:fs';import{gunzipSync}from'node:zlib';import{pathToFileURL}from'node:url';
import{installNumericalKernels}from'../web/numeric-kernels.mjs';
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL('../dist/reasitic.zip',import.meta.url))),'zip');await installNumericalKernels(py,readFileSync(new URL('../dist/numeric.wasm',import.meta.url)));
const root='/shunt-port-tail';py.FS.mkdirTree(root+'/tools');py.FS.mkdirTree(root+'/tests/fixtures');
const names=new Set(['shunt_port_tail_original.json.gz','shunt_node_history_original.json.gz','shunt_second_driver_original.json.gz']);
for(const name of [...names]){const f=JSON.parse(gunzipSync(readFileSync(new URL('../tests/fixtures/'+name,import.meta.url))));for(const parent of Object.keys(f.parents))names.add(parent);}
for(const name of names)py.FS.writeFile(root+'/tests/fixtures/'+name,readFileSync(new URL('../tests/fixtures/'+name,import.meta.url)));
for(const name of readdirSync(new URL('.',import.meta.url)).filter(n=>n.endsWith('.py')))py.FS.writeFile(root+'/tools/'+name,readFileSync(new URL(name,import.meta.url)));
py.FS.writeFile(root+'/tests/test_shunt_port_tail_original.py',readFileSync(new URL('../tests/test_shunt_port_tail_original.py',import.meta.url)));
const status=py.runPython(`
import sys,json,gzip,unittest
from pathlib import Path
sys.path[:0]=['${root}/tools','${root}/tests']
from reasitic.linear import _compiled_general
assert _compiled_general is not None
from audit_shunt_port_tail_original import run
from test_shunt_port_tail_original import ShuntPortTailTests
passed=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ShuntPortTailTests)).wasSuccessful()
fixture=json.loads(gzip.decompress(Path('${root}/tests/fixtures/shunt_port_tail_original.json.gz').read_bytes()))
report=run(fixture)
Path('${root}/report.json').write_text(json.dumps(report,indent=2)+'\\n')
int(bool(report['differences'])or not passed)
`);
if(process.argv[3])writeFileSync(process.argv[3],py.FS.readFile(root+'/report.json'));
process.exitCode=Number(status);
