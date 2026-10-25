// Native physical-segment arrays, complete lifetimes and shared branch stores.
import{readFileSync,readdirSync,writeFileSync}from'node:fs';import{gunzipSync}from'node:zlib';import{pathToFileURL}from'node:url';
import{installNumericalKernels}from'../web/numeric-kernels.mjs';
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL('../dist/reasitic.zip',import.meta.url))),'zip');await installNumericalKernels(py,readFileSync(new URL('../dist/numeric.wasm',import.meta.url)));
const root='/shunt-filaments';py.FS.mkdirTree(root+'/tools');py.FS.mkdirTree(root+'/tests/fixtures');
const names=new Set(['shunt_filament_storage_original.json.gz','shunt_geometry_storage_original.json.gz','shunt_sessions_original.json.gz','shunt_original.json.gz']);
for(const name of [...names]){const f=JSON.parse(gunzipSync(readFileSync(new URL('../tests/fixtures/'+name,import.meta.url))));for(const parent of Object.keys(f.parents))names.add(parent);}
for(const name of names)py.FS.writeFile(root+'/tests/fixtures/'+name,readFileSync(new URL('../tests/fixtures/'+name,import.meta.url)));
for(const name of readdirSync(new URL('.',import.meta.url)).filter(n=>n.endsWith('.py')))py.FS.writeFile(root+'/tools/'+name,readFileSync(new URL(name,import.meta.url)));
py.FS.writeFile(root+'/tests/test_shunt_filament_storage_original.py',readFileSync(new URL('../tests/test_shunt_filament_storage_original.py',import.meta.url)));
const passed=py.runPython(`
import json,sys,unittest
from pathlib import Path
sys.path[:0]=['${root}/tools','${root}/tests']
from reasitic.impedance import _compiled_assembly
assert _compiled_assembly is not None
from test_shunt_filament_storage_original import ShuntFilamentStorageTests
from audit_shunt_filament_storage_original import run
passed=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ShuntFilamentStorageTests)).wasSuccessful()
report=run(ShuntFilamentStorageTests.fixture)
Path('${root}/report.json').write_text(json.dumps(report,indent=2)+'\\n')
passed and not report['differences']
`);
if(process.argv[3])writeFileSync(process.argv[3],py.FS.readFile(root+'/report.json'));
process.exitCode=passed?0:1;
