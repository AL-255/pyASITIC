// Original scene copies/name/link histories through real webpage/Pyodide flows.
import{readFileSync}from'node:fs';import{gunzipSync}from'node:zlib';import{pathToFileURL}from'node:url';import assert from'node:assert/strict';
import{installNumericalKernels}from'../web/numeric-kernels.mjs';import{circuitSVG,sweepSVG,transformerSVG}from'../web/analysis-views.mjs';
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();py.unpackArchive(new Uint8Array(readFileSync(new URL('../dist/reasitic.zip',import.meta.url))),'zip');await installNumericalKernels(py,readFileSync(new URL('../dist/numeric.wasm',import.meta.url)));
const fixtures={};py.FS.mkdirTree('/copies/tests/fixtures');
for(const name of['copy_links_original','copy_sessions_original']){const data=readFileSync(new URL('../tests/fixtures/'+name+'.json.gz',import.meta.url));fixtures[name]=JSON.parse(gunzipSync(data));py.FS.writeFile('/copies/tests/fixtures/'+name+'.json.gz',data);}
for(const name of Object.keys(fixtures.copy_links_original.parents))py.FS.writeFile('/copies/tests/fixtures/'+name+'.json',readFileSync(new URL('../tests/fixtures/'+name+'.json',import.meta.url)));
for(const name of Object.keys(fixtures.copy_sessions_original.parents))py.FS.writeFile('/copies/tests/fixtures/'+name,readFileSync(new URL('../tests/fixtures/'+name,import.meta.url)));
for(const name of['test_copy_links_original','test_copy_sessions_original','test_spatial_sessions_original'])py.FS.writeFile('/copies/tests/'+name+'.py',readFileSync(new URL('../tests/'+name+'.py',import.meta.url)));
try{py.runPython(`
import sys,unittest
sys.path.insert(0,'/copies/tests')
from test_copy_links_original import OriginalCopyLinkTests
from test_copy_sessions_original import OriginalCopySessionTests
suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(c)for c in(OriginalCopyLinkTests,OriginalCopySessionTests))
assert unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful()
from reasitic.bridge import request_json
`);}catch(error){console.error(String(error));process.exit(1);}
const call=py.globals.get('request_json'),{JSDOM}=await import(pathToFileURL(process.argv[3]).href),dom=new JSDOM(readFileSync(new URL('../dist/index.html',import.meta.url),'utf8'),{url:'https://example.test/',runScripts:'outside-only'}),w=dom.window,downloads=[],requests=[];
Object.assign(w,{circuitSVG,sweepSVG,transformerSVG,Blob});w.URL.createObjectURL=blob=>{downloads.push(blob);return'blob:test';};w.URL.revokeObjectURL=()=>{};w.HTMLAnchorElement.prototype.click=()=>{};
const inputJSON=value=>JSON.stringify(value,(_key,v)=>Object.is(v,-0)?'-0':v),inputNumber=value=>Object.is(value,-0)?'-0':String(value);
w.Worker=class{constructor(){queueMicrotask(()=>this.onmessage({data:{ready:true}}));}postMessage({id,request}){requests.push(request);queueMicrotask(()=>this.onmessage({data:{id,...JSON.parse(call(inputJSON(request)))}}));}};
const source=readFileSync(new URL('../dist/app.js',import.meta.url),'utf8').replace(/^import[^\n]+\n/,'').replaceAll('import.meta.url','"https://example.test/app.js"');w.eval(source+'\nglobalThis.copyState=()=>({ready,busy,current,currentDefinition,technology,pi2Result,transformerResult});');
const $=s=>w.document.querySelector(s),state=()=>w.copyState();
async function idle(){for(let i=0;i<1000;i++){await new Promise(setImmediate);if(state().ready&&!state().busy)return;}throw Error('Copy app did not become idle');}
async function click(id,expectedError=false){assert.equal($(id).disabled,false,id+' disabled');$(id).click();await idle();assert.equal($('#error').hidden,!expectedError,$('#error').textContent);}
async function change(id,value){$(id).value=String(value);$(id).dispatchEvent(new w.Event('change'));await idle();}
async function restore(project){Object.defineProperty($('#project-file'),'files',{configurable:true,value:[{text:async()=>inputJSON(project)}]});$('#project-file').dispatchEvent(new w.Event('change'));await idle();assert.equal($('#error').hidden,true,$('#error').textContent);}
function bits(value){const b=Buffer.alloc(8);b.writeDoubleLE(value);return b.toString('hex');}
function exact(snapshot){const actual=state().current,native=snapshot.shapes.find(s=>s.name===actual.name);assert.ok(native,actual.name);assert.equal(actual.origin.map(bits).join(''),native.origin_bits);assert.equal(actual.segments.length,native.segments.length);for(const[s,r]of actual.segments.map((s,i)=>[s,native.segments[i]])){assert.equal(['start','end','outer_start','outer_end','inner_start','inner_end'].flatMap(k=>Array.from(s[k])).map(bits).join(''),r.coordinates_bits);assert.equal(bits(s.width),r.width_bits);assert.equal(s.metal,r.metal);if(r.thickness_bits)assert.equal(bits(s.thickness),r.thickness_bits);else assert.deepEqual([s.nx,s.ny],[r.nx,r.ny]);}assert.deepEqual(Array.from(actual.windings).sort(),snapshot.shapes.map(s=>s.name).sort());for(let i=0;i<actual.windings.length;i++){const ref=snapshot.shapes.find(s=>s.name===actual.windings[i]);assert.equal(actual.partners[i]===null?null:actual.windings[actual.partners[i]],ref.partner);}}
async function edit(op,expectedError=false){
 if((state().currentDefinition.winding||0)!==(op.winding??0))await change('#active-winding',op.winding??0);await change('#edit-command',op.command);
 if('name'in op)$('#edit-name').value=op.name;if('other'in op)$('#edit-other').value=String(op.other);
 if(op.command==='COPY'){
  const index='metal'in op?state().technology.metals.findIndex(m=>m.name.toUpperCase()===String(op.metal).toUpperCase()): -1;await change('#edit-metal',index<0?'':index);$('#edit-keep-origin').checked= !('x'in op&&'y'in op);$('#edit-keep-origin').dispatchEvent(new w.Event('change'));
 }
 if('angle'in op)$('#edit-x').value=inputNumber(op.angle);if('x'in op)$('#edit-x').value=inputNumber(op.x);if('y'in op)$(op.command==='MOVEY'?'#edit-x':'#edit-y').value=inputNumber(op.y);await click('#edit-apply',expectedError);
}
function roundEven(v){const n=Math.floor(v),f=v-n;return f<.5?n:f>.5?n+1:n%2?n+1:n;}
async function gds(snapshot){
 await click('#download-gds');const data=Buffer.from(await downloads.at(-1).arrayBuffer()),polygons=[];let layer,datatype;
 for(let at=0;at<data.length;){const n=data.readUInt16BE(at),t=data[at+2];assert.ok(n>=4&&at+n<=data.length);if(t===13)layer=data.readInt16BE(at+4);if(t===14)datatype=data.readInt16BE(at+4);if(t===16){const points=[];for(let p=at+4;p<at+n;p+=8)points.push([data.readInt32BE(p),data.readInt32BE(p+4)]);polygons.push({layer,datatype,points});}at+=n;}
 let position=0;const tech=state().technology;
 for(const name of state().current.windings){const native=snapshot.shapes.find(s=>s.name===name),origin=Buffer.from(native.origin_bits,'hex'),ox=origin.readDoubleLE(),oy=origin.readDoubleLE(8);for(const s of native.segments){if(s.metal<tech.metals.length){const b=Buffer.from(s.coordinates_bits,'hex'),points=[6,9,15,12,6].map(k=>[roundEven((b.readDoubleLE(8*k)+ox)*1000),roundEven((b.readDoubleLE(8*(k+1))+oy)*1000)]);assert.deepEqual(polygons[position].points,points);assert.deepEqual([polygons[position].layer,polygons[position].datatype],[s.metal+1,0]);position++;}else{const index=s.metal-tech.metals.length,v=tech.vias[index],layers=[v.bottom+1,v.top+1,...Array(s.nx*s.ny).fill(100+index)];assert.deepEqual(polygons.slice(position,position+layers.length).map(p=>p.layer),layers);position+=layers.length;}}}
 assert.equal(position,polygons.length);
}
await idle();let valid=0,rejected=0;
for(const c of fixtures.copy_links_original.cases){
 await restore({format:'reasitic-project',version:1,shape:c.public,technology:c.technology});
 for(let i=0;i<c.states.length;i++){
  const op=c.operations[i-1];
  if(c.label==='copy-used'&&i===2){const before=inputJSON(state().currentDefinition);await edit(op,true);assert.match($('#error').textContent,/Cannot copy using/);assert.equal(inputJSON(state().currentDefinition),before);assert.equal(c.states[i].shapes[0].segments.length,0);exact(c.states[i-1]);rejected++;continue;}
  if(i)await edit(op);
  // Original four-argument COPY parses X but keeps the source origin. Preserve
  // that imported input history as well as testing the equivalent UI choice.
  if(op?.command==='COPY'&&'x'in op&&!('y'in op))await restore({format:'reasitic-project',version:1,shape:{...c.public,edits:c.operations.slice(0,i)},technology:c.technology});
  for(let index=0;index<state().current.windings.length;index++){if((state().currentDefinition.winding||0)!==index)await change('#active-winding',index);exact(c.states[i]);}
  if(state().current.windings.length>2){assert.equal($('#transformer-run').disabled,false);assert.equal($('#mesh-target option[value=calctrans]').disabled,false);assert.equal($('#other-winding').options.length,state().current.windings.length-1);}
  await gds(c.states[i]);await click('#download-project');const saved=JSON.parse(await downloads.at(-1).text()),history=inputJSON(saved.shape.edits||[]);await restore(saved);exact(c.states[i]);await click('#generate');exact(c.states[i]);assert.equal(inputJSON(state().currentDefinition.edits||[]),history);valid++;
 }
 console.log('Original copy/link UI history',c.label,'passed');
}
assert.deepEqual([valid,rejected],[228,1]);
// Undo/reset must recover if the selected copied object is removed.
for(const kind of['wire','symmetric_square','symmetric_polygon','transformer','transformer3d']){
 await restore({format:'reasitic-project',version:1,shape:{kind,parameters:{},native_interactive:true}});const sourceName=state().current.name;await edit({command:'COPY',winding:0,name:'newcopy'});const index=state().current.windings.length-1;await change('#active-winding',index);const before=inputJSON(state().current.segments);await click('#download-project');await restore(JSON.parse(await downloads.at(-1).text()));await click('#generate');await change('#active-winding',index);assert.equal(inputJSON(state().current.segments),before);assert.equal(state().current.name,'NEWCOPY');await click('#edit-undo');assert.equal(state().currentDefinition.winding,0);assert.equal(state().current.name,sourceName);await edit({command:'COPY',winding:0,name:'newcopy'});await change('#active-winding',state().current.windings.length-1);await click('#edit-reset');assert.equal(state().current.name,sourceName);
}
function pi(r,c){const y=r.admittance_matrix,keys=['inductance_h','resistance_ohm','capacitance_first_f','capacitance_second_f','resistance_first_ohm','resistance_second_ohm','q_first','q_second','q_differential','shunt_single_ohm','shunt_differential_ohm'];assert.deepEqual([y[1][1],y[1][0],y[0][1],y[0][0]].flat().map(bits),c.model.Y);[r.frequency_hz,...keys.map(k=>r.pi[k])].forEach((v,i)=>{if(Number.isFinite(Buffer.from(c.model.M[i],'hex').readDoubleLE()))assert.equal(bits(v),c.model.M[i]);else assert.equal(v,null);});assert.deepEqual(r.scattering_matrix.flat(2).map(bits),c.scattering.S);}
function coupled(r,c){const y=r.admittance_matrix,z=r.impedance_matrix,keys=['first_inductance_h','second_inductance_h','first_resistance_ohm','second_resistance_ohm','ground_resistance_ohm','mutual_h','coupling'];assert.deepEqual([y[1][1],y[1][0],y[0][1],y[0][0],z[0][0],z[0][1],z[1][0],z[1][1]].flat().concat(keys.map(k=>r.model[k])).map(bits),c.raw_output_bits.slice(0,23));assert.deepEqual(r.scattering_matrix.flat(2).map(bits),c.records[0].S);}
for(const c of fixtures.copy_sessions_original.cases){
 const r=c.request;await restore({format:'reasitic-project',version:1,shape:{kind:r.kind,parameters:r.parameters,native_interactive:true},technology:r.technology,mesh:r.mesh});for(const op of r.edits)await edit(op);await change('#active-winding',r.winding);exact(c.geometry_states[0]);$('#frequency').value=String(r.frequency_ghz);$('#eddy-mode').checked=r.eddy;
 const pair=r.action==='calctrans';if(pair){await change('#other-winding',r.second_winding);$('#transformer-termination').value=String(r.termination_ohm);await change('#transformer-ground-mode','none');}
 else{await change('#model-ground-mode',r.ground?'other':'none');if(r.ground)await change('#other-winding',r.ground.winding);}
 await click(pair?'#transformer-run':'#pi2');const result=pair?state().transformerResult:state().pi2Result,check=pair?coupled:pi;check(result,c);await click(pair?'#download-transformer':'#download-pi2');check(JSON.parse(await downloads.at(-1).text()),c);
 if(pair){assert.equal(requests.filter(q=>q.action==='calctrans').at(-1).second_winding,r.second_winding);await click('#download-project');const saved=JSON.parse(await downloads.at(-1).text());await restore(saved);assert.equal(Number($('#other-winding').value),r.second_winding);}
 // The global other-winding selector also routes CAP and Pi ground requests.
 await change('#model-ground-mode','other');await change('#other-winding',0);await change('#mesh-target','pi2');await click('#mesh-check');const mesh=requests.filter(q=>q.action==='mesh').at(-1);assert.equal(mesh.model,'pi2');assert.equal(mesh.ground.winding,0);assert.deepEqual(mesh.ground.edits,mesh.edits);$('#cap-ground').checked=true;
 const nonfinite=fixtures.copy_sessions_original.cap_reference_failures.find(q=>q.label===c.label);await click('#capacitance',!!nonfinite);if(nonfinite)assert.match($('#error').textContent,/Original CAP reduction is nonfinite/);assert.equal(requests.filter(q=>q.action==='capacitance').at(-1).ground.winding,0);
}
// Automatic fitting must preserve the copied selection and the replay history.
const copied=fixtures.copy_sessions_original.cases.find(c=>c.label==='wire/pi2').request;
await restore({format:'reasitic-project',version:1,shape:{kind:copied.kind,parameters:copied.parameters,native_interactive:true,winding:copied.winding,other_winding:0,edits:copied.edits},technology:copied.technology,
 mesh:{length_cell:1,width_cell:.1,thickness_cell:.1,capacitance_length_cell:1000,capacitance_width_cell:1000,max_width_cells:500},mesh_auto_fit:true});
await change('#model-ground-mode','none');const beforeFit=requests.length;await click('#pi2');
const fitted=requests.slice(beforeFit),solve=fitted.find(q=>q.action==='pi2');assert.equal(fitted.filter(q=>q.fit).length,1);assert.equal(solve.winding,copied.winding);assert.deepEqual(JSON.parse(inputJSON(solve.edits)),copied.edits);
assert.ok(state().pi2Result.filaments<=256);assert.equal(state().current.name,'C_FINAL');assert.equal(Number($('#other-winding').value),0);
await click('#download-project');const fittedProject=JSON.parse(await downloads.at(-1).text());assert.equal(fittedProject.mesh_auto_fit,true);assert.equal(fittedProject.shape.winding,copied.winding);assert.deepEqual(fittedProject.shape.edits,copied.edits);
call.destroy();w.close();console.log('All 229 original copy/name/link states: 228 exact scenes / 117,630 XYZ stores, native rejections and duplicate-copy diagnostic, every scene/winding/project/GDS flow, self/one-way links, ignored COPY X, removed-selection undo/reset, port/reference selection, automatic mesh fitting of a copied winding and five full copied-model JSON downloads, including a VIA copied onto a conductor metal, passed.');
