// Intact-original 3D boundaries and real shipped-runtime numerical paths.
import{readFileSync}from'node:fs';
import{pathToFileURL}from'node:url';
import assert from'node:assert/strict';
import{installNumericalKernels}from'../web/numeric-kernels.mjs';
import{circuitSVG,sweepSVG,transformerSVG}from'../web/analysis-views.mjs';
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL('../dist/reasitic.zip',import.meta.url))),'zip');
await installNumericalKernels(py,readFileSync(new URL('../dist/numeric.wasm',import.meta.url)));
py.FS.mkdirTree('/3d/tests/fixtures');
for(const name of['transformer3d_original','transformer3d_sessions_original'])py.FS.writeFile('/3d/tests/fixtures/'+name+'.json',readFileSync(new URL('../tests/fixtures/'+name+'.json',import.meta.url)));
for(const name of['test_transformer3d_original','test_transformer3d_sessions_original'])py.FS.writeFile('/3d/tests/'+name+'.py',readFileSync(new URL('../tests/'+name+'.py',import.meta.url)));
py.runPython(`
import sys,unittest,json,struct
sys.path.insert(0,'/3d/tests')
from test_transformer3d_original import OriginalTransformer3DTests
from test_transformer3d_sessions_original import OriginalTransformer3DSessionTests
suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(c)for c in(OriginalTransformer3DTests,OriginalTransformer3DSessionTests)])
assert unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful()
from reasitic.bridge import request_json
`);
console.log('96 original 3D creators / 94,824 exact XYZ stores and defined scalar fields, twelve raw winding LMAT matrices, and six original failed coupled histories passed in real Pyodide.');
const geometry=JSON.parse(readFileSync(new URL('../tests/fixtures/transformer3d_original.json',import.meta.url))),electrical=JSON.parse(readFileSync(new URL('../tests/fixtures/transformer3d_sessions_original.json',import.meta.url))),call=py.globals.get('request_json');
const inputJSON=value=>JSON.stringify(value,(_key,v)=>Object.is(v,-0)?'-0':v);
function bits(v){const b=Buffer.alloc(8);b.writeDoubleLE(v);return b.toString('hex');}
function definition(c){return{kind:'transformer3d',parameters:c.parameters,native_interactive:true};}
function exactGeometry(s,c,index=0){const w=c.windings[index];assert.equal(s.name,w.name);assert.equal(s.origin.map(bits).join(''),w.origin_bits);assert.deepEqual(Array.from(s.windings),c.windings.map(w=>w.name));assert.equal(s.segments.length,w.segments.length);for(const[a,b]of s.segments.map((v,i)=>[v,w.segments[i]])){assert.equal(['start','end','outer_start','outer_end','inner_start','inner_end'].flatMap(k=>Array.from(a[k])).map(bits).join(''),b.coordinates_bits);for(const key of['width','thickness','primary_width','primary_thickness'])assert.equal(bits(a[key]),b[key+'_bits']);assert.equal(a.metal,b.metal);}}
const{JSDOM}=await import(pathToFileURL(process.argv[3]).href),dom=new JSDOM(readFileSync(new URL('../dist/index.html',import.meta.url),'utf8'),{url:'https://example.test/',runScripts:'outside-only'}),w=dom.window,downloads=[],requests=[];
Object.assign(w,{circuitSVG,sweepSVG,transformerSVG,Blob});w.URL.createObjectURL=blob=>{downloads.push(blob);return'blob:test';};w.URL.revokeObjectURL=()=>{};w.HTMLAnchorElement.prototype.click=()=>{};
w.Worker=class{constructor(){queueMicrotask(()=>this.onmessage({data:{ready:true}}));}postMessage({id,request}){requests.push(request);queueMicrotask(()=>this.onmessage({data:{id,...JSON.parse(call(JSON.stringify(request)))}}));}};
const source=readFileSync(new URL('../dist/app.js',import.meta.url),'utf8').replace(/^import[^\n]+\n/,'').replaceAll('import.meta.url','"https://example.test/app.js"');
w.eval(source+'\nglobalThis.threeDState=()=>({ready,busy,current,currentDefinition,matrixResult,technology});');
const $=s=>w.document.querySelector(s),form=$('#geometry-form');
async function idle(){for(let i=0;i<500;i++){await new Promise(setImmediate);const s=w.threeDState();if(s.ready&&!s.busy)return;}throw Error('3D app did not become idle');}
async function click(id,expectedError=false){assert.equal($(id).disabled,false,id+' disabled');$(id).click();await idle();if(!expectedError)assert.equal($('#error').hidden,true,$('#error').textContent);}
async function restore(project){Object.defineProperty($('#project-file'),'files',{configurable:true,value:[{text:async()=>inputJSON(project)}]});$('#project-file').dispatchEvent(new w.Event('change'));await idle();assert.equal($('#error').hidden,true,$('#error').textContent);}
async function change(id,value){$(id).value=String(value);$(id).dispatchEvent(new w.Event('change'));await idle();}
await idle();
for(const c of[geometry.cases[1],...geometry.cases.slice(78)]){
 await restore({format:'reasitic-project',version:1,technology:geometry.technology,shape:definition(c)});exactGeometry(w.threeDState().current,c);
 assert.equal(form.elements.namedItem('length').hasAttribute('min'),false);assert.equal(form.elements.namedItem('height').hasAttribute('min'),false);assert.equal(form.elements.namedItem('width').min,'1e-10');assert.match($('#ring-input-note').textContent,/full precision/);
 const prior=requests.length;await click('#generate');assert.ok(requests.length>prior,'Generation must run');assert.equal(w.threeDState().currentDefinition.native_interactive,true);exactGeometry(w.threeDState().current,c);
 await change('#active-winding',1);exactGeometry(w.threeDState().current,c,1);await click('#download-project');const project=JSON.parse(await downloads.at(-1).text());assert.equal(project.shape.native_interactive,true);assert.equal(project.shape.winding,1);await restore(project);exactGeometry(w.threeDState().current,c,1);
}
// An omitted secondary layer follows the primary, not the process top metal.
await restore({format:'reasitic-project',version:1,technology:geometry.technology,shape:{kind:'transformer3d',native_interactive:true,parameters:{primary_name:'P',secondary_name:'S',metal:'M3',spacing:8}}});
assert.equal(form.elements.namedItem('secondary_metal').value,'1');const before=JSON.stringify(w.threeDState().current.segments);await click('#generate');assert.equal(JSON.stringify(w.threeDState().current.segments),before);
// Independently decode every conductor in every combined 3D GDS stream.
function roundEven(v){const a=Math.floor(v),f=v-a;return f<.5?a:f>.5?a+1:a%2?a+1:a;}
for(const c of geometry.cases){
 const response=JSON.parse(call(JSON.stringify({action:'gds',...definition(c),technology:geometry.technology})));assert.ok(!response.error,response.error);const gds=Buffer.from(response.result.base64,'base64'),polygons=[];let layer,datatype;
 for(let at=0;at<gds.length;){const length=gds.readUInt16BE(at),type=gds[at+2];assert.ok(length>=4&&at+length<=gds.length);if(type===13)layer=gds.readInt16BE(at+4);if(type===14)datatype=gds.readInt16BE(at+4);if(type===16){const points=[];for(let k=at+4;k<at+length;k+=8)points.push([gds.readInt32BE(k),gds.readInt32BE(k+4)]);polygons.push({layer,datatype,points});}at+=length;}
 let position=0;for(const winding of c.windings)for(const s of winding.segments){const raw=Buffer.from(s.coordinates_bits,'hex'),v=Array.from({length:18},(_,i)=>raw.readDoubleLE(8*i));const expected=[6,9,15,12,6].map(k=>[roundEven((v[k]+winding.origin[0])*1000),roundEven((v[k+1]+winding.origin[1])*1000)]);assert.deepEqual(polygons[position].points,expected);assert.equal(polygons[position].layer,s.metal+1);assert.equal(polygons[position].datatype,0);position++;}assert.equal(position,polygons.length);
}
for(const c of electrical.cases){
 const r=c.request;await restore({format:'reasitic-project',version:1,technology:r.technology,shape:definition(r),mesh:r.mesh});$('#frequency').value=String(r.frequency_ghz);$('#eddy-mode').checked=r.eddy;
 for(const[i,m]of c.lmat.entries()){
  await change('#active-winding',i);await click('#lmat');const result=w.threeDState().matrixResult,n=m.size;assert.equal(result.matrix.length,n);assert.equal(Array.from({length:n},(_,j)=>Array.from({length:n},(_,i)=>result.matrix[i][j].map(bits).join('')).join('')).join(''),m.matrix_bits);await click('#download-matrix');assert.match(await downloads.at(-1).text(),/real_ohm,imag_ohm/);
 }
 await change('#active-winding',0);$('#transformer-termination').value=String(r.termination_ohm);await change('#transformer-ground-mode',r.ground?'first':'none');await click('#transformer-run',true);assert.match($('#error').textContent,/nonzero planar segment length/);assert.equal($('#download-transformer').disabled,true);
}
call.destroy();w.close();console.log('Actual native 3D form precision, spacing boundaries, zero/negative dimensions, phase/name handling, defaults, duplicate names, projects, all 96 combined GDS streams, twelve LMAT displays/CSV exports and six coupled diagnostics passed.');
