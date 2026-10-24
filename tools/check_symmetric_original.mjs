// Original symmetric geometry boundaries and actual webpage creation/model/GDS flows.
import{readFileSync}from"node:fs";
import{pathToFileURL}from"node:url";
import assert from"node:assert/strict";
import{installNumericalKernels}from"../web/numeric-kernels.mjs";
import{circuitSVG,sweepSVG,transformerSVG}from"../web/analysis-views.mjs";
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL("../dist/reasitic.zip",import.meta.url))),"zip");
await installNumericalKernels(py,readFileSync(new URL("../dist/numeric.wasm",import.meta.url)));
const geometry=JSON.parse(readFileSync(new URL("../tests/fixtures/symmetric_geometry_original.json",import.meta.url))),electrical=JSON.parse(readFileSync(new URL("../tests/fixtures/symmetric_sessions_original.json",import.meta.url)));
py.globals.set("symmetric_fixture",JSON.stringify(geometry));
py.runPython(`
import json,struct
from reasitic import Technology,build
from reasitic.bridge import request_json
from reasitic.symmetric_geometry import _compiled_geometry
assert _compiled_geometry is not None
f=json.loads(symmetric_fixture);tech=Technology.from_text(f['technology']);assert len(f['cases'])==114
for i,c in enumerate(f['cases']):
 shape=build(c['kind'],technology=tech,native_keyword=c['native_keyword'],**c['parameters'])
 assert struct.pack('<2d',*shape.origin)==struct.pack('<2d',*c['origin'])
 assert len(shape.segments)==len(c['segments'])
 for s,r in zip(shape.segments,c['segments']):
  assert struct.pack('<18d',*(v for point in s.points for v in point)).hex()==r['coordinates_bits'],('Original symmetric',i)
  assert struct.pack('<d',s.width).hex()==r['width_bits'] and s.metal==r['metal']
  if 'thickness_bits'in r:assert struct.pack('<d',s.thickness).hex()==r['thickness_bits']
  else:assert(s.nx,s.ny)==(r['nx'],r['ny'])
`);
py.runPython(`
from array import array
from _reasitic_numeric import symmetric_geometry as kernel
cfg=array('d',[1,3,2,60,6,15,3,2,2,0]);output=array('d',[123.])* (64*14);before=cfg.tobytes()
assert kernel(cfg,output)>0 and cfg.tobytes()==before
for index,bad in [(0,2),(1,-1),(4,5),(8,1.5),(8,4000)]:
 copy=array('d',cfg);copy[index]=bad;untouched=output.tobytes()
 try:kernel(copy,output)
 except Exception:pass
 else:raise AssertionError('Invalid symmetric batch accepted')
 assert output.tobytes()==untouched
try:kernel(cfg,array('d',[0.])*14)
except Exception:pass
else:raise AssertionError('Undersized symmetric output accepted')
assert kernel(cfg,output)>0 and cfg.tobytes()==before
`);
console.log("114 original symmetric creators / 60,804 XYZ stores and all defined scalar/metal/via fields match in the compiled browser path.");
const call=py.globals.get("request_json"),keys=["inductance_h","resistance_ohm","capacitance_first_f","capacitance_second_f","resistance_first_ohm","resistance_second_ohm","q_first","q_second","q_differential","shunt_single_ohm","shunt_differential_ohm"];
function bits(value){const b=Buffer.alloc(8);b.writeDoubleLE(value);return b.toString("hex");}
function exactGeometry(shape,c){
 assert.deepEqual(Array.from(shape.origin),c.origin);assert.equal(shape.segments.length,c.segments.length);
 shape.segments.forEach((s,i)=>{const values=["start","end","outer_start","outer_end","inner_start","inner_end"].flatMap(k=>Array.from(s[k])),b=Buffer.alloc(144);values.forEach((v,j)=>b.writeDoubleLE(v,8*j));assert.equal(b.toString("hex"),c.segments[i].coordinates_bits);assert.equal(bits(s.width),c.segments[i].width_bits);assert.equal(s.metal,c.segments[i].metal);});
}
function exactModel(result,c){
 const y=result.admittance_matrix;assert.deepEqual([y[1][1],y[1][0],y[0][1],y[0][0]].flat().map(bits),c.model.Y);assert.deepEqual(c.model.Y,c.scattering.Y);
 const model=[result.frequency_hz,...keys.map(k=>result.pi[k])];assert.equal(model.length,c.model.M.length);
 model.forEach((v,i)=>{if(Number.isFinite(Buffer.from(c.model.M[i],"hex").readDoubleLE()))assert.equal(bits(v),c.model.M[i]);else assert.equal(v,null);});
 assert.deepEqual(result.scattering_matrix.flat(2).map(bits),c.scattering.S);
 const raw=Buffer.from(c.resonance.extended_bits,"hex"),exponent=raw.readUInt16LE(8),expected=Number(raw.readBigUInt64LE())*2**((exponent&0x7fff)-16383-63)*(exponent&0x8000?-1:1);assert.equal(result.pi.resonant_frequency_hz,expected);
}
assert.equal(electrical.cases.length,8);
for(const c of electrical.cases){const r=JSON.parse(call(JSON.stringify(c.request)));assert.ok(!r.error,r.error);exactModel(r.result,c);}
for(const c of electrical.invalid_cases){const r=JSON.parse(call(JSON.stringify(c.request)));assert.match(r.error,/coordinates lie outside/);assert.match(c.stdout,/Coordinate out of range/);}
console.log("Eight complete original symmetric Pi2 sessions, including native/typed inputs, reversed phase and eddy, match every Y/model/S/resonance store; original out-of-chip rejection retained.");
const{JSDOM}=await import(pathToFileURL(process.argv[3]).href),dom=new JSDOM(readFileSync(new URL("../dist/index.html",import.meta.url),"utf8"),{url:"https://example.test/",runScripts:"outside-only"}),w=dom.window,downloads=[],requests=[];
Object.assign(w,{circuitSVG,sweepSVG,transformerSVG,Blob});w.URL.createObjectURL=blob=>{downloads.push(blob);return"blob:test";};w.URL.revokeObjectURL=()=>{};w.HTMLAnchorElement.prototype.click=()=>{};
w.Worker=class{constructor(){queueMicrotask(()=>this.onmessage({data:{ready:true}}));}postMessage({id,request}){requests.push(request);queueMicrotask(()=>this.onmessage({data:{id,...JSON.parse(call(JSON.stringify(request)))}}));}};
const source=readFileSync(new URL("../dist/app.js",import.meta.url),"utf8").replace(/^import[^\n]+\n/,"").replaceAll("import.meta.url",'"https://example.test/app.js"');w.eval(source+"\nglobalThis.symmetricState=()=>({ready,busy,current,currentDefinition,pi2Result,technology});");
const $=s=>w.document.querySelector(s),form=$("#geometry-form");
async function idle(){for(let i=0;i<500;i++){await new Promise(setImmediate);const s=w.symmetricState();if(s.ready&&!s.busy)return;}throw Error("Symmetric app did not become idle");}
async function click(id,expectedError=false){assert.equal($(id).disabled,false,id+" disabled");$(id).click();await idle();if(!expectedError)assert.equal($("#error").hidden,true,$("#error").textContent);}
async function restore(project){Object.defineProperty($("#project-file"),"files",{configurable:true,value:[{text:async()=>JSON.stringify(project)}]});$("#project-file").dispatchEvent(new w.Event("change"));await idle();assert.equal($("#error").hidden,true,$("#error").textContent);}
await idle();const selected=geometry.cases.find(c=>c.label==="keyword/symmetric_polygon/6/2/M4/17/-1");assert.ok(selected);
for(const c of [selected,...geometry.cases.filter(c=>c.label.startsWith('defaults/'))]){
 await restore({format:"reasitic-project",version:1,technology:geometry.technology,shape:{kind:c.kind,parameters:c.parameters,native_keyword:true}});
 assert.equal($("#ring-input-note").hidden,false);
 await click("#generate");exactGeometry(w.symmetricState().current,c);assert.equal(w.symmetricState().currentDefinition.native_keyword,true);
 await click("#download-project");const project=JSON.parse(await downloads.at(-1).text());assert.equal(project.shape.native_keyword,true);await restore(project);exactGeometry(w.symmetricState().current,c);
}
// Derived default edits remain explicit, while unchanged defaults survive repeated regeneration.
form.elements.namedItem("inner_gap").value="15.375";await click("#generate");
assert.equal(w.symmetricState().currentDefinition.parameters.inner_gap,15.375);
assert.equal("x"in w.symmetricState().currentDefinition.parameters,false);
const edited=JSON.stringify(w.symmetricState().current.segments),editedOrigin=Array.from(w.symmetricState().current.origin);
await click("#generate");assert.equal(JSON.stringify(w.symmetricState().current.segments),edited);assert.deepEqual(Array.from(w.symmetricState().current.origin),editedOrigin);
form.elements.namedItem("x").value=String(editedOrigin[0]+1);await click("#generate");assert.ok("x"in w.symmetricState().currentDefinition.parameters);assert.notEqual(w.symmetricState().current.origin[0],editedOrigin[0]);
// Independently decode every GDS conductor and layer/count for the same original stores.
for(const boundary of geometry.cases){
 const request={action:"gds",kind:boundary.kind,parameters:boundary.parameters,native_keyword:boundary.native_keyword,technology:geometry.technology};
 const response=JSON.parse(call(JSON.stringify(request)));assert.ok(!response.error,response.error);
 const gds=Buffer.from(response.result.base64,"base64");
const polygons=[];let layer,datatype;
for(let offset=0;offset<gds.length;){
 const length=gds.readUInt16BE(offset),kind=gds[offset+2];assert.ok(length>=4&&offset+length<=gds.length);
 if(kind===13)layer=gds.readInt16BE(offset+4);if(kind===14)datatype=gds.readInt16BE(offset+4);
 if(kind===16){const points=[];for(let k=offset+4;k<offset+length;k+=8)points.push([gds.readInt32BE(k),gds.readInt32BE(k+4)]);polygons.push({layer,datatype,points});}offset+=length;
}
function roundEven(value){const low=Math.floor(value),fraction=value-low;return fraction<.5?low:fraction>.5?low+1:low%2?low+1:low;}
let position=0;const technology=w.symmetricState().technology;
for(const segment of boundary.segments){
 if(segment.metal<technology.metals.length){
  const b=Buffer.from(segment.coordinates_bits,"hex"),values=Array.from({length:18},(_,i)=>b.readDoubleLE(8*i));
  const expected=[6,9,15,12,6].map(k=>[roundEven((values[k]+boundary.origin[0])*1000),roundEven((values[k+1]+boundary.origin[1])*1000)]);
  assert.deepEqual(polygons[position].points,expected);assert.equal(polygons[position].layer,segment.metal+1);assert.equal(polygons[position].datatype,0);position++;
 }else{
  const index=segment.metal-technology.metals.length,via=technology.vias[index],expected=[via.bottom+1,via.top+1,...Array(segment.nx*segment.ny).fill(100+index)];
  assert.deepEqual(polygons.slice(position,position+expected.length).map(p=>p.layer),expected);position+=expected.length;
 }
}
assert.equal(position,polygons.length);
}
for(const sample of electrical.cases){
 await restore({format:"reasitic-project",version:1,technology:sample.request.technology,shape:{kind:sample.request.kind,parameters:sample.request.parameters,native_keyword:sample.request.native_keyword},mesh:sample.request.mesh});
 $("#frequency").value=String(sample.request.frequency_ghz);$("#eddy-mode").checked=sample.request.eddy;await click("#pi2");exactModel(w.symmetricState().pi2Result,sample);await click("#download-pi2");exactModel(JSON.parse(await downloads.at(-1).text()),sample);
}
const bad=electrical.invalid_cases[0];await restore({format:"reasitic-project",version:1,technology:bad.request.technology,shape:{kind:bad.request.kind,parameters:bad.request.parameters,native_keyword:true},mesh:bad.request.mesh});$("#frequency").value=String(bad.request.frequency_ghz);await click("#pi2",true);assert.match($("#error").textContent,/coordinates lie outside/);assert.equal($("#download-pi2").disabled,true);
call.destroy();w.close();console.log("Actual symmetric form, effective defaults, named layers, native whole-turn parsing, project/GDS export, native/typed original Pi2 JSON downloads and bounded coordinate failure passed.");
