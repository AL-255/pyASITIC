// Original conductor commands through compiled kernels and actual webpage handlers.
import{readFileSync}from'node:fs';
import{pathToFileURL}from'node:url';
import assert from'node:assert/strict';
import{installNumericalKernels}from'../web/numeric-kernels.mjs';
import{circuitSVG,sweepSVG,transformerSVG}from'../web/analysis-views.mjs';
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL('../dist/reasitic.zip',import.meta.url))),'zip');await installNumericalKernels(py,readFileSync(new URL('../dist/numeric.wasm',import.meta.url)));
const fixture=JSON.parse(readFileSync(new URL('../tests/fixtures/conductor_metrics_original.json',import.meta.url)));
py.FS.mkdirTree('/conductor/tests/fixtures');
for(const name of['conductor_metrics_original',...Object.keys(fixture.parents)])py.FS.writeFile('/conductor/tests/fixtures/'+name+'.json',readFileSync(new URL('../tests/fixtures/'+name+'.json',import.meta.url)));
py.FS.writeFile('/conductor/tests/test_conductor_metrics_original.py',readFileSync(new URL('../tests/test_conductor_metrics_original.py',import.meta.url)));
py.runPython(`
import sys,unittest,struct
from array import array
sys.path.insert(0,'/conductor/tests')
from test_conductor_metrics_original import OriginalConductorMetricTests
from reasitic.conductor_metrics import _compiled
assert _compiled is not None
assert unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(OriginalConductorMetricTests)).wasSuccessful()
valid=array('d',[0.,0.,0.,40.,0.,0.,5.,.5,.065,0.,0.,0.,0.,0.,5.,.5]);original=valid.tobytes();output=array('d',[0.])*9
assert _compiled(valid,output)==0 and valid.tobytes()==original
for data,out in[(valid,array('d',[19.])*8),(array('d',[0.]*(16*2001)),array('d',[19.])*9),(array('d',[0.]*17),array('d',[19.])*9)]:
 before=out.tobytes()
 try:_compiled(data,out)
 except Exception:pass
 else:raise AssertionError('Invalid conductor metric batch accepted')
 assert out.tobytes()==before
for index,value in[(9,2),(9,-1),(10,1.5),(11,2147483648.)]:
 data=array('d',valid);data[9]=1.;data[index]=value;before=output.tobytes()
 try:_compiled(data,output)
 except Exception:pass
 else:raise AssertionError('Invalid conductor metric record accepted')
 assert output.tobytes()==before
assert _compiled(array('d'),output)==0 and list(output)==[0.]*9
assert _compiled(valid,output)==0 and valid.tobytes()==original
from reasitic.bridge import request_json
`);
console.log('56 complete original conductor histories / 392 raw DC returns, 56 printed L and 392 QLF stores passed in compiled Pyodide. Batch bounds, immutable caller buffers and failure recovery passed.');
const call=py.globals.get('request_json'),{JSDOM}=await import(pathToFileURL(process.argv[3]).href),dom=new JSDOM(readFileSync(new URL('../dist/index.html',import.meta.url),'utf8'),{url:'https://example.test/',runScripts:'outside-only'}),w=dom.window,downloads=[],responses=[];
Object.assign(w,{circuitSVG,sweepSVG,transformerSVG,Blob});w.URL.createObjectURL=blob=>{downloads.push(blob);return'blob:test';};w.URL.revokeObjectURL=()=>{};w.HTMLAnchorElement.prototype.click=()=>{};
w.Worker=class{constructor(){queueMicrotask(()=>this.onmessage({data:{ready:true}}));}postMessage({id,request}){queueMicrotask(()=>{const r=JSON.parse(call(JSON.stringify(request)));responses.push({request,...r});this.onmessage({data:{id,...r}});});}};
const source=readFileSync(new URL('../dist/app.js',import.meta.url),'utf8').replace(/^import[^\n]+\n/,'').replaceAll('import.meta.url','"https://example.test/app.js"');w.eval(source+'\nglobalThis.conductorState=()=>({ready,busy,current,sweepRows});');
const $=s=>w.document.querySelector(s);
async function idle(){for(let i=0;i<500;i++){await new Promise(setImmediate);const s=w.conductorState();if(s.ready&&!s.busy)return;}throw Error('Conductor app did not become idle');}
async function click(id,error=false){assert.equal($(id).disabled,false,id+' disabled');$(id).click();await idle();if(!error)assert.equal($('#error').hidden,true,$('#error').textContent);}
async function restore(c){Object.defineProperty($('#project-file'),'files',{configurable:true,value:[{text:async()=>JSON.stringify({format:'reasitic-project',version:1,technology:c.technology,shape:c.public,mesh:c.mesh})}]});$('#project-file').dispatchEvent(new w.Event('change'));await idle();assert.equal($('#error').hidden,true,$('#error').textContent);}
function bits(v){const b=Buffer.alloc(8);b.writeDoubleLE(v);return b.toString('hex');}
await idle();
for(const c of fixture.cases){
 await restore(c);const before=JSON.stringify(w.conductorState().current.segments);$('#frequency').value='0.001';await click('#simulate');const r=responses.at(-1).result;
 assert.equal(bits(r.inductance_nh),c.reports[0].output_bits);assert.equal(bits(r.qlf),c.reports[1].output_bits);assert.equal(JSON.stringify(w.conductorState().current.segments),before);
 assert.match($('#result-l').textContent,/nH/);assert.match($('#result-r').textContent,/Ω/);
}
const c=fixture.cases.find(c=>c.label==='square_sessions_original/1');assert.ok(c);await restore(c);
$('#sweep-model').value='estimates';$('#sweep-model').dispatchEvent(new w.Event('change'));$('#sweep-first').value='1';$('#sweep-last').value='100';$('#sweep-count').value='3';$('#sweep-scale').value='log';await click('#sweep');
const sweep=w.conductorState().sweepRows;assert.equal(sweep.length,3);
for(const[row,e]of sweep.map((r,i)=>[r,c.reports[i+3]])){assert.equal(bits(row.inductance_nh),c.reports[0].output_bits);assert.equal(bits(row.q),e.output_bits);}
$('#sweep-metric').value='q';$('#sweep-metric').dispatchEvent(new w.Event('change'));assert.ok($('#sweep-chart svg'));await click('#download-csv');const csv=(await downloads.at(-1).text()).trim().split('\n');assert.equal(csv.length,4);
for(let i=0;i<3;i++){const fields=csv[i+1].split(',');assert.equal(bits(Number(fields[3])),bits(sweep[i].inductance_nh));assert.equal(bits(Number(fields[5])),bits(sweep[i].q));}
// Same shared numerical plans must remain usable after the conductor aggregate.
const network=JSON.parse(readFileSync(new URL('../tests/fixtures/square_sessions_original.json',import.meta.url))).cases[1];
await restore({technology:network.request.technology,public:{kind:network.request.kind,parameters:network.request.parameters,native_keyword:network.request.native_keyword},mesh:network.request.mesh});$('#frequency').value=String(network.request.frequency_ghz);await click('#pi2');const model=responses.at(-1).result,y=model.admittance_matrix;
assert.deepEqual([y[1][1],y[1][0],y[0][1],y[0][0]].flat().map(bits),network.model.Y);assert.deepEqual(model.scattering_matrix.flat(2).map(bits),network.scattering.S);
call.destroy();w.close();console.log('All 56 actual project/estimate displays, original 1/10/100 GHz QLF plot/CSV stores, unchanged geometry and a subsequent complete original Pi2 model passed.');
