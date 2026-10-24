// Intact-original clearance boundaries and actual webpage generation/export flows.
import{readFileSync}from'node:fs';
import{pathToFileURL}from'node:url';
import assert from'node:assert/strict';
import{installNumericalKernels}from'../web/numeric-kernels.mjs';
import{circuitSVG,sweepSVG,transformerSVG}from'../web/analysis-views.mjs';
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL('../dist/reasitic.zip',import.meta.url))),'zip');await installNumericalKernels(py,readFileSync(new URL('../dist/numeric.wasm',import.meta.url)));
py.FS.mkdirTree('/transition/tests/fixtures');
for(const name of['transition_original','transition_sessions_original'])py.FS.writeFile('/transition/tests/fixtures/'+name+'.json',readFileSync(new URL('../tests/fixtures/'+name+'.json',import.meta.url)));
for(const name of['test_transition_original','test_transition_sessions_original'])py.FS.writeFile('/transition/tests/'+name+'.py',readFileSync(new URL('../tests/'+name+'.py',import.meta.url)));
py.runPython(`
import sys,unittest
sys.path.insert(0,'/transition/tests')
from test_transition_original import OriginalTransitionTests
from test_transition_sessions_original import OriginalTransitionSessionTests
from reasitic.symmetric_geometry import _compiled_geometry
assert _compiled_geometry is not None
suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(c)for c in(OriginalTransitionTests,OriginalTransitionSessionTests)])
assert unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful()
from reasitic.bridge import request_json
`);
console.log('840 original acceptance decisions, 780 consumed transition store sets, 682 creators / 92,070 XYZ stores, two finite complete models and four original nonfinite histories passed in real Pyodide.');
const geometry=JSON.parse(readFileSync(new URL('../tests/fixtures/transition_original.json',import.meta.url))),electrical=JSON.parse(readFileSync(new URL('../tests/fixtures/transition_sessions_original.json',import.meta.url))),call=py.globals.get('request_json');
function bits(v){const b=Buffer.alloc(8);b.writeDoubleLE(v);return b.toString('hex');}
function definition(c){return{kind:c.kind,parameters:c.parameters,native_keyword:true};}
function exactGeometry(s,c){assert.equal(s.name,c.config.name);assert.equal(s.origin.map(bits).join(''),c.origin_bits);assert.equal(s.segments.length,c.segments.length);for(const[a,b]of s.segments.map((v,i)=>[v,c.segments[i]])){assert.equal(['start','end','outer_start','outer_end','inner_start','inner_end'].flatMap(k=>Array.from(a[k])).map(bits).join(''),b.coordinates_bits);assert.equal(bits(a.width),b.width_bits);assert.equal(a.metal,b.metal);assert.equal(bits(a.thickness),b.thickness_bits);}}
const keys=['inductance_h','resistance_ohm','capacitance_first_f','capacitance_second_f','resistance_first_ohm','resistance_second_ohm','q_first','q_second','q_differential','shunt_single_ohm','shunt_differential_ohm'];
function exactModel(r,c){const y=r.admittance_matrix;assert.deepEqual([y[1][1],y[1][0],y[0][1],y[0][0]].flat().map(bits),c.model.Y);assert.deepEqual(r.scattering_matrix.flat(2).map(bits),c.scattering.S);assert.deepEqual([r.frequency_hz,...keys.map(k=>r.pi[k])].map(bits),c.model.M);}
const{JSDOM}=await import(pathToFileURL(process.argv[3]).href),dom=new JSDOM(readFileSync(new URL('../dist/index.html',import.meta.url),'utf8'),{url:'https://example.test/',runScripts:'outside-only'}),w=dom.window,downloads=[],requests=[];
Object.assign(w,{circuitSVG,sweepSVG,transformerSVG,Blob});w.URL.createObjectURL=blob=>{downloads.push(blob);return'blob:test';};w.URL.revokeObjectURL=()=>{};w.HTMLAnchorElement.prototype.click=()=>{};
w.Worker=class{constructor(){queueMicrotask(()=>this.onmessage({data:{ready:true}}));}postMessage({id,request}){requests.push(request);queueMicrotask(()=>this.onmessage({data:{id,...JSON.parse(call(JSON.stringify(request)))}}));}};
const source=readFileSync(new URL('../dist/app.js',import.meta.url),'utf8').replace(/^import[^\n]+\n/,'').replaceAll('import.meta.url','"https://example.test/app.js"');w.eval(source+'\nglobalThis.transitionState=()=>({ready,busy,current,currentDefinition,pi2Result,technology});');
const $=s=>w.document.querySelector(s),form=$('#geometry-form');
async function idle(){for(let i=0;i<500;i++){await new Promise(setImmediate);const s=w.transitionState();if(s.ready&&!s.busy)return;}throw Error('Transition app did not become idle');}
async function click(id,expectedError=false){assert.equal($(id).disabled,false,id+' disabled');$(id).click();await idle();if(!expectedError)assert.equal($('#error').hidden,true,$('#error').textContent);}
async function restore(project){Object.defineProperty($('#project-file'),'files',{configurable:true,value:[{text:async()=>JSON.stringify(project)}]});$('#project-file').dispatchEvent(new w.Event('change'));await idle();assert.equal($('#error').hidden,true,$('#error').textContent);}
function roundEven(v){const a=Math.floor(v),f=v-a;return f<.5?a:f>.5?a+1:a%2?a+1:a;}
await idle();let accepted=0,defaultRejects=0;
for(const c of geometry.cases){
 if(!c.accepted)continue;
 await restore({format:'reasitic-project',version:1,technology:geometry.technology,shape:definition(c)});exactGeometry(w.transitionState().current,c);
 assert.equal(form.elements.namedItem('inner_gap').hasAttribute('min'),false);
 assert.equal(form.checkValidity(),true,'Signed native gap must be enterable');await click('#generate');exactGeometry(w.transitionState().current,c);
 assert.equal('inner_gap'in w.transitionState().currentDefinition.parameters,'inner_gap'in c.parameters);
 await click('#download-project');const project=JSON.parse(await downloads.at(-1).text());await restore(project);exactGeometry(w.transitionState().current,c);
 await click('#download-gds');const gds=Buffer.from(await downloads.at(-1).arrayBuffer()),polygons=[];let layer,datatype;
 for(let at=0;at<gds.length;){const length=gds.readUInt16BE(at),type=gds[at+2];assert.ok(length>=4&&at+length<=gds.length);if(type===13)layer=gds.readInt16BE(at+4);if(type===14)datatype=gds.readInt16BE(at+4);if(type===16){const points=[];for(let k=at+4;k<at+length;k+=8)points.push([gds.readInt32BE(k),gds.readInt32BE(k+4)]);polygons.push({layer,datatype,points});}at+=length;}
 assert.equal(polygons.length,c.segments.length);
 for(const[s,i]of c.segments.map((v,i)=>[v,i])){const raw=Buffer.from(s.coordinates_bits,'hex'),v=Array.from({length:18},(_,i)=>raw.readDoubleLE(8*i));const expected=[6,9,15,12,6].map(k=>[roundEven((v[k]+c.origin[0])*1000),roundEven((v[k+1]+c.origin[1])*1000)]);assert.deepEqual(polygons[i].points,expected);assert.equal(polygons[i].layer,s.metal+1);assert.equal(polygons[i].datatype,0);}
 // Equal numeric gap values can have different native omitted/explicit paths.
 if(!('inner_gap'in c.parameters)){
  const explicit=JSON.parse(call(JSON.stringify({action:'build',...definition(c),parameters:{...c.parameters,inner_gap:w.transitionState().current.parameters.inner_gap},technology:geometry.technology})));
  if(explicit.error){assert.match(explicit.error,/Need more space for transitions/);defaultRejects++;}
 }
 accepted++;
 if(accepted%100===0)console.log(`${accepted} accepted original layouts regenerated, restored and independently decoded from downloaded GDS.`);
}
assert.equal(accepted,682);assert.ok(defaultRejects>0);
// Invalid explicit gaps report errors and preserve the last successful layout.
for(const kind of['symmetric_square','symmetric_polygon']){
 const valid=geometry.cases.find(c=>c.kind===kind&&c.accepted&&c.parameters.inner_gap===0),bad=geometry.cases.find(c=>c.kind===kind&&!c.accepted&&c.parameters.width===valid.parameters.width&&c.parameters.spacing===valid.parameters.spacing);
 assert.ok(valid&&bad);await restore({format:'reasitic-project',version:1,technology:geometry.technology,shape:definition(valid)});const before=JSON.stringify(w.transitionState().current);
 form.elements.namedItem('inner_gap').value=String(bad.parameters.inner_gap);await click('#generate',true);assert.match($('#error').textContent,/Need more space for transitions/);assert.equal(JSON.stringify(w.transitionState().current),before);
}
for(const[i,c]of electrical.cases.entries()){
 const r=c.request;await restore({format:'reasitic-project',version:1,technology:r.technology,shape:definition(r),mesh:r.mesh});$('#frequency').value=String(r.frequency_ghz);$('#eddy-mode').checked=r.eddy;const finite=i===3||i===5;
 await click('#pi2',!finite);
 if(finite){exactModel(w.transitionState().pi2Result,c);await click('#download-pi2');exactModel(JSON.parse(await downloads.at(-1).text()),c);}
 else{assert.match($('#error').textContent,i===1||i===4?/nonzero planar segment length/:/contact collapses/);assert.equal($('#download-pi2').disabled,true);}
}
call.destroy();w.close();console.log('All 682 actual form/regeneration/project/GDS flows, omitted versus explicit defaults, signed-gap controls, rejected-gap state preservation, two finite model displays/downloads and four bounded nonfinite histories passed.');
