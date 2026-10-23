// Coupled models through the shipped runtime, with original-binary oracles.
import{readFileSync}from"node:fs";
import{pathToFileURL}from"node:url";
import assert from"node:assert/strict";
import{installNumericalKernels}from"../web/numeric-kernels.mjs";
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL("../dist/reasitic.zip",import.meta.url))),"zip");
await installNumericalKernels(py,readFileSync(new URL("../dist/numeric.wasm",import.meta.url)));
py.runPython(`
import json,struct
from reasitic.transformer import extract_transformer_equivalent,invert_transformer_admittance,MODEL_KEYS,_compiled_transformer
assert _compiled_transformer is not None
def transformer_probe(payload):
 c=json.loads(payload);y={k:complex(float(z[0]),float(z[1])) for k,z in zip(("y11","y12","y21","y22"),c["input"])}
 saved=struct.pack("<8d",*[v for z in y.values() for v in (z.real,z.imag)])
 i=invert_transformer_admittance(y);m,z=extract_transformer_equivalent(y,c["frequency_hz"])
 assert saved==struct.pack("<8d",*[v for z in y.values() for v in (z.real,z.imag)]),"Input Y mutated"
 def bits(values):return [struct.pack("<d",v).hex() for v in values]
 return json.dumps(dict(I=bits(v for a in i.values() for v in (a.real,a.imag)),M=bits(m[k] for k in MODEL_KEYS),Z=bits(v for a in z.values() for v in (a.real,a.imag))))
`);
function nativeJSON(value){
 if(typeof value==="number"&&Object.is(value,-0))return"-0.0";
 if(Array.isArray(value))return"["+value.map(nativeJSON).join(",")+"]";
 if(value&&typeof value==="object")return"{"+Object.entries(value).map(([k,v])=>JSON.stringify(k)+":"+nativeJSON(v)).join(",")+"}";
 return JSON.stringify(value);
}
function exact(actual,expected,label){
 assert.equal(actual.length,expected.length,label);
 for(let j=0;j<expected.length;j++){
  const bytes=Buffer.from(actual[j],"hex"),value=bytes.readDoubleLE(),target=expected[j];
  if(target==="nan")assert.ok(Number.isNaN(value),label+" NaN");
  else if(target==="inf"||target==="-inf")assert.equal(value,Number(target==="inf"?Infinity:-Infinity),label);
  else{const b=Buffer.alloc(8);b.writeDoubleLE(target);assert.equal(bytes.toString("hex"),b.toString("hex"),label+` component ${j}`);}
 }
}
const fixture=JSON.parse(readFileSync(new URL("../tests/fixtures/transformer_network.json",import.meta.url))),probe=py.globals.get("transformer_probe");let components=0;
for(const c of fixture.rules){
 // Rules that start at node matrices additionally have their original Y record.
 const input=c.input||Array.from({length:4},(_,i)=>c.Y.slice(2*i,2*i+2));
 const actual=JSON.parse(probe(nativeJSON({...c,input})));
 for(const key of["I","M","Z"]){exact(actual[key],c[key],`Original transformer ${key}`);components+=c[key].length;}
}
probe.destroy();console.log(`${fixture.rules.length} original transformer extractions passed (${components} finite-bit/nonfinite-classification components).`);
// Real coupled-session Y records independently exercise the extractor with
// full binary precision, before the original text export rounds its digits.
const capturedProbe=py.globals.get("transformer_probe");
function decoded(hex){const value=Buffer.from(hex,"hex").readDoubleLE();return Number.isNaN(value)?"nan":value===Infinity?"inf":value===-Infinity?"-inf":value;}
for(const [i,c]of fixture.cases.entries()){
 const values=c.raw_output_bits.map(decoded),input=Array.from({length:4},(_,j)=>values.slice(j*2,j*2+2));
 const actual=JSON.parse(capturedProbe(nativeJSON({input,frequency_hz:c.frequency_hz})));
 exact(actual.Z,values.slice(8,16),`Original session ${i} Z extraction`);
 exact(actual.M,values.slice(16,23),`Original session ${i} SI model extraction`);
}
capturedProbe.destroy();console.log(`${fixture.cases.length} actual original-session Y→Z/model extractions also passed at raw SI output boundaries.`);
py.runPython("from reasitic.bridge import request_json");const call=py.globals.get("request_json");
function near(a,b,floor,relative=1e-8){
 if(Array.isArray(b)){assert.equal(a.length,b.length);a.forEach((v,i)=>near(v,b[i],floor,relative));}
 else if(typeof b==="string")assert.equal(a,null,"Native nonfinite metric");
 else assert.ok(Number.isFinite(a)&&Math.abs(a-b)<=Math.max(floor,Math.abs(b)*relative),`Original coupled value ${a} / ${b}`);
}
for(const [i,c]of fixture.cases.entries()){
 const request={action:"calctrans",first:c.first,second:c.second,ground:c.ground,frequency_hz:c.frequency_hz,technology:c.technology,mesh:c.mesh,eddy:c.eddy,termination_ohm:c.termination_ohm,include_matrices:true};
 const response=JSON.parse(call(JSON.stringify(request)));
 if(c.nonfinite_model){assert.match(response.error,/contact collapses|nonfinite inductive kernel/,`Original nonfinite history ${i}`);continue;}
 assert.ok(!response.error,response.error);const r=response.result;
 for(const key of["admittance_matrix","scattering_matrix","nodal_capacitance_matrix"])near(r[key],c[key],key==="nodal_capacitance_matrix"?1e-16:1e-10);
 const keys=["first_inductance_h","first_resistance_ohm","second_inductance_h","second_resistance_ohm","mutual_h","coupling","ground_resistance_ohm"],scales=[1e9,1,1e9,1,1e9,1,1];
 keys.forEach((key,j)=>near(r.model[key]===null?null:r.model[key]*scales[j],c.metrics[j],1e-9));
}
console.log(`${fixture.cases.length} original coupled sessions passed: omitted/explicit references, terminations, transformer/balun geometries, eddy on/off and native nonfinite diagnostics.`);
if(process.argv[3]){
 const{JSDOM}=await import(pathToFileURL(process.argv[3]).href);
 const{circuitSVG,sweepSVG,transformerSVG}=await import("../web/analysis-views.mjs");
 const dom=new JSDOM(readFileSync(new URL("../dist/index.html",import.meta.url),"utf8"),{url:"https://example.test/",runScripts:"outside-only"}),w=dom.window,downloads=[],requests=[];
 Object.assign(w,{circuitSVG,sweepSVG,transformerSVG,Blob});w.URL.createObjectURL=blob=>{downloads.push(blob);return"blob:test";};w.URL.revokeObjectURL=()=>{};w.HTMLAnchorElement.prototype.click=()=>{};
 w.Worker=class{
  constructor(){queueMicrotask(()=>this.onmessage({data:{ready:true}}));}
  postMessage({id,request}){requests.push(request);queueMicrotask(()=>this.onmessage({data:{id,...JSON.parse(call(JSON.stringify(request)))}}));}
 };
 const source=readFileSync(new URL("../dist/app.js",import.meta.url),"utf8").replace(/^import[^\n]+\n/,"").replaceAll("import.meta.url",'"https://example.test/app.js"');
 w.eval(source+"\nglobalThis.coupledState=()=>({ready,busy,current,transformerResult,transformerRows,transformerRequest});");
 const $=s=>w.document.querySelector(s);
 async function idle(){for(let i=0;i<500;i++){await new Promise(setImmediate);const s=w.coupledState();if(s.ready&&!s.busy)return;}throw Error("Coupled app did not become idle");}
 async function click(id,expectedError=false){assert.equal($(id).disabled,false,id+" disabled");$(id).click();await idle();if(!expectedError)assert.equal($("#error").hidden,true,$("#error").textContent);}
 async function change(id,value){$(id).value=value;$(id).dispatchEvent(new w.Event("change"));await idle();}
 await idle();assert.equal($("#transformer-run").disabled,true,"Single-winding model must not run CALCTRANS");
 const c=fixture.cases.find(c=>c.first.kind==="transformer"&&c.reference_mode==="default"&&c.first.winding===0);
 const project={format:"reasitic-project",version:1,shape:c.first,technology:c.technology};
 Object.defineProperty($("#project-file"),"files",{configurable:true,value:[{text:async()=>JSON.stringify(project)}]});$("#project-file").dispatchEvent(new w.Event("change"));await idle();
 assert.equal($("#error").hidden,true,$("#error").textContent);
 for(const [id,key]of[["#mesh-length","length_cell"],["#mesh-width","width_cell"],["#mesh-thickness","thickness_cell"],["#cap-length","capacitance_length_cell"],["#cap-width","capacitance_width_cell"]])$(id).value=String(c.mesh[key]);
 $("#frequency").value="1";
 await click("#transformer-run");let state=w.coupledState();
 near(state.transformerResult.model.first_inductance_h*1e9,c.metrics[0],1e-9);
 assert.ok($("#transformer-circuit svg"));assert.ok($("#transformer-circuit").textContent.includes("M ="));assert.ok($("#transformer-circuit").textContent.includes("nH"));
 await click("#download-transformer");const exported=JSON.parse(await downloads.at(-1).text());assert.equal(exported.inputs.action,"calctrans");assert.equal(exported.first_winding,"A");
 await click("#download-transformer-ports");assert.equal((await downloads.at(-1).text()).split("\n").length,13);
 await change("#transformer-termination","1e-10");await click("#transformer-run");assert.equal(requests.filter(r=>r.action==="calctrans").at(-1).termination_ohm,Math.fround(1e-10),"Native binary32 command termination");
 await change("#transformer-termination","0");$("#sweep-first").value="1";$("#sweep-last").value="2";$("#sweep-count").value="2";
 await click("#transformer-sweep");state=w.coupledState();assert.equal(state.transformerRows.length,2);assert.ok($("#transformer-chart svg"));
 await change("#transformer-sweep-metric","first_inductance_nh");assert.ok($("#transformer-chart").textContent.includes("First inductance (nH)"));
 $("#transformer-chart [data-index='1']").dispatchEvent(new w.MouseEvent("click",{bubbles:true}));assert.equal(Number($("#frequency").value),2);assert.equal(w.coupledState().transformerResult.frequency_hz,2e9);
 await click("#download-transformer-sweep");assert.equal((await downloads.at(-1).text()).trim().split("\n").length,3);
 await change("#active-winding","1");$("#frequency").value="1";await click("#transformer-run");
 const reversed=fixture.cases.find(c=>c.first.kind==="transformer"&&c.reference_mode==="default"&&c.first.winding===1);assert.ok(reversed);
 near(w.coupledState().transformerResult.model.first_inductance_h*1e9,reversed.metrics[0],1e-9);assert.equal(w.coupledState().transformerResult.first_winding,"B");
 await change("#transformer-ground-mode","first");await click("#transformer-run",true);assert.equal($("#error").hidden,false);assert.match($("#error").textContent,/nonfinite inductive kernel/);assert.equal($("#download-transformer").disabled,true);
 dom.window.close();console.log("Actual coupled DOM handlers passed: paired selection, native input precision, circuit/model exports, two-point sweep, plot inspection, reversed winding and nonfinite diagnostics.");
}
call.destroy();
