// Strict original input-stage checks and complete-session parity audit.
// Every complete captured session is mandatory; --audit-full remains compatible.
import {readFileSync} from "node:fs";
import {pathToFileURL} from "node:url";
import {installNumericalKernels} from "../web/numeric-kernels.mjs";
const {loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL("../dist/reasitic.zip",import.meta.url))),"zip");
await installNumericalKernels(py,readFileSync(new URL("../dist/numeric.wasm",import.meta.url)));
for(const [key,name]of [["sessions_text","pi_sessions_original"],["metrics_text","network_metrics_original"]])py.globals.set(key,readFileSync(new URL(`../tests/fixtures/${name}.json`,import.meta.url),"utf8"));
try {py.runPython(`
import json,struct,math
from fractions import Fraction
from reasitic.network_metrics import probe,PI_KEYS
from reasitic.network import extract_pi_equivalent,convert_scattering
from reasitic.bridge import handle
sessions=json.loads(sessions_text)['cases'];metrics=json.loads(metrics_text)['cases']
captured={c['session_index']:c for c in metrics if 'session_index' in c and c['input'][2:4]==[0,0]}
def value(bits):return struct.unpack('<d',bytes.fromhex(bits))[0]
def equal(actual,bits):
 expected=value(bits)
 if actual is None:return not math.isfinite(expected)
 return math.isnan(actual) if math.isnan(expected) else struct.pack('<d',actual).hex()==bits
def native_y(words):return {k:complex(value(words[2*i]),value(words[2*i+1]))for i,k in enumerate(('y11','y12','y21','y22'))}
def resonance(bits):
 sig,exp=struct.unpack('<QH',bytes.fromhex(bits))
 if exp&0x7fff==0x7fff:return math.nan if sig&0x7fffffffffffffff else math.copysign(math.inf,-1 if exp&0x8000 else 1)
 return float(Fraction(sig)*Fraction(2)**((exp&0x7fff)-16383-63)*(-1 if exp&0x8000 else 1))
differences=[];exact=0;components=0
for i,c in enumerate(sessions):
 # The full actual CLI metric stage must match at its independently captured Y.
 y=native_y(c['model']['Y']);f=value(c['model']['frequency_bits'])
 model=extract_pi_equivalent(y,f)
 for key,bits in zip(PI_KEYS,c['model']['M'][1:]):assert equal(model[key],bits),('Original CLI metric stage',i,key)
 expected_res=resonance(c['resonance']['extended_bits'])
 assert model['resonant_frequency_hz'] is None if not math.isfinite(expected_res) else struct.pack('<d',model['resonant_frequency_hz'])==struct.pack('<d',expected_res)
 # Native Pi3 and a later 2PORT command have different reference mesh types.
 # Check both S input histories, rather than substituting one for the other.
 raw=bytes.fromhex(captured[i]['output_bits']);model_s=[raw[8*k:8*k+8].hex()for k in range(20,28)]
 for words,expected in [(c['model']['Y'],model_s),(c['scattering']['Y'],c['scattering']['S'])]:
  s=convert_scattering(native_y(words))
  assert all(equal(v,bits)for v,bits in zip([v for row in s for z in row for v in (z.real,z.imag)],expected)),('Original CLI S stage',i)
 r=handle(c['request']);Y=r['admittance_matrix']
 actual_y=[v for z in (Y[1][1],Y[1][0],Y[0][1],Y[0][0])for v in z]
 actual_m=[r['frequency_hz'],*[r['pi'][k]for k in PI_KEYS]]
 actual_s=[v for row in r['scattering_matrix']for z in row for v in z]
 counts=[sum(not equal(v,b)for v,b in zip(a,b))for a,b in [(actual_y,c['model']['Y']),(actual_m,c['model']['M']),(actual_s,model_s)]]
 res_ok=r['pi']['resonant_frequency_hz'] is None if not math.isfinite(expected_res) else struct.pack('<d',r['pi']['resonant_frequency_hz'])==struct.pack('<d',expected_res)
 components+=29
 label=(c['fixture'],c['index'])
 if any(counts) or not res_ok:
  differences.append(label)
  print(label,'different output components Y/model/S:',counts,'resonance equal:',res_ok)
 else:exact+=1
 assert not any(counts) and res_ok,('Required complete original Pi session',label,counts)
assert len(sessions)==41 and len(captured)==41
print(f'All {len(sessions)} actual-original CLI metric/S stages passed at identical Y inputs. {exact}/{len(sessions)} complete sessions match every raw Y/model/S finite output and resonance; undefined metrics retain public nulls.')
assert exact==len(sessions)
`);} catch(error) {console.error(String(error));process.exitCode=1;}
