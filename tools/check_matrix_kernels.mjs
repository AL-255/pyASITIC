// Exact original-binary factor/pivot/inverse checks through the shipped Python API.
import {readFileSync} from "node:fs";
import {pathToFileURL} from "node:url";
import assert from "node:assert/strict";
import{createHash}from'node:crypto';
import {installNumericalKernels} from "../web/numeric-kernels.mjs";
const {loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL("../dist/reasitic.zip",import.meta.url))),"zip");
await installNumericalKernels(py,readFileSync(new URL("../dist/numeric.wasm",import.meta.url)));
py.runPython(`
import json,hashlib,struct,math
from reasitic.symmetric import factor_symmetric_upper,inverse_symmetric,_compiled_symmetric
from reasitic.numeric_limits import MATRIX_CAPACITY
assert _compiled_symmetric is not None
assert MATRIX_CAPACITY==512
def digest(a):
    return hashlib.sha256(b"".join(struct.pack("<dd",a[i][j].real,a[i][j].imag) for i in range(len(a)) for j in range(i,len(a)))).hexdigest()
def matrix_probe(payload):
    c=json.loads(payload)
    if "matrix" in c:a=[[complex(*z) for z in row] for row in c["matrix"]]
    else:
        n,kind=c["n"],c["kind"];a=[]
        for i in range(n):
            row=[]
            for j in range(n):
                if i==j:z=complex(3+i*.01,2) if kind=="dominant" else complex(.001*(i+1),.003)
                elif kind=="paired" and j==(i^1):z=complex(1,.2)
                else:z=complex(.01/(i+j+1),.02/(abs(i-j)+1))
                row.append(z)
            a.append(row)
    original=[row.copy() for row in a]
    input_digest=digest(a)
    try:factor,pivots=factor_symmetric_upper(a);inverse=inverse_symmetric(a)
    except ValueError as error:
        if "Singular" not in str(error):raise
        return json.dumps(dict(singular=True))
    assert a==original,"Matrix API mutated caller input"
    for i in range(len(a)):
        for j in range(i):
            assert struct.pack("<dd",factor[i][j].real,factor[i][j].imag)==struct.pack("<dd",a[i][j].real,a[i][j].imag),"Factor changed the native untouched lower triangle"
            assert struct.pack("<dd",inverse[i][j].real,inverse[i][j].imag)==struct.pack("<dd",inverse[j][i].real,inverse[j][i].imag),"Full inverse lost symmetric reconstruction"
    if "matrix" not in c:return json.dumps(dict(P=pivots,input_sha256=input_digest,factor_sha256=digest(factor),inverse_sha256=digest(inverse)))
    def bits(matrix):
        return [[struct.pack("<dd",matrix[i][j].real,matrix[i][j].imag).hex() for j in range(i,len(matrix))] for i in range(len(matrix))]
    return json.dumps(dict(P=pivots,F=bits(factor),I=bits(inverse)))
`);
const probe=py.globals.get("matrix_probe");
function nativeJSON(value){
  if(typeof value==="number"&&Object.is(value,-0))return "-0.0";
  if(Array.isArray(value))return "["+value.map(nativeJSON).join(",")+"]";
  if(value&&typeof value==="object")return "{"+Object.entries(value).map(([k,v])=>JSON.stringify(k)+":"+nativeJSON(v)).join(",")+"}";
  return JSON.stringify(value);
}
function bits(pair){
  const bytes=Buffer.alloc(16);bytes.writeDoubleLE(Number(pair[0]),0);bytes.writeDoubleLE(Number(pair[1]),8);return bytes.toString("hex");
}
const small=JSON.parse(readFileSync(new URL("../tests/fixtures/symmetric.json",import.meta.url)));
assert.equal(small.original_verification.cases,small.cases.length);
let components=0;
for(const c of small.cases){
  const actual=JSON.parse(probe(nativeJSON(c)));
  if(c.S){assert.equal(actual.singular,true);continue;}
  assert.deepEqual(actual.P,c.P,"Original symmetric pivots");
  for(const key of ["F","I"])for(let i=0;i<c.matrix.length;i++)for(let j=i;j<c.matrix.length;j++){
    assert.equal(actual[key][i][j-i],bits(c[key][i][j]),`Exact original ${key} ${c.matrix.length} [${i},${j}]`);components+=2;
  }
}
console.log(`${small.cases.length} original-binary symmetric cases passed (${components} exact upper-triangle components, pivots and singular classification).`);
const largeBytes=readFileSync(new URL("../tests/fixtures/symmetric_large.json",import.meta.url)),large=JSON.parse(largeBytes);
const wide=JSON.parse(readFileSync(new URL('../tests/fixtures/symmetric_wide_original.json',import.meta.url)));
assert.equal(wide.parent_sha256,createHash('sha256').update(largeBytes).digest('hex'));
assert.equal(wide.original_sha256,small.original_verification.original_sha256);
assert.equal(wide.legacy_sha256,small.original_verification.legacy_sha256);
assert.equal(wide.probe_source,readFileSync(new URL('./original_symmetric_probe.cpp',import.meta.url),'utf8'));
for(const c of [...large.cases,...wide.cases]){
  const actual=JSON.parse(probe(JSON.stringify(c)));
  assert.deepEqual(actual.P,c.P,`Original ${c.n} ${c.kind} pivots`);
  for(const key of ["input_sha256","factor_sha256","inverse_sha256"])assert.equal(actual[key],c[key],`Original ${c.n} ${c.kind} ${key}`);
  if(c.kind==="paired")assert.ok(actual.P.some(p=>p<0),"Large case exercises two-entry pivots");
  console.log(`${c.n}×${c.n} ${c.kind}: complete original factor/inverse digests match.`);
}
// The Python wrapper rejects invalid inputs before entering the bounded kernel.
py.runPython(`
from array import array
for n in (0,513):
    try:_compiled_symmetric(array('d'),n,1)
    except Exception:pass
    else:raise AssertionError('Compiled matrix capacity bound was bypassed')
for a in ([],[[1j,0j]],[[complex(float("nan"),0)]],[[complex(float("inf"),0)]]):
    for function in (factor_symmetric_upper,inverse_symmetric):
        try:function(a)
        except ValueError:pass
        else:raise AssertionError("Invalid matrix was accepted")
`);
probe.destroy();
py.runPython("from reasitic.bridge import request_json");
const call=py.globals.get("request_json");
const networks=JSON.parse(readFileSync(new URL("../tests/fixtures/network_dense.json",import.meta.url)));
for(const c of networks.cases){
  const response=JSON.parse(call(JSON.stringify({action:"pi2",kind:c.kind,parameters:c.parameters,technology:c.technology,frequency_hz:c.frequency_hz,mesh:c.mesh})));
  assert.ok(!response.error,response.error);const result=response.result;
  assert.equal(result.filaments,189);assert.equal(result.contacts,63);
  for(const key of ["admittance_matrix","scattering_matrix"])result[key].forEach((row,i)=>row.forEach((pair,j)=>pair.forEach((value,k)=>{
    const expected=c[key][i][j][k];
    assert.ok(Math.abs(value-expected)<=Math.max(1e-10,Math.abs(expected)*1e-8),`Original dense Pi2 ${c.fft} ${c.frequency_hz} ${key} [${i},${j},${k}]`);
  })));
}
call.destroy();
console.log(`${networks.cases.length} complete original-binary dense Pi2 sessions passed at 189 filaments and 63 contacts.`);
