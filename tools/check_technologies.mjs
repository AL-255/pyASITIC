// Test every bundled process in the exact Pages archive, then its DOM controls.
// Usage: node tools/check_technologies.mjs /path/to/pyodide.mjs [/path/to/jsdom/api.js]
import {readFileSync} from "node:fs";
import {pathToFileURL} from "node:url";
import assert from "node:assert/strict";
import {installNumericalKernels} from "../web/numeric-kernels.mjs";
import {circuitSVG,sweepSVG,transformerSVG} from "../web/analysis-views.mjs";
const {loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL("../dist/reasitic.zip",import.meta.url))),"zip");
await installNumericalKernels(py,readFileSync(new URL("../dist/numeric.wasm",import.meta.url)));
py.runPython("from reasitic.bridge import request_json");
const call=py.globals.get("request_json");
function request(payload){const result=JSON.parse(call(JSON.stringify(payload)));if(result.error)throw Error(result.error);return result.result;}
const presets=request({action:"init"}).presets;
assert.equal(presets.length,46);
let files=0;
for(const p of presets.filter(p=>p.id!=="sample-cmos")){
  for(const density of Object.keys(p.variants)){
    const r=request({action:"technology",preset:p.id,mim_density:density});
    assert.equal(r.preset.id,p.id);assert.equal(r.preset.density,density);
    assert.equal(request({action:"init",technology:r.text}).technology.chip.techfile,r.technology.chip.techfile);
    const shape={kind:"wire",parameters:{length:40,width:8,metal:`M${p.routing_metals}`,x:40,y:40}};
    assert.ok(Number.isFinite(request({action:"simulate",...shape,technology:r.text,frequency_hz:2e9}).inductance_nh));
    assert.ok(Buffer.from(request({action:"gds",...shape,technology:r.text}).base64,"base64").length>100);
    ++files;
  }
}
assert.equal(files,73);console.log("All 45 GF180 stacks / 73 technology variants load, simulate and export GDS in WebAssembly.");
const fixture=JSON.parse(readFileSync(new URL("../tests/fixtures/gf180_network.json",import.meta.url)));
for(const c of fixture.cases){
  const r=request({action:"pi2",kind:c.kind,parameters:c.parameters,technology:c.technology,frequency_hz:c.frequency_hz});
  for(const key of ["admittance_matrix","scattering_matrix"]){
    r[key].forEach((row,i)=>row.forEach((z,j)=>z.forEach((v,k)=>assert.ok(Math.abs(v-c[key][i][j][k])<=Math.max(1e-10,Math.abs(c[key][i][j][k])*1e-8),`${c.preset} ${key} ${i},${j}/${k}`))));
  }
}
console.log("Three native GF180 distributed network sessions passed in WebAssembly.");
if(process.argv[3]){
  const {JSDOM}=await import(pathToFileURL(process.argv[3]).href);
  const dom=new JSDOM(readFileSync(new URL("../dist/index.html",import.meta.url),"utf8"),{url:"https://example.test/",runScripts:"outside-only"});
  const {window:w}=dom,downloads=[];w.circuitSVG=circuitSVG;w.sweepSVG=sweepSVG;w.transformerSVG=transformerSVG;w.Blob=Blob;
  w.URL.createObjectURL=blob=>{downloads.push(blob);return "blob:test";};w.URL.revokeObjectURL=()=>{};w.HTMLAnchorElement.prototype.click=()=>{};
  // Only transport is replaced. The actual app event handlers, DOM, Python
  // bridge, geometry and process files run together from this release.
  w.Worker=class{
    constructor(){queueMicrotask(()=>this.onmessage({data:{ready:true}}));}
    postMessage({id,request:payload}){queueMicrotask(()=>this.onmessage({data:{id,...JSON.parse(call(JSON.stringify(payload)))}}));}
  };
  const source=readFileSync(new URL("../dist/app.js",import.meta.url),"utf8").replace(/^import[^\n]+\n/,"").replaceAll("import.meta.url",'"https://example.test/app.js"');
  w.eval(source+"\nglobalThis.testState=()=>({ready,busy,current,technologyText,technologyPreset});");
  const $=s=>w.document.querySelector(s);
  async function idle(){for(let i=0;i<500;i++){await new Promise(setImmediate);const state=w.testState();if(state.ready&&!state.busy)return;}throw Error("App did not become idle");}
  async function change(id,value){$(id).value=value;$(id).dispatchEvent(new w.Event("change"));await idle();assert.equal($("#error").hidden,true,$("#error").textContent);}
  async function click(id){$(id).click();await idle();assert.equal($("#error").hidden,true,$("#error").textContent);}
  await idle();assert.ok(w.testState().current);assert.equal($("#technology-preset").options.length,47);
  assert.equal($("#sweep-model").value,"pi2");assert.equal($("#sweep-count").value,"11");
  await change("#pi-model","pi");assert.equal($("#sweep-model").value,"pi2","Fast-Pi inspection must not select estimate physics");
  await change("#pi-model","pi2");
  $("#sweep-count").value="2";
  await click("#sweep");
  assert.ok($("#sweep-chart svg"));assert.ok($("#sweep-method").textContent.includes("frequency-dependent distributed model"));
  $("#sweep-chart [data-index]").dispatchEvent(new w.MouseEvent("click",{bubbles:true}));
  assert.equal(Number($("#frequency").value),Number($("#sweep-first").value));
  assert.equal($("#download-pi2").disabled,false);assert.ok($("#model-circuit svg"));
  console.log("Default distributed Pi2 sweep, valid starter contacts and plotted-point circuit inspection passed through actual DOM handlers.");
  await change("#technology-preset","gf180-1p3m-6ka-no-mim");
  assert.equal($("#gf180-settings").hidden,false);assert.equal($("#mim-density-field").hidden,true);assert.equal($("#metal").selectedOptions[0].textContent.split(" · ")[0],"M3");
  await change("#technology-preset","gf180-1p6m-9ka-mim-b");
  assert.equal($("#mim-density-field").hidden,false);assert.equal($("#secondary-metal").selectedOptions[0].textContent.split(" · ")[0],"M5");
  await change("#mim-density","1.0");await change("#substrate-rho","15");await change("#substrate-thickness","350");
  assert.equal(w.testState().technologyPreset.density,"1.0");
  await click("#download-technology");const downloaded=await downloads.at(-1).text();assert.ok(downloaded.includes("<layer> 0\nt = 350\nrho = 15\n"));
  await click("#generate");await click("#download-project");const project=JSON.parse(await downloads.at(-1).text());
  assert.equal(project.technology,downloaded);assert.ok(w.testState().current);
  await click("#reset-technology");assert.equal($("#technology-preset").value,"sample-cmos");assert.equal($("#gf180-settings").hidden,true);
  const fileInput=$("#project-file");Object.defineProperty(fileInput,"files",{configurable:true,value:[{text:async()=>JSON.stringify(project)}]});
  fileInput.dispatchEvent(new w.Event("change"));await idle();
  assert.equal($("#technology-preset").value,"gf180-1p6m-9ka-mim-b");assert.equal($("#mim-density").value,"1.0");assert.equal($("#substrate-rho").value,"15");
  assert.equal(w.testState().technologyText,downloaded);assert.ok(w.testState().current);
  console.log("Actual process-selection DOM handlers passed: metal defaults, MIM gap, substrate edits, .tek/project downloads, reset and project restore.");
  w.close();
}
call.destroy();
