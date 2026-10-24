// Paired creators, literal original stores, independent GDS, and actual webpage handlers.
import{readFileSync}from'node:fs';
import{pathToFileURL}from'node:url';
import assert from'node:assert/strict';
import{installNumericalKernels}from'../web/numeric-kernels.mjs';
import{circuitSVG,sweepSVG,transformerSVG}from'../web/analysis-views.mjs';
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL('../dist/reasitic.zip',import.meta.url))),'zip');
await installNumericalKernels(py,readFileSync(new URL('../dist/numeric.wasm',import.meta.url)));
// Run the same raw-bit and full-matrix assertions in the shipped interpreter.
py.FS.mkdirTree('/paired/tests/fixtures');
for(const name of['paired_original','paired_sessions_original'])py.FS.writeFile('/paired/tests/fixtures/'+name+'.json',readFileSync(new URL('../tests/fixtures/'+name+'.json',import.meta.url)));
for(const name of['test_paired_original','test_paired_sessions_original'])py.FS.writeFile('/paired/tests/'+name+'.py',readFileSync(new URL('../tests/'+name+'.py',import.meta.url)));
py.runPython(`
import sys,unittest,json,struct
sys.path.insert(0,'/paired/tests')
from test_paired_original import OriginalPairedTests
from test_paired_sessions_original import OriginalPairedSessionTests
suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(c)for c in(OriginalPairedTests,OriginalPairedSessionTests)])
assert unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful()
from reasitic.bridge import request_json
`);
console.log('98 original paired creators / 38,592 XYZ stores, six actual joined meshes, five finite full-matrix/Y/Z/model/S sessions and one original nonfinite history passed in real Pyodide.');
const geometry=JSON.parse(readFileSync(new URL('../tests/fixtures/paired_original.json',import.meta.url))),electrical=JSON.parse(readFileSync(new URL('../tests/fixtures/paired_sessions_original.json',import.meta.url))),call=py.globals.get('request_json');
function bits(v){const b=Buffer.alloc(8);b.writeDoubleLE(v);return b.toString('hex');}
function definition(c){return{kind:c.kind,parameters:c.parameters,native_keyword:c.native_keyword||false,native_interactive:c.native_interactive||false};}
function exactGeometry(s,c,index=0){
 const w=c.windings[index];assert.equal(s.name,w.name);assert.equal(s.origin.map(bits).join(''),w.origin_bits);assert.deepEqual(Array.from(s.windings),c.windings.map(w=>w.name));assert.equal(s.segments.length,w.segments.length);
 for(const[a,b]of s.segments.map((v,i)=>[v,w.segments[i]])){
  assert.equal(['start','end','outer_start','outer_end','inner_start','inner_end'].flatMap(k=>Array.from(a[k])).map(bits).join(''),b.coordinates_bits);assert.equal(bits(a.width),b.width_bits);assert.equal(a.metal,b.metal);
 }
}
function exactModel(r,c){
 const y=r.admittance_matrix,z=r.impedance_matrix,keys=['first_inductance_h','second_inductance_h','first_resistance_ohm','second_resistance_ohm','ground_resistance_ohm','mutual_h','coupling'];
 const actual=[y[1][1],y[1][0],y[0][1],y[0][0],z[0][0],z[0][1],z[1][0],z[1][1]].flat().concat(keys.map(k=>r.model[k]));
 assert.deepEqual(actual.map(bits),c.raw_output_bits);assert.deepEqual(r.scattering_matrix.flat(2).map(bits),c.scattering.S);
}
const{JSDOM}=await import(pathToFileURL(process.argv[3]).href),dom=new JSDOM(readFileSync(new URL('../dist/index.html',import.meta.url),'utf8'),{url:'https://example.test/',runScripts:'outside-only'}),w=dom.window,downloads=[],requests=[];
Object.assign(w,{circuitSVG,sweepSVG,transformerSVG,Blob});w.URL.createObjectURL=blob=>{downloads.push(blob);return'blob:test';};w.URL.revokeObjectURL=()=>{};w.HTMLAnchorElement.prototype.click=()=>{};
w.Worker=class{constructor(){queueMicrotask(()=>this.onmessage({data:{ready:true}}));}postMessage({id,request}){requests.push(request);queueMicrotask(()=>this.onmessage({data:{id,...JSON.parse(call(JSON.stringify(request)))}}));}};
const source=readFileSync(new URL('../dist/app.js',import.meta.url),'utf8').replace(/^import[^\n]+\n/,'').replaceAll('import.meta.url','"https://example.test/app.js"');
w.eval(source+'\nglobalThis.pairedState=()=>({ready,busy,current,currentDefinition,transformerResult,technology});');
const $=s=>w.document.querySelector(s),form=$('#geometry-form');
async function idle(){for(let i=0;i<500;i++){await new Promise(setImmediate);const s=w.pairedState();if(s.ready&&!s.busy)return;}throw Error('Paired app did not become idle');}
async function click(id,expectedError=false){assert.equal($(id).disabled,false,id+' disabled');$(id).click();await idle();if(!expectedError)assert.equal($('#error').hidden,true,$('#error').textContent);}
async function restore(project){Object.defineProperty($('#project-file'),'files',{configurable:true,value:[{text:async()=>JSON.stringify(project)}]});$('#project-file').dispatchEvent(new w.Event('change'));await idle();assert.equal($('#error').hidden,true,$('#error').textContent);}
async function change(id,value){$(id).value=String(value);$(id).dispatchEvent(new w.Event('change'));await idle();}
await idle();
const selected=geometry.cases.find(c=>c.label==='keyword/trans/1.75/2/M3/17/-1');assert.ok(selected);
for(const c of[selected,...geometry.cases.filter(c=>c.label.startsWith('defaults/')),...geometry.cases.filter(c=>c.label.includes('default-same-metal'))]){
 await restore({format:'reasitic-project',version:1,technology:geometry.technology,shape:definition(c)});exactGeometry(w.pairedState().current,c);
 if(c.kind==='balun')assert.equal(form.elements.namedItem('turns').hasAttribute('min'),false,'Native keyword balun low/negative turns are allowed');
 const prior=requests.length;await click('#generate');assert.ok(requests.length>prior,'Generation must actually run');exactGeometry(w.pairedState().current,c);assert.equal(w.pairedState().currentDefinition.native_keyword,true);
 if(c.label.includes('default-same-metal'))assert.equal('secondary_metal'in w.pairedState().currentDefinition.parameters,false,'Omitted native transition default stays omitted');
 await change('#active-winding',1);exactGeometry(w.pairedState().current,c,1);
 await click('#download-project');const project=JSON.parse(await downloads.at(-1).text());assert.equal(project.shape.winding,1);await restore(project);exactGeometry(w.pairedState().current,c,1);
}
// Distinct winding indices must remain selectable even when native names coincide.
const duplicate=geometry.cases.find(c=>c.label==='defaults/trans/PNAME=aa:SNAME=aa');
await restore({format:'reasitic-project',version:1,technology:geometry.technology,shape:definition(duplicate)});await change('#active-winding',1);exactGeometry(w.pairedState().current,duplicate,1);
// Interactive projects retain their larger native prompt limits for analysis/export.
for(const c of geometry.cases.filter(c=>c.label==='interactive/trans/6.25'||c.label==='interactive/balun/13.75')){
 await restore({format:'reasitic-project',version:1,technology:geometry.technology,shape:definition(c)});exactGeometry(w.pairedState().current,c);await click('#download-project');assert.equal(JSON.parse(await downloads.at(-1).text()).shape.native_interactive,true);
}
// Independently decode both windings of every generated GDS boundary.
function roundEven(v){const a=Math.floor(v),f=v-a;return f<.5?a:f>.5?a+1:a%2?a+1:a;}
for(const c of geometry.cases){
 const response=JSON.parse(call(JSON.stringify({action:'gds',...definition(c),technology:geometry.technology})));assert.ok(!response.error,response.error);const gds=Buffer.from(response.result.base64,'base64'),polygons=[];let layer,datatype;
 for(let at=0;at<gds.length;){const length=gds.readUInt16BE(at),type=gds[at+2];assert.ok(length>=4&&at+length<=gds.length);if(type===13)layer=gds.readInt16BE(at+4);if(type===14)datatype=gds.readInt16BE(at+4);if(type===16){const points=[];for(let k=at+4;k<at+length;k+=8)points.push([gds.readInt32BE(k),gds.readInt32BE(k+4)]);polygons.push({layer,datatype,points});}at+=length;}
 let position=0;const tech=w.pairedState().technology;
 for(const winding of c.windings)for(const s of winding.segments){
  if(s.metal<tech.metals.length){const raw=Buffer.from(s.coordinates_bits,'hex'),values=Array.from({length:18},(_,i)=>raw.readDoubleLE(8*i));const expected=[6,9,15,12,6].map(k=>[roundEven((values[k]+winding.origin[0])*1000),roundEven((values[k+1]+winding.origin[1])*1000)]);assert.deepEqual(polygons[position].points,expected);assert.equal(polygons[position].layer,s.metal+1);assert.equal(polygons[position].datatype,0);position++;}
  else{const index=s.metal-tech.metals.length,v=tech.vias[index],expected=[v.bottom+1,v.top+1,...Array(s.nx*s.ny).fill(100+index)];assert.deepEqual(polygons.slice(position,position+expected.length).map(p=>p.layer),expected);position+=expected.length;}
 }
 assert.equal(position,polygons.length);
}
for(const[i,c]of electrical.cases.entries()){
 const r=c.request;await restore({format:'reasitic-project',version:1,technology:r.technology,shape:definition(r),mesh:r.mesh});
 $('#frequency').value=String(r.frequency_ghz);$('#eddy-mode').checked=r.eddy;$('#transformer-termination').value=String(r.termination_ohm);await change('#transformer-ground-mode',r.ground?'first':'none');
 await click('#transformer-run',i===3);
 if(i===3){assert.match($('#error').textContent,/nonfinite inductive kernel/);assert.equal($('#download-transformer').disabled,true);}
 else{exactModel(w.pairedState().transformerResult,c);await click('#download-transformer');exactModel(JSON.parse(await downloads.at(-1).text()),c);}
}
call.destroy();w.close();console.log('Actual paired form/name/default handling, duplicate-name winding selection, interactive project retention, all 98 combined GDS exports, and six coupled-model/download/diagnostic flows passed.');
