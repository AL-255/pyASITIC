// Native mesh command inputs through the shipped runtime and real DOM handlers.
import{readFileSync}from'node:fs';
import{gunzipSync}from'node:zlib';
import{pathToFileURL}from'node:url';
import assert from'node:assert/strict';
import{installNumericalKernels}from'../web/numeric-kernels.mjs';
import{circuitSVG,sweepSVG,transformerSVG}from'../web/analysis-views.mjs';
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL('../dist/reasitic.zip',import.meta.url))),'zip');await installNumericalKernels(py,readFileSync(new URL('../dist/numeric.wasm',import.meta.url)));
const data=readFileSync(new URL('../tests/fixtures/mesh_inputs_original.json.gz',import.meta.url)),fixture=JSON.parse(gunzipSync(data));
py.FS.mkdirTree('/mesh-inputs/tests/fixtures');py.FS.writeFile('/mesh-inputs/tests/fixtures/mesh_inputs_original.json.gz',data);
for(const name of['test_mesh_inputs_original','test_reduction'])py.FS.writeFile('/mesh-inputs/tests/'+name+'.py',readFileSync(new URL('../tests/'+name+'.py',import.meta.url)));
try{py.runPython(`
import sys,unittest
sys.path.insert(0,'/mesh-inputs/tests')
from test_mesh_inputs_original import OriginalMeshInputTests
from test_reduction import OriginalReductionTests
from reasitic.reduction import _compiled_sum
from array import array
from reasitic.filament import _compiled_filaments
assert _compiled_filaments is not None
assert _compiled_sum is not None
suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(c)for c in(OriginalMeshInputTests,OriginalReductionTests))
assert unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful()
for data,output in[(array('d',[0.]*3),array('d',[23.]*2)),(array('d',[0.]*(2*65537)),array('d',[23.]*2)),(array('d',[1.,2.]),array('d',[23.]))]:
 before=data.tobytes();saved=output.tobytes()
 try:_compiled_sum(data,output)
 except Exception:pass
 else:raise AssertionError('Invalid complex accumulation buffer accepted')
 assert data.tobytes()==before and output.tobytes()==saved
for n in(0,1,65536):
 data=array('d',[0.])*(2*n);output=array('d',[23.]*2);before=data.tobytes()
 assert _compiled_sum(data,output)==0 and list(output)==[0.,0.]and data.tobytes()==before

`);}catch(error){console.error(String(error));process.exit(1);}
py.runPython('from reasitic.bridge import request_json');const call=py.globals.get('request_json');
const{JSDOM}=await import(pathToFileURL(process.argv[3]).href),dom=new JSDOM(readFileSync(new URL('../dist/index.html',import.meta.url),'utf8'),{url:'https://example.test/',runScripts:'outside-only'}),w=dom.window,requests=[],downloads=[];
Object.assign(w,{circuitSVG,sweepSVG,transformerSVG,Blob});w.URL.createObjectURL=blob=>{downloads.push(blob);return'blob:test';};w.URL.revokeObjectURL=()=>{};w.HTMLAnchorElement.prototype.click=()=>{};
w.Worker=class{constructor(){queueMicrotask(()=>this.onmessage({data:{ready:true}}));}postMessage({id,request}){requests.push(request);queueMicrotask(()=>this.onmessage({data:{id,...JSON.parse(call(JSON.stringify(request)))}}));}};
const source=readFileSync(new URL('../dist/app.js',import.meta.url),'utf8').replace(/^import[^\n]+\n/,'').replaceAll('import.meta.url','"https://example.test/app.js"');
w.eval(source+'\nglobalThis.meshInputState=()=>({ready,busy,matrixResult,pi2Result});');const $=s=>w.document.querySelector(s);
async function idle(){for(let i=0;i<1000;i++){await new Promise(setImmediate);const s=w.meshInputState();if(s.ready&&!s.busy)return;}throw Error('Mesh input app did not become idle');}
async function click(id){assert.equal($(id).disabled,false,id+' disabled');$(id).click();await idle();assert.equal($('#error').hidden,true,$('#error').textContent);}
async function restore(c){const{kind,parameters,native_keyword,technology,mesh}=c.request,project={format:'reasitic-project',version:1,shape:{kind,parameters,native_keyword},technology,mesh};Object.defineProperty($('#project-file'),'files',{configurable:true,value:[{text:async()=>JSON.stringify(project)}]});$('#project-file').dispatchEvent(new w.Event('change'));await idle();assert.equal($('#error').hidden,true,$('#error').textContent);}
function bits(value){const b=Buffer.alloc(8);b.writeDoubleLE(value);return b.toString('hex');}
await idle();$('#frequency').value='1';
for(const[i,c]of fixture.cases.entries()){
 await restore(c);$('#mesh-target').value='lmat';await click('#mesh-check');assert.match($('#mesh-feedback').textContent,new RegExp(c.lmat.counts[0].total+' / 256 filaments'));assert.match($('#mesh-feedback').textContent,/Effective cells:/);
 await click('#lmat');let result=w.meshInputState().matrixResult;assert.equal(bits(result.inductance_h)+bits(result.resistance_ohm),c.lmat.reports[0].bits,'Actual LMAT UI '+i);
 const request=requests.filter(r=>r.action==='lmat').at(-1);assert.equal(request.native_mesh,true);for(const key of['length_cell','width_cell','thickness_cell'])assert.equal(request.mesh[key],c.request.mesh[key],'Preserve original input before native parsing');
 await click('#pi2');result=w.meshInputState().pi2Result;const y=result.admittance_matrix;assert.deepEqual([y[1][1],y[1][0],y[0][1],y[0][0]].flat().map(bits),c.pi2.model.Y,'Actual Pi2 UI '+i);assert.equal(requests.filter(r=>r.action==='pi2').at(-1).native_mesh,true);
 await click('#download-project');const saved=JSON.parse(await downloads.at(-1).text());assert.equal(saved.native_mesh,true);for(const[key,value]of Object.entries(c.request.mesh))assert.equal(saved.mesh[key],value,'Project retains entered decimal mesh values');
}
await click('#capacitance');assert.equal(requests.filter(r=>r.action==='capacitance').at(-1).native_mesh,true,'Standalone CAP shares native CCELL parsing');
call.destroy();w.close();console.log('All six original fractional CELL/CCELL histories passed in compiled Pyodide and actual LMAT/Pi2/CAP/project handlers, including the 200-filament case. All globals, counts, finite filament/LMAT/Y/model/S stores and resonance classifications match. Typed binary64 requests remain distinct.');
