// Deliberately exits nonzero while any version-bound native scalar differs.
// This broader diagnostic includes extreme power inputs beyond the captured
// production integration traces. It does not apply component tolerances.
import {readFileSync} from "node:fs";
const {instance:{exports:api}}=await WebAssembly.instantiate(readFileSync(new URL("../dist/numeric.wasm",import.meta.url)));
const fixture=JSON.parse(readFileSync(new URL("../tests/fixtures/imported_math.json",import.meta.url)));
const counts=[0,0,0],total=[0,0,0];
for(const c of fixture.cases){
 const input=c.input==="inf"?Infinity:c.input==="-inf"?-Infinity:c.input==="nan"?NaN:c.input;
 const actual=api.binary64_trig_probe(c.operation,input),expected=Buffer.from(c.output_bits,"hex").readDoubleLE();total[c.operation]++;
 if(!(Number.isNaN(expected)?Number.isNaN(actual):Object.is(actual,expected))){
  counts[c.operation]++;
  console.log(`Native ${["cos","sin","pow(x,1.5)"][c.operation]}(${input}): ${actual} / ${expected}`);
 }
}
for(let i=0;i<3;i++)console.log(`${["cos","sin","pow(x,1.5)"][i]}: ${total[i]-counts[i]}/${total[i]} exact (nonfinite values by classification)`);
process.exitCode=counts.some(Boolean)?1:0;
