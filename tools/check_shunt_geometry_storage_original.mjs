// Secondary geometry bytes and consecutive commands on the actual source heap.
import{readFileSync,readdirSync,writeFileSync}from'node:fs';import{gunzipSync}from'node:zlib';import{pathToFileURL}from'node:url';
import{installNumericalKernels}from'../web/numeric-kernels.mjs';
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL('../dist/reasitic.zip',import.meta.url))),'zip');
await installNumericalKernels(py,readFileSync(new URL('../dist/numeric.wasm',import.meta.url)));
const root='/shunt-storage';py.FS.mkdirTree(root+'/tools');py.FS.mkdirTree(root+'/tests/fixtures');
const names=new Set(['shunt_geometry_storage_original.json.gz','shunt_dispatch_original.json.gz','shunt_original.json.gz','shunt_sessions_original.json.gz']);
for(const name of [...names]){const f=JSON.parse(gunzipSync(readFileSync(new URL('../tests/fixtures/'+name,import.meta.url))));for(const parent of Object.keys(f.parents))names.add(parent);}
for(const name of names)py.FS.writeFile(root+'/tests/fixtures/'+name,readFileSync(new URL('../tests/fixtures/'+name,import.meta.url)));
for(const name of readdirSync(new URL('.',import.meta.url)).filter(n=>n.endsWith('.py')))py.FS.writeFile(root+'/tools/'+name,readFileSync(new URL(name,import.meta.url)));
py.FS.writeFile(root+'/tests/test_shunt_geometry_storage_original.py',readFileSync(new URL('../tests/test_shunt_geometry_storage_original.py',import.meta.url)));
const passed=py.runPython(`
import json,sys,unittest
from pathlib import Path
sys.path[:0]=['${root}/tools','${root}/tests']
from reasitic.filament import _compiled_filaments
assert _compiled_filaments is not None
from test_shunt_geometry_storage_original import ShuntGeometryStorageTests
from audit_shunt_dispatch_original import run
from audit_geometry_setup_original import main
passed=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ShuntGeometryStorageTests)).wasSuccessful()
report=run(ShuntGeometryStorageTests.dispatch)
Path('${root}/dispatch-report.json').write_text(json.dumps(report,indent=2)+'\\n')
sys.argv=['audit_geometry_setup_original','--fixture','${root}/tests/fixtures/shunt_geometry_storage_original.json.gz','--output','${root}/setup-report.json']
try:main()
except SystemExit as error:passed=passed and not error.code
passed and not report['differences']
`);
for(const[i,name]of['setup-report','dispatch-report'].entries())if(process.argv[i+3])writeFileSync(process.argv[i+3],py.FS.readFile(root+'/'+name+'.json'));
process.exitCode=passed?0:1;
