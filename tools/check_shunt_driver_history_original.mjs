// Actual shared-memory cache, numerical and console driver in packaged Pyodide.
import{readFileSync,readdirSync,writeFileSync}from'node:fs';import{gunzipSync}from'node:zlib';import{pathToFileURL}from'node:url';
import{installNumericalKernels}from'../web/numeric-kernels.mjs';
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL('../dist/reasitic.zip',import.meta.url))),'zip');await installNumericalKernels(py,readFileSync(new URL('../dist/numeric.wasm',import.meta.url)));
const root='/shunt-driver';py.FS.mkdirTree(root+'/tools');py.FS.mkdirTree(root+'/tests/fixtures');
const names=new Set(['shunt_driver_history_original.json.gz','shunt_filament_storage_original.json.gz']);
for(const name of [...names]){const f=JSON.parse(gunzipSync(readFileSync(new URL('../tests/fixtures/'+name,import.meta.url))));for(const parent of Object.keys(f.parents))names.add(parent);}
for(const name of names)py.FS.writeFile(root+'/tests/fixtures/'+name,readFileSync(new URL('../tests/fixtures/'+name,import.meta.url)));
for(const name of readdirSync(new URL('.',import.meta.url)).filter(n=>n.endsWith('.py')))py.FS.writeFile(root+'/tools/'+name,readFileSync(new URL(name,import.meta.url)));
py.FS.writeFile(root+'/tests/test_shunt_driver_history_original.py',readFileSync(new URL('../tests/test_shunt_driver_history_original.py',import.meta.url)));
const status=py.runPython(`
import sys,json,gzip,unittest
from pathlib import Path
sys.path[:0]=['${root}/tools','${root}/tests']
from reasitic.table_kernel import _compiled_samples
assert _compiled_samples is not None
from audit_shunt_driver_history_original import run
from test_shunt_driver_history_original import ShuntDriverHistoryTests
passed=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ShuntDriverHistoryTests)).wasSuccessful()
fixture=json.loads(gzip.decompress(Path('${root}/tests/fixtures/shunt_driver_history_original.json.gz').read_bytes()))
report=run(fixture)
Path('${root}/report.json').write_text(json.dumps(report,indent=2)+'\\n')
int(bool(report['differences'])or not passed)
`);
if(process.argv[3])writeFileSync(process.argv[3],py.FS.readFile(root+'/report.json'));
process.exitCode=Number(status);
