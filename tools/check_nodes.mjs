// Complete original folded-node boundaries through the shipped Python API.
import {readFileSync} from "node:fs";
import {pathToFileURL} from "node:url";
import {installNumericalKernels} from "../web/numeric-kernels.mjs";
const {loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL("../dist/reasitic.zip",import.meta.url))),"zip");
await installNumericalKernels(py,readFileSync(new URL("../dist/numeric.wasm",import.meta.url)));
py.globals.set("fixture_text",readFileSync(new URL("../tests/fixtures/nodes_original.json",import.meta.url),"utf8"));
py.runPython(`
import base64,hashlib,json,math,struct,zlib
from array import array
from reasitic.network import solve_node_equations,_compiled_node
from reasitic.node_math import folded
assert _compiled_node is not None
cases=json.loads(fixture_text)["cases"]
for label,driver in (("Compiled driver",solve_node_equations),("Python driver with compiled general solve",folded)):
 components=0
 for c in cases:
  n=c["n"];raw=zlib.decompress(base64.b64decode(c["input_zlib_base64"]))
  assert len(raw)==32*n*n and hashlib.sha256(raw).hexdigest()==c["input_sha256"]
  values=struct.unpack("<"+"d"*(4*n*n),raw)
  cap,ind=[[[complex(*values[offset+2*(j*n+i):offset+2*(j*n+i)+2]) for j in range(n)] for i in range(n)] for offset in (0,2*n*n)]
  def packed(matrices):return b"".join(struct.pack("<dd",m[i][j].real,m[i][j].imag) for m in matrices for j in range(n) for i in range(n))
  y,nodal=driver(cap,ind)
  assert packed((cap,ind))==raw,(c["label"],"mutated caller matrices")
  assert hashlib.sha256(packed((nodal,))).hexdigest()==c["cap_sha256"],(c["label"],"folded CAP digest")
  for value,bits in zip((v for key in ("y11","y12","y21","y22") for v in (y[key].real,y[key].imag)),c["Y"]):
   expected=struct.unpack("<d",bytes.fromhex(bits))[0]
   assert struct.pack("<d",value).hex()==bits or (math.isnan(value) and math.isnan(expected)),(c["label"],value,expected)
  components+=2*n*n+8
 print(f"{label}: {len(cases)} complete original folded-node solves / {components} exact components, including 256 nodes and 15 production sessions")
for cap,ind in (([],[]),([[1j]],[]),([[1j,2j]],[[1j]])):
 try:solve_node_equations(cap,ind)
 except ValueError:pass
 else:raise AssertionError("Invalid folded-node dimensions accepted")
for data,out,n in ((array('d'),array('d'),0),(array('d',[0.])*4,array('d',[0.])*10,257),(array('d',[0.])*4,array('d',[0.]),1)):
 try:_compiled_node(data,out,n)
 except Exception:pass
 else:raise AssertionError("Malformed folded-node transport accepted")
`);
