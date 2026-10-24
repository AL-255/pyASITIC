// Original COUPLING histories through the compiled browser transport.
import{readFileSync}from'node:fs';
import{gunzipSync}from'node:zlib';
import{execFileSync}from'node:child_process';
import{pathToFileURL}from'node:url';
import assert from'node:assert/strict';
import{installNumericalKernels}from'../web/numeric-kernels.mjs';
import{circuitSVG,sweepSVG,transformerSVG}from'../web/analysis-views.mjs';
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL('../dist/reasitic.zip',import.meta.url))),'zip');await installNumericalKernels(py,readFileSync(new URL('../dist/numeric.wasm',import.meta.url)));
const data=readFileSync(new URL('../tests/fixtures/coupling_original.json.gz',import.meta.url)),fixture=JSON.parse(gunzipSync(data));
py.FS.mkdirTree('/coupling/tests/fixtures');py.FS.writeFile('/coupling/tests/fixtures/coupling_original.json.gz',data);
for(const name of Object.keys(fixture.parents))py.FS.writeFile('/coupling/tests/fixtures/'+name+'.json',readFileSync(new URL('../tests/fixtures/'+name+'.json',import.meta.url)));
for(const name of['test_coupling_original','test_conductor_metrics_original'])py.FS.writeFile('/coupling/tests/'+name+'.py',readFileSync(new URL('../tests/'+name+'.py',import.meta.url)));
py.runPython(`
import sys,unittest
sys.path.insert(0,'/coupling/tests')
from test_coupling_original import OriginalCouplingTests
from reasitic.coupling_metrics import _compiled
assert _compiled is not None
assert unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(OriginalCouplingTests)).wasSuccessful()
from array import array
valid=array('d',[0.,0.,0.,40.,0.,0.,5.,1.,0.,10.,1.,40.,10.,1.,5.,1.,0.,0.,0.,0.,1.,1.]);out=array('d',[0.])*22;before=valid.tobytes()
assert _compiled(valid,out,1,1)==0 and valid.tobytes()==before
for na,nb,size,output in[(1,1,21,22),(1,1,22,21),(-1,1,6,6),(2001,0,16014,16014),(1001,1000,16014,16014),(1.5,1,26,26)]:
 data=array('d',[0.])*size;result=array('d',[19.])*output;saved=result.tobytes()
 try:_compiled(data,result,na,nb)
 except Exception:pass
 else:raise AssertionError('Invalid coupling batch accepted')
 assert result.tobytes()==saved
assert _compiled(array('d',[0.]*6),array('d',[0.]*6),0,0)==0
assert _compiled(valid,out,1,1)==0 and valid.tobytes()==before
`);
console.log('Compiled original COUPLING history, raw coefficient, geometry and bounded transport checks passed.');
if(process.argv.includes('--baseline')){
 py.globals.set('baseline_source',execFileSync('git',['show','4ba28b787be3c103ace55bdbb34cc794aae26a89:src/reasitic/inductance.py'],{cwd:new URL('..',import.meta.url),encoding:'utf8'}));
 py.runPython(`
import gzip,json,collections
from test_coupling_original import shapes,bits
namespace={'__name__':'reasitic._baseline_coupling','__package__':'reasitic'};exec(compile(baseline_source,'baseline_coupling','exec'),namespace)
fixture=json.loads(gzip.decompress(open('/coupling/tests/fixtures/coupling_original.json.gz','rb').read()));count=collections.Counter()
for c in fixture['cases']:
 if not c['calls']:continue
 tech,ss=shapes(c);by_name={s.name:s for s in ss}
 for e,report in zip(c['calls'],c['reports']):
  a,b=(by_name[e[side+'_before']['name']]for side in('first','second'));m,k=namespace['coupling_estimate'](a,b,tech);count['M']+=bits(m)!=report['mutual_bits'];count['k']+=bits(k)!=report['coefficient_bits'];count['calls']+=1
print('Prior 4ba28b7 browser runtime differences:',dict(count))
`);
}
if(process.argv.includes('--pairs')){
 py.globals.set('audit_source',readFileSync(new URL('./audit_coupling_original.py',import.meta.url),'utf8'));
 try{py.runPython(`
namespace={'__name__':'_coupling_audit','__file__':'/coupling/tools/audit_coupling_original.py'};exec(compile(audit_source,namespace['__file__'],'exec'),namespace)
sys.argv=['audit_coupling_original.py','--pairs']
try:namespace['main']()
except SystemExit as result:assert result.code==0
`);}catch(error){console.error(String(error));process.exit(1);}
}


// Actual project restoration and Estimate coupling handlers. Each worker request
// reconstructs a fresh geometry, so compare with the original first call.
py.runPython("from reasitic.bridge import request_json");const call=py.globals.get('request_json');
const{JSDOM}=await import(pathToFileURL(process.argv[3]).href),dom=new JSDOM(readFileSync(new URL('../dist/index.html',import.meta.url),'utf8'),{url:'https://example.test/',runScripts:'outside-only'}),w=dom.window,responses=[];
Object.assign(w,{circuitSVG,sweepSVG,transformerSVG,Blob});w.URL.createObjectURL=()=> 'blob:test';w.URL.revokeObjectURL=()=>{};w.HTMLAnchorElement.prototype.click=()=>{};
w.Worker=class{constructor(){queueMicrotask(()=>this.onmessage({data:{ready:true}}));}postMessage({id,request}){queueMicrotask(()=>{const r=JSON.parse(call(JSON.stringify(request)));responses.push({request,...r});this.onmessage({data:{id,...r}});});}};
const source=readFileSync(new URL('../dist/app.js',import.meta.url),'utf8').replace(/^import[^\n]+\n/,'').replaceAll('import.meta.url','"https://example.test/app.js"');w.eval(source+'\nglobalThis.couplingState=()=>({ready,busy,current});');
const $=s=>w.document.querySelector(s);
async function idle(){for(let i=0;i<500;i++){await new Promise(setImmediate);const s=w.couplingState();if(s.ready&&!s.busy)return;}throw Error('Coupling app did not become idle');}
async function click(id){assert.equal($(id).disabled,false,id+' disabled');$(id).click();await idle();assert.equal($('#error').hidden,true,$('#error').textContent);}
function bits(v){const b=Buffer.alloc(8);b.writeDoubleLE(v);return b.toString('hex');}
await idle();let count=0;
for(const c of fixture.cases.filter(c=>c.public&&c.calls.length)){
 Object.defineProperty($('#project-file'),'files',{configurable:true,value:[{text:async()=>JSON.stringify({format:'reasitic-project',version:1,technology:c.technology,shape:c.public})}]});$('#project-file').dispatchEvent(new w.Event('change'));await idle();assert.equal($('#error').hidden,true,$('#error').textContent);
 const before=JSON.stringify(w.couplingState().current.segments);await click('#coupling');const r=responses.at(-1).result;
 assert.equal(bits(r.mutual_nh),c.reports[0].mutual_bits,c.label);assert.equal(bits(r.k),c.reports[0].coefficient_bits,c.label);assert.match($('#analysis-status').textContent,/ASITIC coupling estimate/);assert.equal(JSON.stringify(w.couplingState().current.segments),before);count++;
}
// Exercise the distributed solver after all coupling batches in the same runtime.
const network=JSON.parse(readFileSync(new URL('../tests/fixtures/square_sessions_original.json',import.meta.url))).cases[1];
Object.defineProperty($('#project-file'),'files',{configurable:true,value:[{text:async()=>JSON.stringify({format:'reasitic-project',version:1,technology:network.request.technology,shape:{kind:network.request.kind,parameters:network.request.parameters,native_keyword:network.request.native_keyword},mesh:network.request.mesh})}]});$('#project-file').dispatchEvent(new w.Event('change'));await idle();assert.equal($('#error').hidden,true,$('#error').textContent);
$('#frequency').value=String(network.request.frequency_ghz);await click('#pi2');const model=responses.at(-1).result,y=model.admittance_matrix;
assert.deepEqual([y[1][1],y[1][0],y[0][1],y[0][0]].flat().map(bits),network.model.Y);assert.deepEqual(model.scattering_matrix.flat(2).map(bits),network.scattering.S);
call.destroy();w.close();console.log(`${count} actual paired project/coupling displays passed with original exact M/k stores; project preview remains unchanged. Subsequent original Pi2 Y/S stores also match.`);
