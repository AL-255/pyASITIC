// Exact original via stores, including signed zeros and untouched inputs.
import {readFileSync} from "node:fs";
import {pathToFileURL} from "node:url";
import {installNumericalKernels} from "../web/numeric-kernels.mjs";
const {loadPyodide}=await import(pathToFileURL(process.argv[2]).href);
const py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL("../dist/reasitic.zip",import.meta.url))),"zip");
await installNumericalKernels(py,readFileSync(new URL("../dist/numeric.wasm",import.meta.url)));
py.globals.set("fixture_text",readFileSync(new URL("../tests/fixtures/vias_original.json",import.meta.url),"utf8"));
py.runPython(`
import json,struct,math
from reasitic.vias import stamp,_compiled_via_stamp,active_height
from array import array
assert _compiled_via_stamp is not None
cases=json.loads(fixture_text)["cases"]
rows=[c["input"][:5]+[int(v) for v in c["input"][5:7]]+c["input"][7:] for c in cases]
before=struct.pack("="+"d"*(9*len(rows)),*(v for row in rows for v in row))
actual=stamp(rows)
assert len(actual)==len(cases)
for i,(z,c) in enumerate(zip(actual,cases)):
 for component,(value,bits) in enumerate(zip((z.real,z.imag),c["output_bits"])):
  expected=struct.unpack("<d",bytes.fromhex(bits))[0]
  assert struct.pack("<d",value).hex()==bits or (math.isnan(value) and math.isnan(expected)),(i,component,value,expected)
assert before==struct.pack("="+"d"*(9*len(rows)),*(v for row in rows for v in row))
assert stamp([])==[]
assert not active_height(0.,1e-10) and active_height(0.,math.nextafter(1e-10,math.inf))
for counts in ((-65536,1),(1,1.5),(1,65536)):
 try:stamp([[1e9,0.,1.,.8,.137,*counts,0.,0.]])
 except ValueError:pass
 else:raise AssertionError("Invalid via cell count accepted")
for length in (0,8,10):
 try:stamp([[0.]*length])
 except ValueError:pass
 else:raise AssertionError("Invalid via record accepted")
print(f"{len(cases)} original via stamps / {2*len(cases)} exact binary64 components passed")
`);
// The JS boundary also rejects malformed buffers supplied outside the wrapper.
py.runPython(`
for data,out in ((array('d'),array('d')), (array('d',[1.])*9,array('d',[0.]))):
 try:_compiled_via_stamp(data,out)
 except Exception:pass
 else:raise AssertionError("Malformed via transport accepted")
for count in (65536.,-65536.,1.5):
 data=array('d',[1.,0.,1.,.8,.137,count,1.,0.,0.])
 try:_compiled_via_stamp(data,array('d',[0.,0.]))
 except Exception:pass
 else:raise AssertionError("Invalid count crossed the via transport")
`);
