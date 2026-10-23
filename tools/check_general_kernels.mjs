// Direct-original general factors, n-workspace inverses and three RHS solves.
import {readFileSync} from "node:fs";
import {pathToFileURL} from "node:url";
import assert from "node:assert/strict";
import {installNumericalKernels} from "../web/numeric-kernels.mjs";
const {loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL("../dist/reasitic.zip",import.meta.url))),"zip");
await installNumericalKernels(py,readFileSync(new URL("../dist/numeric.wasm",import.meta.url)));
py.runPython(`
import json,hashlib,struct
from array import array
from reasitic.linear import factor_general,inverse_general,solve_general,matrix_vector,_compiled_general
assert _compiled_general is not None

def generated_matrix(n,kind):
    if kind=="diagonal":return [[complex(2+i*.01,.5) if i==j else 0j for j in range(n)] for i in range(n)]
    return [[complex(3+i*.01,2) if j==(i+13)%n else complex(.01/(i+j+1),.02/(abs(i-j)+1)) for j in range(n)] for i in range(n)]

def right_sides(n):
    return [[complex(i==r,0) for i in range(n)] for r in (0,n-1)]+[[complex((i%7-3)*.125,(i%11-5)*.0625) for i in range(n)]]

def packed(matrix):return b"".join(struct.pack("<dd",z.real,z.imag) for row in matrix for z in row)
def digest(matrix):return hashlib.sha256(packed(matrix)).hexdigest()
def general_probe(payload):
    c=json.loads(payload)
    a=[[complex(float(z[0]),float(z[1])) for z in row] for row in c["matrix"]] if "matrix" in c else generated_matrix(c["n"],c["kind"])
    saved=packed(a);n=len(a)
    assert digest(a)==c["input_sha256"],"Original general input bits differ"
    values=array("d",(v for j in range(n) for i in range(n) for v in (a[i][j].real,a[i][j].imag)))
    values.extend([0.]*(3*n))
    status=_compiled_general(values,n,0)
    factor=[[complex(values[2*(j*n+i)],values[2*(j*n+i)+1]) for j in range(n)] for i in range(n)]
    pivots=[int(p)-1 for p in values[2*n*n:2*n*n+n]]
    result=dict(S=status,P=pivots)
    rhs=right_sides(n);saved_rhs=packed(rhs)
    matrices=dict(F=factor,V=[matrix_vector(a,row) for row in rhs])
    assert packed(rhs)==saved_rhs,"Matrix-vector API mutated caller input"
    if status:
        for function in (factor_general,inverse_general):
            try:function(a)
            except ValueError as e:assert "Singular" in str(e)
            else:raise AssertionError("Singular original matrix accepted")
    else:
        public,p=factor_general(a)
        assert packed(public)==packed(factor) and p==pivots,"Public factor differs from primitive"
        saved_factor=packed(factor);saved_pivots=pivots.copy();rhs=right_sides(n);saved_rhs=packed(rhs)
        matrices["B"]=[solve_general(factor,pivots,row) for row in rhs]
        assert packed(factor)==saved_factor and pivots==saved_pivots and packed(rhs)==saved_rhs,"Solve mutated caller data"
        matrices["I"]=inverse_general(a)
    assert packed(a)==saved,"General API mutated caller matrix"
    for key,m in matrices.items():
        if "matrix" in c:result[key]=[[struct.pack("<dd",z.real,z.imag).hex() for z in row] for row in m]
        else:result[key+"_sha256"]=digest(m)
    return json.dumps(result)
`);
function nativeJSON(value){
  if(typeof value==="number"&&Object.is(value,-0))return "-0.0";
  if(Array.isArray(value))return "["+value.map(nativeJSON).join(",")+"]";
  if(value&&typeof value==="object")return "{"+Object.entries(value).map(([k,v])=>JSON.stringify(k)+":"+nativeJSON(v)).join(",")+"}";
  return JSON.stringify(value);
}
const fixture=JSON.parse(readFileSync(new URL("../tests/fixtures/general.json",import.meta.url)));
const probe=py.globals.get("general_probe");let components=0;
for(const [index,c] of fixture.cases.entries()){
  const actual=JSON.parse(probe(nativeJSON(c)));
  assert.equal(actual.S,c.S,`Original general INFO ${index}`);
  assert.deepEqual(actual.P,c.P,`Original general pivots ${index}`);
  for(const key of ["F","I","B","V"]){
    if(c[key+"_sha256"]){assert.equal(actual[key+"_sha256"],c[key+"_sha256"],`Original complete ${key} bits ${c.n} ${c.kind}`);components+=["B","V"].includes(key)?6*c.n:2*c.n*c.n;continue;}
    if(!c[key])continue;
    c[key].forEach((row,i)=>row.forEach((z,j)=>z.forEach((expected,k)=>{
      const bytes=Buffer.from(actual[key][i][j],"hex"),value=bytes.readDoubleLE(8*k);
      if(expected==="nan")assert.ok(Number.isNaN(value),`Original ${key} NaN classification ${index}`);
      else if(expected==="inf"||expected==="-inf")assert.equal(value,expected==="inf"?Infinity:-Infinity);
      else{const target=Buffer.alloc(8);target.writeDoubleLE(expected);assert.equal(bytes.subarray(8*k,8*k+8).toString("hex"),target.toString("hex"),`Original ${key} bits case ${index} [${i},${j},${k}]`);}
      components++;
    })));
  }
}
assert.equal(components,fixture.components);
probe.destroy();
console.log(`${fixture.cases.length} original-binary general cases passed (${components} output components), including complete 64/65/128/129/256/514-entry factors, inverses, three RHS solves and network products.`);
