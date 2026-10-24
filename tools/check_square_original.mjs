// Original square/contact boundaries and actual webpage creation/model/GDS flows.
import{readFileSync}from"node:fs";
import{pathToFileURL}from"node:url";
import assert from"node:assert/strict";
import{installNumericalKernels}from"../web/numeric-kernels.mjs";
import{circuitSVG,sweepSVG,transformerSVG}from"../web/analysis-views.mjs";
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL("../dist/reasitic.zip",import.meta.url))),"zip");
await installNumericalKernels(py,readFileSync(new URL("../dist/numeric.wasm",import.meta.url)));
const geometry=JSON.parse(readFileSync(new URL("../tests/fixtures/square_original.json",import.meta.url))),electrical=JSON.parse(readFileSync(new URL("../tests/fixtures/square_sessions_original.json",import.meta.url)));
py.globals.set("square_fixture",JSON.stringify(geometry));py.globals.set("contact_fixture",readFileSync(new URL("../tests/fixtures/contact_geometry_original.json",import.meta.url),"utf8"));
py.runPython(`
import json,struct
from types import SimpleNamespace
from reasitic import Technology,build
from reasitic.bridge import request_json
from reasitic.model import Shape,Segment
from reasitic.contact_geometry import groups
from reasitic.potential import Contact
f=json.loads(square_fixture);tech=Technology.from_text(f['technology']);assert len(f['cases'])==126
for i,c in enumerate(f['cases']):
 shape=build('square',technology=tech,native_keyword=c['native_keyword'],**c['parameters'])
 assert struct.pack('<2d',*shape.origin)==struct.pack('<2d',*c['origin'])
 assert len(shape.segments)==len(c['segments'])
 for s,r in zip(shape.segments,c['segments']):
  assert struct.pack('<18d',*(v for point in s.points for v in point)).hex()==r['coordinates_bits'],('Original square',i)
  assert struct.pack('<d',s.width).hex()==r['width_bits'] and s.metal==r['metal']
  if 'thickness_bits'in r:assert struct.pack('<d',s.thickness).hex()==r['thickness_bits']
  else:assert(s.nx,s.ny)==(r['nx'],r['ny'])
builders=contacts=0
for c in json.loads(contact_fixture)['cases']:
 o=c['options'];tech=SimpleNamespace(metals=[None]*o['metal_count'])
 for r in c['records']:
  s=r['segment'];shape=Shape('Probe','wire',r['origin'],{},[Segment(*s['points'],s['width'],0.,s['metal'],s['nx'],s['ny'],s['primary_width'])]);seen=[]
  expected=[a['indices']for a in r['contacts']]
  if all(0<=a<b<=o['nx']and 0<=c<d<=o['ny']for a,b,c,d,_ in expected):
   result=groups(shape,tech,o['nx'],o['ny'],o['width'],o['height'],o['length_step'],o['width_step'],1024,Contact,observe=seen.append)
   assert [[a.x0,a.x1,a.y0,a.y1,a.metal]for a in result[0]]==expected
  else:
   try:groups(shape,tech,o['nx'],o['ny'],o['width'],o['height'],o['length_step'],o['width_step'],1024,Contact,observe=seen.append)
   except ValueError as error:assert 'collapses'in str(error)
   else:raise AssertionError('Original zero-area contact was accepted')
  assert [struct.pack('<4d',*v).hex()for v in reversed(seen)]==[a['bounds_bits']for a in r['contacts']]
  builders+=1;contacts+=len(expected)
assert(builders,contacts)==(280,338)
`);
console.log("126 original square creators / 14,742 XYZ stores and 280 original contact builders / 338 physical/grid contact records passed in WebAssembly, including the bounded native zero-area history.");
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
assert.equal(electrical.cases.length,4);
for(const c of electrical.cases){const r=JSON.parse(call(JSON.stringify(c.request)));assert.ok(!r.error,r.error);exactModel(r.result,c);}
for(const c of electrical.invalid_cases){const r=JSON.parse(call(JSON.stringify(c.request)));assert.match(r.error,/coordinates lie outside/);assert.match(c.stdout,/Coordinate out of range/);}
console.log("Four complete original square Pi2 sessions, including native/typed inputs, reversed phase and eddy, match every Y/model/S/resonance store; original out-of-chip rejection retained.");
const{JSDOM}=await import(pathToFileURL(process.argv[3]).href),dom=new JSDOM(readFileSync(new URL("../dist/index.html",import.meta.url),"utf8"),{url:"https://example.test/",runScripts:"outside-only"}),w=dom.window,downloads=[],requests=[];
Object.assign(w,{circuitSVG,sweepSVG,transformerSVG,Blob});w.URL.createObjectURL=blob=>{downloads.push(blob);return"blob:test";};w.URL.revokeObjectURL=()=>{};w.HTMLAnchorElement.prototype.click=()=>{};
w.Worker=class{constructor(){queueMicrotask(()=>this.onmessage({data:{ready:true}}));}postMessage({id,request}){requests.push(request);queueMicrotask(()=>this.onmessage({data:{id,...JSON.parse(call(JSON.stringify(request)))}}));}};
const source=readFileSync(new URL("../dist/app.js",import.meta.url),"utf8").replace(/^import[^\n]+\n/,"").replaceAll("import.meta.url",'"https://example.test/app.js"');w.eval(source+"\nglobalThis.squareState=()=>({ready,busy,current,currentDefinition,pi2Result,technology});");
const $=s=>w.document.querySelector(s),form=$("#geometry-form");
async function idle(){for(let i=0;i<500;i++){await new Promise(setImmediate);const s=w.squareState();if(s.ready&&!s.busy)return;}throw Error("Square app did not become idle");}
async function click(id,expectedError=false){assert.equal($(id).disabled,false,id+" disabled");$(id).click();await idle();if(!expectedError)assert.equal($("#error").hidden,true,$("#error").textContent);}
async function restore(project){Object.defineProperty($("#project-file"),"files",{configurable:true,value:[{text:async()=>JSON.stringify(project)}]});$("#project-file").dispatchEvent(new w.Event("change"));await idle();assert.equal($("#error").hidden,true,$("#error").textContent);}
await idle();const c=geometry.cases.find(c=>c.label==="keyword/0.5/M3/17/-1");assert.ok(c);
await restore({format:"reasitic-project",version:1,technology:geometry.technology,shape:{kind:"square",parameters:c.parameters,native_keyword:true}});
assert.equal($("#ring-input-note").hidden,false);assert.equal($("#metal").value,"3");assert.equal($("#exit-metal").value,"2");
await click("#generate");exactGeometry(w.squareState().current,c);assert.equal(w.squareState().currentDefinition.native_keyword,true);
// Native F32 turn parsing promotes this near-quarter input before truncation.
const boundary=geometry.cases.find(c=>c.label.startsWith("keyword/turn-boundary/")&&c.parameters.turns===1.74999999);assert.ok(boundary);
for(const[key,value]of Object.entries(boundary.parameters))if(form.elements.namedItem(key))form.elements.namedItem(key).value=key==="metal"?"3":key==="exit_metal"?"2":String(value);
await click("#generate");exactGeometry(w.squareState().current,boundary);assert.equal(w.squareState().current.parameters.turns,1.75);
await click("#download-project");const project=JSON.parse(await downloads.at(-1).text());assert.equal(project.shape.native_keyword,true);await restore(project);exactGeometry(w.squareState().current,boundary);
await click("#download-gds");assert.equal(requests.at(-1).native_keyword,true);const gds=Buffer.from(await downloads.at(-1).arrayBuffer());assert.equal(gds.readUInt16BE(),6);assert.ok(gds.length>100);
const polygons=[];let layer,datatype;
for(let offset=0;offset<gds.length;){
 const length=gds.readUInt16BE(offset),kind=gds[offset+2];assert.ok(length>=4&&offset+length<=gds.length);
 if(kind===13)layer=gds.readInt16BE(offset+4);if(kind===14)datatype=gds.readInt16BE(offset+4);
 if(kind===16){const points=[];for(let k=offset+4;k<offset+length;k+=8)points.push([gds.readInt32BE(k),gds.readInt32BE(k+4)]);polygons.push({layer,datatype,points});}offset+=length;
}
function roundEven(value){const low=Math.floor(value),fraction=value-low;return fraction<.5?low:fraction>.5?low+1:low%2?low+1:low;}
let position=0;const technology=w.squareState().technology;
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
for(const sample of[electrical.cases[0],electrical.cases[3]]){
 await restore({format:"reasitic-project",version:1,technology:sample.request.technology,shape:{kind:"square",parameters:sample.request.parameters,native_keyword:sample.request.native_keyword},mesh:sample.request.mesh});
 $("#frequency").value=String(sample.request.frequency_ghz);await click("#pi2");exactModel(w.squareState().pi2Result,sample);await click("#download-pi2");exactModel(JSON.parse(await downloads.at(-1).text()),sample);
}
const bad=electrical.invalid_cases[0];await restore({format:"reasitic-project",version:1,technology:bad.request.technology,shape:{kind:"square",parameters:bad.request.parameters,native_keyword:true},mesh:bad.request.mesh});$("#frequency").value=String(bad.request.frequency_ghz);await click("#pi2",true);assert.match($("#error").textContent,/coordinates lie outside/);assert.equal($("#download-pi2").disabled,true);
call.destroy();w.close();console.log("Actual square form, named layers, native near-quarter parsing, project/GDS export, native/typed original Pi2 JSON downloads and bounded coordinate failure passed.");
