// Strict diagnostic: keep the original joined model and every differing word.
import{readFileSync,writeFileSync}from'node:fs';import{gunzipSync}from'node:zlib';import{pathToFileURL}from'node:url';import assert from'node:assert/strict';import{installNumericalKernels}from'../web/numeric-kernels.mjs';
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();py.unpackArchive(new Uint8Array(readFileSync(new URL('../dist/reasitic.zip',import.meta.url))),'zip');const wasm=readFileSync(new URL('../dist/numeric.wasm',import.meta.url));await installNumericalKernels(py,wasm);
const load=name=>JSON.parse(gunzipSync(readFileSync(new URL('../tests/fixtures/'+name+'.json.gz',import.meta.url)))),c=load('join_sessions_original').cases.find(c=>c.label==='finite-balun/calctrans');
py.globals.set('query',JSON.stringify({...c.request,include_matrices:true}));let response;
try{response=JSON.parse(py.runPython('from reasitic.bridge import request_json\nrequest_json(query)'));}catch(error){console.error(String(error));process.exit(1);}
assert.equal(response.error,undefined,response.error);const r=response.result,differences=[],counts={};
function compare(kind,actual,expected,where){counts[kind]=(counts[kind]||0)+1;if(actual!==expected)differences.push({kind,where,actual,original:expected});}
const bits=value=>{const b=Buffer.alloc(8);b.writeDoubleLE(value);return b.toString('hex');};
for(const[native,key]of[['capacitance','capacitance_matrix'],['inductance','inductive_admittance_matrix']]){
 const data=Buffer.from(c.nodes[0][native],'hex'),n=c.nodes[0].size;assert.equal(r[key].length,n);let at=0;
 for(let j=0;j<n;j++)for(let i=0;i<n;i++)for(let k=0;k<2;k++){compare(key,bits(r[key][i][j][k]),data.subarray(at,at+8).toString('hex'),[i,j,k]);at+=8;}
}
const y=r.admittance_matrix,z=r.impedance_matrix,keys=['first_inductance_h','second_inductance_h','first_resistance_ohm','second_resistance_ohm','ground_resistance_ohm','mutual_h','coupling'];
[y[1][1],y[1][0],y[0][1],y[0][0],z[0][0],z[0][1],z[1][0],z[1][1]].flat().concat(keys.map(k=>r.model[k])).forEach((v,i)=>compare('model',bits(v),c.raw_output_bits[i],i));r.scattering_matrix.flat(2).forEach((v,i)=>compare('scattering',bits(v),c.records[0].S[i],i));
py.globals.set('assembly_json',JSON.stringify(load('join_assembly_original').cases[0]));const upper=JSON.parse(py.runPython(`
import json,struct
from reasitic.inductance import segment_mutual
from reasitic.impedance import assemble,_compiled_assembly
from reasitic.mutual_kernel import _compiled_mutual
assert _compiled_assembly is not None and _compiled_mutual is not None
v=json.loads(assembly_json)
wires=[struct.unpack('<8d',bytes.fromhex(r['wire_bits']))for r in v['records']]
pairs=[segment_mutual(a,b)for i,a in enumerate(wires)for b in wires[i+1:]]
m=assemble(wires,[(r['sheet_resistance'],r['thickness_count'])for r in v['records']],pairs,v['frequency'])
expected=bytes.fromhex(v['upper_bits']);rows=[];at=0
for j in range(v['n']):
 for i in range(j+1):
  word=struct.pack('<2d',m[i][j].real,m[i][j].imag)
  rows.append(dict(where=[i,j],actual=word.hex(),original=expected[at:at+16].hex()));at+=16
json.dumps(rows)
`));
for(const row of upper)compare('upper_entry',row.actual,row.original,row.where);
const{instance:{exports:api}}=await WebAssembly.instantiate(wasm),traces=load('join_mutual_traces_original');
for(const c of traces.cases)for(const e of c.events)for(const op of e.math||[]){
 if(op.operation!=='fcos')continue;const x=Buffer.from(op.input_words[0],'hex'),sig=x.readBigUInt64LE(),exponent=x.readUInt16LE(8),value=Number(sig)*2**((exponent&32767)-16383-63)*(exponent&32768?-1:1);
 assert.equal(BigInt(Number(sig)),sig,'The captured FCOS argument must be exactly representable by this binary64 probe');assert.equal(api.retained_math_probe(4,value,0,0),0);const words=new Float64Array(api.memory.buffer,api.retained_math_buffer(),4),out=Buffer.alloc(10);out.writeUInt32LE(words[1]);out.writeUInt32LE(words[2],4);out.writeUInt16LE(words[3],8);compare('fcos_raw',out.toString('hex'),op.output_words,[c.first,c.second]);
}
const report={counts,differences};if(process.argv[3])writeFileSync(process.argv[3],JSON.stringify(report,null,2)+'\n');else for(const row of differences)console.log(JSON.stringify(row));
console.log(JSON.stringify({counts,differences:differences.length}));process.exitCode=differences.length?1:0;
