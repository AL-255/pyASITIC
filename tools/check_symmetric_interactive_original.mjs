// Original interactive symmetric descriptors and actual webpage input-mode flows.
import{readFileSync}from'node:fs';
import{pathToFileURL}from'node:url';
import assert from'node:assert/strict';
import{installNumericalKernels}from'../web/numeric-kernels.mjs';
import{circuitSVG,sweepSVG,transformerSVG}from'../web/analysis-views.mjs';
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL('../dist/reasitic.zip',import.meta.url))),'zip');await installNumericalKernels(py,readFileSync(new URL('../dist/numeric.wasm',import.meta.url)));
py.FS.mkdirTree('/inner/tests/fixtures');
for(const name of['symmetric_interactive_original','symmetric_interactive_sessions_original','symmetric_geometry_original'])py.FS.writeFile('/inner/tests/fixtures/'+name+'.json',readFileSync(new URL('../tests/fixtures/'+name+'.json',import.meta.url)));
for(const name of['test_symmetric_interactive_original','test_symmetric_interactive_sessions_original'])py.FS.writeFile('/inner/tests/'+name+'.py',readFileSync(new URL('../tests/'+name+'.py',import.meta.url)));
py.runPython(`
import sys,unittest,json,struct
sys.path.insert(0,'/inner/tests')
from test_symmetric_interactive_original import OriginalSymmetricInteractiveTests
from test_symmetric_interactive_sessions_original import OriginalSymmetricInteractiveSessionTests
suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(c)for c in(OriginalSymmetricInteractiveTests,OriginalSymmetricInteractiveSessionTests)])
assert unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful()
from reasitic.bridge import request_json
`);
console.log('36 original interactive creators / 10,386 XYZ stores, 11 repeated-prompt histories and six complete original electrical sessions passed in real Pyodide.');
const geometry=JSON.parse(readFileSync(new URL('../tests/fixtures/symmetric_interactive_original.json',import.meta.url))),electrical=JSON.parse(readFileSync(new URL('../tests/fixtures/symmetric_interactive_sessions_original.json',import.meta.url))),call=py.globals.get('request_json');
const inputJSON=value=>JSON.stringify(value,(_key,v)=>Object.is(v,-0)?'-0':v);
function bits(v){const b=Buffer.alloc(8);b.writeDoubleLE(v);return b.toString('hex');}
function definition(c){return{kind:c.kind,parameters:c.parameters,...(c.native_interactive?{native_interactive:true}:{native_keyword:true})};}
function exactGeometry(s,c){assert.equal(s.name,c.config.name);assert.equal(s.origin.map(bits).join(''),c.origin_bits);assert.equal(s.segments.length,c.segments.length);for(const[a,b]of s.segments.map((v,i)=>[v,c.segments[i]])){assert.equal(['start','end','outer_start','outer_end','inner_start','inner_end'].flatMap(k=>Array.from(a[k])).map(bits).join(''),b.coordinates_bits);assert.equal(bits(a.width),b.width_bits);assert.equal(a.metal,b.metal);}}
const keys=['inductance_h','resistance_ohm','capacitance_first_f','capacitance_second_f','resistance_first_ohm','resistance_second_ohm','q_first','q_second','q_differential','shunt_single_ohm','shunt_differential_ohm'];
function exactModel(r,c){const y=r.admittance_matrix;assert.deepEqual([y[1][1],y[1][0],y[0][1],y[0][0]].flat().map(bits),c.model.Y);assert.deepEqual(r.scattering_matrix.flat(2).map(bits),c.scattering.S);const m=[r.frequency_hz,...keys.map(k=>r.pi[k])];m.forEach((v,i)=>{if(Number.isFinite(Buffer.from(c.model.M[i],'hex').readDoubleLE()))assert.equal(bits(v),c.model.M[i]);else assert.equal(v,null);});const raw=Buffer.from(c.resonance.extended_bits,'hex'),exponent=raw.readUInt16LE(8);if((exponent&0x7fff)===0x7fff)assert.equal(r.pi.resonant_frequency_hz,null);else assert.equal(r.pi.resonant_frequency_hz,Number(raw.readBigUInt64LE())*2**((exponent&0x7fff)-16383-63)*(exponent&0x8000?-1:1));}
const{JSDOM}=await import(pathToFileURL(process.argv[3]).href),dom=new JSDOM(readFileSync(new URL('../dist/index.html',import.meta.url),'utf8'),{url:'https://example.test/',runScripts:'outside-only'}),w=dom.window,downloads=[],requests=[];
Object.assign(w,{circuitSVG,sweepSVG,transformerSVG,Blob});w.URL.createObjectURL=blob=>{downloads.push(blob);return'blob:test';};w.URL.revokeObjectURL=()=>{};w.HTMLAnchorElement.prototype.click=()=>{};
w.Worker=class{constructor(){queueMicrotask(()=>this.onmessage({data:{ready:true}}));}postMessage({id,request}){requests.push(request);queueMicrotask(()=>this.onmessage({data:{id,...JSON.parse(call(inputJSON(request)))}}));}};
const source=readFileSync(new URL('../dist/app.js',import.meta.url),'utf8').replace(/^import[^\n]+\n/,'').replaceAll('import.meta.url','"https://example.test/app.js"');w.eval(source+'\nglobalThis.innerState=()=>({ready,busy,current,currentDefinition,pi2Result,technology});');
const $=s=>w.document.querySelector(s),form=$('#geometry-form');
async function idle(){for(let i=0;i<500;i++){await new Promise(setImmediate);const s=w.innerState();if(s.ready&&!s.busy)return;}throw Error('Inner-dimension app did not become idle');}
async function click(id,expectedError=false){assert.equal($(id).disabled,false,id+' disabled');$(id).click();await idle();if(!expectedError)assert.equal($('#error').hidden,true,$('#error').textContent);}
async function restore(project){Object.defineProperty($('#project-file'),'files',{configurable:true,value:[{text:async()=>inputJSON(project)}]});$('#project-file').dispatchEvent(new w.Event('change'));await idle();assert.equal($('#error').hidden,true,$('#error').textContent);}
async function change(id,value){$(id).value=String(value);$(id).dispatchEvent(new w.Event('change'));await idle();}
await idle();
for(const c of geometry.cases){
 await restore({format:'reasitic-project',version:1,technology:c.technology,shape:definition(c)});exactGeometry(w.innerState().current,c);
 assert.equal($('#rectangular-input-mode').value,'interactive');assert.equal($('#dimension-mode').closest('label').hidden,true);
 for(const key of['angle','phase'])assert.equal(form.elements.namedItem(key).disabled,true);
 assert.equal(form.checkValidity(),true,c.label+' must be enterable');
 await click('#generate');exactGeometry(w.innerState().current,c);assert.equal(w.innerState().currentDefinition.native_interactive,true);
 for(const key of['inner_gap',...(c.kind==='symmetric_square'?['length']:[])])assert.equal(key in w.innerState().currentDefinition.parameters,key in c.parameters,'Preserve original default omission');
 await click('#download-project');const project=JSON.parse(await downloads.at(-1).text());await restore(project);exactGeometry(w.innerState().current,c);
}
const selected=geometry.cases.find(c=>c.kind==='symmetric_square'&&c.parameters.length===38&&c.technology.indexOf('SMIN=1')<0);assert.ok(selected);
await restore({format:'reasitic-project',version:1,technology:selected.technology,shape:definition(selected)});
await change('#rectangular-input-mode','keyword');assert.equal(form.elements.namedItem('angle').disabled,false);await click('#generate',true);assert.match($('#error').textContent,/supports 1–3 turns/);
await change('#rectangular-input-mode','interactive');await click('#generate');exactGeometry(w.innerState().current,selected);
for(const c of geometry.failed_cases){
 const before=JSON.stringify(w.innerState().current);Object.defineProperty($('#project-file'),'files',{configurable:true,value:[{text:async()=>JSON.stringify({format:'reasitic-project',version:1,technology:c.technology,shape:definition(c)})}]});$('#project-file').dispatchEvent(new w.Event('change'));await idle();assert.match($('#error').textContent,c.kind==='symmetric_polygon'?/maximum-zero spacing\/transition prompt/:/Need more space for transitions/);assert.equal(JSON.stringify(w.innerState().current),before);
}
// Independently decode every conductor and via landing/cut layer in all streams.
function roundEven(v){const a=Math.floor(v),f=v-a;return f<.5?a:f>.5?a+1:a%2?a+1:a;}
for(const c of geometry.cases){
 const response=JSON.parse(call(inputJSON({action:'gds',...definition(c),technology:c.technology})));assert.ok(!response.error,response.error);const gds=Buffer.from(response.result.base64,'base64'),polygons=[];let layer,datatype;
 for(let at=0;at<gds.length;){const length=gds.readUInt16BE(at),type=gds[at+2];assert.ok(length>=4&&at+length<=gds.length);if(type===13)layer=gds.readInt16BE(at+4);if(type===14)datatype=gds.readInt16BE(at+4);if(type===16){const points=[];for(let k=at+4;k<at+length;k+=8)points.push([gds.readInt32BE(k),gds.readInt32BE(k+4)]);polygons.push({layer,datatype,points});}at+=length;}
 let position=0;const tech=w.innerState().technology;
 for(const s of c.segments){if(s.metal<tech.metals.length){const raw=Buffer.from(s.coordinates_bits,'hex'),v=Array.from({length:18},(_,i)=>raw.readDoubleLE(8*i));const expected=[6,9,15,12,6].map(k=>[roundEven((v[k]+c.origin[0])*1000),roundEven((v[k+1]+c.origin[1])*1000)]);assert.deepEqual(polygons[position].points,expected);assert.equal(polygons[position].layer,s.metal+1);assert.equal(polygons[position].datatype,0);position++;}else{const index=s.metal-tech.metals.length,via=tech.vias[index],expected=[via.bottom+1,via.top+1,...Array(s.nx*s.ny).fill(100+index)];assert.deepEqual(polygons.slice(position,position+expected.length).map(p=>p.layer),expected);position+=expected.length;}}
 assert.equal(position,polygons.length);
}
for(const[index,c]of electrical.cases.entries()){
 const r=c.request;await restore({format:'reasitic-project',version:1,technology:r.technology,shape:definition(r),mesh:r.mesh});$('#frequency').value=String(r.frequency_ghz);$('#eddy-mode').checked=r.eddy;const finite=[0,2,3].includes(index);await click('#pi2',!finite);
 if(finite){exactModel(w.innerState().pi2Result,c);await click('#download-pi2');exactModel(JSON.parse(await downloads.at(-1).text()),c);}
 else{assert.match($('#error').textContent,/contact collapses/);assert.equal($('#download-pi2').disabled,true);}
}
call.destroy();w.close();console.log('Actual symmetric mode selector, full-precision/signed inputs, all 36 regeneration/project/GDS flows, omission retention, capacity differences, 11 bounded prompt errors and six model/download/diagnostic flows passed.');
