// Every captured UNJOIN upper entry, using the actual packaged compiled path.
import{readFileSync,writeFileSync}from'node:fs';import{pathToFileURL}from'node:url';
import{gunzipSync}from'node:zlib';import{installNumericalKernels}from'../web/numeric-kernels.mjs';
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL('../dist/reasitic.zip',import.meta.url))),'zip');
await installNumericalKernels(py,readFileSync(new URL('../dist/numeric.wasm',import.meta.url)));
const root='/unjoin-assembly';py.FS.mkdirTree(root+'/tools');py.FS.mkdirTree(root+'/tests/fixtures');
const fixture=readFileSync(new URL('../tests/fixtures/unjoin_assembly_original.json.gz',import.meta.url));
const traces=readFileSync(new URL('../tests/fixtures/unjoin_mutual_traces_original.json.gz',import.meta.url));
for(const name of new Set(['unjoin_assembly_original.json.gz','unjoin_mutual_traces_original.json.gz',...Object.keys(JSON.parse(gunzipSync(fixture)).parents),...Object.keys(JSON.parse(gunzipSync(traces)).parents)]))py.FS.writeFile(root+'/tests/fixtures/'+name,readFileSync(new URL('../tests/fixtures/'+name,import.meta.url)));
// Capture modules are imported only to assert provenance; native binaries do
// not execute in the browser and their outputs never enter the runtime package.
for(const name of['capture_unjoin_assembly_original','capture_impedance_original','capture_original_symmetric','capture_trailing_via_heap_original','capture_unjoin_mutual_traces_original','capture_mutual_command_traces_original','audit_unjoin_assembly_original','audit_mutual_command_traces_original'])py.FS.writeFile(root+'/tools/'+name+'.py',readFileSync(new URL(name+'.py',import.meta.url)));
py.FS.writeFile(root+'/tests/test_unjoin_assembly_original.py',readFileSync(new URL('../tests/test_unjoin_assembly_original.py',import.meta.url)));
const passed=py.runPython(`
import json,sys,unittest
from pathlib import Path
sys.path[:0]=['${root}/tools','${root}/tests']
from reasitic.impedance import _compiled_assembly
from reasitic.mutual_kernel import _compiled_mutual
assert _compiled_assembly is not None and _compiled_mutual is not None
from test_unjoin_assembly_original import UnjoinAssemblyTests
from audit_unjoin_assembly_original import compare_model,compare_traces,run
passed=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(UnjoinAssemblyTests)).wasSuccessful()
report=run(UnjoinAssemblyTests.fixture);report['traces']=compare_traces(UnjoinAssemblyTests.traces)
report['model']=compare_model(UnjoinAssemblyTests.model,next(c for c in UnjoinAssemblyTests.fixture['cases']if c['label']==UnjoinAssemblyTests.model['label']))
Path('${root}/report.json').write_text(json.dumps(report,indent=2)+'\\n')
passed
`);
if(process.argv[3])writeFileSync(process.argv[3],py.FS.readFile(root+'/report.json'));
process.exitCode=passed?0:1;
