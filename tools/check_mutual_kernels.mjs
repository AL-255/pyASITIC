// Direct original-binary mutual outputs through the shipped Python transport.
import {readFileSync} from "node:fs";
import {pathToFileURL} from "node:url";
import assert from "node:assert/strict";
import {installNumericalKernels} from "../web/numeric-kernels.mjs";
const bytes=readFileSync(new URL("../dist/numeric.wasm",import.meta.url));
const {loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL("../dist/reasitic.zip",import.meta.url))),"zip");
await installNumericalKernels(py,bytes);
const fixtureText=readFileSync(new URL("../tests/fixtures/mutual_original.json",import.meta.url),"utf8");
py.globals.set("fixture_text",fixtureText);
py.globals.set("boundary_text",readFileSync(new URL("../tests/fixtures/mutual_boundaries_original.json",import.meta.url),"utf8"));
try {py.runPython(`
import json,struct,math
from array import array
from reasitic.mutual_kernel import probe,_compiled_mutual,mesh_mutual
from reasitic.inductance import segment_mutual
assert _compiled_mutual is not None
cases=[c for c in json.loads(fixture_text)['cases']+json.loads(boundary_text)['cases'] if c['mode']<5]
rows=[[c['mode'],*map(float,c['input'])] for c in cases]
saved=struct.pack('<'+'d'*sum(map(len,rows)),*[v for row in rows for v in row]);actual=probe(rows);scalar_extended_differences=0
assert saved==struct.pack('<'+'d'*sum(map(len,rows)),*[v for row in rows for v in row]),'Mutual inputs changed'
for i,(c,out) in enumerate(zip(cases,actual)):
 assert int(out[0])==c['status'],('Original status',i,out[0],c['status'])
 expected=struct.unpack('<d',bytes.fromhex(c['output_bits']))[0]
 assert math.isnan(out[1]) if math.isnan(expected) else struct.pack('<d',out[1]).hex()==c['output_bits'],('Original output',i,out[1],expected)
 assert bool(out[5])==bool(c['warnings']),('Original warning',i)
 if c['mode']<2 and not math.isnan(expected):
  scalar_extended_differences+=struct.pack('<IIH',int(out[2]),int(out[3]),int(out[4])).hex()!=c['extended_bits']
 if c['mode']==4:
  args=list(map(float,c['input']));messages=[];value=segment_mutual(args[:8],args[8:16],messages)
  assert math.isnan(value) if math.isnan(expected) else struct.pack('<d',value).hex()==c['output_bits'],('Public segment output',i)
  assert bool(messages)==bool(c['warnings']),('Public warning',i)
# Packed geometry caching preserves input bits and returns the same complete
# upper-triangle order, without per-frequency scaling in the cache.
group=[c for c in cases if c.get('production_pair',{}).get('coupled_case')==16]
wires={}
for c in group:
 p=c['production_pair'];wires[p['row']]=c['input'][:8];wires[p['column']]=c['input'][8:16]
key=b''.join(struct.pack('=8d',*wires[i]) for i in range(len(wires)))
mesh_mutual.cache_clear();cached=mesh_mutual(key);assert mesh_mutual(key) is cached
for j,c in enumerate(group):assert struct.pack('<d',cached[3*j+1]).hex()==c['output_bits']
assert mesh_mutual.cache_info().hits==1
for a,b in [(array('d',[0.]),array('d',[0.])*6),(array('d',[0.])*18,array('d',[0.]))]:
 try:_compiled_mutual(a,b)
 except Exception:pass
 else:raise AssertionError('Invalid mutual buffer accepted')
print(len(cases),'intact original self/cross-section/separation/parallel/whole-pair outputs and statuses passed exactly at binary64 boundaries; immutable input and packed cache checks passed.')
print(scalar_extended_differences,'standalone scalar raw extended results differ; those words remain recorded for further validation.')
`);} catch(error) {console.error(String(error));process.exit(1);}
// These independently captured instruction tests are explicitly distinct from
// calls into the original executable. They gate the consumed binary64 stores;
// raw 80-bit differences remain recorded for further hardware validation.
const {instance:{exports:api}}=await WebAssembly.instantiate(bytes);
const output=new Float64Array(api.memory.buffer,api.retained_math_buffer(),4);
const fixture=JSON.parse(fixtureText);let count=0,extendedDifferences=0;
for(const c of fixture.cases.filter(c=>c.mode>=5)){
 const values=c.input.map(v=>v==="nan"?NaN:v==="inf"?Infinity:v==="-inf"?-Infinity:v);
 assert.equal(api.retained_math_probe(c.mode-5,values[0],values[1],values[2]),0);
 const expected=Buffer.from(c.output_bits,"hex").readDoubleLE(),actual=Buffer.alloc(8);actual.writeDoubleLE(output[0]);
 if(Number.isNaN(expected))assert.ok(Number.isNaN(output[0]));else assert.equal(actual.toString("hex"),c.output_bits,`Native instruction mode ${c.mode}, ${c.input}`);
 const extended=Buffer.alloc(10);extended.writeUInt32LE(output[1],0);extended.writeUInt32LE(output[2],4);extended.writeUInt16LE(output[3],8);
 if(!Number.isNaN(expected)&&extended.toString("hex")!==c.extended_bits)extendedDifferences++;count++;
}
console.log(`${count} separate native x87 instruction outputs passed at binary64 boundaries; ${extendedDifferences} raw extended intermediates differ (no universal 80-bit equality claim).`);
