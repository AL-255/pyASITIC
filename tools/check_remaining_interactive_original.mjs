// Actual Generate/project/GDS/model handlers with the shipped Python/WASM runtime.
import{readFileSync}from'node:fs';import{gunzipSync}from'node:zlib';import{pathToFileURL}from'node:url';import assert from'node:assert/strict';
import{installNumericalKernels}from'../web/numeric-kernels.mjs';import{circuitSVG,sweepSVG,transformerSVG}from'../web/analysis-views.mjs';
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();py.unpackArchive(new Uint8Array(readFileSync(new URL('../dist/reasitic.zip',import.meta.url))),'zip');await installNumericalKernels(py,readFileSync(new URL('../dist/numeric.wasm',import.meta.url)));
const compressed={};py.FS.mkdirTree('/interactive/tests/fixtures');
for(const name of['paired_interactive_bounds_original','paired_interactive_bounds_sessions_original','primitive_names_original']){const data=readFileSync(new URL('../tests/fixtures/'+name+'.json.gz',import.meta.url));compressed[name]=JSON.parse(gunzipSync(data));py.FS.writeFile('/interactive/tests/fixtures/'+name+'.json.gz',data);}
py.FS.writeFile('/interactive/tests/test_remaining_interactive_original.py',readFileSync(new URL('../tests/test_remaining_interactive_original.py',import.meta.url)));
try{py.runPython(`
import sys,unittest
sys.path.insert(0,'/interactive/tests')
from test_remaining_interactive_original import OriginalRemainingInteractiveTests
assert unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(OriginalRemainingInteractiveTests)).wasSuccessful()
from reasitic.bridge import request_json
`);}catch(error){console.error(String(error));process.exit(1);}
const call=py.globals.get('request_json'),read=name=>JSON.parse(readFileSync(new URL('../tests/fixtures/'+name+'.json',import.meta.url)));
const wire=read('wire_original'),primitive=read('primitive_original'),paired=read('paired_original');
const{JSDOM}=await import(pathToFileURL(process.argv[3]).href),dom=new JSDOM(readFileSync(new URL('../dist/index.html',import.meta.url),'utf8'),{url:'https://example.test/',runScripts:'outside-only'}),w=dom.window,downloads=[],requests=[];
Object.assign(w,{circuitSVG,sweepSVG,transformerSVG,Blob});w.URL.createObjectURL=blob=>{downloads.push(blob);return'blob:test';};w.URL.revokeObjectURL=()=>{};w.HTMLAnchorElement.prototype.click=()=>{};
const inputJSON=value=>JSON.stringify(value,(_key,v)=>Object.is(v,-0)?'-0':v);
w.Worker=class{constructor(){queueMicrotask(()=>this.onmessage({data:{ready:true}}));}postMessage({id,request}){requests.push(request);queueMicrotask(()=>this.onmessage({data:{id,...JSON.parse(call(inputJSON(request)))}}));}};
const source=readFileSync(new URL('../dist/app.js',import.meta.url),'utf8').replace(/^import[^\n]+\n/,'').replaceAll('import.meta.url','"https://example.test/app.js"');w.eval(source+'\nglobalThis.interactiveState=()=>({ready,busy,current,currentDefinition,pi2Result,transformerResult,technology});');
const $=s=>w.document.querySelector(s),form=$('#geometry-form'),state=()=>w.interactiveState();
async function idle(){for(let i=0;i<1000;i++){await new Promise(setImmediate);if(state().ready&&!state().busy)return;}throw Error('Interactive app did not become idle');}
async function click(id,expectedError=false){assert.equal($(id).disabled,false,id+' disabled');$(id).click();await idle();assert.equal($('#error').hidden,!expectedError,$('#error').textContent);}
async function change(id,value){$(id).value=String(value);$(id).dispatchEvent(new w.Event('change'));await idle();}
async function restore(project){Object.defineProperty($('#project-file'),'files',{configurable:true,value:[{text:async()=>inputJSON(project)}]});$('#project-file').dispatchEvent(new w.Event('change'));await idle();assert.equal($('#error').hidden,true,$('#error').textContent);}
function bits(v){const b=Buffer.alloc(8);b.writeDoubleLE(v);return b.toString('hex');}
function definition(c){return{kind:c.kind,parameters:c.parameters,native_interactive:true};}
function exact(shape,c,index=0){
 const native=c.windings?.[index]??c;assert.equal(shape.name,native.name??c.parameters.name);assert.equal(shape.origin.map(bits).join(''),native.origin_bits??native.origin.map(bits).join(''));assert.equal(shape.segments.length,native.segments.length);
 for(const[s,b]of shape.segments.map((s,i)=>[s,native.segments[i]])){
  assert.equal(['start','end','outer_start','outer_end','inner_start','inner_end'].flatMap(k=>Array.from(s[k])).map(bits).join(''),b.coordinates_bits);assert.equal(bits(s.width),b.width_bits);assert.equal(s.metal,b.metal);
  if(b.thickness_bits)assert.equal(bits(s.thickness),b.thickness_bits);else assert.deepEqual([s.nx,s.ny],[b.nx,b.ny]);
 }
 if(c.windings)assert.deepEqual(Array.from(shape.windings),c.windings.map(w=>w.name));
}
function roundEven(v){const a=Math.floor(v),f=v-a;return f<.5?a:f>.5?a+1:a%2?a+1:a;}
async function exactGDS(c){
 await click('#download-gds');const data=Buffer.from(await downloads.at(-1).arrayBuffer()),polygons=[];let layer,datatype;
 for(let at=0;at<data.length;){const length=data.readUInt16BE(at),type=data[at+2];assert.ok(length>=4&&at+length<=data.length);if(type===13)layer=data.readInt16BE(at+4);if(type===14)datatype=data.readInt16BE(at+4);if(type===16){const points=[];for(let k=at+4;k<at+length;k+=8)points.push([data.readInt32BE(k),data.readInt32BE(k+4)]);polygons.push({layer,datatype,points});}at+=length;}
 let position=0;const tech=state().technology;
 for(const winding of c.windings??[c])for(const s of winding.segments){
  if(s.metal<tech.metals.length){const raw=Buffer.from(s.coordinates_bits,'hex'),v=Array.from({length:18},(_,i)=>raw.readDoubleLE(8*i)),expected=[6,9,15,12,6].map(k=>[roundEven((v[k]+winding.origin[0])*1000),roundEven((v[k+1]+winding.origin[1])*1000)]);assert.deepEqual(polygons[position].points,expected);assert.deepEqual([polygons[position].layer,polygons[position].datatype],[s.metal+1,0]);position++;}
  else{const index=s.metal-tech.metals.length,via=tech.vias[index],expected=[via.bottom+1,via.top+1,...Array(s.nx*s.ny).fill(100+index)];assert.deepEqual(polygons.slice(position,position+expected.length).map(p=>p.layer),expected);position+=expected.length;}
 }
 assert.equal(position,polygons.length);
}
await idle();
const histories=[...wire.cases.filter(c=>c.native_interactive).map(c=>({...c,kind:'wire',technology:wire.technology})),...primitive.cases.filter(c=>c.native_interactive).map(c=>({...c,technology:primitive.technology})),...paired.cases.filter(c=>c.native_interactive).map(c=>({...c,technology:paired.technology})),...compressed.paired_interactive_bounds_original.cases,...compressed.primitive_names_original.cases.map(c=>({...c,technology:compressed.primitive_names_original.technology}))];
assert.equal(histories.length,84);
for(const c of histories){
 await restore({format:'reasitic-project',version:1,shape:definition(c),technology:c.technology});exact(state().current,c);
 if(c.kind!=='via'){assert.equal($('#rectangular-input-mode').value,'interactive');assert.equal($('#rectangular-input-mode').disabled,false);assert.equal($('#rectangular-input-mode').closest('[data-kinds]').hidden,false);}
 const primitive=['wire','capacitor'].includes(c.kind),pair=['transformer','balun'].includes(c.kind);
 if(primitive){assert.equal($('#angle-unit').textContent,'rad');assert.equal(form.elements.namedItem('angle').value,String(c.parameters.angle??0));assert.match($('#ring-input-note').textContent,/stored as radians/);}
 if(pair){assert.equal(form.elements.namedItem('angle').disabled,true);if(c.kind==='transformer')for(const key of['phase','secondary_turns'])assert.equal(form.elements.namedItem(key).disabled,true);}
 const before=requests.filter(r=>r.action==='build').length;await click('#generate');assert.equal(requests.filter(r=>r.action==='build').length,before+1);assert.equal(state().currentDefinition.native_interactive,true);exact(state().current,c);
 if(pair){assert.equal('angle'in state().currentDefinition.parameters,false);if(c.kind==='transformer')for(const key of['phase','secondary_turns'])assert.equal(key in state().currentDefinition.parameters,false);await change('#active-winding',1);exact(state().current,c,1);}
 await exactGDS(c);await click('#download-project');const saved=JSON.parse(await downloads.at(-1).text());assert.equal(saved.shape.native_interactive,true);await restore(saved);exact(state().current,c,pair?1:0);
}
// Every exposed mode must restore defaults rather than stale fields from a prior project.
for(const kind of['wire','capacitor','transformer','balun']){
 await restore({format:'reasitic-project',version:1,shape:{kind,parameters:{},native_interactive:true},technology:wire.technology});const before=inputJSON(state().current.segments);await click('#generate');assert.equal(inputJSON(state().current.segments),before,kind+' omitted defaults');
}
// The same literal angle has distinct original keyword/interactive meanings.
const angleCase=histories.find(c=>c.kind==='wire'&&c.parameters.angle===37);await restore({format:'reasitic-project',version:1,shape:definition(angleCase),technology:angleCase.technology});
await change('#rectangular-input-mode','keyword');assert.equal($('#angle-unit').textContent,'°');assert.equal(form.elements.namedItem('angle').value,'37');form.elements.namedItem('width').value='3.14159265358979';await click('#generate');assert.equal(state().currentDefinition.native_keyword,true);
await change('#rectangular-input-mode','interactive');assert.equal($('#angle-unit').textContent,'rad');assert.equal(form.elements.namedItem('angle').value,'37');await click('#generate');assert.equal(state().currentDefinition.native_interactive,true);
const low=paired.cases.find(c=>c.label.includes('low-turn')||c.label.includes('default-same-metal'));assert.ok(low);await restore({format:'reasitic-project',version:1,shape:{kind:low.kind,parameters:low.parameters,native_keyword:true},technology:paired.technology});assert.equal(form.elements.namedItem('turns').hasAttribute('min'),false);await click('#generate');exact(state().current,low);
const piKeys=['inductance_h','resistance_ohm','capacitance_first_f','capacitance_second_f','resistance_first_ohm','resistance_second_ohm','q_first','q_second','q_differential','shunt_single_ohm','shunt_differential_ohm'];
function exactPi(r,c){const y=r.admittance_matrix;assert.deepEqual([y[1][1],y[1][0],y[0][1],y[0][0]].flat().map(bits),c.model.Y);[r.frequency_hz,...piKeys.map(k=>r.pi[k])].forEach((v,i)=>{if(Number.isFinite(Buffer.from(c.model.M[i],'hex').readDoubleLE()))assert.equal(bits(v),c.model.M[i]);else assert.equal(v,null);});assert.deepEqual(r.scattering_matrix.flat(2).map(bits),c.scattering.S);}
function exactCoupled(r,c){const y=r.admittance_matrix,z=r.impedance_matrix,keys=['first_inductance_h','second_inductance_h','first_resistance_ohm','second_resistance_ohm','ground_resistance_ohm','mutual_h','coupling'],raw=c.raw_output_bits.slice(0,23);assert.deepEqual([y[1][1],y[1][0],y[0][1],y[0][0],z[0][0],z[0][1],z[1][0],z[1][1]].flat().concat(keys.map(k=>r.model[k])).map(bits),raw);assert.deepEqual(r.scattering_matrix.flat(2).map(bits),c.records?.[0].S??c.scattering.S);}
const piSessions=[...read('wire_sessions_original').cases,...read('primitive_sessions_original').cases].filter(c=>c.request.native_interactive);
for(const c of piSessions){const r=c.request;await restore({format:'reasitic-project',version:1,shape:definition(r),technology:r.technology,mesh:r.mesh});await click('#generate');$('#frequency').value=String(r.frequency_ghz);$('#eddy-mode').checked=r.eddy;await click('#pi2');exactPi(state().pi2Result,c);assert.ok($('#model-circuit svg'));await click('#download-pi2');exactPi(JSON.parse(await downloads.at(-1).text()),c);}
const coupledSessions=[...read('paired_sessions_original').cases.filter(c=>c.request.native_interactive),...compressed.paired_interactive_bounds_sessions_original.cases];
for(const c of coupledSessions){const r=c.request;await restore({format:'reasitic-project',version:1,shape:definition(r),technology:r.technology,mesh:r.mesh});await click('#generate');$('#frequency').value=String(r.frequency_ghz);$('#eddy-mode').checked=r.eddy;$('#transformer-termination').value=String(r.termination_ohm);await change('#transformer-ground-mode',r.ground?'first':'none');const raw=c.raw_output_bits.slice(0,23),nonfinite=raw.every(v=>Number.isNaN(Buffer.from(v,'hex').readDoubleLE()));await click('#transformer-run',nonfinite);if(nonfinite){assert.match($('#error').textContent,c.parent_index===6?/contact collapses/:/nonfinite inductive kernel/);assert.equal($('#download-transformer').disabled,true);}else{exactCoupled(state().transformerResult,c);await click('#download-transformer');exactCoupled(JSON.parse(await downloads.at(-1).text()),c);}}
call.destroy();w.close();console.log('84 original interactive creations passed actual Generate, exact winding geometry, GDS decode and project round-trips; all four new mode/default flows, literal angle switching, four Pi2 and five coupled model/JSON/diagnostic histories passed.');
