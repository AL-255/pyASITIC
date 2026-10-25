// Real edit/project/export/model DOM handlers with packaged Python and WASM.
import{readFileSync,readdirSync}from'node:fs';import{gunzipSync}from'node:zlib';import{pathToFileURL}from'node:url';import assert from'node:assert/strict';
import{installNumericalKernels}from'../web/numeric-kernels.mjs';import{circuitSVG,sweepSVG,transformerSVG}from'../web/analysis-views.mjs';
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();py.unpackArchive(new Uint8Array(readFileSync(new URL('../dist/reasitic.zip',import.meta.url))),'zip');await installNumericalKernels(py,readFileSync(new URL('../dist/numeric.wasm',import.meta.url)));
const root='/breakup',fixtures={},names=new Set(['breakup_original.json.gz','breakup_sessions_original.json.gz','breakup_plain_outcomes_original.json.gz']);
for(const name of [...names]){const f=JSON.parse(gunzipSync(readFileSync(new URL('../tests/fixtures/'+name,import.meta.url))));fixtures[name]=f;for(const file of Object.keys(f.parents||{}))names.add(file);}
py.FS.mkdirTree(root+'/tests/fixtures');py.FS.mkdirTree(root+'/tools');
for(const name of names)py.FS.writeFile(root+'/tests/fixtures/'+name,readFileSync(new URL('../tests/fixtures/'+name,import.meta.url)));
for(const name of readdirSync(new URL('.',import.meta.url)).filter(n=>n.endsWith('.py')))py.FS.writeFile(root+'/tools/'+name,readFileSync(new URL(name,import.meta.url)));
for(const name of['test_breakup_original','test_breakup_sessions_original','test_spatial_sessions_original'])py.FS.writeFile(root+'/tests/'+name+'.py',readFileSync(new URL('../tests/'+name+'.py',import.meta.url)));
py.runPython(`
import sys,unittest
sys.path[:0]=['${root}/tests','${root}/tools']
from reasitic.mutual_kernel import _compiled_mutual
from reasitic.impedance import _compiled_assembly
assert _compiled_mutual is not None and _compiled_assembly is not None
from test_breakup_original import BreakupTests
from test_breakup_sessions_original import BreakupSessionTests
assert unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(c)for c in(BreakupTests,BreakupSessionTests))).wasSuccessful()
from reasitic.bridge import request_json
`);
const call=py.globals.get('request_json'),{JSDOM}=await import(pathToFileURL(process.argv[3]).href),dom=new JSDOM(readFileSync(new URL('../dist/index.html',import.meta.url),'utf8'),{url:'https://example.test/',runScripts:'outside-only'}),w=dom.window,downloads=[];
const inputJSON=value=>JSON.stringify(value,(_k,v)=>Object.is(v,-0)?'-0':v);
Object.assign(w,{circuitSVG,sweepSVG,transformerSVG,Blob});w.URL.createObjectURL=blob=>{downloads.push(blob);return'blob:test';};w.URL.revokeObjectURL=()=>{};w.HTMLAnchorElement.prototype.click=()=>{};
w.Worker=class{constructor(){queueMicrotask(()=>this.onmessage({data:{ready:true}}));}postMessage({id,request}){queueMicrotask(()=>this.onmessage({data:{id,...JSON.parse(call(inputJSON(request)))}}));}};
const source=readFileSync(new URL('../dist/app.js',import.meta.url),'utf8').replace(/^import[^\n]+\n/,'').replaceAll('import.meta.url','"https://example.test/app.js"');w.eval(source+'\nglobalThis.breakupState=()=>({ready,busy,current,currentDefinition,technology,pi2Result,transformerResult});');
const $=s=>w.document.querySelector(s),state=()=>w.breakupState(),bits=v=>{const b=Buffer.alloc(8);b.writeDoubleLE(v);return b.toString('hex');};
async function idle(){for(let i=0;i<1000;i++){await new Promise(setImmediate);if(state().ready&&!state().busy)return;}throw Error('Breakup app did not become idle');}
async function click(id,error=false){assert.equal($(id).disabled,false,id+' disabled');$(id).click();await idle();assert.equal($('#error').hidden,!error,$('#error').textContent);}
async function change(id,value){$(id).value=String(value);$(id).dispatchEvent(new w.Event('change'));await idle();}
async function restore(project){Object.defineProperty($('#project-file'),'files',{configurable:true,value:[{text:async()=>inputJSON(project)}]});$('#project-file').dispatchEvent(new w.Event('change'));await idle();assert.equal($('#error').hidden,true,$('#error').textContent);}
function exact(snapshot){
 const native=[...snapshot.shapes].reverse(),actual=state().current;assert.deepEqual(Array.from(actual.windings),native.map(s=>s.name));const n=native[actual.winding];assert.equal(actual.name,n.name);assert.equal(actual.origin.map(bits).join(''),n.origin_bits);assert.equal(actual.segments.length,n.segments.length);
 for(const[s,r]of actual.segments.map((s,i)=>[s,n.segments[i]])){
  assert.equal(['start','end','outer_start','outer_end','inner_start','inner_end'].flatMap(k=>Array.from(s[k])).map(bits).join(''),r.coordinates_bits);assert.equal(bits(s.width),r.width_bits);assert.equal(s.metal,r.metal);
  if(r.thickness_bits)assert.equal(bits(s.thickness),r.thickness_bits);else assert.deepEqual([s.nx,s.ny],[r.nx,r.ny]);
 }
 for(let i=0;i<native.length;i++){assert.equal(actual.partners[i]===null?null:actual.windings[actual.partners[i]],native[i].partner);assert.equal(!!actual.dangling_partners[i],native[i].dangling_partner);}
 assert.ok(!/NaN|Infinity/.test($('#drawing').outerHTML));
}
async function edit(op,error=false){
 if((state().currentDefinition.winding||0)!==(op.winding??0))await change('#active-winding',op.winding??0);
 const command=['DEMOLISH','SP2WIRE','BREAKUP'].includes(op.command)?'SPTOWIRE':op.command;await change('#edit-command',command);
 if('x'in op)$('#edit-x').value=String(op.x);if('y'in op)$('#edit-y').value=String(op.y);if('phase'in op)$('#edit-phase').value=String(op.phase);if('name'in op)$('#edit-name').value=op.name;if('index'in op)$('#edit-index').value=String(op.index);
 if(command==='SPTOWIRE')for(const id of['edit-x-field','edit-y-field','edit-name-field','edit-index-field','edit-metal-field','edit-origin-field'])assert.equal($('#'+id).hidden,true,id);
 await click('#edit-apply',error);
}
async function gds(snapshot){
 await click('#download-gds');const data=Buffer.from(await downloads.at(-1).arrayBuffer()),polygons=[];let layer,datatype;
 for(let at=0;at<data.length;){const size=data.readUInt16BE(at),type=data[at+2];assert.ok(size>=4&&at+size<=data.length);if(type===13)layer=data.readInt16BE(at+4);if(type===14)datatype=data.readInt16BE(at+4);if(type===16){const points=[];for(let p=at+4;p<at+size;p+=8)points.push([data.readInt32BE(p),data.readInt32BE(p+4)]);polygons.push({layer,datatype,points});}at+=size;}
 let position=0;const tech=state().technology;
 for(const n of [...snapshot.shapes].reverse()){
  const origin=Buffer.from(n.origin_bits,'hex'),ox=origin.readDoubleLE(),oy=origin.readDoubleLE(8);
  for(const s of n.segments){
   if(s.metal<tech.metals.length){const raw=Buffer.from(s.coordinates_bits,'hex'),points=[6,9,15,12,6].map(k=>[roundEven((raw.readDoubleLE(8*k)+ox)*1000),roundEven((raw.readDoubleLE(8*(k+1))+oy)*1000)]);assert.deepEqual(polygons[position].points,points);assert.deepEqual([polygons[position].layer,polygons[position].datatype],[s.metal+1,0]);position++;}
   else{const index=s.metal-tech.metals.length,via=tech.vias[index],layers=[via.bottom+1,via.top+1,...Array(s.nx*s.ny).fill(100+index)];assert.deepEqual(polygons.slice(position,position+layers.length).map(p=>p.layer),layers);position+=layers.length;}
  }
 }
 assert.equal(position,polygons.length);
}
function roundEven(v){const n=Math.floor(v),f=v-n;return f<.5?n:f>.5?n+1:n%2?n+1:n;}
await idle();let states=0;
for(const c of fixtures['breakup_original.json.gz'].cases){
 await restore({format:'reasitic-project',version:1,shape:c.public,technology:c.technology});
 for(let i=0;i<c.states.length;i++){
  if(i)await edit(c.operations[i-1]);
  for(let index=0;index<state().current.windings.length;index++){if(state().current.winding!==index)await change('#active-winding',index);exact(c.states[i]);}
  await gds(c.states[i]);await click('#download-project');const saved=JSON.parse(await downloads.at(-1).text());await restore(saved);exact(c.states[i]);await click('#generate');exact(c.states[i]);states++;
 }
 if(c.signal){const previous=inputJSON(state().currentDefinition.edits);await change('#active-winding',1);await change('#edit-command','SPTOWIRE');assert.equal($('#edit-apply').disabled,true);$('#edit-apply').click();await idle();const result=JSON.parse(call(inputJSON({...c.public,action:'build',technology:c.technology,edits:c.operations})));assert.match(result.error,/SPTOWIRE faults on an empty segment chain/);assert.equal(inputJSON(state().currentDefinition.edits),previous);}
 await click('#edit-undo');exact(c.states.at(-2));console.log('Original breakup UI history',c.label,'passed');
}
assert.equal(states,111);
function modelExact(result,c){
 const y=result.admittance_matrix,values=[y[1][1],y[1][0],y[0][1],y[0][0]].flat();
 if(c.request.action==='calctrans'){
  const z=result.impedance_matrix,keys=['first_inductance_h','second_inductance_h','first_resistance_ohm','second_resistance_ohm','ground_resistance_ohm','mutual_h','coupling'];assert.deepEqual(values.concat([z[0][0],z[0][1],z[1][0],z[1][1]].flat(),keys.map(k=>result.model[k])).map(bits),c.raw_output_bits.slice(0,23));assert.deepEqual(result.scattering_matrix.flat(2).map(bits),c.records[0].S);
 }else{
  assert.deepEqual(values.map(bits),c.model.Y);const keys=['inductance_h','resistance_ohm','capacitance_first_f','capacitance_second_f','resistance_first_ohm','resistance_second_ohm','q_first','q_second','q_differential','shunt_single_ohm','shunt_differential_ohm'];
  [result.frequency_hz,...keys.map(k=>result.pi[k])].forEach((v,i)=>{const target=Buffer.from(c.model.M[i],'hex').readDoubleLE();if(Number.isFinite(target))assert.equal(bits(v),c.model.M[i]);else assert.equal(v,null);});assert.deepEqual(result.scattering_matrix.flat(2).map(bits),c.scattering.S);
 }
}
for(const c of fixtures['breakup_sessions_original.json.gz'].cases){
 const r=c.request;await restore({format:'reasitic-project',version:1,shape:{kind:r.kind,parameters:r.parameters,edits:r.edits,...Object.fromEntries(['native_keyword','native_interactive'].filter(k=>k in r).map(k=>[k,r[k]]))},technology:r.technology,mesh:r.mesh});await change('#active-winding',r.winding);$('#frequency').value=String(r.frequency_ghz);$('#eddy-mode').checked=r.eddy;
 const coupled=r.action==='calctrans';if(coupled){await change('#other-winding',r.second_winding);$('#transformer-termination').value=String(r.termination_ohm);await change('#transformer-ground-mode','none');}else await change('#model-ground-mode','none');
 await click(coupled?'#transformer-run':'#pi2');modelExact(coupled?state().transformerResult:state().pi2Result,c);await click(coupled?'#download-transformer':'#download-pi2');modelExact(JSON.parse(await downloads.at(-1).text()),c);
}
call.destroy();w.close();console.log(JSON.stringify({states,coordinate_words:22788,finite_models:7,native_faults:1,project_gds_selection_undo_and_model_downloads:'passed'}));
