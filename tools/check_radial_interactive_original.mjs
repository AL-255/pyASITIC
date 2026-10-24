// Original interactive radial inputs, native failures and actual webpage flows.
import{readFileSync}from'node:fs';import{gunzipSync}from'node:zlib';import{pathToFileURL}from'node:url';import assert from'node:assert/strict';
import{installNumericalKernels}from'../web/numeric-kernels.mjs';import{circuitSVG,sweepSVG,transformerSVG}from'../web/analysis-views.mjs';
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();py.unpackArchive(new Uint8Array(readFileSync(new URL('../dist/reasitic.zip',import.meta.url))),'zip');await installNumericalKernels(py,readFileSync(new URL('../dist/numeric.wasm',import.meta.url)));
const fixtures={};py.FS.mkdirTree('/radial/tests/fixtures');
for(const name of['radial_interactive_original','radial_interactive_sessions_original']){const data=readFileSync(new URL('../tests/fixtures/'+name+'.json.gz',import.meta.url));fixtures[name]=JSON.parse(gunzipSync(data));py.FS.writeFile('/radial/tests/fixtures/'+name+'.json.gz',data);}
for(const name of['test_radial_interactive_original','test_radial_interactive_sessions_original'])py.FS.writeFile('/radial/tests/'+name+'.py',readFileSync(new URL('../tests/'+name+'.py',import.meta.url)));
try{py.runPython(`
import sys,unittest
sys.path.insert(0,'/radial/tests')
from test_radial_interactive_original import OriginalRadialInteractiveTests
from test_radial_interactive_sessions_original import OriginalRadialInteractiveSessionTests
suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(c)for c in(OriginalRadialInteractiveTests,OriginalRadialInteractiveSessionTests))
assert unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful()
`);}catch(error){console.error(String(error));process.exit(1);}
py.runPython('from reasitic.bridge import request_json');const call=py.globals.get('request_json');
const{JSDOM}=await import(pathToFileURL(process.argv[3]).href),dom=new JSDOM(readFileSync(new URL('../dist/index.html',import.meta.url),'utf8'),{url:'https://example.test/',runScripts:'outside-only'}),w=dom.window,requests=[],downloads=[];
Object.assign(w,{circuitSVG,sweepSVG,transformerSVG,Blob});w.URL.createObjectURL=blob=>{downloads.push(blob);return'blob:test';};w.URL.revokeObjectURL=()=>{};w.HTMLAnchorElement.prototype.click=()=>{};
w.Worker=class{constructor(){queueMicrotask(()=>this.onmessage({data:{ready:true}}));}postMessage({id,request}){requests.push(request);queueMicrotask(()=>this.onmessage({data:{id,...JSON.parse(call(JSON.stringify(request)))}}));}};
const source=readFileSync(new URL('../dist/app.js',import.meta.url),'utf8').replace(/^import[^\n]+\n/,'').replaceAll('import.meta.url','"https://example.test/app.js"');w.eval(source+'\nglobalThis.radialState=()=>({ready,busy,current,currentDefinition,pi2Result});');
const $=s=>w.document.querySelector(s),form=$('#geometry-form');
async function idle(){for(let i=0;i<1000;i++){await new Promise(setImmediate);const s=w.radialState();if(s.ready&&!s.busy)return;}throw Error('Radial app did not become idle');}
async function click(id,expectedError=false){assert.equal($(id).disabled,false,id+' disabled');$(id).click();await idle();assert.equal($('#error').hidden,!expectedError,$('#error').textContent);}
async function restore(project){Object.defineProperty($('#project-file'),'files',{configurable:true,value:[{text:async()=>JSON.stringify(project)}]});$('#project-file').dispatchEvent(new w.Event('change'));await idle();assert.equal($('#error').hidden,true,$('#error').textContent);}
function bits(value){const b=Buffer.alloc(8);b.writeDoubleLE(value);return b.toString('hex');}
function exact(shape,c){assert.equal(shape.name,c.created_name);assert.equal(shape.origin.map(bits).join(''),c.origin_bits);assert.equal(shape.segments.length,c.segments.length);shape.segments.forEach((s,i)=>{assert.equal(['start','end','outer_start','outer_end','inner_start','inner_end'].flatMap(k=>s[k]).map(bits).join(''),c.segments[i].coordinates_bits);assert.equal(bits(s.width),c.segments[i].width_bits);assert.equal(bits(s.thickness),c.segments[i].thickness_bits);assert.equal(s.metal,c.segments[i].metal);});}
function roundEven(v){const n=Math.floor(v),f=v-n;return f<.5?n:f>.5?n+1:n%2?n+1:n;}
async function gdsMatches(c){await click('#download-gds');const data=Buffer.from(await downloads.at(-1).arrayBuffer()),polygons=[];let layer,datatype;for(let at=0;at<data.length;){const length=data.readUInt16BE(at),kind=data[at+2];assert.ok(length>=4&&at+length<=data.length);if(kind===13)layer=data.readInt16BE(at+4);if(kind===14)datatype=data.readInt16BE(at+4);if(kind===16){const points=[];for(let p=at+4;p<at+length;p+=8)points.push([data.readInt32BE(p),data.readInt32BE(p+4)]);polygons.push({layer,datatype,points});}at+=length;}assert.equal(polygons.length,c.segments.length);const origin=Buffer.from(c.origin_bits,'hex'),ox=origin.readDoubleLE(),oy=origin.readDoubleLE(8);polygons.forEach((p,i)=>{const raw=Buffer.from(c.segments[i].coordinates_bits,'hex'),expected=[6,9,15,12,6].map(k=>[roundEven((raw.readDoubleLE(8*k)+ox)*1000),roundEven((raw.readDoubleLE(8*(k+1))+oy)*1000)]);assert.deepEqual(p.points,expected);assert.equal(p.layer,c.segments[i].metal+1);assert.equal(p.datatype,0);});}
await idle();const fixture=fixtures.radial_interactive_original;let created=0;
for(const c of fixture.cases){
 if(!c.returned)continue;
 const shape={kind:c.kind,parameters:c.parameters,...(c.native_keyword?{native_keyword:true}:{native_interactive:true})};
 await restore({format:'reasitic-project',version:1,shape,technology:fixture.technology});exact(w.radialState().current,c);
 assert.equal($('#rectangular-input-mode').value,c.native_keyword?'keyword':'interactive');assert.equal($('#rectangular-input-mode').disabled,false);assert.equal($('#rectangular-input-mode').closest('[data-kinds]').hidden,false);assert.equal($('#dimension-mode').disabled,true);assert.equal(form.elements.namedItem('angle').disabled,!c.native_keyword);assert.equal(form.elements.namedItem('phase').disabled,true);
 await click('#generate');exact(w.radialState().current,c);assert.equal(!!w.radialState().currentDefinition.native_interactive,!c.native_keyword);assert.ok($('#drawing polygon'));
 await gdsMatches(c);await click('#download-project');const saved=JSON.parse(await downloads.at(-1).text());assert.equal(!!saved.shape.native_interactive,!c.native_keyword);await restore(saved);exact(w.radialState().current,c);created++;
}
assert.equal(created,109);
// Omitted native defaults must replace fields left by the previous project.
for(const kind of['ring','polygon']){await restore({format:'reasitic-project',version:1,shape:{kind,native_interactive:true,parameters:{}},technology:fixture.technology});const before=JSON.stringify(w.radialState().current.segments);assert.equal(form.elements.namedItem('sides').value,'16');assert.equal(form.elements.namedItem('radius').value,'50');await click('#generate');assert.equal(JSON.stringify(w.radialState().current.segments),before);}
form.elements.namedItem('gap').value='-20';$('#kind').value='ring';$('#kind').dispatchEvent(new w.Event('change'));await click('#generate',true);assert.match($('#error').textContent,/gap exceeds/);
// Switch input modes through the real change handler, retaining the shown values.
form.elements.namedItem('gap').value='720.1234567';form.elements.namedItem('radius').value='40.123456789';$('#rectangular-input-mode').value='keyword';$('#rectangular-input-mode').dispatchEvent(new w.Event('change'));assert.equal(form.elements.namedItem('angle').disabled,false);await click('#generate');assert.equal(w.radialState().currentDefinition.native_keyword,true);
$('#rectangular-input-mode').value='interactive';$('#rectangular-input-mode').dispatchEvent(new w.Event('change'));await click('#generate');assert.equal(w.radialState().currentDefinition.native_interactive,true);assert.equal(w.radialState().current.parameters.radius,40.123456789);
const keys=['inductance_h','resistance_ohm','capacitance_first_f','capacitance_second_f','resistance_first_ohm','resistance_second_ohm','q_first','q_second','q_differential','shunt_single_ohm','shunt_differential_ohm'];
function session(result,c){const y=result.admittance_matrix;assert.deepEqual([y[1][1],y[1][0],y[0][1],y[0][0]].flat().map(bits),c.model.Y);[result.frequency_hz,...keys.map(k=>result.pi[k])].forEach((v,i)=>{if(Number.isFinite(Buffer.from(c.model.M[i],'hex').readDoubleLE()))assert.equal(bits(v),c.model.M[i]);else assert.equal(v,null);});assert.deepEqual(result.scattering_matrix.flat(2).map(bits),c.scattering.S);}
for(const c of fixtures.radial_interactive_sessions_original.cases){const{kind,parameters,technology,mesh}=c.request;await restore({format:'reasitic-project',version:1,shape:{kind,parameters,native_interactive:true},technology,mesh});$('#frequency').value=String(c.request.frequency_ghz);$('#eddy-mode').checked=c.request.eddy;$('#eddy-mode').dispatchEvent(new w.Event('change'));await click('#pi2');session(w.radialState().pi2Result,c);assert.ok($('#model-circuit svg'));await click('#download-pi2');session(JSON.parse(await downloads.at(-1).text()),c);}
call.destroy();w.close();console.log('120 original radial histories passed: 109 exact creations / 65,268 XYZ stores, 11 native failures, every successful form/project/regeneration/GDS stream, omitted-default recovery, mode switching and all six complete Pi2/model/JSON handlers, including eddy and a wide ring.');
