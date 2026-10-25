// Native caller phases around a still-required formatter, without snapshot replay.
import{readFileSync,readdirSync,writeFileSync}from'node:fs';import{createHash}from'node:crypto';import{pathToFileURL}from'node:url';import assert from'node:assert/strict';
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL('../dist/reasitic.zip',import.meta.url))),'zip');
py.FS.mkdirTree('/vfprintf/tools');py.FS.mkdirTree('/vfprintf/tests/fixtures');
const fixture=JSON.parse(readFileSync(new URL('../tests/fixtures/vfprintf_original.manifest.json',import.meta.url)));
const shard=Number(process.argv[4]??1),shards=Number(process.argv[5]??1);assert.ok(Number.isInteger(shard)&&Number.isInteger(shards)&&1<=shard&&shard<=shards&&shards<=fixture.histories,'Require 1 <= shard <= shards <= histories');
const digest=createHash('sha256');let bytes=0;
for(const part of fixture.parts){const data=readFileSync(new URL('../tests/fixtures/'+part.file,import.meta.url));assert.equal(data.length,part.bytes);assert.equal(createHash('sha256').update(data).digest('hex'),part.sha256);digest.update(data);bytes+=data.length;py.FS.writeFile('/vfprintf/tests/fixtures/'+part.file,data);}
assert.equal(bytes,fixture.bytes);assert.equal(digest.digest('hex'),fixture.sha256);
for(const name of new Set(['vfprintf_original.manifest.json','square_original.json','unjoin_sessions_original.json.gz',...Object.keys(fixture.parents)]))py.FS.writeFile('/vfprintf/tests/fixtures/'+name,readFileSync(new URL('../tests/fixtures/'+name,import.meta.url)));
for(const name of readdirSync(new URL('.',import.meta.url)).filter(n=>n.endsWith('.py')))py.FS.writeFile('/vfprintf/tools/'+name,readFileSync(new URL(name,import.meta.url)));
py.FS.writeFile('/vfprintf/tests/test_vfprintf_original.py',readFileSync(new URL('../tests/test_vfprintf_original.py',import.meta.url)));
py.globals.set('vfprintf_shard',shard);py.globals.set('vfprintf_shards',shards);
let passed;
try{passed=py.runPython(`
import os,sys,unittest
sys.path[:0]=['/vfprintf/tools','/vfprintf/tests']
os.environ['PYASITIC_VFPRINTF_SHARD']=str(vfprintf_shard)
os.environ['PYASITIC_VFPRINTF_SHARDS']=str(vfprintf_shards)
os.environ['PYASITIC_VFPRINTF_REPORT']='/vfprintf/report.json'
import test_vfprintf_original as tests
unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(tests)).wasSuccessful()
`);}catch(error){console.error(String(error));process.exit(1);}
if(process.argv[3])writeFileSync(process.argv[3],py.FS.readFile('/vfprintf/report.json'));
process.exitCode=passed?0:1;
