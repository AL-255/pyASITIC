// Actual original ring stores through Pyodide, webpage forms and GDS download.
import{readFileSync}from"node:fs";
import{pathToFileURL}from"node:url";
import assert from"node:assert/strict";
import{installNumericalKernels}from"../web/numeric-kernels.mjs";
import{circuitSVG,sweepSVG,transformerSVG}from"../web/analysis-views.mjs";
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL("../dist/reasitic.zip",import.meta.url))),"zip");
await installNumericalKernels(py,readFileSync(new URL("../dist/numeric.wasm",import.meta.url)));
const fixture=JSON.parse(readFileSync(new URL("../tests/fixtures/ring_original.json",import.meta.url)));
py.globals.set("ring_fixture",JSON.stringify(fixture));
py.runPython(`
import json,struct
from reasitic.ring import vertices
from reasitic.bridge import request_json
for i,c in enumerate(json.loads(ring_fixture)['cases']):
 rows=vertices(*c['config'])
 assert len(rows)==len(c['rows'])
 for row,expected in zip(rows,c['rows']):assert struct.pack('<12d',*row).hex()==expected,('Original ring',i)
`);
const call=py.globals.get("request_json");
function exact(shape,c){
 assert.deepEqual(Array.from(shape.origin),c.origin);assert.equal(shape.segments.length,c.rows.length);
 shape.segments.forEach((s,i)=>{
  const values=["start","end","outer_start","outer_end","inner_start","inner_end"].flatMap(key=>Array.from(s[key]).slice(0,2)),bytes=Buffer.alloc(96);
  values.forEach((v,j)=>bytes.writeDoubleLE(v,8*j));assert.equal(bytes.toString("hex"),c.rows[i],`Original ring row ${i}`);assert.equal(s.width,c.config[2]);
 });
}
assert.equal(fixture.cases.length,45);
for(const c of fixture.cases){const response=JSON.parse(call(JSON.stringify({action:"build",kind:"ring",parameters:c.parameters,technology:fixture.technology,native_keyword:true})));assert.ok(!response.error,response.error);exact(response.result,c);}
console.log("45 original ring creators / 12,588 exact XY stores and complete native-keyword builds passed in WebAssembly.");
const electrical=JSON.parse(readFileSync(new URL("../tests/fixtures/ring_sessions_original.json",import.meta.url)));
const metricKeys=["inductance_h","resistance_ohm","capacitance_first_f","capacitance_second_f","resistance_first_ohm","resistance_second_ohm","q_first","q_second","q_differential","shunt_single_ohm","shunt_differential_ohm"];
function bits(value){const bytes=Buffer.alloc(8);bytes.writeDoubleLE(value);return bytes.toString("hex");}
function exactSession(result,c){
 const y=result.admittance_matrix;assert.deepEqual([y[1][1],y[1][0],y[0][1],y[0][0]].flat().map(bits),c.model.Y);
 assert.deepEqual(c.model.Y,c.scattering.Y);
 const model=[result.frequency_hz,...metricKeys.map(k=>result.pi[k])];assert.equal(model.length,c.model.M.length);
 model.forEach((value,i)=>{if(Number.isFinite(Buffer.from(c.model.M[i],"hex").readDoubleLE()))assert.equal(bits(value),c.model.M[i]);else assert.equal(value,null);});
 assert.deepEqual(result.scattering_matrix.flat(2).map(bits),c.scattering.S);
 const raw=Buffer.from(c.resonance.extended_bits,"hex"),exponent=raw.readUInt16LE(8),expected=Number(raw.readBigUInt64LE())*2**((exponent&0x7fff)-16383-63)*(exponent&0x8000?-1:1);
 assert.equal(result.pi.resonant_frequency_hz,expected);
}
assert.equal(electrical.cases.length,3);
for(const c of electrical.cases){const response=JSON.parse(call(JSON.stringify(c.request)));assert.ok(!response.error,response.error);exactSession(response.result,c);}
console.log("Three complete original ring Pi2 sessions, including eddy correction, match every Y/model/S and finite resonance store in WebAssembly.");
const{JSDOM}=await import(pathToFileURL(process.argv[3]).href),dom=new JSDOM(readFileSync(new URL("../dist/index.html",import.meta.url),"utf8"),{url:"https://example.test/",runScripts:"outside-only"}),w=dom.window,downloads=[],requests=[];
Object.assign(w,{circuitSVG,sweepSVG,transformerSVG,Blob});w.URL.createObjectURL=blob=>{downloads.push(blob);return"blob:test";};w.URL.revokeObjectURL=()=>{};w.HTMLAnchorElement.prototype.click=()=>{};
w.Worker=class{
 constructor(){queueMicrotask(()=>this.onmessage({data:{ready:true}}));}
 postMessage({id,request}){requests.push(request);queueMicrotask(()=>this.onmessage({data:{id,...JSON.parse(call(JSON.stringify(request)))}}));}
};
const source=readFileSync(new URL("../dist/app.js",import.meta.url),"utf8").replace(/^import[^\n]+\n/,"").replaceAll("import.meta.url",'"https://example.test/app.js"');
w.eval(source+"\nglobalThis.ringState=()=>({ready,busy,current,currentDefinition,pi2Result});");const $=s=>w.document.querySelector(s),form=$("#geometry-form");
async function idle(){for(let i=0;i<500;i++){await new Promise(setImmediate);const s=w.ringState();if(s.ready&&!s.busy)return;}throw Error("Ring app did not become idle");}
async function click(id){assert.equal($(id).disabled,false,id+" disabled");$(id).click();await idle();assert.equal($("#error").hidden,true,$("#error").textContent);}
async function restore(project){Object.defineProperty($("#project-file"),"files",{configurable:true,value:[{text:async()=>JSON.stringify(project)}]});$("#project-file").dispatchEvent(new w.Event("change"));await idle();assert.equal($("#error").hidden,true,$("#error").textContent);}
await idle();const c=fixture.cases[40];
await restore({format:"reasitic-project",version:1,technology:fixture.technology,shape:{kind:"wire",parameters:{length:40,width:3,metal:"M4"}}});
$("#kind").value="ring";$("#kind").dispatchEvent(new w.Event("change"));
assert.equal($("#ring-input-note").hidden,false);
for(const[key,value]of Object.entries(c.parameters))if(form.elements.namedItem(key))form.elements.namedItem(key).value=key==="metal"?"3":String(value);
await click("#generate");exact(w.ringState().current,c);assert.equal(w.ringState().currentDefinition.native_keyword,true);assert.ok($("#drawing polygon"));
await click("#download-project");const project=JSON.parse(await downloads.at(-1).text());assert.equal(project.shape.native_keyword,true);assert.equal(project.shape.parameters.width,c.parameters.width);
Object.assign(project.shape.parameters,{metal:"M4",exit_metal:"m3",bottom_metal:"M2",secondary_metal:"M1",via:"via2"});
await restore(project);exact(w.ringState().current,c);
for(const[id,value]of[["#metal","3"],["#exit-metal","2"],["#bottom-metal","1"],["#secondary-metal","0"],["#via","1"]])assert.equal($(id).value,value,"Named project layer must survive form regeneration");
await click("#download-gds");assert.equal(requests.at(-1).action,"gds");assert.equal(requests.at(-1).native_keyword,true);
// Independently decode the GDS XY records, comparing their nanometre grid
// against captured original ribbons rather than regenerated Python polygons.
const gds=Buffer.from(await downloads.at(-1).arrayBuffer()),polygons=[];let layer,datatype;
for(let offset=0;offset<gds.length;){
 const length=gds.readUInt16BE(offset),kind=gds[offset+2];assert.ok(length>=4&&offset+length<=gds.length);
 if(kind===13)layer=gds.readInt16BE(offset+4);if(kind===14)datatype=gds.readInt16BE(offset+4);
 if(kind===16){const points=[];for(let k=offset+4;k<offset+length;k+=8)points.push([gds.readInt32BE(k),gds.readInt32BE(k+4)]);polygons.push({layer,datatype,points});}
 offset+=length;
}
assert.equal(polygons.length,c.rows.length);
function roundEven(value){const low=Math.floor(value),fraction=value-low;return fraction<.5?low:fraction>.5?low+1:low%2?low+1:low;}
for(let i=0;i<c.rows.length;i++){
 const bytes=Buffer.from(c.rows[i],"hex"),values=Array.from({length:12},(_,j)=>bytes.readDoubleLE(8*j));
 const expected=[4,6,10,8,4].map(k=>[roundEven((values[k]+c.origin[0])*1000),roundEven((values[k+1]+c.origin[1])*1000)]);
 assert.equal(polygons[i].layer,4);assert.equal(polygons[i].datatype,0);assert.deepEqual(polygons[i].points,expected);
}
// Regeneration must preserve native input mode even after project reload.
await click("#generate");exact(w.ringState().current,c);assert.equal(w.ringState().currentDefinition.native_keyword,true);
const sample=electrical.cases[0];await restore({format:"reasitic-project",version:1,technology:sample.request.technology,shape:{kind:"ring",parameters:sample.request.parameters,native_keyword:true},mesh:sample.request.mesh});
$("#frequency").value=String(sample.request.frequency_ghz);await click("#pi2");exactSession(w.ringState().pi2Result,sample);
await click("#download-pi2");exactSession(JSON.parse(await downloads.at(-1).text()),sample);
call.destroy();w.close();console.log("Actual ring form, snap/angle parsing, named-layer project reload/regeneration, independently decoded GDS and original Pi2 model/JSON download passed.");
