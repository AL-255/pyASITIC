// Earlier strcmp lazy binding -> complete native target and capacitor phase.
import{readFileSync,readdirSync,writeFileSync}from'node:fs';import{gunzipSync}from'node:zlib';import{pathToFileURL}from'node:url';
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL('../dist/reasitic.zip',import.meta.url))),'zip');
const root='/phase-origin';py.FS.mkdirTree(root+'/tools');py.FS.mkdirTree(root+'/tests/fixtures');
const fixture=JSON.parse(gunzipSync(readFileSync(new URL('../tests/fixtures/phase_origin_original.json.gz',import.meta.url))));
for(const name of new Set(['phase_origin_original.json.gz',...Object.keys(fixture.parents)]))py.FS.writeFile(root+'/tests/fixtures/'+name,readFileSync(new URL('../tests/fixtures/'+name,import.meta.url)));
for(const name of readdirSync(new URL('.',import.meta.url)).filter(n=>n.endsWith('.py')))py.FS.writeFile(root+'/tools/'+name,readFileSync(new URL(name,import.meta.url)));
py.FS.writeFile(root+'/tests/test_phase_origin_original.py',readFileSync(new URL('../tests/test_phase_origin_original.py',import.meta.url)));
const passed=py.runPython(`
import json,sys,unittest
from pathlib import Path
sys.path[:0]=['${root}/tools','${root}/tests']
from test_phase_origin_original import PhaseOriginTests
from audit_phase_origin_original import run
passed=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(PhaseOriginTests)).wasSuccessful()
report=run(PhaseOriginTests.fixture)
Path('${root}/report.json').write_text(json.dumps(report,indent=2)+'\\n')
passed and not report['differences']
`);
if(process.argv[3])writeFileSync(process.argv[3],py.FS.readFile(root+'/report.json'));
process.exitCode=passed?0:1;
