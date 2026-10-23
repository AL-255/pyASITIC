// Actual mesh controls + real worker payloads, Python and compiled kernels.
import {readFileSync} from "node:fs";
import {pathToFileURL} from "node:url";
import assert from "node:assert/strict";
import {installNumericalKernels} from "../web/numeric-kernels.mjs";
import {circuitSVG,sweepSVG,transformerSVG} from "../web/analysis-views.mjs";
const {loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL("../dist/reasitic.zip",import.meta.url))),"zip");
await installNumericalKernels(py,readFileSync(new URL("../dist/numeric.wasm",import.meta.url)));
py.runPython("from reasitic.bridge import request_json");const call=py.globals.get("request_json");
const {JSDOM}=await import(pathToFileURL(process.argv[3]).href);
const dom=new JSDOM(readFileSync(new URL("../dist/index.html",import.meta.url),"utf8"),{url:"https://example.test/",runScripts:"outside-only"});
const w=dom.window,downloads=[],requests=[];Object.assign(w,{circuitSVG,sweepSVG,transformerSVG,Blob});
w.URL.createObjectURL=blob=>{downloads.push(blob);return"blob:test";};w.URL.revokeObjectURL=()=>{};w.HTMLAnchorElement.prototype.click=()=>{};
w.Worker=class{
 constructor(){queueMicrotask(()=>this.onmessage({data:{ready:true}}));}
 postMessage({id,request}){requests.push(request);queueMicrotask(()=>this.onmessage({data:{id,...JSON.parse(call(JSON.stringify(request)))}}));}
};
const source=readFileSync(new URL("../dist/app.js",import.meta.url),"utf8").replace(/^import[^\n]+\n/,"").replaceAll("import.meta.url",'"https://example.test/app.js"');
w.eval(source+"\nglobalThis.meshState=()=>({ready,busy,current,pi2Result});");
const $=s=>w.document.querySelector(s);
async function idle(){for(let i=0;i<500;i++){await new Promise(setImmediate);const s=w.meshState();if(s.ready&&!s.busy)return;}throw Error("Mesh app did not become idle");}
async function click(id,expectedError=false){assert.equal($(id).disabled,false,id+" disabled");$(id).click();await idle();if(!expectedError)assert.equal($("#error").hidden,true,$("#error").textContent);}
async function change(id,value){$(id).value=value;$(id).dispatchEvent(new w.Event("change"));await idle();}
async function restore(project){Object.defineProperty($("#project-file"),"files",{configurable:true,value:[{text:async()=>JSON.stringify(project)}]});$("#project-file").dispatchEvent(new w.Event("change"));await idle();}
await idle();assert.equal($("#mesh-settings").open,true);
for(const id of["mesh-length","mesh-width","mesh-thickness","cap-length","cap-width"])assert.equal(w.document.querySelectorAll("#"+id).length,1,"One shared cell field");
const project={format:"reasitic-project",version:1,shape:{kind:"wire",parameters:{name:"Dense",length:400,width:6,metal:"M5",x:20,y:50}},mesh:{length_cell:20,width_cell:.5,thickness_cell:.5,capacitance_length_cell:1000,capacitance_width_cell:1000}};
await restore(project);assert.equal($("#error").hidden,true,$("#error").textContent);assert.equal($("#mesh-length").value,"20");assert.equal($("#mesh-preset").value,"custom");
const prior=requests.filter(r=>r.action==="pi2").length;
await click("#pi2",true);assert.match($("#error").textContent,/360 filaments/);assert.equal(requests.filter(r=>r.action==="pi2").length,prior,"Over-budget mesh must stop before expensive CAP/LMAT solves");assert.equal($("#mesh-settings").open,true);
await click("#mesh-fit");assert.equal($("#mesh-length").value,"40");assert.equal($("#mesh-width").value,"1");assert.equal($("#mesh-thickness").value,"1");assert.match($("#mesh-feedback").textContent,/60 \/ 256 filaments/);
assert.equal($("#cap-length").value,"1000");assert.equal($("#cap-width").value,"1000","Filament fitting preserves CAP cell settings");
await click("#pi2");assert.equal(w.meshState().pi2Result.filaments,60);assert.equal($("#download-pi2").disabled,false);
await change("#mesh-width","2");assert.equal($("#download-pi2").disabled,true,"Changed cells must invalidate exported results");
await change("#mesh-preset","coarse");for(const id of["mesh-length","mesh-width","mesh-thickness","cap-length","cap-width"])assert.equal($("#"+id).value,"1000");
await click("#mesh-check");assert.match($("#mesh-feedback").textContent,/1 \/ 256 filaments/);
await click("#download-project");const saved=JSON.parse(await downloads.at(-1).text());assert.deepEqual(saved.mesh,{length_cell:1000,width_cell:1000,thickness_cell:1000,capacitance_length_cell:1000,capacitance_width_cell:1000});
await change("#mesh-preset","fine");assert.equal($("#mesh-width").value,"1");await restore(saved);assert.equal($("#mesh-width").value,"1000");assert.equal($("#mesh-preset").value,"coarse");
await change("#mesh-target","pi4");await click("#mesh-check");assert.match($("#mesh-feedback").textContent,/19 \/ 256 filaments/);
await change("#mesh-width","0");await click("#mesh-check",true);assert.match($("#error").textContent,/positive/);
await change("#mesh-preset","coarse");assert.equal($("#error").hidden,true,"Changing the mesh clears the stale failure message");
call.destroy();w.close();console.log("Actual mesh DOM handlers passed: visible shared fields, 360-filament rejection before simulation, fit to 60, successful Pi2, invalidation, presets, native pad counts and project save/restore.");
