// Original WIRE creator stores, full electrical sessions and actual UI exports.
import{readFileSync}from"node:fs";
import{pathToFileURL}from"node:url";
import assert from"node:assert/strict";
import{installNumericalKernels}from"../web/numeric-kernels.mjs";
import{circuitSVG,sweepSVG,transformerSVG}from"../web/analysis-views.mjs";
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL("../dist/reasitic.zip",import.meta.url))),"zip");await installNumericalKernels(py,readFileSync(new URL("../dist/numeric.wasm",import.meta.url)));
const geometry=JSON.parse(readFileSync(new URL("../tests/fixtures/wire_original.json",import.meta.url))),electrical=JSON.parse(readFileSync(new URL("../tests/fixtures/wire_sessions_original.json",import.meta.url)));
py.globals.set("wire_fixture",JSON.stringify(geometry));
py.runPython(`
import json,struct
from reasitic import Technology,build
from reasitic.bridge import request_json
f=json.loads(wire_fixture);tech=Technology.from_text(f['technology']);assert len(f['cases'])==101
for i,c in enumerate(f['cases']):
 shape=build('wire',technology=tech,native_keyword=c['native_keyword'],native_interactive=c.get('native_interactive',False),**c['parameters'])
 assert struct.pack('<2d',*shape.origin)==struct.pack('<2d',*c['origin'])
 assert len(shape.segments)==1 and shape.parameters['phase']==c['config']['phase']
 s=shape.segments[0];r=c['segments'][0]
 assert struct.pack('<18d',*(v for p in s.points for v in p)).hex()==r['coordinates_bits'],('Wire XYZ',i)
 for value,key in((s.width,'width_bits'),(s.thickness,'thickness_bits'),(s.width if s.primary_width is None else s.primary_width,'primary_width_bits'),(s.thickness if s.primary_thickness is None else s.primary_thickness,'primary_thickness_bits')):assert struct.pack('<d',value).hex()==r[key]
 assert s.metal==r['metal']
`);
py.FS.mkdirTree('/wire-original-tests/fixtures');
for(const name of['wire_original.json','wire_sessions_original.json'])py.FS.writeFile('/wire-original-tests/fixtures/'+name,readFileSync(new URL('../tests/fixtures/'+name,import.meta.url)));
py.FS.writeFile('/wire-original-tests/test_wire_sessions_original.py',readFileSync(new URL('../tests/test_wire_sessions_original.py',import.meta.url)));
py.runPython(`
import sys,unittest
sys.path.insert(0,'/wire-original-tests')
import test_wire_sessions_original
result=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromModule(test_wire_sessions_original))
assert result.wasSuccessful(),'Original wire electrical session gate failed'
`);
console.log('101 original WIRE creators / 1,818 XYZ stores, six finite full Pi2 sessions and two original nonfinite/contact histories pass in WebAssembly.');
const call=py.globals.get('request_json');
function request(p){const r=JSON.parse(call(JSON.stringify(p)));assert.ok(!r.error,r.error);return r.result;}
function bits(value){const b=Buffer.alloc(8);b.writeDoubleLE(value);return b.toString('hex');}
function roundEven(value){const low=Math.floor(value),fraction=value-low;return fraction<.5?low:fraction>.5?low+1:low%2?low+1:low;}
function exactGeometry(s,c){assert.deepEqual(Array.from(s.origin),c.origin);assert.equal(s.segments.length,1);const a=s.segments[0],r=c.segments[0],b=Buffer.alloc(144);['start','end','outer_start','outer_end','inner_start','inner_end'].flatMap(k=>Array.from(a[k])).forEach((v,i)=>b.writeDoubleLE(v,8*i));assert.equal(b.toString('hex'),r.coordinates_bits);assert.equal(bits(a.width),r.width_bits);assert.equal(a.metal,r.metal);}
function gdsExact(bytes,c){
 const b=Buffer.from(bytes),polygons=[];let layer,datatype;
 for(let offset=0;offset<b.length;){const n=b.readUInt16BE(offset),kind=b[offset+2];assert.ok(n>=4&&offset+n<=b.length);if(kind===13)layer=b.readInt16BE(offset+4);if(kind===14)datatype=b.readInt16BE(offset+4);if(kind===16){const points=[];for(let k=offset+4;k<offset+n;k+=8)points.push([b.readInt32BE(k),b.readInt32BE(k+4)]);polygons.push({layer,datatype,points});}offset+=n;}
 assert.equal(polygons.length,1);const r=c.segments[0],raw=Buffer.from(r.coordinates_bits,'hex'),v=Array.from({length:18},(_,i)=>raw.readDoubleLE(i*8));assert.deepEqual(polygons[0].points,[6,9,15,12,6].map(k=>[roundEven((v[k]+c.origin[0])*1000),roundEven((v[k+1]+c.origin[1])*1000)]));assert.equal(polygons[0].layer,r.metal+1);assert.equal(polygons[0].datatype,0);
}
for(const c of geometry.cases){const r=request({action:'gds',kind:'wire',parameters:c.parameters,native_keyword:c.native_keyword,native_interactive:!!c.native_interactive,technology:geometry.technology});gdsExact(Buffer.from(r.base64,'base64'),c);}
console.log('All 101 native/interactive WIRE GDS streams independently decode to the original ribbon coordinates/layers.');
const{JSDOM}=await import(pathToFileURL(process.argv[3]).href),dom=new JSDOM(readFileSync(new URL('../dist/index.html',import.meta.url),'utf8'),{url:'https://example.test/',runScripts:'outside-only'}),w=dom.window,downloads=[],requests=[];
Object.assign(w,{circuitSVG,sweepSVG,transformerSVG,Blob});w.URL.createObjectURL=blob=>{downloads.push(blob);return'blob:test';};w.URL.revokeObjectURL=()=>{};w.HTMLAnchorElement.prototype.click=()=>{};
w.Worker=class{constructor(){queueMicrotask(()=>this.onmessage({data:{ready:true}}));}postMessage({id,request}){requests.push(request);queueMicrotask(()=>this.onmessage({data:{id,...JSON.parse(call(JSON.stringify(request)))}}));}};
const source=readFileSync(new URL('../dist/app.js',import.meta.url),'utf8').replace(/^import[^\n]+\n/,'').replaceAll('import.meta.url','"https://example.test/app.js"');w.eval(source+'\nglobalThis.wireState=()=>({ready,busy,current,currentDefinition,pi2Result});globalThis.wireStripProbe=()=>stripDefinition("model-ground","");');
const $=s=>w.document.querySelector(s);
async function idle(){for(let i=0;i<500;i++){await new Promise(setImmediate);const s=w.wireState();if(s.ready&&!s.busy)return;}throw Error('Wire app did not become idle');}
async function click(id,error=false){assert.equal($(id).disabled,false,id+' disabled');$(id).click();await idle();if(!error)assert.equal($('#error').hidden,true,$('#error').textContent);}
async function restore(project){Object.defineProperty($('#project-file'),'files',{configurable:true,value:[{text:async()=>JSON.stringify(project)}]});$('#project-file').dispatchEvent(new w.Event('change'));await idle();assert.equal($('#error').hidden,true,$('#error').textContent);}
function definition(c){return{kind:'wire',parameters:c.parameters,native_keyword:c.native_keyword,native_interactive:!!c.native_interactive};}
await idle();const c=geometry.cases.find(c=>c.label==='keyword/3.25/M5/-35.5/-1');assert.ok(c);
await restore({format:'reasitic-project',version:1,technology:geometry.technology,shape:definition(c)});await click('#generate');exactGeometry(w.wireState().current,c);assert.equal(w.wireState().currentDefinition.native_keyword,true);assert.equal($('#ring-input-note').hidden,false);
const defaults=geometry.cases.find(c=>c.label==='keyword/defaults/metal,angle,phase,x,y');assert.ok(defaults);await restore({format:'reasitic-project',version:1,technology:geometry.technology,shape:definition(defaults)});assert.equal($('#metal').value,'4');assert.equal(Number(w.document.querySelector('[name=y]').value),defaults.config.width);await click('#generate');exactGeometry(w.wireState().current,defaults);
for(const phase of geometry.cases.filter(c=>c.label.startsWith('keyword/phase/'))){await restore({format:'reasitic-project',version:1,technology:geometry.technology,shape:definition(phase)});assert.equal(w.document.querySelector('[name=phase]').value,phase.config.phase<0?'-1':'1');await click('#generate');exactGeometry(w.wireState().current,phase);}
for(const sample of[c,geometry.cases.find(c=>c.label==='interactive/0.01/37/1')]){
 await restore({format:'reasitic-project',version:1,technology:geometry.technology,shape:definition(sample)});exactGeometry(w.wireState().current,sample);
 if(sample.native_interactive)assert.match($('#ring-input-note').textContent,/stored as radians/);
 await click('#download-project');const project=JSON.parse(await downloads.at(-1).text());assert.equal(!!project.shape.native_interactive,!!sample.native_interactive);await restore(project);exactGeometry(w.wireState().current,sample);
 await click('#download-gds');gdsExact(await downloads.at(-1).arrayBuffer(),sample);assert.equal(!!requests.at(-1).native_interactive,!!sample.native_interactive);
}
// Ground and pad controls share this WIRE factory, including its numeric parser.
const ground=geometry.cases.find(c=>c.label==='keyword/3.25/M1/0/1');assert.ok(ground);
for(const key of['length','width','x','y'])$('#model-ground-'+key).value=String(ground.parameters[key]);$('#model-ground-metal').value='0';
const strip=w.wireStripProbe();assert.equal(strip.native_keyword,true);exactGeometry(request({action:'build',...strip,technology:geometry.technology}),ground);
const keys=['inductance_h','resistance_ohm','capacitance_first_f','capacitance_second_f','resistance_first_ohm','resistance_second_ohm','q_first','q_second','q_differential','shunt_single_ohm','shunt_differential_ohm'];
function exactModel(r,c){const y=r.admittance_matrix;assert.deepEqual([y[1][1],y[1][0],y[0][1],y[0][0]].flat().map(bits),c.model.Y);[r.frequency_hz,...keys.map(k=>r.pi[k])].forEach((v,i)=>{if(Number.isFinite(Buffer.from(c.model.M[i],'hex').readDoubleLE()))assert.equal(bits(v),c.model.M[i]);else assert.equal(v,null);});assert.deepEqual(r.scattering_matrix.flat(2).map(bits),c.scattering.S);}
for(const c of[electrical.cases.find(c=>c.index===0),electrical.cases.find(c=>c.index===4)]){
 const p=c.request;await restore({format:'reasitic-project',version:1,technology:p.technology,shape:{kind:'wire',parameters:p.parameters,native_keyword:p.native_keyword,native_interactive:p.native_interactive},mesh:p.mesh});$('#frequency').value=String(p.frequency_ghz);await click('#pi2');exactModel(w.wireState().pi2Result,c);await click('#download-pi2');exactModel(JSON.parse(await downloads.at(-1).text()),c);
}
for(const c of electrical.undefined_cases){const p=c.request;await restore({format:'reasitic-project',version:1,technology:p.technology,shape:{kind:'wire',parameters:p.parameters,native_keyword:p.native_keyword,native_interactive:p.native_interactive},mesh:p.mesh});$('#frequency').value=String(p.frequency_ghz);await click('#pi2',true);assert.match($('#error').textContent,c.index===2?/contact collapses/:/nonfinite admittance/);assert.equal($('#download-pi2').disabled,true);}
call.destroy();w.close();console.log('Actual WIRE form/default restoration, command regeneration, interactive angle notice, project/GDS modes, original Pi2 JSON exports and both native nonfinite diagnostics passed.');
