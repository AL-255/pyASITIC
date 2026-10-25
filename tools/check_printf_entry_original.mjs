// Public printf entries through their real parent/formatter, with every target required.
import{readFileSync,readdirSync,writeFileSync}from'node:fs';import{createHash}from'node:crypto';import{pathToFileURL,fileURLToPath}from'node:url';import{resolve,dirname,join,basename}from'node:path';import assert from'node:assert/strict';
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL('../dist/reasitic.zip',import.meta.url))),'zip');
const root='/printf-entry';py.FS.mkdirTree(root+'/tools');py.FS.mkdirTree(root+'/tests/fixtures');
const fixturePath=process.argv[6]?resolve(process.argv[6]):fileURLToPath(new URL('../tests/fixtures/printf_entry_original.manifest.json',import.meta.url)),raw=readFileSync(fixturePath),fixture=JSON.parse(raw),directory=dirname(fixturePath);
const shard=Number(process.argv[4]??1),shards=Number(process.argv[5]??1);assert.ok(Number.isInteger(shard)&&Number.isInteger(shards)&&1<=shard&&shard<=shards&&shards<=fixture.histories);
const digest=createHash('sha256');let bytes=0;
for(const part of fixture.parts){assert.equal(part.file,basename(part.file));assert.ok(part.file!=='.'&&part.file!=='..');const data=readFileSync(join(directory,part.file));assert.equal(data.length,part.bytes);assert.equal(createHash('sha256').update(data).digest('hex'),part.sha256);digest.update(data);bytes+=data.length;py.FS.writeFile(root+'/tests/fixtures/'+part.file,data);}
assert.equal(bytes,fixture.bytes);assert.equal(digest.digest('hex'),fixture.sha256);
py.FS.writeFile(root+'/tests/fixtures/printf_entry_original.manifest.json',raw);
for(const name of new Set(['square_original.json','unjoin_sessions_original.json.gz','printf_entry_probe.json.gz',...Object.keys(fixture.parents)]))py.FS.writeFile(root+'/tests/fixtures/'+name,readFileSync(new URL('../tests/fixtures/'+name,import.meta.url)));
for(const name of readdirSync(new URL('.',import.meta.url)).filter(n=>n.endsWith('.py')))py.FS.writeFile(root+'/tools/'+name,readFileSync(new URL(name,import.meta.url)));
py.FS.writeFile(root+'/tests/test_printf_entry_original.py',readFileSync(new URL('../tests/test_printf_entry_original.py',import.meta.url)));
py.globals.set('printf_entry_shard',shard);py.globals.set('printf_entry_shards',shards);
let passed;
try{passed=py.runPython(`
import os,sys,unittest
sys.path[:0]=['${root}/tools','${root}/tests']
os.environ['PYASITIC_PRINTF_ENTRY_SHARD']=str(printf_entry_shard)
os.environ['PYASITIC_PRINTF_ENTRY_SHARDS']=str(printf_entry_shards)
os.environ['PYASITIC_PRINTF_ENTRY_REPORT']='${root}/report.json'
os.environ['PYASITIC_PRINTF_ENTRY_PROBE_REPORT']='${root}/probe-report.json'
import test_printf_entry_original as tests
unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(tests)).wasSuccessful()
`);}catch(error){console.error(String(error));process.exit(1);}
if(process.argv[3]){writeFileSync(process.argv[3],py.FS.readFile(root+'/report.json'));writeFileSync(process.argv[3]+'.probe.json',py.FS.readFile(root+'/probe-report.json'));}
process.exitCode=passed?0:1;
