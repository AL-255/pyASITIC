// Exact actual-original Green returns, imported libm and complete eddy stamps.
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {pathToFileURL} from "node:url";
import {inflateSync} from "node:zlib";
import {installNumericalKernels} from "../web/numeric-kernels.mjs";
const bytes=readFileSync(new URL("../dist/numeric.wasm",import.meta.url));
const {instance:{exports:api}}=await WebAssembly.instantiate(bytes);
const config=new Float64Array(api.memory.buffer,api.green_config_buffer(),8),output=new Float64Array(api.memory.buffer,api.green_result_buffer(),3032);
const trace=new Uint8Array(api.memory.buffer,api.green_trace_buffer(),65536*8);
const fixture=JSON.parse(readFileSync(new URL("../tests/fixtures/eddy_original.json",import.meta.url)));
let green=0,trig=0;
for(const c of fixture.cases){
 let history=[0,0,0];
 for(const row of c.green){
  const raw=Buffer.from(row.input_bits,"hex"),args=Array.from({length:4},(_,i)=>raw.readDoubleLE(8*i));
  config.set([...args,...history,0]);assert.equal(api.green_reflection_integral(),0);
  history=Array.from(output.slice(10,13));const actual=Buffer.alloc(10);
  actual.writeUInt32LE(output[13],0);actual.writeUInt32LE(output[14],4);actual.writeUInt16LE(output[15],8);
  assert.equal(actual.toString("hex"),row.extended_bits,`Original retained Green session ${c.session_index}, call ${green}`);green++;
  const points=inflateSync(Buffer.from(row.points_zlib_base64,"base64"));assert.equal(output[5],row.observations);
  assert.ok(row.observations<=65536);assert.equal(Buffer.from(trace.subarray(0,8*row.observations)).toString("hex"),points.toString("hex"),"Every original Green callback abscissa");
 }
 for(const row of c.trig){
  const input=Buffer.from(row.argument_bits,"hex").readDoubleLE(),raw=Buffer.from(row.extended_bits,"hex"),sig=raw.readBigUInt64LE(),exponent=raw.readUInt16LE(8);
  assert.equal(sig&2047n,0n,"Original imported libm return is stored binary64");
  const target=Number(sig)*2**((exponent&0x7fff)-16383-63)*(exponent&0x8000?-1:1);
  const actual=api.binary64_trig_probe(row.kind==="cos"?0:1,input);
  assert.ok(Object.is(actual,target),`Original imported ${row.kind}(${input}): ${actual} / ${target}`);trig++;
 }
}
assert.equal(green,fixture.coverage.green);assert.equal(trig,fixture.coverage.trig);
assert.deepEqual(fixture.cases.filter(c=>c.source==="coupled").map(c=>c.session_index),[5,8,11]);
assert.equal(fixture.cases.filter(c=>c.source==="lmat").length,10);
console.log(`${green} actual-original retained Green returns and ${trig} imported libm returns passed exactly.`);
const mathFixture=JSON.parse(readFileSync(new URL("../tests/fixtures/imported_math.json",import.meta.url)));
for(const c of mathFixture.cases.filter(c=>c.operation<2)){
 const input=c.input==="inf"?Infinity:c.input==="-inf"?-Infinity:c.input==="nan"?NaN:c.input;
 const actual=api.binary64_trig_probe(c.operation,input),expected=Buffer.from(c.output_bits,"hex").readDoubleLE();
 assert.ok(Number.isNaN(expected)?Number.isNaN(actual):Object.is(actual,expected),`Native imported math ${c.operation}(${input}): ${actual} / ${expected}`);
}
console.log(`${mathFixture.cases.filter(c=>c.operation<2).length} separately identified native libm sin/cos cases passed at binary64 boundaries. Extreme power cases retain a separate strict audit.`);
const {loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL("../dist/reasitic.zip",import.meta.url))),"zip");
await installNumericalKernels(py,bytes);
py.globals.set("fixture_text",JSON.stringify(fixture));
py.runPython(`
import base64,json,struct,zlib
from fractions import Fraction
from array import array
from _reasitic_numeric import eddy_stamp
from reasitic.eddy import _compiled_stamp
from reasitic.green_integration import _compiled_reflection,GreenIntegrationState,green_integral
from reasitic.green import GreenLayers
assert _compiled_stamp is not None and _compiled_reflection is not None
components=0;stamps=0
for case in json.loads(fixture_text)["cases"]:
 state=GreenIntegrationState(GreenLayers(1e5,0.,0.),'reflection')
 for c in case['green']:
  args=struct.unpack('<4d',bytes.fromhex(c['input_bits']));value=green_integral(*args,state)
  sig,exponent=struct.unpack('<QH',bytes.fromhex(c['extended_bits']))
  expected=float(Fraction(sig)*Fraction(2)**((exponent&0x7fff)-16383-63)*(-1 if exponent&0x8000 else 1))
  assert struct.pack('<d',value.value)==struct.pack('<d',expected)
  assert value.observations==c['observations']
  points=zlib.decompress(base64.b64decode(c['points_zlib_base64']))
  assert struct.pack('<d',value.last_point)==points[-8:]
  infinite=abs(args[1])<1e-10
  assert value.method==('DQAGIE' if infinite else 'DQAWFE')
  assert value.evaluations==value.observations-(101 if infinite else 0)
  assert (state.frequency,state.separation,state.height,state.z_offset)==args
 for c in case["stamps"]:
  config=array('d',c['config']);n=c['rows']
  wires=array('d',(v for s in c['segments'] for v in [*struct.unpack('<7d',bytes.fromhex(s['wire_bits'])),s['metal']]))
  matrix=array('d');matrix.frombytes(bytes.fromhex(c['before_bits']))
  saved_config=config.tobytes();saved_wires=wires.tobytes()
  size=2*__import__('math').ceil(c['config'][11]) if c['kind']=='square' else 0
  output=array('d',[0.])*(32+size*size)
  assert eddy_stamp(config,wires,matrix,output)==0
  assert matrix.tobytes().hex()==c['after_bits'],('Original complete stamp',case['session_index'])
  assert config.tobytes()==saved_config and wires.tobytes()==saved_wires
  assert output[0]==c['green_count']==sum(output[1:17])
  components+=2*n*n
  stamps+=1
assert stamps==json.loads(fixture_text)['coverage']['stamps']
print(f"{stamps} complete original eddy matrix stamps / {components} exact components and immutable config/wires passed")
`);
