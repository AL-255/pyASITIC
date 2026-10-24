// Original GHz command stores, including the actual webpage event handlers.
import{readFileSync}from"node:fs";
import{pathToFileURL}from"node:url";
import assert from"node:assert/strict";
import{installNumericalKernels}from"../web/numeric-kernels.mjs";
import{circuitSVG,sweepSVG,transformerSVG}from"../web/analysis-views.mjs";
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL("../dist/reasitic.zip",import.meta.url))),"zip");
await installNumericalKernels(py,readFileSync(new URL("../dist/numeric.wasm",import.meta.url)));
py.runPython("from reasitic.bridge import request_json");const call=py.globals.get("request_json");
const fixture=JSON.parse(readFileSync(new URL("../tests/fixtures/frequency_inputs_original.json",import.meta.url)));
const keys=["inductance_h","resistance_ohm","capacitance_first_f","capacitance_second_f","resistance_first_ohm","resistance_second_ohm","q_first","q_second","q_differential","shunt_single_ohm","shunt_differential_ohm"];
function bits(value){const b=Buffer.alloc(8);b.writeDoubleLE(value);return b.toString("hex");}
function decoded(value){return Buffer.from(value,"hex").readDoubleLE();}
function exact(result,c){
 const y=result.admittance_matrix;
 assert.deepEqual([y[1][1],y[1][0],y[0][1],y[0][0]].flat().map(bits),c.model.Y);
 const actual=[result.frequency_hz,...keys.map(key=>result.pi[key])];
 assert.equal(actual.length,c.model.M.length);
 actual.forEach((value,i)=>{if(Number.isFinite(decoded(c.model.M[i])))assert.equal(bits(value),c.model.M[i],`${c.command_ghz} GHz output ${i}`);else assert.equal(value,null);});
}
assert.equal(fixture.cases.length,17);
for(const c of fixture.cases){const response=JSON.parse(call(JSON.stringify(c.request)));assert.ok(!response.error,response.error);exact(response.result,c);}
console.log("All 17 actual-original fractional GHz sessions match every stored Y/model output in WebAssembly.");
function exactCoupled(result,c){
 const y=result.admittance_matrix,z=result.impedance_matrix;
 const actual=[...[y[1][1],y[1][0],y[0][1],y[0][0],z[0][0],z[0][1],z[1][0],z[1][1]].flat(),...["first_inductance_h","second_inductance_h","first_resistance_ohm","second_resistance_ohm","ground_resistance_ohm","mutual_h","coupling"].map(key=>result.model[key])];
 assert.equal(bits(result.frequency_hz),c.frequency_bits);assert.equal(actual.length,c.raw_output_bits.length);
 actual.forEach((value,i)=>{if(Number.isFinite(decoded(c.raw_output_bits[i])))assert.equal(bits(value),c.raw_output_bits[i],`${c.command_ghz} GHz coupled output ${i}`);else assert.equal(value,null);});
}
assert.equal(fixture.coupled_cases.length,3);
for(const c of fixture.coupled_cases){const response=JSON.parse(call(JSON.stringify(c.request)));assert.ok(!response.error,response.error);exactCoupled(response.result,c);}
console.log("All three actual-original fractional coupled sessions match every stored Y/Z/model output in WebAssembly.");
const{JSDOM}=await import(pathToFileURL(process.argv[3]).href);
const dom=new JSDOM(readFileSync(new URL("../dist/index.html",import.meta.url),"utf8"),{url:"https://example.test/",runScripts:"outside-only"}),w=dom.window,requests=[],downloads=[];
Object.assign(w,{circuitSVG,sweepSVG,transformerSVG,Blob});
w.URL.createObjectURL=blob=>{downloads.push(blob);return"blob:test";};w.URL.revokeObjectURL=()=>{};w.HTMLAnchorElement.prototype.click=()=>{};
w.Worker=class{
 constructor(){queueMicrotask(()=>this.onmessage({data:{ready:true}}));}
 postMessage({id,request}){requests.push(request);queueMicrotask(()=>this.onmessage({data:{id,...JSON.parse(call(JSON.stringify(request)))}}));}
};
const source=readFileSync(new URL("../dist/app.js",import.meta.url),"utf8").replace(/^import[^\n]+\n/,"").replaceAll("import.meta.url",'"https://example.test/app.js"');
w.eval(source+"\nglobalThis.inputState=()=>({ready,busy,pi2Result,sweepRows,sweepModels,sweepContext,selfresResult,transformerResult,transformerRows,transformerRange});");
const $=s=>w.document.querySelector(s);
async function idle(){for(let i=0;i<500;i++){await new Promise(setImmediate);const s=w.inputState();if(s.ready&&!s.busy)return;}throw Error("Input app did not become idle");}
async function click(id){assert.equal($(id).disabled,false,id+" disabled");$(id).click();await idle();assert.equal($("#error").hidden,true,$("#error").textContent);}
async function change(id,value){$(id).value=value;$(id).dispatchEvent(new w.Event("change"));await idle();}
async function restore(shape,technology,mesh){
 const project={format:"reasitic-project",version:1,shape,technology,mesh};
 Object.defineProperty($("#project-file"),"files",{configurable:true,value:[{text:async()=>JSON.stringify(project)}]});$("#project-file").dispatchEvent(new w.Event("change"));await idle();
 assert.equal($("#error").hidden,true,$("#error").textContent);
}
await idle();const first=fixture.cases[0],last=fixture.cases[3];
await restore({kind:first.request.kind,parameters:first.request.parameters},first.request.technology,first.request.mesh);
$("#frequency").value=first.command_ghz;await click("#pi2");exact(w.inputState().pi2Result,first);
// Select an actual retained-store midpoint that Math.fround(NumberGHz * 1e9)
// would round differently. It must survive textbox -> worker -> Python intact.
const midpoint=fixture.cases.find(c=>Math.fround(Number(c.command_ghz)*1e9)!==decoded(c.model.M[0]));assert.ok(midpoint,"Oracle must expose double rounding");
$("#frequency").value=midpoint.command_ghz;await click("#pi2");exact(w.inputState().pi2Result,midpoint);
await change("#sweep-model","pi2");$("#sweep-first").value=first.command_ghz;$("#sweep-last").value=last.command_ghz;$("#sweep-count").value="2";
await click("#sweep");let state=w.inputState();exact(state.sweepModels[0],first);exact(state.sweepModels[1],last);
assert.deepEqual(Array.from(state.sweepRows,row=>row.frequency_hz),[decoded(first.model.M[0]),decoded(last.model.M[0])]);
assert.equal(state.sweepContext.firstHz,decoded(first.model.M[0]));assert.equal(state.sweepContext.lastHz,decoded(last.model.M[0]));
const circles=Array.from($("#sweep-chart").querySelectorAll(".plot-point circle:last-child"));assert.equal(Number(circles[0].getAttribute("cx")),90);assert.equal(Number(circles[1].getAttribute("cx")),730);
await click("#download-csv");const csv=(await downloads.at(-1).text()).trim().split("\n");assert.equal(Number(csv[1].split(",")[2]),decoded(first.model.M[0]));assert.equal(Number(csv[2].split(",")[2]),decoded(last.model.M[0]));
$("#sweep-chart [data-index='1']").dispatchEvent(new w.MouseEvent("click",{bubbles:true}));assert.equal(Number($("#frequency").value),decoded(last.model.M[0])/1e9);
// CAP, LMAT and estimates share the command parser; all retain the GHz text.
for(const id of["#lmat","#capacitance","#simulate"]){$("#frequency").value=first.command_ghz;await click(id);assert.equal(requests.at(-1).frequency_ghz,Number(first.command_ghz));}
$("#selfres-first").value=first.command_ghz;$("#selfres-last").value=last.command_ghz;$("#selfres-step").value="1";await click("#selfres");
const search=requests.filter(r=>r.action==="selfres").at(-1);assert.equal(search.first_ghz,Number(first.command_ghz));assert.equal(search.last_ghz,Number(last.command_ghz));assert.equal(search.step_ghz,1);
const coupled=JSON.parse(readFileSync(new URL("../tests/fixtures/transformer_network.json",import.meta.url))).cases.find(c=>c.first.kind==="transformer"&&c.reference_mode==="default"&&c.first.winding===0);
await restore(coupled.first,coupled.technology,coupled.mesh);$("#frequency").value=first.command_ghz;await click("#transformer-run");
exactCoupled(w.inputState().transformerResult,fixture.coupled_cases[0]);assert.equal(requests.filter(r=>r.action==="calctrans").at(-1).frequency_ghz,Number(first.command_ghz));
$("#sweep-first").value=first.command_ghz;$("#sweep-last").value=last.command_ghz;$("#sweep-count").value="2";await click("#transformer-sweep");state=w.inputState();
assert.deepEqual(Array.from(state.transformerRows,row=>row.frequency_hz),[decoded(first.model.M[0]),decoded(last.model.M[0])]);assert.equal(state.transformerRange.firstHz,decoded(first.model.M[0]));assert.equal(state.transformerRange.lastHz,decoded(last.model.M[0]));
exactCoupled(state.transformerResult,fixture.coupled_cases[0]);
$("#transformer-chart [data-index='1']").dispatchEvent(new w.MouseEvent("click",{bubbles:true}));exactCoupled(w.inputState().transformerResult,fixture.coupled_cases[1]);
await click("#download-transformer-sweep");const coupledCSV=(await downloads.at(-1).text()).trim().split("\n");assert.equal(Number(coupledCSV[1].split(",")[3]),decoded(first.model.M[0]));assert.equal(Number(coupledCSV[2].split(",")[3]),decoded(last.model.M[0]));
call.destroy();w.close();console.log("Actual GHz textbox, retained midpoint, Pi2/coupled sweeps, computed-frequency plots/CSV, CAP/LMAT/estimates and SELFRES input handlers passed.");
