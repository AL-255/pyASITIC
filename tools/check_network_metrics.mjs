// Same intact-original metric records through the production Python transport.
import {readFileSync} from "node:fs";
import {pathToFileURL} from "node:url";
import {installNumericalKernels} from "../web/numeric-kernels.mjs";
const {loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL("../dist/reasitic.zip",import.meta.url))),"zip");
await installNumericalKernels(py,readFileSync(new URL("../dist/numeric.wasm",import.meta.url)));
py.globals.set("fixture_text",readFileSync(new URL("../tests/fixtures/network_metrics_original.json",import.meta.url),"utf8"));
py.runPython(`
import json,math,struct
from array import array
from reasitic.network_metrics import probe,_compiled_metrics,PI_KEYS
from reasitic.network import two_port_impedance,extract_pi_equivalent,convert_scattering
assert _compiled_metrics is not None
cases=json.loads(fixture_text)['cases'];components=0;retained=0
for offset in range(0,len(cases),256):
 batch=cases[offset:offset+256];rows=[[float(v) for v in c['input']] for c in batch]
 saved=[struct.pack('<26d',*row) for row in rows];actual=probe(rows)
 assert saved==[struct.pack('<26d',*row) for row in rows]
 for i,(c,out) in enumerate(zip(batch,actual)):
  target=bytes.fromhex(c['output_bits'])
  def equal(a,raw):
   value=struct.unpack('<d',raw)[0]
   return math.isnan(a) if math.isnan(value) else struct.pack('<d',a)==raw
  for k in range(28):
   assert equal(out[k+1],target[8*k:8*k+8]),('Original component',offset+i,k,out[k+1])
   components+=1
  for k,bits in enumerate(c['extended_bits']):
   raw=bytes.fromhex(bits)
   if struct.unpack_from('<H',raw,8)[0]&0x7fff!=0x7fff:
    assert struct.pack('<IIH',*map(int,out[29+3*k:32+3*k]))==raw,('Original retained return',offset+i,k)
    retained+=1
  if c['input'][0]==0:
   y={key:complex(*rows[i][6+2*j:8+2*j]) for j,key in enumerate(('y11','y12','y21','y22'))}
   model=extract_pi_equivalent(y,rows[i][1])
   for j,key in enumerate(PI_KEYS):
    expected=struct.unpack_from('<d',target,8*(j+1))[0]
    assert model[key] is None if not math.isfinite(expected) else equal(model[key],target[8*(j+1):8*(j+2)]),('Public metric',offset+i,key)
   expected=struct.unpack_from('<d',target,14*8)[0]
   assert model['resonant_frequency_hz'] is None if not math.isfinite(expected) else equal(model['resonant_frequency_hz'],target[14*8:15*8])
   z=two_port_impedance(y,differential=bool(rows[i][3]),port=int(rows[i][2]))
   assert equal(z.real,target[15*8:16*8]) and equal(z.imag,target[16*8:17*8])
   s=convert_scattering(y)
   for j,z in enumerate([z for row in s for z in row]):
    assert equal(z.real,target[(20+2*j)*8:(21+2*j)*8]) and equal(z.imag,target[(21+2*j)*8:(22+2*j)*8]),('Public S',offset+i,j)
 # Operation-specific calls cannot leak stale results from previous operations.
 for operation,fields in [(0,[*range(1,16),*range(29,38)]),(1,[*range(16,21),*range(38,41)]),(2,list(range(21,29)))]:
  partial=probe(rows,operation)
  for a,b in zip(actual,partial):
   for k in fields:assert math.isnan(b[k]) if math.isnan(a[k]) else struct.pack('<d',a[k])==struct.pack('<d',b[k])
   for k in set(range(42))-set(fields):assert b[k]==0.
for a,b,operation in [(array('d',[0.])*25,array('d',[0.])*42,3),(array('d',[0.])*26,array('d',[0.]),3),(array('d',[0.])*26,array('d',[0.])*42,4)]:
 try:_compiled_metrics(a,b,operation)
 except Exception:pass
 else:raise AssertionError('Invalid metric transport accepted')
print(f'{len(cases)} intact original network metric records / {components} binary64 components and {retained} finite retained returns passed; public APIs, operation isolation and immutable inputs passed.')
`);
