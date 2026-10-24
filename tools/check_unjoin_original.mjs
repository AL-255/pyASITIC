// Original UNJOIN histories, real model requests and actual DOM/download flows.
import{readFileSync}from'node:fs';import{gunzipSync}from'node:zlib';import{pathToFileURL}from'node:url';import assert from'node:assert/strict';
import{installNumericalKernels}from'../web/numeric-kernels.mjs';import{circuitSVG,sweepSVG,transformerSVG}from'../web/analysis-views.mjs';
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();py.unpackArchive(new Uint8Array(readFileSync(new URL('../dist/reasitic.zip',import.meta.url))),'zip');await installNumericalKernels(py,readFileSync(new URL('../dist/numeric.wasm',import.meta.url)));
const fixtures={};py.FS.mkdirTree('/copies/tests/fixtures');
for(const name of['unjoin_original','unjoin_sessions_original','unjoin_plain_outcomes_original','unjoin_vias_original']){const data=readFileSync(new URL('../tests/fixtures/'+name+'.json.gz',import.meta.url));fixtures[name]=JSON.parse(gunzipSync(data));py.FS.writeFile('/copies/tests/fixtures/'+name+'.json.gz',data);}
for(const fixture of Object.values(fixtures))for(const name of Object.keys(fixture.parents||{}))py.FS.writeFile('/copies/tests/fixtures/'+name,readFileSync(new URL('../tests/fixtures/'+name,import.meta.url)));
for(const name of['test_unjoin_original','test_unjoin_sessions_original','test_erase_original','test_spatial_sessions_original'])py.FS.writeFile('/copies/tests/'+name+'.py',readFileSync(new URL('../tests/'+name+'.py',import.meta.url)));
try{py.runPython(`
import sys,unittest
sys.path.insert(0,'/copies/tests')
from test_unjoin_original import OriginalUnjoinTests
from test_unjoin_sessions_original import OriginalUnjoinSessionTests
suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(c)for c in(OriginalUnjoinTests,OriginalUnjoinSessionTests))
unjoin_units_passed=unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful()
from reasitic.bridge import request_json
`);}catch(error){console.error(String(error));process.exit(1);}
const unitsPassed=py.globals.get('unjoin_units_passed');
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
function exact(snapshot,opaque=false){
 if(!snapshot.shapes.length){assert.equal(state().current.windings.length,0);assert.equal(state().current.segments.length,0);assert.equal(state().current.polygons.length,0);for(const id of['simulate','pi2','lmat','sweep','selfres','mesh-fit','edit-apply'])assert.equal($('#'+id).disabled,true,id);assert.equal($('#edit-reset').disabled,false);return;}const actual=state().current,native=snapshot.shapes.find(s=>s.name===actual.name);assert.ok(native,actual.name);if(opaque){assert.ok(actual.electrical_phase>0&&native.attributes>0);}else assert.equal(actual.electrical_phase,native.attributes);if('dangling_partner'in native)assert.equal(!!actual.dangling_partners[actual.winding],native.dangling_partner);assert.equal(actual.origin.map(bits).join(''),native.origin_bits);assert.equal(actual.segments.length,native.segments.length);for(const[s,r]of actual.segments.map((s,i)=>[s,native.segments[i]])){assert.equal(['start','end','outer_start','outer_end','inner_start','inner_end'].flatMap(k=>Array.from(s[k])).map(bits).join(''),r.coordinates_bits);assert.equal(bits(s.width),r.width_bits);assert.equal(s.metal,r.metal);if(r.thickness_bits)assert.equal(bits(s.thickness),r.thickness_bits);else assert.deepEqual([s.nx,s.ny],[r.nx,r.ny]);}assert.deepEqual(Array.from(actual.windings).sort(),snapshot.shapes.map(s=>s.name).sort());for(let i=0;i<actual.windings.length;i++){const ref=snapshot.shapes.find(s=>s.name===actual.windings[i]);assert.equal(actual.partners[i]===null?null:actual.windings[actual.partners[i]],ref.partner);}}
async function edit(op,expectedError=false){
 if(op.command!=='ERASE'&&(state().currentDefinition.winding||0)!==(op.winding??0))await change('#active-winding',op.winding??0);await change('#edit-command',op.command);
 if(op.command==='JOIN')for(const option of $('#edit-join').options)option.selected=op.others.includes(Number(option.value));
 if(op.command==='ERASE')for(const option of $('#edit-erase').options)option.selected=op.windings.includes(Number(option.value));
 if('index'in op)$('#edit-index').value=String(op.index);
 if('phase'in op)$('#edit-phase').value=String(op.phase);
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
await idle();let checked=0;
function matches(c,i){const native=c.states[i].shapes.find(s=>s.name===state().current.name);exact(c.states[i],c.public.kind==='capacitor'&&native.attributes>0);const empty=state().current.segments.length===0;
 for(const id of['simulate','pi2','lmat','sweep','selfres','mesh-fit'])assert.equal($('#'+id).disabled,empty,id);
 assert.ok(!/NaN|Infinity/.test($('#drawing').outerHTML),'Finite preview coordinates');
 assert.deepEqual(Array.from(state().current.winding_segment_counts),Array.from(state().current.windings,name=>c.states[i].shapes.find(s=>s.name===name).segments.length));
}
for(const c of fixtures.unjoin_original.cases){
 await restore({format:'reasitic-project',version:1,shape:c.public,technology:c.technology});
 for(let i=0;i<c.states.length;i++){
  if(i)await edit(c.operations[i-1]);
  for(let index=0;index<state().current.windings.length;index++){if(state().current.winding!==index)await change('#active-winding',index);matches(c,i);}
  await gds(c.states[i]);await click('#download-project');const saved=JSON.parse(await downloads.at(-1).text());await restore(saved);matches(c,i);await click('#generate');matches(c,i);checked++;
 }
 if(c.signal){const before=inputJSON(state().currentDefinition.edits);await edit(c.operations.at(-1),true);assert.match($('#error').textContent,/faults on an empty segment chain/);assert.equal(inputJSON(state().currentDefinition.edits),before);}
 await click('#edit-undo');matches(c,c.states.length-2);if(state().currentDefinition.edits.length)await click('#edit-reset');else assert.equal($('#edit-reset').disabled,true);matches(c,0);
 console.log('Original UNJOIN UI history',c.label,'passed');
}
assert.equal(checked,178);
function pi(r,c){const y=r.admittance_matrix,keys=['inductance_h','resistance_ohm','capacitance_first_f','capacitance_second_f','resistance_first_ohm','resistance_second_ohm','q_first','q_second','q_differential','shunt_single_ohm','shunt_differential_ohm'];assert.deepEqual([y[1][1],y[1][0],y[0][1],y[0][0]].flat().map(bits),c.model.Y);[r.frequency_hz,...keys.map(k=>r.pi[k])].forEach((v,i)=>{if(Number.isFinite(Buffer.from(c.model.M[i],'hex').readDoubleLE()))assert.equal(bits(v),c.model.M[i]);else assert.equal(v,null);});assert.deepEqual(r.scattering_matrix.flat(2).map(bits),c.scattering.S);}
function coupled(r,c){const y=r.admittance_matrix,z=r.impedance_matrix,keys=['first_inductance_h','second_inductance_h','first_resistance_ohm','second_resistance_ohm','ground_resistance_ohm','mutual_h','coupling'];assert.deepEqual([y[1][1],y[1][0],y[0][1],y[0][0],z[0][0],z[0][1],z[1][0],z[1][1]].flat().concat(keys.map(k=>r.model[k])).map(bits),c.raw_output_bits.slice(0,23));assert.deepEqual(r.scattering_matrix.flat(2).map(bits),c.records[0].S);}
let finite=0,nonfinite=0;const modelFailures=[];
for(const c of fixtures.unjoin_sessions_original.cases){
 const r=c.request,shape={kind:r.kind,parameters:r.parameters,...Object.fromEntries(['native_keyword','native_interactive'].filter(k=>k in r).map(k=>[k,r[k]]))};
 await restore({format:'reasitic-project',version:1,shape,technology:r.technology,mesh:r.mesh});for(const op of r.edits)await edit(op);await change('#active-winding',r.winding);exact(c.geometry_states[0]);$('#frequency').value=String(r.frequency_ghz);$('#eddy-mode').checked=r.eddy;
 const pair=r.action==='calctrans',words=pair?c.raw_output_bits.slice(0,8):c.model.Y,bad=words.some(w=>!Number.isFinite(Buffer.from(w,'hex').readDoubleLE()));
 if(pair){await change('#other-winding',r.second_winding);$('#transformer-termination').value=String(r.termination_ohm);await change('#transformer-ground-mode','none');}else await change('#model-ground-mode','none');
 assert.equal($(pair?'#transformer-run':'#pi2').disabled,false);$(pair?'#transformer-run':'#pi2').click();await idle();
 if(!bad&&!$('#error').hidden){modelFailures.push({label:c.label,kind:'solve',error:$('#error').textContent});finite++;continue;}
 if(bad){nonfinite++;assert.match($('#error').textContent,/contact collapses or exceeds the FFT grid/);continue;}
 const result=pair?state().transformerResult:state().pi2Result,check=pair?coupled:pi;
 for(const [kind,value]of[['live',result],['download',await(async()=>{await click(pair?'#download-transformer':'#download-pi2');return JSON.parse(await downloads.at(-1).text());})()]]){
  try{check(value,c);}catch(error){modelFailures.push({label:c.label,kind,error:String(error)});}
 }
 finite++;
}
assert.equal(finite,8);assert.equal(nonfinite,0);
const failed=fixtures.unjoin_plain_outcomes_original.cases.filter(c=>!c.produced_model);assert.equal(failed.length,1);
for(const c of failed){const r=c.request;await restore({format:'reasitic-project',version:1,shape:{kind:r.kind,parameters:r.parameters,native_interactive:true,edits:r.edits,winding:r.winding},technology:r.technology,mesh:r.mesh});assert.equal(state().current.segments.length,0);assert.equal($('#pi2').disabled,true);const before=requests.length;$('#pi2').click();await idle();assert.equal(requests.length,before);const result=JSON.parse(call(inputJSON(r)));assert.match(result.error,/contains no segments/);}
call.destroy();w.close();console.log(JSON.stringify({geometry_states:checked,xyz_stores:33084,finite_models_checked:finite,native_nonfinite_and_failure_cases:nonfinite+failed.length,unitsPassed,modelFailures}));process.exitCode=unitsPassed&&modelFailures.length===0?0:1;
