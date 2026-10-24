// All original spatial states through actual webpage actions and real Pyodide.
import{readFileSync}from'node:fs';import{gunzipSync}from'node:zlib';import{pathToFileURL}from'node:url';import assert from'node:assert/strict';
import{installNumericalKernels}from'../web/numeric-kernels.mjs';import{circuitSVG,sweepSVG,transformerSVG}from'../web/analysis-views.mjs';
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();py.unpackArchive(new Uint8Array(readFileSync(new URL('../dist/reasitic.zip',import.meta.url))),'zip');await installNumericalKernels(py,readFileSync(new URL('../dist/numeric.wasm',import.meta.url)));
const fixtures={};py.FS.mkdirTree('/edits/tests/fixtures');
for(const name of['spatial_edits_original','rotation_points_original','spatial_sessions_original']){const data=readFileSync(new URL('../tests/fixtures/'+name+'.json.gz',import.meta.url));fixtures[name]=JSON.parse(gunzipSync(data));py.FS.writeFile('/edits/tests/fixtures/'+name+'.json.gz',data);}
for(const name of Object.keys(fixtures.spatial_edits_original.parents))py.FS.writeFile('/edits/tests/fixtures/'+name+'.json',readFileSync(new URL('../tests/fixtures/'+name+'.json',import.meta.url)));
for(const name of Object.keys(fixtures.spatial_sessions_original.parents))py.FS.writeFile('/edits/tests/fixtures/'+name,readFileSync(new URL('../tests/fixtures/'+name,import.meta.url)));
for(const name of['test_spatial_edits_original','test_spatial_sessions_original'])py.FS.writeFile('/edits/tests/'+name+'.py',readFileSync(new URL('../tests/'+name+'.py',import.meta.url)));
try{py.runPython(`
import sys,unittest
sys.path.insert(0,'/edits/tests')
from test_spatial_edits_original import OriginalSpatialEditTests
from test_spatial_sessions_original import OriginalSpatialSessionTests
suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(c)for c in(OriginalSpatialEditTests,OriginalSpatialSessionTests))
assert unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful()
from reasitic.bridge import request_json
`);}catch(error){console.error(String(error));process.exit(1);}
const call=py.globals.get('request_json'),{JSDOM}=await import(pathToFileURL(process.argv[3]).href),dom=new JSDOM(readFileSync(new URL('../dist/index.html',import.meta.url),'utf8'),{url:'https://example.test/',runScripts:'outside-only'}),w=dom.window,downloads=[],requests=[];
Object.assign(w,{circuitSVG,sweepSVG,transformerSVG,Blob});w.URL.createObjectURL=blob=>{downloads.push(blob);return'blob:test';};w.URL.revokeObjectURL=()=>{};w.HTMLAnchorElement.prototype.click=()=>{};
const inputJSON=value=>JSON.stringify(value,(_key,v)=>Object.is(v,-0)?'-0':v);
w.Worker=class{constructor(){queueMicrotask(()=>this.onmessage({data:{ready:true}}));}postMessage({id,request}){requests.push(request);queueMicrotask(()=>this.onmessage({data:{id,...JSON.parse(call(inputJSON(request)))}}));}};
const source=readFileSync(new URL('../dist/app.js',import.meta.url),'utf8').replace(/^import[^\n]+\n/,'').replaceAll('import.meta.url','"https://example.test/app.js"');w.eval(source+'\nglobalThis.editsState=()=>({ready,busy,current,currentDefinition,technology,pi2Result,transformerResult});');
const $=s=>w.document.querySelector(s),state=()=>w.editsState();
async function idle(){for(let i=0;i<1000;i++){await new Promise(setImmediate);if(state().ready&&!state().busy)return;}throw Error('Edited app did not become idle');}
async function click(id,expectedError=false){assert.equal($(id).disabled,false,id+' disabled');$(id).click();await idle();assert.equal($('#error').hidden,!expectedError,$('#error').textContent);}
async function change(id,value){$(id).value=String(value);$(id).dispatchEvent(new w.Event('change'));await idle();}
async function restore(project){Object.defineProperty($('#project-file'),'files',{configurable:true,value:[{text:async()=>inputJSON(project)}]});$('#project-file').dispatchEvent(new w.Event('change'));await idle();assert.equal($('#error').hidden,true,$('#error').textContent);}
function bits(value){const b=Buffer.alloc(8);b.writeDoubleLE(value);return b.toString('hex');}
function exact(snapshot,index,names){const native=snapshot.shapes.find(s=>s.name===names[index]),actual=state().current;assert.ok(native);assert.equal(actual.name,native.name);assert.equal(actual.origin.map(bits).join(''),native.origin_bits);assert.equal(actual.segments.length,native.segments.length);for(const[s,r]of actual.segments.map((s,i)=>[s,native.segments[i]])){assert.equal(['start','end','outer_start','outer_end','inner_start','inner_end'].flatMap(k=>Array.from(s[k])).map(bits).join(''),r.coordinates_bits);assert.equal(bits(s.width),r.width_bits);assert.equal(s.metal,r.metal);if(r.thickness_bits)assert.equal(bits(s.thickness),r.thickness_bits);else assert.deepEqual([s.nx,s.ny],[r.nx,r.ny]);}}
const inputNumber=value=>Object.is(value,-0)?'-0':String(value);
async function edit(op){if((state().currentDefinition.winding||0)!==op.winding)await change('#active-winding',op.winding);await change('#edit-command',op.command);if('angle'in op)$('#edit-x').value=inputNumber(op.angle);if('x'in op)$('#edit-x').value=inputNumber(op.x);if('y'in op)$(op.command==='MOVEY'?'#edit-x':'#edit-y').value=inputNumber(op.y);await click('#edit-apply');}
function roundEven(v){const n=Math.floor(v),f=v-n;return f<.5?n:f>.5?n+1:n%2?n+1:n;}
async function gds(snapshot,names){
 const tech=state().technology;let outside=false;const expected=[];
 for(const name of names){const native=snapshot.shapes.find(s=>s.name===name),origin=Buffer.from(native.origin_bits,'hex'),ox=origin.readDoubleLE(),oy=origin.readDoubleLE(8);for(const s of native.segments){if(s.metal<tech.metals.length){const b=Buffer.from(s.coordinates_bits,'hex'),points=[6,9,15,12,6].map(k=>[roundEven((b.readDoubleLE(8*k)+ox)*1000),roundEven((b.readDoubleLE(8*(k+1))+oy)*1000)]);outside||=points.flat().some(v=>v< -2147483648||v>2147483647);expected.push({layer:s.metal+1,points});}else{const index=s.metal-tech.metals.length,v=tech.vias[index];expected.push(...[v.bottom+1,v.top+1,...Array(s.nx*s.ny).fill(100+index)].map(layer=>({layer})));}}}
 const before=downloads.length;await click('#download-gds',outside);if(outside){assert.match($('#error').textContent,/signed 32-bit GDS coordinate range/);assert.equal(downloads.length,before);return;}
 const data=Buffer.from(await downloads.at(-1).arrayBuffer()),polygons=[];let layer,datatype;
 for(let at=0;at<data.length;){const length=data.readUInt16BE(at),type=data[at+2];assert.ok(length>=4&&at+length<=data.length);if(type===13)layer=data.readInt16BE(at+4);if(type===14)datatype=data.readInt16BE(at+4);if(type===16){const points=[];for(let p=at+4;p<at+length;p+=8)points.push([data.readInt32BE(p),data.readInt32BE(p+4)]);polygons.push({layer,datatype,points});}at+=length;}
 assert.equal(polygons.length,expected.length);for(const[p,e]of polygons.map((p,i)=>[p,expected[i]])){assert.equal(p.layer,e.layer);assert.equal(p.datatype,0);if(e.points)assert.deepEqual(p.points,e.points);}
}
assert.equal($('#edit-apply').disabled,true);await idle();assert.equal($('#edit-apply').disabled,false);assert.equal($('#edit-undo').disabled,true);let states=0;
for(const c of fixtures.spatial_edits_original.cases){
 await restore({format:'reasitic-project',version:1,shape:c.public,technology:c.technology});assert.equal($('#edit-undo').disabled,true);
 for(let i=0;i<c.states.length;i++){
  if(i)await edit(c.operations[i-1]);
  assert.equal(state().currentDefinition.edits?.length||0,i);assert.equal($('#edit-history').children.length,i);
  for(let index=0;index<c.names.length;index++){if((state().currentDefinition.winding||0)!==index)await change('#active-winding',index);exact(c.states[i],index,c.names);}
  await gds(c.states[i],c.names);await click('#download-project');const saved=JSON.parse(await downloads.at(-1).text());assert.deepEqual(saved.shape.edits||[],JSON.parse(inputJSON(c.operations.slice(0,i))));await restore(saved);exact(c.states[i],saved.shape.winding||0,c.names);
  await click('#generate');exact(c.states[i],0,c.names);assert.equal(state().currentDefinition.edits?.length||0,i);states++;
 }
 await click('#edit-undo');exact(c.states.at(-2),0,c.names);await click('#edit-reset');exact(c.states[0],0,c.names);assert.equal($('#edit-undo').disabled,true);console.log('Original spatial UI history',c.label,c.states.length,'states passed');
}
assert.equal(states,186);
// Omitted native symmetric origins must not be replaced by already edited origins.
for(const kind of['symmetric_square','symmetric_polygon']){
 await restore({format:'reasitic-project',version:1,shape:{kind,parameters:{},native_interactive:true}});await edit({command:'MOVE',winding:0,x:10.123456789,y:-2.3456789});const before=inputJSON(state().current.segments),origin=state().current.origin.map(bits).join('');await click('#download-project');await restore(JSON.parse(await downloads.at(-1).text()));await click('#generate');assert.equal(inputJSON(state().current.segments),before);assert.equal(state().current.origin.map(bits).join(''),origin);
}
const before=inputJSON(state().currentDefinition);await change('#edit-command','ROTATE');$('#edit-x').value='';await click('#edit-apply',true);assert.match($('#error').textContent,/finite number/);assert.equal(inputJSON(state().currentDefinition),before,'Failed edits preserve the active project');
function exactPi(r,c){const y=r.admittance_matrix,keys=['inductance_h','resistance_ohm','capacitance_first_f','capacitance_second_f','resistance_first_ohm','resistance_second_ohm','q_first','q_second','q_differential','shunt_single_ohm','shunt_differential_ohm'];assert.deepEqual([y[1][1],y[1][0],y[0][1],y[0][0]].flat().map(bits),c.model.Y);[r.frequency_hz,...keys.map(k=>r.pi[k])].forEach((v,i)=>{if(Number.isFinite(Buffer.from(c.model.M[i],'hex').readDoubleLE()))assert.equal(bits(v),c.model.M[i]);else assert.equal(v,null);});assert.deepEqual(r.scattering_matrix.flat(2).map(bits),c.scattering.S);}
function exactCoupled(r,c){const y=r.admittance_matrix,z=r.impedance_matrix,keys=['first_inductance_h','second_inductance_h','first_resistance_ohm','second_resistance_ohm','ground_resistance_ohm','mutual_h','coupling'];assert.deepEqual([y[1][1],y[1][0],y[0][1],y[0][0],z[0][0],z[0][1],z[1][0],z[1][1]].flat().concat(keys.map(k=>r.model[k])).map(bits),c.raw_output_bits.slice(0,23));assert.deepEqual(r.scattering_matrix.flat(2).map(bits),c.records[0].S);}
for(const c of fixtures.spatial_sessions_original.cases){
 const r=c.request;await restore({format:'reasitic-project',version:1,shape:{kind:r.kind,parameters:r.parameters,native_keyword:r.native_keyword,native_interactive:r.native_interactive},technology:r.technology,mesh:r.mesh});for(const op of r.edits)await edit(op);if(state().currentDefinition.winding)await change('#active-winding',0);$('#frequency').value=String(r.frequency_ghz);$('#eddy-mode').checked=r.eddy;
 const coupled=r.action==='calctrans',run=coupled?'#transformer-run':'#pi2',download=coupled?'#download-transformer':'#download-pi2',check=coupled?exactCoupled:exactPi;
 if(coupled){$('#transformer-termination').value=String(r.termination_ohm);await change('#transformer-ground-mode','none');}await click(run);check(coupled?state().transformerResult:state().pi2Result,c);assert.deepEqual(JSON.parse(inputJSON(requests.filter(p=>p.action===r.action).at(-1).edits)),r.edits);await click(download);check(JSON.parse(await downloads.at(-1).text()),c);await edit({command:'MOVE',winding:0,x:1,y:1});assert.equal($(download).disabled,true,'An edit invalidates exported models');await click('#edit-undo');assert.equal($(download).disabled,true,'Undo requires a fresh electrical solve');
}
call.destroy();w.close();console.log('All 186 original edit states / 29,052 XYZ stores passed real Generate/edit/undo/reset/project/GDS handlers, including linked windings, zero rotations, grid boundaries, far-away export diagnostics, omitted defaults and all three complete edited model/JSON sessions.');
