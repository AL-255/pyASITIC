// Original raw resistance returns, batch bounds and actual estimate/sweep UI.
import{readFileSync}from"node:fs";
import{pathToFileURL}from"node:url";
import assert from"node:assert/strict";
import{installNumericalKernels}from"../web/numeric-kernels.mjs";
import{circuitSVG,sweepSVG,transformerSVG}from"../web/analysis-views.mjs";
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL("../dist/reasitic.zip",import.meta.url))),"zip");
await installNumericalKernels(py,readFileSync(new URL("../dist/numeric.wasm",import.meta.url)));
const fixture=JSON.parse(readFileSync(new URL("../tests/fixtures/resistance_original.json",import.meta.url)));
py.globals.set("resistance_fixture",JSON.stringify(fixture));
py.runPython(`
from array import array
from fractions import Fraction
import json,math,struct
from reasitic import Technology,build,resistance_dc,resistance_hf
from reasitic.model import Shape,Segment
from reasitic.resistance import _compiled,_records
from reasitic.bridge import request_json
assert _compiled is not None
finite=undefined=matched=0;pending=[]
for c in json.loads(resistance_fixture)['cases']:
 tech=Technology.from_text(c['technology']);segments=[]
 for r in c['inputs']:
  p=r['endpoints'];segments.append(Segment(p[:3],p[3:],p[:3],p[3:],p[:3],p[3:],r['width'],r.get('thickness',0.),r['metal'],r.get('nx',0),r.get('ny',0)))
 shape=Shape('A','probe',[0,0],{},segments);rows=_records(shape,tech)
 data=array('d',(v for r in rows for v in r));saved=data.tobytes()
 p=c['public'];public=build(p['kind'],technology=tech,native_keyword=p.get('native_keyword',False),**p['parameters'])
 exact_inputs=[struct.pack('<12d',*r)for r in _records(public,tech)]==[struct.pack('<12d',*r)for r in rows]
 if exact_inputs:matched+=1
 else:pending.append(c['label'])
 for e in c['events']:
  output=array('d',[0.])*4;frequency=e.get('frequency_hz');assert _compiled(data,output,0 if frequency is None else 1,frequency or 0.)==0
  sig,ex=struct.unpack('<QH',bytes.fromhex(e['extended_bits']));power=ex&0x7fff
  if power==0x7fff:
   assert math.isnan(output[0])
   try:resistance_hf(shape,tech,frequency)
   except ValueError as error:assert 'width ≥ metal thickness'in str(error)
   else:raise AssertionError('Native undefined HF resistance accepted')
   undefined+=1
  else:
   assert struct.pack('<IIH',*(int(v)for v in output[1:])).hex()==e['extended_bits'],(c['label'],e)
   expected=float(Fraction(sig)*Fraction(2)**((power or 1)-16383-63)*(-1 if ex&0x8000 else 1))
   actual=resistance_dc(shape,tech)if frequency is None else resistance_hf(shape,tech,frequency)
   assert struct.pack('<d',actual)==struct.pack('<d',expected)
   if exact_inputs:
    actual=resistance_dc(public,tech)if frequency is None else resistance_hf(public,tech,frequency)
    assert struct.pack('<d',actual)==struct.pack('<d',expected)
   finite+=1
 assert data.tobytes()==saved
assert(finite,undefined,matched)==(270,2,31)
assert pending==['analysis/1','analysis/11','wire/M5/0.1']
output=array('d',[3.,4.,5.,6.]);assert _compiled(array('d'),output,0,0.)==0 and list(output)==[0.,0.,0.,0.]
valid=array('d',[0.,0.,0.,40.,0.,0.,5.,.5,.065,0.,0.,0.]);saved=valid.tobytes()
for data,out,operation,frequency in((valid,array('d',[19.]*3),0,0.),(valid,array('d',[19.]*4),2,0.),(valid,array('d',[19.]*4),1,-1.),(valid,array('d',[19.]*4),1,math.nan),(array('d',[0.]*(12*20001)),array('d',[19.]*4),0,0.)):
 before=out.tobytes()
 try:_compiled(data,out,operation,frequency)
 except Exception:pass
 else:raise AssertionError('Invalid resistance batch accepted')
 assert out.tobytes()==before
assert valid.tobytes()==saved
assert _compiled(valid,array('d',[0.]*4),1,1e9)==0
`);
console.log("34 original histories / all 270 finite raw x87 resistance returns and two bounded native NaNs match in WebAssembly. All 31 matching public creator histories pass; three pre-existing creator input gaps remain explicit. Batch bounds, empty input, failure recovery and caller buffers pass.");
const call=py.globals.get("request_json"),{JSDOM}=await import(pathToFileURL(process.argv[3]).href),dom=new JSDOM(readFileSync(new URL("../dist/index.html",import.meta.url),"utf8"),{url:"https://example.test/",runScripts:"outside-only"}),w=dom.window,downloads=[],requests=[],responses=[];
Object.assign(w,{circuitSVG,sweepSVG,transformerSVG,Blob});w.URL.createObjectURL=blob=>{downloads.push(blob);return"blob:test";};w.URL.revokeObjectURL=()=>{};w.HTMLAnchorElement.prototype.click=()=>{};
w.Worker=class{constructor(){queueMicrotask(()=>this.onmessage({data:{ready:true}}));}postMessage({id,request}){requests.push(request);queueMicrotask(()=>{const result=JSON.parse(call(JSON.stringify(request)));responses.push({request,...result});this.onmessage({data:{id,...result}});});}};
const source=readFileSync(new URL("../dist/app.js",import.meta.url),"utf8").replace(/^import[^\n]+\n/,"").replaceAll("import.meta.url",'"https://example.test/app.js"');w.eval(source+"\nglobalThis.resistanceState=()=>({ready,busy,current,sweepRows});");
const $=s=>w.document.querySelector(s);
async function idle(){for(let i=0;i<500;i++){await new Promise(setImmediate);const s=w.resistanceState();if(s.ready&&!s.busy)return;}throw Error("Resistance app did not become idle");}
async function click(id,error=false){assert.equal($(id).disabled,false,id+" disabled");$(id).click();await idle();if(!error)assert.equal($("#error").hidden,true,$("#error").textContent);}
async function restore(project){Object.defineProperty($("#project-file"),"files",{configurable:true,value:[{text:async()=>JSON.stringify(project)}]});$("#project-file").dispatchEvent(new w.Event("change"));await idle();assert.equal($("#error").hidden,true,$("#error").textContent);}
function bits(v){const b=Buffer.alloc(8);b.writeDoubleLE(v);return b.toString("hex");}
function expected(e){const b=Buffer.from(e.extended_bits,"hex"),ex=b.readUInt16LE(8);return Number(b.readBigUInt64LE())*2**((ex&0x7fff)-16383-63)*(ex&0x8000?-1:1);}
await idle();const c=fixture.cases.find(c=>c.label==="square_sessions_original/1");assert.ok(c);
await restore({format:"reasitic-project",version:1,technology:c.technology,shape:c.public});assert.equal(bits(w.resistanceState().current.dc_ohm),bits(expected(c.events[0])));
for(const e of[c.events[2],c.events[5]]){
 const i=c.events.indexOf(e);$("#frequency").value=String(c.frequency_ghz[i-1]);await click("#simulate");const result=responses.at(-1).result;
 assert.equal(bits(result.hf_ohm),bits(expected(e)));assert.equal(bits(result.dc_ohm),bits(expected(c.events[0])));assert.equal(result.frequency_hz,e.frequency_hz);assert.match($("#result-r").textContent,/Ω/);
}
$("#sweep-model").value="estimates";$("#sweep-model").dispatchEvent(new w.Event("change"));$("#sweep-first").value="1";$("#sweep-last").value="100";$("#sweep-count").value="3";$("#sweep-scale").value="log";await click("#sweep");
const rows=w.resistanceState().sweepRows;assert.equal(rows.length,3);
for(const[row,event]of rows.map((r,i)=>[r,c.events[i+3]])){assert.equal(row.frequency_hz,event.frequency_hz);assert.equal(bits(row.resistance_ohm),bits(expected(event)));}
$("#sweep-metric").value="resistance_ohm";$("#sweep-metric").dispatchEvent(new w.Event("change"));assert.ok($("#sweep-chart svg"));await click("#download-csv");const csv=(await downloads.at(-1).text()).trim().split("\n");assert.equal(csv.length,4);
for(let i=0;i<3;i++){const fields=csv[i+1].split(",");assert.equal(Number(fields[2]),rows[i].frequency_hz);assert.equal(bits(Number(fields[4])),bits(rows[i].resistance_ohm));}
// Resistance and the distributed solvers share retained elementary plans.
// Exercise both in this interpreter to catch buffer/plan interference.
const network=JSON.parse(readFileSync(new URL("../tests/fixtures/square_sessions_original.json",import.meta.url))).cases[1];
await restore({format:"reasitic-project",version:1,technology:network.request.technology,shape:{kind:network.request.kind,parameters:network.request.parameters,native_keyword:network.request.native_keyword},mesh:network.request.mesh});$("#frequency").value=String(network.request.frequency_ghz);await click("#pi2");
const model=responses.at(-1).result,y=model.admittance_matrix;
assert.deepEqual([y[1][1],y[1][0],y[0][1],y[0][0]].flat().map(bits),network.model.Y);assert.deepEqual(model.scattering_matrix.flat(2).map(bits),network.scattering.S);
call.destroy();w.close();console.log("Actual project preview, fractional GHz conductor estimates, original 1/10/100 GHz HF-resistance plot/CSV and a subsequent exact original Pi2 solve pass through the webpage handlers.");
