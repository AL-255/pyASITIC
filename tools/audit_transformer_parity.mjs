// Strict whole-session audit. Unlike component-tolerance regression checks,
// this deliberately exits nonzero while any finite output differs in bits.
import {readFileSync} from "node:fs";
import {pathToFileURL} from "node:url";
import {installNumericalKernels} from "../web/numeric-kernels.mjs";

if(!process.argv[2])throw Error("Supply the pinned pyodide.mjs path");
const {loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL("../dist/reasitic.zip",import.meta.url))),"zip");
await installNumericalKernels(py,readFileSync(new URL("../dist/numeric.wasm",import.meta.url)));
py.runPython(`
import json,struct,math
from reasitic.bridge import handle
from reasitic.transformer import MODEL_KEYS
def coupled_output_bits(payload):
 r=handle(json.loads(payload));y=r['admittance_matrix'];z=r['impedance_matrix']
 values=[v for point in (y[1][1],y[1][0],y[0][1],y[0][0],z[0][0],z[0][1],z[1][0],z[1][1]) for v in point]
 values.extend(r['model'][key] for key in MODEL_KEYS)
 return json.dumps([struct.pack('<d',math.nan if value is None else value).hex() for value in values])
`);
const call=py.globals.get("coupled_output_bits"),fixture=JSON.parse(readFileSync(new URL("../tests/fixtures/transformer_network.json",import.meta.url)));
const fields=["first","second","ground","frequency_hz","technology","mesh","eddy","termination_ohm"];
let sessions=0,exactSessions=0,components=0,differences=0;
function matches(actual,expected){
 const a=Buffer.from(actual,"hex").readDoubleLE(),b=Buffer.from(expected,"hex").readDoubleLE();
 return Number.isNaN(b)?Number.isNaN(a):actual===expected;
}
for(const [i,c]of fixture.cases.entries()){
 // These original all-nonfinite histories are checked separately by the
 // regression suite, which requires explicit bounded failure diagnostics.
 if(c.nonfinite_model)continue;
 const request={action:"calctrans",...Object.fromEntries(fields.map(key=>[key,c[key]]))};
 const actual=JSON.parse(call(JSON.stringify(request))),expected=c.raw_output_bits;
 if(actual.length!==23||expected.length!==23)throw Error("Incomplete original SI output record");
 const changed=actual.map((bits,j)=>matches(bits,expected[j])?null:j).filter(j=>j!==null);
 sessions++;components+=actual.length;differences+=changed.length;if(!changed.length)exactSessions++;
 const counts=[0,0,0];for(const j of changed)counts[j<8?0:j<16?1:2]++;
 console.log(`Case ${i}: ${c.first.kind} / ${c.reference_mode} / eddy ${c.eddy}: ${changed.length?`different components Y=${counts[0]}, Z=${counts[1]}, model=${counts[2]}`:"exact"}`);
}
call.destroy();
console.log(`${exactSessions}/${sessions} complete finite sessions exact; ${differences}/${components} output components differ. Nonfinite outputs compare by classification.`);
process.exitCode=differences?1:0;
