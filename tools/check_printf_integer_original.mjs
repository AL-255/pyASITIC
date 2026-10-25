// All independent native int32 outputs through the Python source in Pyodide.
import{readFileSync,readdirSync,writeFileSync}from'node:fs';import{createHash}from'node:crypto';import{pathToFileURL}from'node:url';import assert from'node:assert/strict';
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL('../dist/reasitic.zip',import.meta.url))),'zip');
py.FS.mkdirTree('/printf-integer/tools');py.FS.mkdirTree('/printf-integer/tests/fixtures');
const fixture=JSON.parse(readFileSync(new URL('../tests/fixtures/printf_format_original.manifest.json',import.meta.url))),digest=createHash('sha256');let bytes=0;
for(const part of fixture.parts){const data=readFileSync(new URL('../tests/fixtures/'+part.file,import.meta.url));assert.equal(data.length,part.bytes);assert.equal(createHash('sha256').update(data).digest('hex'),part.sha256);digest.update(data);bytes+=data.length;py.FS.writeFile('/printf-integer/tests/fixtures/'+part.file,data);}
assert.equal(bytes,fixture.bytes);assert.equal(digest.digest('hex'),fixture.sha256);
for(const name of['printf_format_original.manifest.json','printf_integer_original.json.gz'])py.FS.writeFile('/printf-integer/tests/fixtures/'+name,readFileSync(new URL('../tests/fixtures/'+name,import.meta.url)));
for(const name of readdirSync(new URL('.',import.meta.url)).filter(n=>n.endsWith('.py')))py.FS.writeFile('/printf-integer/tools/'+name,readFileSync(new URL(name,import.meta.url)));
py.FS.writeFile('/printf-integer/tests/test_printf_integer_original.py',readFileSync(new URL('../tests/test_printf_integer_original.py',import.meta.url)));
let passed;
try{passed=py.runPython(`
import os,sys,unittest
sys.path[:0]=['/printf-integer/tools','/printf-integer/tests']
os.environ['PYASITIC_PRINTF_INTEGER_REPORT']='/printf-integer/report.json'
import test_printf_integer_original as tests
unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(tests)).wasSuccessful()
`);}catch(error){console.error(String(error));process.exit(1);}
if(process.argv[3])writeFileSync(process.argv[3],py.FS.readFile('/printf-integer/report.json'));
process.exitCode=passed?0:1;
