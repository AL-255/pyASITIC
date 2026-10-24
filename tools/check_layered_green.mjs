// Original Green/legacy DSO boundaries, with a separate strict raw-trig audit.
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
const {instance:{exports:api}}=await WebAssembly.instantiate(readFileSync(new URL("../dist/numeric.wasm",import.meta.url)));
const input=new Float64Array(api.memory.buffer,api.layered_green_buffer(),256*9);
const output=new Float64Array(api.memory.buffer,api.layered_green_result_buffer(),256*6);
const fixture=JSON.parse(readFileSync(new URL("../tests/fixtures/layered_green_original.json",import.meta.url)));
let original=0,instructions=0,extendedDifferences=0,finiteComponents=0;
for(let offset=0;offset<fixture.cases.length;offset+=256){
 const rows=fixture.cases.slice(offset,offset+256);
 rows.forEach((c,i)=>input.set([c.mode,...c.input.map(v=>v==="inf"?Infinity:v==="-inf"?-Infinity:Number(v))],i*9));
 const saved=Buffer.from(input.buffer,input.byteOffset,rows.length*9*8).toString("hex");
 assert.equal(api.layered_green_probe(rows.length),0);
 assert.equal(Buffer.from(input.buffer,input.byteOffset,rows.length*9*8).toString("hex"),saved,"Immutable primitive input");
 rows.forEach((c,i)=>{
  const expected=Buffer.from(c.output_bits,"hex");
  for(let k=0;k<2;k++){
   const target=expected.readDoubleLE(8*k),actual=output[6*i+1+k];
   assert.ok(Number.isNaN(target)?Number.isNaN(actual):Object.is(actual,target),`Original Green/complex/instruction ${offset+i}, mode ${c.mode}, component ${k}: ${actual} / ${target}`);
   if(Number.isFinite(target))finiteComponents++;
  }
  const raw=Buffer.alloc(10);raw.writeUInt32LE(output[6*i+3]);raw.writeUInt32LE(output[6*i+4],4);raw.writeUInt16LE(output[6*i+5],8);
  const scalar=expected.readDoubleLE();
  if(c.mode<12){
   original++;
   if(Number.isFinite(scalar))assert.equal(raw.toString("hex"),c.extended_bits,`Retained original Green ${offset+i}`);
  }else{
   instructions++;
   if(Number.isFinite(scalar)&&raw.toString("hex")!==c.extended_bits)extendedDifferences++;
  }
 });
}
assert.equal(api.layered_green_probe(0),-1);assert.equal(api.layered_green_probe(257),-1);
console.log(`${original} intact original Green/legacy-complex calls and ${instructions} separately identified native trig instruction calls passed at binary64 boundaries (${finiteComponents} finite components, signed zeros exact).`);
console.log(`${extendedDifferences} finite raw trig instruction results differ; these remain recorded, and --raw-trig deliberately fails until they match. Complete consumed original Green returns are gated separately.`);
if(process.argv.includes("--raw-trig")&&extendedDifferences)process.exitCode=1;
