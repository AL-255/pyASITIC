import { circuitSVG,sweepSVG } from "./analysis-views.mjs";
const $ = selector => document.querySelector(selector);
const form = $("#geometry-form");
const NS = "http://www.w3.org/2000/svg";
const COLORS = ["#e8bd65", "#81b4ef", "#b899eb", "#8fd1ae", "#e89971", "#e88fbd", "#64cbd1", "#cecf86"];
let worker, ready = false, busy = false, nextId = 0, current = null, currentDefinition = null, technology = null, technologyText = "", sweepRows = null, matrixResult = null, capacitanceResult = null, pi2Result = null;
let sweepContext=null,sweepModels=[];
let selfresResult=null,selfresTrace=[];
const MODEL_NAMES={pi:"Pi",pi2:"Pi2",pi3:"Pi3",pi4:"Pi4"};
const eddyEnabled=()=>!!$("#eddy-mode")?.checked;
const pending = new Map();
const fmt = (value, digits=4) => Number(value).toLocaleString(undefined, { maximumSignificantDigits: digits });

function error(message="") { $("#error").hidden = !message; $("#error").textContent = message; }
function status(message) { $("#analysis-status").textContent = message; }
function controls() {
  for(const el of document.querySelectorAll(".analysis-panel input,.analysis-panel select"))el.disabled=busy;
  $("#generate").disabled = !ready || busy;
  for (const id of ["simulate", "sweep", "lmat", "capacitance", "pi2", "selfres", "download-gds", "download-project"]) $("#"+id).disabled = !ready || busy || !current;
  for(const id of ["download-selfres","download-selfres-csv","download-selfres-plot"])$("#"+id).disabled=busy||!selfresResult;
  $("#download-csv").disabled = busy || !sweepRows?.length;
  $("#download-plot").disabled = busy || !sweepRows?.length;
  $("#download-model-svg").disabled = busy || !current;
  if($("#pi-model").value==="pi")$("#pi2").disabled=true;
  $("#download-matrix").disabled = busy || !matrixResult;
  $("#download-capacitance").disabled = busy || !capacitanceResult;
  for(const id of ["download-pi2","download-ports"]) $("#"+id).disabled = busy || !pi2Result;
  $("#active-winding").disabled = busy;
  $("#coupling").disabled = busy || !current || current.windings.length!==2;
}
function request(payload,onProgress=null) {
  const id = ++nextId;
  return new Promise((resolve, reject) => { pending.set(id, {resolve,reject,onProgress}); worker.postMessage({id,request:payload}); });
}
async function task(callback) {
  if (busy || !ready) return;
  busy = true; controls(); error();
  try { await callback(); } catch (e) { error(e.message || String(e)); status("Could not complete the operation. Check the message above."); }
  finally { busy = false; controls(); }
}
function definition() {
  const values = Object.fromEntries(new FormData(form));
  const kind = values.kind; delete values.kind;
  for (const key of Object.keys(values)) if (!["name", "metal", "exit_metal", "bottom_metal", "via"].includes(key)) values[key] = Number(values[key]);
  return {kind,parameters:values,winding:0};
}
function showFields() {
  const kind = $("#kind").value;
  $("#secondary-metal").parentElement.firstChild.nodeValue=kind==="transformer3d"?"Secondary winding metal":"Crossover metal";
  for (const label of form.querySelectorAll("[data-kinds]")) {
    const visible = label.dataset.kinds.split(" ").includes(kind);
    label.hidden = !visible;
    for (const input of label.querySelectorAll("input,select")) input.disabled = !visible;
  }
}
function svgElement(tag,attributes={},text) {
  const el = document.createElementNS(NS,tag);
  for (const [key,value] of Object.entries(attributes)) el.setAttribute(key,String(value));
  if (text !== undefined) el.textContent = text;
  return el;
}
let viewport = {scale:1,x:0,y:0};
function fit() { viewport = {scale:1,x:0,y:0}; transform(); }
function transform() {
  $("#drawing").setAttribute("transform",`translate(${viewport.x} ${viewport.y}) translate(300 220) scale(${viewport.scale}) translate(-300 -220)`);
}
function render(shape) {
  const drawing = $("#drawing"); drawing.replaceChildren();
  let x0=Infinity,x1=-Infinity,y0=Infinity,y1=-Infinity;
  for (const poly of shape.polygons) for (const [x,y] of poly.points) {x0=Math.min(x0,x);x1=Math.max(x1,x);y0=Math.min(y0,y);y1=Math.max(y1,y);}
  const scale = Math.min(470/Math.max(x1-x0,0.001),315/Math.max(y1-y0,0.001));
  const px = x => 300+(x-(x0+x1)/2)*scale;
  const py = y => 215-(y-(y0+y1)/2)*scale;
  const layerIndices = [...new Set(shape.polygons.map(p=>p.metal))].sort((a,b)=>a-b);
  for (const poly of shape.polygons) drawing.append(svgElement("polygon", {points:poly.points.map(([x,y])=>`${px(x)},${py(y)}`).join(" "), fill:COLORS[poly.metal%COLORS.length], "fill-opacity":poly.metal<technology.metals.length ? 0.67 : 1, stroke:COLORS[poly.metal%COLORS.length], "stroke-width":0.6}));
  const first=shape.segments[0].start, last=shape.segments.at(-1).end;
  for (const [point,name] of [[first,"1"],[last,"2"]]) {
    drawing.append(svgElement("circle",{cx:px(point[0]),cy:py(point[1]),r:5,fill:"#101923",stroke:"#f5dfba","stroke-width":1.5}));
    drawing.append(svgElement("text",{x:px(point[0])+9,y:py(point[1])-7,fill:"#f1dcc0","font-size":11,"font-family":"monospace"},name));
  }
  const bar = Math.pow(10,Math.floor(Math.log10((x1-x0)/4)));
  drawing.append(svgElement("path",{d:`M 475 375 h ${bar*scale} m 0 -4 v 8 m ${-bar*scale} -8 v 8`,stroke:"#a6b6c4",fill:"none","stroke-width":1}));
  drawing.append(svgElement("text",{x:475,y:365,fill:"#a6b6c4","font-size":10,"font-family":"monospace"},`${fmt(bar)} µm`));
  $("#legend").replaceChildren();
  const names = [...technology.metals,...technology.vias].map(m=>m.name);
  for (const layer of layerIndices) {
    const el = document.createElement("span"); el.className="legend-item";
    const dot = document.createElement("i"); dot.className="legend-dot"; dot.style.background=COLORS[layer%COLORS.length];
    el.append(dot, document.createTextNode(names[layer])); $("#legend").append(el);
  }
  $("#layout-title").replaceChildren(document.createTextNode(shape.name+" "));
  const subtitle = document.createElement("span"); subtitle.textContent = $("#kind").selectedOptions[0].textContent; $("#layout-title").append(subtitle);
  $("#winding-control").hidden=shape.windings.length<2;
  $("#cap-ground-control").hidden=shape.windings.length<2;
  updateModelControls(false);
  $("#active-winding").replaceChildren(...shape.windings.map((name,index)=>new Option(name,String(index),false,index===(currentDefinition.winding||0))));
  $("#canvas-caption").textContent=`${fmt(x1-x0)} × ${fmt(y1-y0)} µm · ${shape.windings.length>1?"both windings · ":""}origin (${fmt(shape.origin[0])}, ${fmt(shape.origin[1])})`;
  $("#scale").textContent="Scroll to zoom · drag to pan";
  $("#stat-segments").textContent=shape.segments.length;
  $("#stat-length").textContent=fmt(shape.length)+" µm";
  $("#stat-area").textContent=fmt(shape.area)+" µm²";
  $("#stat-dc").textContent=fmt(shape.dc_ohm)+" Ω";
  $("#warnings").hidden=!shape.warnings.length; $("#warnings").textContent=shape.warnings.join(" ");
  fit();
}
function resetResults() {
  for (const key of ["l","r","q"]) $("#result-"+key).textContent="—";
  resetSweep();
  matrixResult=null; $("#matrix-table").replaceChildren(); $("#lmat-result").textContent="";
  capacitanceResult=null; $("#capacitance-table").replaceChildren(); $("#capacitance-result").textContent="";
  resetModel();
  resetSelfres();
}
async function generate() {
  const next = definition();
  const shape = await request({action:"build",...next,technology:technologyText});
  current=shape; currentDefinition=next;
  render(shape); resetResults(); status("Layout ready. Run estimates at a frequency of your choice.");
}
function fillTechnology(data) {
  technology=data.technology;
  const metalOptions = technology.metals.map((m,i)=>[String(i),`${m.name} · ${fmt(m.thickness)} µm`]);
  function fill(selector,options,selected) {
    $(selector).replaceChildren(...options.map(([value,text])=>new Option(text,value,false,value===String(selected))));
  }
  fill("#metal",metalOptions,technology.metals.length-1);
  fill("#exit-metal",[["-1","No exit lead"],...metalOptions],-1);
  fill("#bottom-metal",metalOptions,Math.max(0,technology.metals.length-2));
  fill("#secondary-metal",metalOptions,Math.max(0,technology.metals.length-2));
  fill("#via",technology.vias.map((v,i)=>[String(i),v.name]),0);
  fill("#model-ground-metal",metalOptions,0);
  for(const id of ["model-pad1-metal","model-pad2-metal"])fill("#"+id,metalOptions,technology.metals.length-1);
  const table=document.createElement("table");
  const head=table.createTHead().insertRow();
  for (const name of ["Metal","Height µm","Rsh Ω/□"]) { const cell=document.createElement("th");cell.textContent=name;head.append(cell); }
  const body=table.createTBody();
  for (const m of technology.metals) { const row=body.insertRow();for(const value of [m.name,fmt(m.height),fmt(m.resistance)]) row.insertCell().textContent=value; }
  $("#tech-table").replaceChildren(table);
}
function download(data,type,filename) {
  const url=URL.createObjectURL(new Blob([data],{type}));
  const link=document.createElement("a"); link.href=url;link.download=filename;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
function filename(extension) { return (current.name.replace(/[^\w.-]/g,"_")||"coil")+extension; }
function numeric(selector) { const value=Number($(selector).value);if(!Number.isFinite(value)||!$(selector).value) throw new Error("Enter a finite number in each required field.");return value; }
function resetSweep(){
  sweepRows=null;sweepModels=[];sweepContext=null;
  $("#sweep-table").replaceChildren();renderSweep([]);
  $("#sweep-readout").textContent="Hover or focus a sample to inspect it. Select a Pi sweep sample to display its circuit.";
}
function resetModel(){
  pi2Result=null;$("#pi2-metrics").replaceChildren();$("#pi2-ports").replaceChildren();$("#pi2-result").textContent="";
  if($("#model-diagnostics")){$("#model-diagnostics").hidden=true;$("#model-diagnostics").textContent="";}
  $("#model-circuit").innerHTML=circuitSVG({}, {model:MODEL_NAMES[$("#pi-model").value],note:$("#pi-model").value==="pi"?"Native fast Pi is unavailable for conductor coils":"Run the selected model to show component values"});
}
function renderSelfres(trace){
  const rows=trace.map(point=>({frequency_hz:point.frequency_hz,reactance_ohm:point.imaginary_impedance_ohm})).sort((a,b)=>a.frequency_hz-b.frequency_hz);
  const bounds=[numeric("#selfres-first")*1e9,numeric("#selfres-last")*1e9].sort((a,b)=>a-b);
  const differential=selfresResult?selfresResult.differential:$("#selfres-mode").value==="differential",eddy=selfresResult?selfresResult.eddy:eddyEnabled();
  $("#selfres-chart").innerHTML=sweepSVG(rows,"reactance_ohm",{model:`SELFRES SLOW · ${differential?"Differential":"Single"}${eddy?" · eddy on":""}`,label:"Input reactance · Ω",scale:"linear",firstHz:bounds[0],lastHz:bounds[1],interactive:false});
  const table=document.createElement("table"),head=table.createTHead().insertRow();
  for(const label of ["Sample","GHz","Input reactance Ω","Lower GHz","Upper GHz"]){const th=document.createElement("th");th.textContent=label;head.append(th);}
  const body=table.createTBody();
  for(const point of trace){const row=body.insertRow();for(const value of [point.iteration,point.frequency_hz/1e9,point.imaginary_impedance_ohm,point.lower_hz/1e9,point.upper_hz/1e9])row.insertCell().textContent=fmt(value,7);}
  $("#selfres-table").replaceChildren(table);
}
function resetSelfres(){
  selfresResult=null;selfresTrace=[];$("#selfres-result").textContent="";$("#selfres-diagnostics").hidden=true;$("#selfres-diagnostics").textContent="";$("#selfres-table").replaceChildren();$("#selfres-chart").replaceChildren();$("#selfres-circuit").replaceChildren();
}
function updateModelControls(clear=true){
  const model=$("#pi-model").value,ground=$("#model-ground-mode"),required=model==="pi3";
  ground.options[0].disabled=required;
  ground.options[0].textContent=model==="pi4"?"Device reference (native default)":"Substrate only";
  ground.options[1].disabled=!current||current.windings.length!==2;
  if(required && ground.value==="none")ground.value="strip";
  if(ground.value==="other" && ground.options[1].disabled)ground.value=required?"strip":"none";
  $("#model-ground-fields").hidden=ground.value!=="strip"||model==="pi";
  $("#model-pad-fields").hidden=model!=="pi4";
  $("#pi2").textContent="Run "+MODEL_NAMES[model];
  $("#model-note").textContent={
    pi:"The supplied ASITIC fast Pi command faults on conductor coils before it produces circuit values. The topology is shown here; numerical fast-Pi results are unavailable in this reference.",
    pi2:"Distributed filament and layered-substrate model. The diagram shows series L/R and two series RC shunts. Uses the frequency above and CAP/LMAT mesh settings below.",
    pi3:"Original Pi3: the distributed model with an explicit ground structure. Choose the other winding or define a ground strip.",
    pi4:"Original Pi4: solve the device with its pads, subtract the pads’ capacitive contribution, and extract the three-terminal circuit. Define two pad strips and a reference."
  }[model]+(model==="pi"?"":eddyEnabled()?" Native eddy correction is enabled; convergence diagnostics appear with results.":" Eddy currents are disabled.");
  if(clear)resetModel();controls();
}
function stripDefinition(prefix,suffix){
  return {kind:"wire",parameters:{name:current.name.slice(0,55)+suffix,metal:$("#"+prefix+"-metal").value,
    length:numeric("#"+prefix+"-length"),width:numeric("#"+prefix+"-width"),x:numeric("#"+prefix+"-x"),y:numeric("#"+prefix+"-y")}};
}
function modelPayload(model,frequency){
  const mode=$("#model-ground-mode").value;
  if(model==="pi3"&&mode==="none")throw new Error("Choose a ground strip or the other winding for Pi3.");
  if(mode==="other" && current.windings.length!==2)throw new Error("This layout has no other winding; choose a ground strip.");
  const ground=mode==="other"?{...currentDefinition,winding:1-(currentDefinition.winding||0)}:mode==="strip"?stripDefinition("model-ground","_ground"):null;
  return {action:model,...currentDefinition,ground,technology:technologyText,frequency_hz:frequency,eddy:eddyEnabled(),
    ...(model==="pi4"?{first_pad:stripDefinition("model-pad1","_pad1"),second_pad:stripDefinition("model-pad2","_pad2")} : {}),
    mesh:{length_cell:numeric("#mesh-length"),width_cell:numeric("#mesh-width"),thickness_cell:numeric("#mesh-thickness"),
      capacitance_length_cell:numeric("#cap-length"),capacitance_width_cell:numeric("#cap-width")}};
}
function renderSweep(rows) {
  const model=sweepContext?.model||$("#sweep-model").value,estimate=model==="estimates",metric=$("#sweep-metric").value;
  const labels={inductance_nh:estimate?"Inductance estimate · nH":"Series inductance · nH",resistance_ohm:estimate?"HF resistance · Ω":"Series resistance · Ω",q:estimate?"LF extrapolated quality · QLF":"Port 1 quality factor · Q"};
  const eddy=sweepContext?!!sweepContext.eddy:!estimate&&eddyEnabled();
  const name=estimate?"Conductor estimates":MODEL_NAMES[model]+(eddy?" · eddy on":"");
  $("#sweep-chart").innerHTML=sweepSVG(rows,metric,{model:name,label:labels[metric],scale:$("#sweep-scale").value,
    firstHz:sweepContext?.firstHz||Number($("#sweep-first").value)*1e9,lastHz:sweepContext?.lastHz||Number($("#sweep-last").value)*1e9});
  $("#sweep-method").textContent=estimate?"Conductor estimates: QLF uses DC loss and the inductance estimate is frequency independent.":`${name}: frequency-dependent distributed model, native eddy ${eddy?"enabled":"disabled"}. Select a plotted point to inspect its three-terminal circuit.`;
  const table=document.createElement("table"),head=table.createTHead().insertRow();
  for(const title of ["GHz",estimate?"L estimate (nH)":"Series L (nH)",estimate?"HF R (Ω)":"Series R (Ω)",estimate?"QLF":"Port 1 Q"]) { const th=document.createElement("th");th.textContent=title;head.append(th); }
  const body=table.createTBody();
  for(const r of rows) {const tr=body.insertRow();for(const value of [r.frequency_hz/1e9,r.inductance_nh,r.resistance_ohm,r.q]) tr.insertCell().textContent=value===null?"Undefined":fmt(value,5);}
  $("#sweep-table").replaceChildren(table);
}
form.addEventListener("submit",event=>{event.preventDefault();task(generate);});
$("#kind").addEventListener("change",()=>{
  const kind=$("#kind").value;
  if(kind==="balun" && Number(form.elements.turns.value)<3)form.elements.turns.value="3";
  if(kind==="transformer3d"){
    if(Number(form.elements.turns.value)<1)form.elements.turns.value="1";
    const minimum=.4142*Number(form.elements.width.value)+2*1.4142;
    if(Number(form.elements.spacing.value)<minimum)form.elements.spacing.value=String(Math.ceil(minimum));
  }
  showFields();
});
$("#active-winding").addEventListener("change",()=>task(async()=>{
  const next={...currentDefinition,winding:Number($("#active-winding").value)};
  const shape=await request({action:"build",...next,technology:technologyText});
  current=shape;currentDefinition=next;render(shape);resetResults();status(`Selected ${shape.name}. Analysis applies to this winding; GDS exports both windings.`);
}));
$("#coupling").addEventListener("click",()=>task(async()=>{
  const result=await request({action:"coupling",technology:technologyText,first:{...currentDefinition,winding:0},second:{...currentDefinition,winding:1}});
  status(`ASITIC coupling estimate: k = ${fmt(result.k,6)}, M = ${fmt(result.mutual_nh,6)} nH.`);
}));
form.addEventListener("input",()=>{if(current)status("Parameters changed. Generate layout to apply them.");});
$("#fit").addEventListener("click",fit);
$("#simulate").addEventListener("click",()=>task(async()=>{
  status("Running ASITIC estimates…");
  const result=await request({action:"simulate",...currentDefinition,technology:technologyText,frequency_hz:numeric("#frequency")*1e9});
  $("#result-l").textContent=fmt(result.inductance_nh,6)+" nH";
  $("#result-r").textContent=fmt(result.hf_ohm,6)+" Ω";
  $("#result-q").textContent=fmt(result.qlf,6);
  status(`Complete at ${fmt(result.frequency_hz/1e9)} GHz. ${result.warnings.join(" ")}`);
}));
$("#sweep").addEventListener("click",()=>task(async()=>{
  const first=numeric("#sweep-first")*1e9,last=numeric("#sweep-last")*1e9,count=numeric("#sweep-count"),model=$("#sweep-model").value;
  if(!(first>0&&last>first&&Number.isInteger(count)&&count>=2&&count<=101))throw new Error("Sweep needs 0 < start < stop and 2–101 points.");
  const log=$("#sweep-scale").value==="log";
  const base=model==="estimates"?{action:"simulate",...currentDefinition,technology:technologyText}:modelPayload(model,first);
  sweepRows=[];sweepModels=[];sweepContext={model,firstHz:first,lastHz:last,eddy:model!=="estimates"&&base.eddy};
  for(let i=0;i<count;i++){
    const f=log?first*(last/first)**(i/(count-1)):first+(last-first)*i/(count-1);
    status(`Running ${model==="estimates"?"conductor estimates":MODEL_NAMES[model]} sweep: ${i+1} / ${count} · ${fmt(f/1e9)} GHz…`);
    const result=await request({...base,frequency_hz:f});
    if(model==="estimates")sweepRows.push({frequency_hz:f,inductance_nh:result.inductance_nh,resistance_ohm:result.hf_ohm,q:result.qlf});
    else {
      const p=result.pi;
      sweepRows.push({frequency_hz:f,inductance_nh:p.inductance_h===null?null:p.inductance_h*1e9,resistance_ohm:p.resistance_ohm,q:p.q_first});
      sweepModels.push(result);
    }
    renderSweep(sweepRows);
  }
  if(sweepModels.length){$("#frequency").value=String(sweepRows[0].frequency_hz/1e9);renderModelResult(sweepModels[0],model);}
  status(`${count}-point ${model==="estimates"?"estimate":MODEL_NAMES[model]} sweep plotted. Switch L/R/Q or select a sample to inspect it.`);
}));
$("#download-csv").addEventListener("click",()=>{
  const keys=["frequency_hz","inductance_nh","resistance_ohm","q"];
  download("model,eddy,"+keys.join(",")+"\n"+sweepRows.map(row=>[sweepContext.model,!!sweepContext.eddy,...keys.map(key=>row[key]??"")].join(",")).join("\n"),"text/csv",filename("-sweep.csv"));
});
$("#download-plot").addEventListener("click",()=>download($("#sweep-chart").innerHTML,"image/svg+xml",filename("-"+$("#sweep-metric").value+"-sweep.svg")));
$("#download-model-svg").addEventListener("click",()=>download($("#model-circuit").innerHTML,"image/svg+xml",filename("-"+$("#pi-model").value+"-circuit.svg")));
for(const id of ["sweep-metric","sweep-scale"])$("#"+id).addEventListener("change",()=>renderSweep(sweepRows||[]));
$("#sweep-model").addEventListener("change",()=>{
  const model=$("#sweep-model").value;$("#sweep-count").value=model==="estimates"?"31":"11";
  if(model!=="estimates"){$("#pi-model").value=model;if(model==="pi4"&&$("#model-ground-mode").value==="none")$("#model-ground-mode").value="strip";updateModelControls();}
  resetSweep();controls();
});
$("#pi-model").addEventListener("change",()=>{
  const model=$("#pi-model").value;$("#sweep-model").value=model==="pi"?"estimates":model;
  if(model==="pi4"&&$("#model-ground-mode").value==="none")$("#model-ground-mode").value="strip";
  $("#sweep-count").value=model==="pi"?"31":"11";resetSweep();updateModelControls();
});
$("#model-ground-mode").addEventListener("change",()=>updateModelControls());
$("#eddy-mode")?.addEventListener("change",()=>{
  updateModelControls();resetSweep();resetSelfres();matrixResult=null;$("#matrix-table").replaceChildren();$("#lmat-result").textContent="";controls();
});
$("#selfres").addEventListener("click",()=>task(async()=>{
  const first=numeric("#selfres-first")*1e9,last=numeric("#selfres-last")*1e9,step=numeric("#selfres-step")*1e9;
  if(!(first>0&&last>0&&step>0))throw new Error("Enter positive SELFRES bounds and resolution.");
  const base=modelPayload("pi2",first),useModel=$("#selfres-reference").value==="model";
  if(useModel&&!base.ground)throw new Error("Choose a ground strip or the other winding in the model reference settings below.");
  resetSelfres();status("Searching self-resonance with repeated distributed network solves…");
  const result=await request({...base,action:"selfres",first_hz:first,last_hz:last,step_hz:step,ground:useModel?base.ground:null,differential:$("#selfres-mode").value==="differential"},point=>{
    selfresTrace.push(point);renderSelfres(selfresTrace);
    $("#selfres-result").textContent=`Sample ${point.iteration} · ${fmt(point.frequency_hz/1e9,7)} GHz · Input reactance ${fmt(point.imaginary_impedance_ohm,7)} Ω`;
    status(`SELFRES sample ${point.iteration}: ${fmt(point.frequency_hz/1e9,6)} GHz…`);
  });
  selfresResult=result;selfresTrace=result.trace;renderSelfres(result.trace);
  const reason={impedance_tolerance:"Input reactance tolerance reached",frequency_step:"Frequency resolution reached",iteration_limit:"Native iteration limit reached"}[result.reason];
  $("#selfres-result").textContent=`${reason}${result.frequency_hz===null?"":` · Reported frequency ${fmt(result.frequency_hz/1e9,8)} GHz`} · ${result.evaluations} network solves · Last evaluated ${fmt(result.last_evaluated_frequency_hz/1e9,8)} GHz · ${result.differential?"Differential":"Single ended"} · Native eddy ${result.eddy?"on":"off"}`;
  $("#selfres-diagnostics").hidden=!result.warnings.length;$("#selfres-diagnostics").textContent=result.warnings.join(" ");
  $("#selfres-circuit").innerHTML=circuitSVG(result.model.pi,{model:"SELFRES · Pi2",frequencyHz:result.last_evaluated_frequency_hz,note:`Last evaluated sample · ${useModel?"Model reference":"Device reference"} · native eddy ${result.eddy?"on":"off"}`});
  status("SELFRES complete. Its circuit shows the last evaluated sample; search JSON includes the reported frequency and full trace.");
}));
$("#download-selfres").addEventListener("click",()=>download(JSON.stringify(selfresResult,null,2),"application/json",filename("-selfres.json")));
$("#download-selfres-plot").addEventListener("click",()=>download($("#selfres-chart").innerHTML,"image/svg+xml",filename("-selfres.svg")));
$("#download-selfres-csv").addEventListener("click",()=>{
  const keys=["iteration","frequency_hz","imaginary_impedance_ohm","lower_hz","upper_hz"];
  download(keys.join(",")+"\n"+selfresResult.trace.map(point=>keys.map(key=>point[key]).join(",")).join("\n"),"text/csv",filename("-selfres.csv"));
});
function inspectSweepPoint(event,select=false){
  const point=event.target.closest?.("[data-index]");if(!point)return;
  const index=Number(point.dataset.index),row=sweepRows?.[index];if(!row)return;
  const display=value=>value===null?"Undefined":fmt(value,6);
  $("#sweep-readout").textContent=`${fmt(row.frequency_hz/1e9,6)} GHz · L ${display(row.inductance_nh)} nH · R ${display(row.resistance_ohm)} Ω · ${sweepContext.model==="estimates"?"QLF":"Q"} ${display(row.q)}`;
  if(select&&sweepModels[index]&&!busy){
    $("#frequency").value=String(row.frequency_hz/1e9);
    $("#pi-model").value=sweepContext.model;updateModelControls(false);renderModelResult(sweepModels[index],sweepContext.model);controls();
  }
}
for(const name of ["pointerover","focusin"])$("#sweep-chart").addEventListener(name,event=>inspectSweepPoint(event));
$("#sweep-chart").addEventListener("click",event=>inspectSweepPoint(event,true));
$("#sweep-chart").addEventListener("keydown",event=>{if(event.key==="Enter"||event.key===" "){event.preventDefault();inspectSweepPoint(event,true);}});
$("#lmat").addEventListener("click",()=>task(async()=>{
  status("Assembling and solving filament impedance matrix…");
  const result=await request({action:"lmat",...currentDefinition,technology:technologyText,frequency_hz:numeric("#frequency")*1e9,eddy:eddyEnabled(),
    mesh:{length_cell:numeric("#mesh-length"),width_cell:numeric("#mesh-width"),thickness_cell:numeric("#mesh-thickness")}});
  matrixResult=result;
  $("#lmat-result").textContent=`L = ${fmt(result.inductance_h*1e9,6)} nH · R = ${fmt(result.resistance_ohm,6)} Ω · Series Q = ${fmt(result.series_q,6)} · ${result.filaments} filaments / ${result.segments} metal segments · Native eddy ${result.eddy?"on":"off"}`;
  const table=document.createElement("table"),head=table.createTHead().insertRow(),limit=Math.min(16,result.matrix.length);
  head.append(document.createElement("th"));
  for(let j=0;j<limit;j++){const th=document.createElement("th");th.textContent=j;head.append(th);}
  const body=table.createTBody();
  for(let i=0;i<limit;i++){
    const row=body.insertRow();const th=document.createElement("th");th.textContent=i;row.append(th);
    for(let j=0;j<limit;j++){const [real,imag]=result.matrix[i][j];row.insertCell().textContent=`${fmt(real,3)} ${imag<0?"−":"+"} j${fmt(Math.abs(imag),3)}`;}
  }
  $("#matrix-table").replaceChildren(table);
  status(`LMAT complete at ${fmt(result.frequency_hz/1e9)} GHz. Matrix entries are Ω. Showing ${limit} × ${limit}; CSV includes the full ${result.segments} × ${result.segments} matrix. ${result.warnings.join(" ")}`);
}));
$("#download-matrix").addEventListener("click",()=>{
  const rows=["row,column,real_ohm,imag_ohm"];
  matrixResult.matrix.forEach((row,i)=>row.forEach(([real,imag],j)=>rows.push([i,j,real,imag].join(","))));
  download(rows.join("\n"),"text/csv",filename("-impedance.csv"));
});
$("#capacitance").addEventListener("click",()=>task(async()=>{
  status("Generating layered Green tables and solving the contact-potential matrix…");
  const ground=current.windings.length===2 && $("#cap-ground").checked ? {...currentDefinition,winding:1-(currentDefinition.winding||0)} : null;
  const result=await request({action:"capacitance",...currentDefinition,ground,technology:technologyText,frequency_hz:numeric("#frequency")*1e9,
    mesh:{length_cell:numeric("#cap-length"),width_cell:numeric("#cap-width")}});
  capacitanceResult=result;
  $("#capacitance-result").textContent=`Total C = ${fmt(result.total_capacitance_f*1e15,6)} fF · Substrate equivalent series R = ${fmt(result.total_resistance_ohm,6)} Ω · ${result.contacts} contacts · ${result.fft_x} × ${result.fft_y} FFT`;
  const table=document.createElement("table"),head=table.createTHead().insertRow(),limit=Math.min(16,result.matrix.length);
  for(const title of ["row","column","conductance (S)","susceptance (S)"]){const th=document.createElement("th");th.textContent=title;head.append(th);}
  const body=table.createTBody();
  for(let i=0;i<limit;i++) for(let j=0;j<limit;j++){
    const row=body.insertRow();const [real,imag]=result.matrix[i][j];
    for(const value of [i,j,real,imag])row.insertCell().textContent=fmt(value,6);
  }
  $("#capacitance-table").replaceChildren(table);
  status(`CAP complete at ${fmt(result.frequency_hz/1e9)} GHz. Showing ${limit} × ${limit}; CSV includes the full matrix. ${ground?"The other winding is grounded.":""}`);
}));
$("#download-capacitance").addEventListener("click",()=>{
  const rows=["row,column,real_siemens,imag_siemens"];
  capacitanceResult.matrix.forEach((row,i)=>row.forEach(([real,imag],j)=>rows.push([i,j,real,imag].join(","))));
  download(rows.join("\n"),"text/csv",filename("-capacitance-admittance.csv"));
});
$("#pi2").addEventListener("click",()=>task(async()=>{
  const model=$("#pi-model").value;
  status(`Running ${MODEL_NAMES[model]} with the selected reference, pads and mesh…`);
  const result=await request(modelPayload(model,numeric("#frequency")*1e9));
  renderModelResult(result,model);
  status(`${MODEL_NAMES[model]} complete. Component values are specific to this frequency; resonance is a narrowband estimate. ${result.warnings.join(" ")}`);
}));
function renderModelResult(result,model){
  pi2Result=result;
  const name=MODEL_NAMES[model];
  $("#pi2-result").textContent=`${name} · ${fmt(result.frequency_hz/1e9)} GHz · ${result.segments} metal segments · ${result.filaments} filaments · ${result.contacts} contacts · Native eddy ${result.eddy?"on":"off"}`;
  $("#model-circuit").innerHTML=circuitSVG(result.pi,{model:name,frequencyHz:result.frequency_hz,note:(model==="pi4"?"Pad capacitance de-embedded":"Frequency-specific equivalent circuit")+` · native eddy ${result.eddy?"on":"off"}`});
  if($("#model-diagnostics")){$("#model-diagnostics").hidden=!result.warnings.length;$("#model-diagnostics").textContent=result.warnings.join(" ");}
  const p=result.pi,table=document.createElement("table"),head=table.createTHead().insertRow();
  for(const title of [name+" metric","Value"]){const th=document.createElement("th");th.textContent=title;head.append(th);}
  const rows=[
    ["Series inductance",p.inductance_h===null?null:p.inductance_h*1e9,"nH"],["Series resistance",p.resistance_ohm,"Ω"],
    ["Port 1 shunt capacitance",p.capacitance_first_f===null?null:p.capacitance_first_f*1e15,"fF"],["Port 1 shunt resistance",p.resistance_first_ohm,"Ω"],
    ["Port 2 shunt capacitance",p.capacitance_second_f===null?null:p.capacitance_second_f*1e15,"fF"],["Port 2 shunt resistance",p.resistance_second_ohm,"Ω"],
    ["Port 1 Q",p.q_first,""],["Port 2 Q",p.q_second,""],["Differential Q",p.q_differential,""],
    ["Single-ended shunt R",p.shunt_single_ohm,"Ω"],["Differential shunt R",p.shunt_differential_ohm,"Ω"],
    ["Narrowband resonance estimate",p.resonant_frequency_hz===null?null:p.resonant_frequency_hz/1e9,"GHz"]
  ];
  const body=table.createTBody();
  for(const [label,value,unit] of rows){const row=body.insertRow();row.insertCell().textContent=label;row.insertCell().textContent=value===null?"Undefined":`${fmt(value,6)} ${unit}`;}
  const complex=z=>`${fmt(z[0],6)} ${z[1]<0?"−":"+"} j${fmt(Math.abs(z[1]),6)}`;
  for(const [label,value] of [["Port 1 input Z",result.input_impedance_first_ohm],["Port 2 input Z",result.input_impedance_second_ohm],["Differential input Z",result.differential_impedance_ohm]]){
    const row=body.insertRow();row.insertCell().textContent=label;row.insertCell().textContent=complex(value)+" Ω";
  }
  $("#pi2-metrics").replaceChildren(table);
  const ports=document.createElement("table"),portsHead=ports.createTHead().insertRow();
  for(const title of ["Parameter","Y (S)","ASITIC S (50 Ω)"]){const th=document.createElement("th");th.textContent=title;portsHead.append(th);}
  const portsBody=ports.createTBody();
  for(let i=0;i<2;i++)for(let j=0;j<2;j++){
    const row=portsBody.insertRow();row.insertCell().textContent=`${i+1}${j+1}`;
    row.insertCell().textContent=complex(result.admittance_matrix[i][j]);row.insertCell().textContent=complex(result.scattering_matrix[i][j]);
  }
  $("#pi2-ports").replaceChildren(ports);
}
$("#download-pi2").addEventListener("click",()=>download(JSON.stringify(pi2Result,null,2),"application/json",filename("-"+$("#pi-model").value+".json")));
$("#download-ports").addEventListener("click",()=>{
  const rows=["frequency_hz,parameter,row,column,real,imag,unit"];
  for(const [parameter,matrix,unit] of [["Y",pi2Result.admittance_matrix,"siemens"],["S",pi2Result.scattering_matrix,"dimensionless"]]){
    matrix.forEach((row,i)=>row.forEach(([real,imag],j)=>rows.push([pi2Result.frequency_hz,parameter,i+1,j+1,real,imag,unit].join(","))));
  }
  download(rows.join("\n"),"text/csv",filename("-two-port.csv"));
});
$("#download-gds").addEventListener("click",()=>task(async()=>{
  const result=await request({action:"gds",...currentDefinition,technology:technologyText});
  download(Uint8Array.from(atob(result.base64),c=>c.charCodeAt(0)),"application/octet-stream",filename(".gds"));
  status("GDSII exported: metals use index + 1, vias use index + 100, datatype 0; 1 nm grid.");
}));
$("#download-project").addEventListener("click",()=>download(JSON.stringify({format:"reasitic-project",version:1,shape:currentDefinition,technology:technologyText},null,2),"application/json",filename(".json")));
$("#project-file").addEventListener("change",event=>task(async()=>{
  const file=event.target.files[0];if(!file)return;
  const data=JSON.parse(await file.text());
  if(data.format!=="reasitic-project"||data.version!==1||!data.shape) throw new Error("Unsupported project file.");
  const text=data.technology||"";
  const init=await request({action:"init",technology:text});
  // Verify geometry before replacing the current project.
  const restored=await request({action:"build",...data.shape,technology:text});
  technologyText=text;fillTechnology(init);$("#tech-name").textContent=text?"Custom":"CMOS";
  $("#kind").value=data.shape.kind;showFields();
  for(const [key,value] of Object.entries(data.shape.parameters)) if(form.elements.namedItem(key))form.elements.namedItem(key).value=String(value);
  currentDefinition=data.shape;current=restored;render(current);resetResults();status("Project restored. Run analysis on the selected winding.");
  event.target.value="";
}));
$("#technology-file").addEventListener("change",event=>task(async()=>{
  const file=event.target.files[0];if(!file)return;
  const text=await file.text(),init=await request({action:"init",technology:text});
  technologyText=text;fillTechnology(init);$("#tech-name").textContent=file.name;
  current=null;currentDefinition=null;$("#drawing").replaceChildren();resetResults();status("Technology loaded. Generate a new layout.");event.target.value="";
}));
$("#reset-technology").addEventListener("click",()=>task(async()=>{fillTechnology(await request({action:"init"}));technologyText="";$("#tech-name").textContent="CMOS";current=null;await generate();}));
$("#layout").addEventListener("wheel",event=>{
  event.preventDefault();viewport.scale=Math.max(.3,Math.min(15,viewport.scale*Math.exp(-event.deltaY*.001)));transform();
},{passive:false});
let drag=null;
$("#layout").addEventListener("pointerdown",event=>{drag=[event.clientX,event.clientY,viewport.x,viewport.y];event.currentTarget.setPointerCapture(event.pointerId);event.currentTarget.classList.add("dragging");});
$("#layout").addEventListener("pointermove",event=>{if(!drag)return;const bounds=event.currentTarget.getBoundingClientRect();viewport.x=drag[2]+(event.clientX-drag[0])*600/bounds.width;viewport.y=drag[3]+(event.clientY-drag[1])*440/bounds.height;transform();});
for(const name of ["pointerup","pointercancel"]) $("#layout").addEventListener(name,event=>{drag=null;event.currentTarget.classList.remove("dragging");});
function fatal(message) {
  ready=false;busy=false;controls();$("#runtime").textContent="Python unavailable";
  error("Could not start Python. Check your connection and reload. "+message);
  for(const entry of pending.values())entry.reject(new Error(message));pending.clear();
}
showFields();
resetSweep();resetModel();updateModelControls(false);
try {
  worker=new Worker(new URL("worker.js",import.meta.url),{type:"module"});
  worker.onerror=event=>fatal(event.message||"Runtime load failed.");
  worker.onmessage=async({data})=>{
    if(data.fatal){fatal(data.fatal);return;}
    if(data.ready){
      ready=true;$("#runtime").replaceChildren();const dot=document.createElement("i");dot.className="led";$("#runtime").append(dot,document.createTextNode("Python ready"));
      await task(async()=>{fillTechnology(await request({action:"init"}));await generate();});return;
    }
    const promise=pending.get(data.id);if(!promise)return;
    if(data.progress){promise.onProgress?.(data.progress);return;}
    pending.delete(data.id);
    data.error ? promise.reject(new Error(data.error)) : promise.resolve(data.result);
  };
} catch(e){fatal(e.message);}
