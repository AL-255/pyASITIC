// Original GEOM/METALAREA through compiled Python and actual project displays.
import{readFileSync}from'node:fs';
import{gunzipSync}from'node:zlib';
import{execFileSync}from'node:child_process';
import{pathToFileURL}from'node:url';
import assert from'node:assert/strict';
import{installNumericalKernels}from'../web/numeric-kernels.mjs';
import{circuitSVG,sweepSVG,transformerSVG}from'../web/analysis-views.mjs';
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL('../dist/reasitic.zip',import.meta.url))),'zip');await installNumericalKernels(py,readFileSync(new URL('../dist/numeric.wasm',import.meta.url)));
const data=readFileSync(new URL('../tests/fixtures/geometry_metrics_original.json.gz',import.meta.url)),fixture=JSON.parse(gunzipSync(data));
py.FS.mkdirTree('/geometry/tests/fixtures');py.FS.writeFile('/geometry/tests/fixtures/geometry_metrics_original.json.gz',data);
for(const name of Object.keys(fixture.parents))py.FS.writeFile('/geometry/tests/fixtures/'+name+'.json',readFileSync(new URL('../tests/fixtures/'+name+'.json',import.meta.url)));
py.FS.writeFile('/geometry/tests/fixtures/geometry_primitives_original.json',readFileSync(new URL('../tests/fixtures/geometry_primitives_original.json',import.meta.url)));
py.FS.writeFile('/geometry/tests/test_geometry_metrics_original.py',readFileSync(new URL('../tests/test_geometry_metrics_original.py',import.meta.url)));
try{py.runPython(`
import sys,unittest
from array import array
sys.path.insert(0,'/geometry/tests')
from test_geometry_metrics_original import OriginalGeometryMetricTests,OriginalGeometryPrimitiveTests
from reasitic.geometry_metrics import _compiled
assert _compiled is not None
suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(c)for c in(OriginalGeometryMetricTests,OriginalGeometryPrimitiveTests))
assert unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful()
valid=array('d',[0.,0.,0.,40.,30.,20.,5.]);out=array('d',[0.])*6;saved=valid.tobytes()
assert _compiled(valid,out)==0 and valid.tobytes()==saved
for data,out in[(array('d',[0.]*8),array('d',[19.]*6)),(valid,array('d',[19.]*5)),(array('d',[0.]*(20001*7)),array('d',[19.]*6))]:
 before=out.tobytes()
 try:_compiled(data,out)
 except Exception:pass
 else:raise AssertionError('Invalid geometry metric batch accepted')
 assert out.tobytes()==before
assert _compiled(array('d'),array('d',[0.])*6)==0
out=array('d',[0.])*6;assert _compiled(valid,out)==0 and valid.tobytes()==saved
`);}catch(error){console.error(String(error));process.exit(1);}
console.log('260 original CLI reports / 3007 raw segment operands and accumulation stores, plus 538 direct threshold/extreme/nonfinite-word cases, passed in compiled Pyodide. Bounds, immutable inputs and rejected-call recovery passed.');
if(process.argv.includes('--baseline')){
 py.globals.set('baseline_source',execFileSync('git',['show','39cdf9c652ff2ad5ab4ee57c67c0b4bfb65658c9:src/reasitic/model.py'],{cwd:new URL('..',import.meta.url),encoding:'utf8'}));
 py.runPython(`
import types,gzip,json,collections
from reasitic import Technology
from reasitic.bridge import _shape
from dataclasses import asdict
from test_geometry_metrics_original import bits
mod=types.ModuleType('reasitic._baseline_geometry');sys.modules[mod.__name__]=mod;exec(compile(baseline_source,'baseline_model','exec'),mod.__dict__)
fixture=json.loads(gzip.decompress(open('/geometry/tests/fixtures/geometry_metrics_original.json.gz','rb').read()));count=collections.Counter()
for c in fixture['cases']:
 if not c['geom']:continue
 shape=_shape(c['public'],Technology.from_text(c['technology']));before=mod.Shape(shape.name,shape.kind,shape.origin,shape.parameters,[mod.Segment(**asdict(s))for s in shape.segments],shape.warnings).to_dict()
 count['length']+=bits(before['length'])!=c['reports'][0]['length_bits'];count['area']+=bits(before['area'])!=c['reports'][0]['area_bits'];count['reports']+=1
print('Previous 39cdf9c browser geometry metric differences:',dict(count))
`);
}
py.runPython('from reasitic.bridge import request_json');const call=py.globals.get('request_json');
const{JSDOM}=await import(pathToFileURL(process.argv[3]).href),dom=new JSDOM(readFileSync(new URL('../dist/index.html',import.meta.url),'utf8'),{url:'https://example.test/',runScripts:'outside-only'}),w=dom.window,responses=[],downloads=[];
Object.assign(w,{circuitSVG,sweepSVG,transformerSVG,Blob});w.URL.createObjectURL=blob=>{downloads.push(blob);return'blob:test';};w.URL.revokeObjectURL=()=>{};w.HTMLAnchorElement.prototype.click=()=>{};
w.Worker=class{constructor(){queueMicrotask(()=>this.onmessage({data:{ready:true}}));}postMessage({id,request}){queueMicrotask(()=>{const r=JSON.parse(call(JSON.stringify(request)));responses.push({request,...r});this.onmessage({data:{id,...r}});});}};
const source=readFileSync(new URL('../dist/app.js',import.meta.url),'utf8').replace(/^import[^\n]+\n/,'').replaceAll('import.meta.url','"https://example.test/app.js"');w.eval(source+'\nglobalThis.geometryState=()=>({ready,busy,current});');
const $=s=>w.document.querySelector(s);
async function idle(){for(let i=0;i<500;i++){await new Promise(setImmediate);const s=w.geometryState();if(s.ready&&!s.busy)return;}throw Error('Geometry app did not become idle');}
async function click(id){assert.equal($(id).disabled,false,id+' disabled');$(id).click();await idle();assert.equal($('#error').hidden,true,$('#error').textContent);}
async function restore(c){Object.defineProperty($('#project-file'),'files',{configurable:true,value:[{text:async()=>JSON.stringify({format:'reasitic-project',version:1,shape:c.public,technology:c.technology,mesh:c.mesh})}]});$('#project-file').dispatchEvent(new w.Event('change'));await idle();assert.equal($('#error').hidden,true,$('#error').textContent);}
function bits(v){const b=Buffer.alloc(8);b.writeDoubleLE(v);return b.toString('hex');}
const fmt=v=>Number(v).toLocaleString(undefined,{maximumSignificantDigits:4});
await idle();let count=0;
for(const c of fixture.cases.filter(c=>c.geom.length)){
 await restore(c);const shape=w.geometryState().current;assert.equal(bits(shape.length),c.reports[0].length_bits,c.label);assert.equal(bits(shape.area),c.reports[0].area_bits,c.label);assert.equal(bits(shape.metal_area),c.reports[1].area_bits,c.label);
 assert.equal($('#stat-length').textContent,fmt(shape.length)+' µm');assert.equal($('#stat-area').textContent,fmt(shape.area)+' µm²');assert.equal($('#stat-metal-area').textContent,fmt(shape.metal_area)+' µm²');count++;
}
const c=fixture.cases.find(c=>c.public.kind==='transformer3d');await restore(c);const before=JSON.stringify(w.geometryState().current.segments);await click('#download-gds');assert.ok((await downloads.at(-1).arrayBuffer()).byteLength>0);assert.equal(JSON.stringify(w.geometryState().current.segments),before);
const network=JSON.parse(readFileSync(new URL('../tests/fixtures/square_sessions_original.json',import.meta.url))).cases[1];await restore({public:{kind:network.request.kind,parameters:network.request.parameters,native_keyword:network.request.native_keyword},technology:network.request.technology,mesh:network.request.mesh});$('#frequency').value=String(network.request.frequency_ghz);await click('#pi2');const result=responses.at(-1).result,y=result.admittance_matrix;
assert.deepEqual([y[1][1],y[1][0],y[0][1],y[0][0]].flat().map(bits),network.model.Y);assert.deepEqual(result.scattering_matrix.flat(2).map(bits),network.scattering.S);
call.destroy();w.close();console.log(`${count} actual original project/GEOM/METALAREA displays, GDS download without geometry mutation and a subsequent exact original Pi2 Y/S model passed.`);
