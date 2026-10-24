import { circuitSVG,sweepSVG,transformerSVG } from "./analysis-views.mjs";
const $ = selector => document.querySelector(selector);
// Numeric fields accept strings at the Python boundary; keep signed-zero input lossless.
const inputJSON=(value,space)=>JSON.stringify(value,(_key,v)=>Object.is(v,-0)?"-0":v,space);
const form = $("#geometry-form");
const NS = "http://www.w3.org/2000/svg";
const COLORS = ["#e8bd65", "#81b4ef", "#b899eb", "#8fd1ae", "#e89971", "#e88fbd", "#64cbd1", "#cecf86"];
let worker, ready = false, busy = false, nextId = 0, current = null, currentDefinition = null, technology = null, technologyText = "", sweepRows = null, matrixResult = null, capacitanceResult = null, pi2Result = null;
let sweepContext=null,sweepModels=[];
let selfresResult=null,selfresTrace=[];
let transformerResult=null,transformerRequest=null,transformerRows=[],transformerSamples=[],transformerRange=null;
let technologyPreset=null,technologyPresets=[];
const MODEL_NAMES={pi:"Pi",pi2:"Pi2",pi3:"Pi3",pi4:"Pi4",pix:"PiX"};
const eddyEnabled=()=>!!$("#eddy-mode")?.checked;
const pending = new Map();
const MESH_FIELDS={length_cell:"mesh-length",width_cell:"mesh-width",thickness_cell:"mesh-thickness",capacitance_length_cell:"cap-length",capacitance_width_cell:"cap-width"};
const MESH_PRESETS={coarse:[1000,1000,1000,1000,1000],balanced:[50,3,.5,1000,1000],fine:[25,1,.25,50,10]};
const meshCache=new Map();
const frequencyFields=(hz,ghz=hz/1e9)=>({frequency_hz:hz,frequency_ghz:ghz});
function frequencyInput(){const ghz=numeric("#frequency");return frequencyFields(ghz*1e9,ghz);}
const fmt = (value, digits=4) => Number(value).toLocaleString(undefined, { maximumSignificantDigits: digits });

function error(message="") { $("#error").hidden = !message; $("#error").textContent = message; }
function status(message) { $("#analysis-status").textContent = message; }
function controls() {
  for(const el of document.querySelectorAll(".technology input,.technology select,.technology button"))el.disabled=!ready||busy;
  for(const el of document.querySelectorAll(".analysis-panel input,.analysis-panel select"))el.disabled=busy;
  $("#generate").disabled = !ready || busy;
  for (const id of ["simulate", "sweep", "lmat", "capacitance", "pi2", "selfres", "download-gds", "download-project"]) $("#"+id).disabled = !ready || busy || !current;
  for(const id of ["mesh-check","mesh-fit"])$("#"+id).disabled=!ready||busy||!current;
  const coupledMesh=$("#mesh-target option[value='calctrans']");coupledMesh.disabled=current?.windings.length!==2;
  if(coupledMesh.disabled&&$("#mesh-target").value==="calctrans")$("#mesh-target").value="pi2";
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
  for(const id of ["transformer-run","transformer-sweep"])$("#"+id).disabled=!ready||busy||current?.windings.length!==2;
  for(const id of ["download-transformer","download-transformer-svg","download-transformer-ports"])$("#"+id).disabled=busy||!transformerResult;
  for(const id of ["download-transformer-sweep","download-transformer-plot"])$("#"+id).disabled=busy||!transformerRows.length;
}
async function request(payload,onProgress=null) {
  if(["lmat","pi2","pi3","pi4","pix","selfres","calctrans"].includes(payload.action)){
    $("#mesh-target").value=["pi3","pix","selfres"].includes(payload.action)?"pi2":payload.action;
    const {frequency_hz,frequency_ghz,first_hz,first_ghz,last_hz,last_ghz,step_hz,step_ghz,eddy,termination_ohm,include_matrices,...geometry}=payload,key=inputJSON(geometry);
    let plan=meshCache.get(key);
    if(!plan){plan=await request({...payload,action:"mesh",model:payload.action});if(meshCache.size>=8)meshCache.delete(meshCache.keys().next().value);meshCache.set(key,plan);}
    renderMeshInfo(plan);
    if(!plan.within_limit)throw Error(`Mesh needs ${plan.filaments} filaments; the browser limit is ${plan.limit}. Use Mesh settings → Fit to 256 filaments, or enter larger cells.`);
  }
  const id = ++nextId;
  return new Promise((resolve, reject) => { pending.set(id, {resolve,reject,onProgress}); worker.postMessage({id,request:JSON.parse(inputJSON(payload))}); });
}
async function task(callback) {
  if (busy || !ready) return;
  busy = true; controls(); error();
  try { await callback(); } catch (e) {
    const message=e.message||String(e);error(message);status("Could not complete the operation. Check the message above.");
    if(/mesh.*(filaments|segments)/i.test(message)){$("#mesh-settings").open=true;$("#mesh-fit").focus();}
  }
  finally { busy = false; controls(); }
}
function definition() {
  const values = Object.fromEntries(new FormData(form));
  const kind = values.kind; delete values.kind;
  const rectangular=["square","multimetal"].includes(kind),inner=rectangular&&$("#dimension-mode").value==="inner";
  for(const key of inner?["length","height"]:["inner_length","inner_height"])delete values[key];
  for(const key of ["primary_name","secondary_name"])if(!values[key])delete values[key];
  for (const key of Object.keys(values)) if (!["name", "primary_name", "secondary_name", "metal", "exit_metal", "bottom_metal", "via"].includes(key)) values[key] = Number(values[key]);
  if(["symmetric_square","symmetric_polygon"].includes(kind)&&currentDefinition?.kind===kind&&(currentDefinition.native_keyword||currentDefinition.native_interactive)){
    // Preserve omitted native derived defaults until the displayed field changes.
    for(const key of ["inner_gap","x","y",...(kind==="symmetric_square"&&currentDefinition.native_interactive?["length"]:[])])
      if(!(key in currentDefinition.parameters)&&Number(values[key])===Number(current.parameters[key]))delete values[key];
  }
  if(kind==="balun"&&currentDefinition?.kind===kind&&currentDefinition.native_keyword&&!("secondary_metal" in currentDefinition.parameters)
      &&Number(values.secondary_metal)===Number(current.parameters.secondary_metal))delete values.secondary_metal;
  if((rectangular||["symmetric_square","symmetric_polygon"].includes(kind))&&$("#rectangular-input-mode").value==="interactive")return {kind,parameters:values,winding:0,native_interactive:true};
  return {kind,parameters:values,winding:0,...(["ring","square","polygon","wire","symmetric_square","symmetric_polygon","multimetal","capacitor","transformer","balun"].includes(kind)?{native_keyword:true}:["via","transformer3d"].includes(kind)?{native_interactive:true}:{})};
}
function restoreFormParameter(key,value){
  const input=form.elements.namedItem(key);if(!input)return;
  const layers=key==="via"?technology.vias:["metal","exit_metal","bottom_metal","secondary_metal"].includes(key)?technology.metals:null;
  const index=layers?.findIndex(layer=>layer.name.toUpperCase()===String(value).toUpperCase())??-1;
  input.value=index>=0?String(index):Object.is(value,-0)?"-0":String(value);
}
function meshSettings(){
  const mesh=Object.fromEntries(Object.entries(MESH_FIELDS).map(([key,id])=>[key,numeric("#"+id)]));
  if(Object.values(mesh).some(v=>v<=0))throw Error("Mesh cell sizes must be positive.");return mesh;
}
function applyMesh(mesh){
  for(const [key,id]of Object.entries(MESH_FIELDS))$("#"+id).value=String(mesh[key]);
  const values=Object.keys(MESH_FIELDS).map(key=>mesh[key]);
  $("#mesh-preset").value=Object.keys(MESH_PRESETS).find(key=>MESH_PRESETS[key].every((v,i)=>v===values[i]))||"custom";
  meshCache.clear();
}
function renderMeshInfo(plan){
  $("#mesh-feedback").className=plan.within_limit?"muted":"warnings";
  $("#mesh-feedback").textContent=`${plan.model.toUpperCase()}: ${plan.filaments} / ${plan.limit} filaments · ${plan.segments} conductor segments.${plan.within_limit?" Ready to solve.":" Use Fit to 256 filaments or larger conductor cells."}`;
}
function meshPayload(){
  const model=$("#mesh-target").value;
  const ghz=numeric("#frequency");
  const payload=model==="calctrans"?transformerPayload(ghz*1e9,ghz):model==="lmat"?{...currentDefinition,technology:technologyText,mesh:meshSettings()}:modelPayload(model,ghz*1e9,ghz);
  return {...payload,action:"mesh",model};
}
function changedMesh(){resetResults();meshCache.clear();error();$("#mesh-feedback").className="muted";$("#mesh-feedback").textContent="Mesh updated. Check the filament count or run an analysis.";status("Mesh settings updated. Check the count or run an analysis.");controls();}
$("#mesh-preset").addEventListener("change",()=>{
  const values=MESH_PRESETS[$("#mesh-preset").value];if(!values)return;
  applyMesh(Object.fromEntries(Object.keys(MESH_FIELDS).map((key,i)=>[key,values[i]])));changedMesh();
});
for(const id of Object.values(MESH_FIELDS))$("#"+id).addEventListener("change",()=>{$("#mesh-preset").value="custom";changedMesh();});
$("#mesh-check").addEventListener("click",()=>task(async()=>{renderMeshInfo(await request(meshPayload()));status("Mesh counted without running the electrical solver.");}));
$("#mesh-fit").addEventListener("click",()=>task(async()=>{
  const plan=await request({...meshPayload(),fit:true});applyMesh(plan.mesh);resetResults();renderMeshInfo(plan);
  status(plan.changed?"Conductor cell sizes increased to fit the filament limit. Run the simulation with this mesh.":"This mesh already fits. Run the simulation with the displayed cell sizes.");
}));
function showFields(loaded=currentDefinition) {
  const kind = $("#kind").value;
  const turns=form.elements.namedItem("turns");
  if(kind==="balun")turns.removeAttribute("min");else turns.min=kind==="transformer3d"?"1":"0.0625";
  for(const key of ["length","height"]){const input=form.elements.namedItem(key);if(kind==="transformer3d")input.removeAttribute("min");else input.min="0.001";}
  form.elements.namedItem("width").min=kind==="transformer3d"?"1e-10":"0.001";
  $("#ring-input-note").hidden=!["ring","square","polygon","wire","symmetric_square","symmetric_polygon","multimetal","capacitor","via","transformer","balun","transformer3d"].includes(kind);
  $("#ring-input-note").textContent=kind==="transformer3d"?"3D transformer inputs keep full precision. Orientation and phase are recorded without transforming the layout.":["transformer","balun"].includes(kind)&&loaded?.native_interactive?"Loaded interactive windings keep full-precision dimensions. Generate uses the ASITIC grid and keyword turn limits.":kind==="via"?"Via origins keep the entered precision. Counts are whole numbers.":["wire","capacitor"].includes(kind)&&loaded?.native_interactive?`Loaded interactive ${kind==="wire"?"WIRE":"CAPACITOR"} angles are stored as radians. Generate layout uses degrees and the ASITIC 0.1 µm grid.`:"Coil, wire and capacitor dimensions and origins snap to the ASITIC 0.1 µm grid.";
  $("#secondary-metal").parentElement.firstChild.nodeValue=kind==="transformer3d"?"Secondary winding metal":"Crossover metal";
  for (const label of form.querySelectorAll("[data-kinds]")) {
    const visible = label.dataset.kinds.split(" ").includes(kind);
    label.hidden = !visible;
    for (const input of label.querySelectorAll("input,select")) input.disabled = !visible;
  }
  if(["symmetric_square","symmetric_polygon"].includes(kind))form.elements.namedItem("inner_gap").removeAttribute("min");
  const rectangular=["square","multimetal"].includes(kind),symmetric=["symmetric_square","symmetric_polygon"].includes(kind),inner=rectangular&&$("#dimension-mode").value==="inner",interactive=(rectangular||symmetric)&&$("#rectangular-input-mode").value==="interactive";
  $("#dimension-mode").closest("label").hidden=!rectangular;$("#dimension-mode").disabled=!rectangular;
  for(const key of ["inner_length","inner_height",...(rectangular?["length","height"]:[])]){
    const input=form.elements.namedItem(key),hidden=key.startsWith("inner_")?!inner:inner;
    input.closest("label").hidden=hidden;input.disabled=hidden;if(key.startsWith("inner_")&&!interactive)input.removeAttribute("min");else input.min=interactive?"1e-10":"0.001";
  }
  if(rectangular||symmetric){
    if(symmetric)form.elements.namedItem(kind==="symmetric_square"?"length":"radius").min=interactive?"1e-10":"0.001";
    form.elements.namedItem("turns").min=interactive?"1":"0.0625";
    form.elements.namedItem("width").min=interactive?"1e-10":"0.001";
    if(interactive&&symmetric&&technology?.metals[Number(form.elements.namedItem("metal").value)]?.minimum_spacing)form.elements.namedItem("spacing").removeAttribute("min");
    else form.elements.namedItem("spacing").min=interactive?"1e-10":"0";
    for(const key of ["angle","phase"]){const input=form.elements.namedItem(key);input.closest("label").hidden=interactive;input.disabled=interactive;}
    $("#ring-input-note").textContent=symmetric?(interactive?"Original interactive input keeps full precision and floors turns first. Transition-gap bounds and warnings follow the process minima. Orientation and phase are zero.":"Original keyword input snaps to 0.1 µm. Explicit transition gaps use the keyword clearance test."):interactive?"Original interactive input keeps full precision. Inner-opening expansion and turn limits follow the prompt rules; orientation is zero and phase is positive.":"Original keyword input snaps to 0.1 µm. Inner dimensions expand before turns are rounded down.";
  }else form.elements.namedItem("spacing").min="0";
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
  updateTransformerControls();
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
  $("#mesh-feedback").className="muted";$("#mesh-feedback").textContent="Check the filament count before solving. Fit coarsens conductor cells; it does not run a simulation.";
  for (const key of ["l","r","q"]) $("#result-"+key).textContent="—";
  resetSweep();
  matrixResult=null; $("#matrix-table").replaceChildren(); $("#lmat-result").textContent="";
  capacitanceResult=null; $("#capacitance-table").replaceChildren(); $("#capacitance-result").textContent="";
  resetModel();
  resetSelfres();
  resetTransformer();
}
async function generate() {
  const next = definition();
  const shape = await request({action:"build",...next,technology:technologyText});
  current=shape; currentDefinition=next;showFields();
  if(["symmetric_square","symmetric_polygon"].includes(next.kind)&&(next.native_keyword||next.native_interactive))
    for(const key of ["inner_gap","x","y",...(next.kind==="symmetric_square"&&next.native_interactive?["length"]:[])])if(!(key in next.parameters))restoreFormParameter(key,shape.parameters[key]);
  render(shape); resetResults(); status("Layout ready. Run a Pi model or frequency sweep.");
}
function fillTechnology(data) {
  technology=data.technology;
  technologyPreset=data.preset||null;technologyPresets=data.presets||technologyPresets;
  const selector=$("#technology-preset"),groups=new Map();selector.replaceChildren();
  selector.append(new Option("Sample CMOS · 5 metals","sample-cmos"));
  for(const preset of technologyPresets.filter(p=>p.id!=="sample-cmos")){
    if(!groups.has(preset.routing_metals)){const group=document.createElement("optgroup");group.label=`GF180 · ${preset.routing_metals} routing metals`;groups.set(preset.routing_metals,group);selector.append(group);}
    groups.get(preset.routing_metals).append(new Option(`${preset.label} (§${preset.section})`,preset.id));
  }
  const custom=new Option("Custom .tek file","custom");custom.disabled=true;selector.append(custom);
  selector.value=technologyPreset?.id||(technologyText?"custom":"sample-cmos");
  $("#tech-name").textContent=technologyPreset?`GF180 · ${technologyPreset.routing_metals}M · ${technologyPreset.top_metal_ka}kÅ`:technologyText?"Custom":"CMOS";
  $("#gf180-settings").hidden=!technologyPreset;
  if(technologyPreset){
    $("#mim-density-field").hidden=technologyPreset.mim==="none";
    if(technologyPreset.density!=="none")$("#mim-density").value=technologyPreset.density;
    $("#substrate-rho").value=technology.substrate[0].rho;$("#substrate-thickness").value=technology.substrate[0].t;
    $("#technology-source").href=technologyPreset.source;
    $("#technology-note").textContent="Nominal coil stack. Substrate values are assumptions. Local MIM nitride and transistor topography are omitted; CAP is not a calibrated MIM model."+(technologyPreset.top_metal_ka===11?" Uses drawing values: top metal 1.1925 µm, oxide passivation 2.3925 µm; the general tables differ.":"");
  }
  $("#technology-description").textContent=technologyPreset?"All 45 documented GF180 cross sections are available. MIM stacks include a selectable MIM plate and both documented dielectric thicknesses. GDS uses GF180 drawn layer numbers.":"Choose a bundled stack or load an ASITIC .tek file. The sample CMOS process is illustrative.";
  const metalOptions = technology.metals.map((m,i)=>[String(i),`${m.name} · ${fmt(m.thickness)} µm`]);
  const routing=technology.metals.map((m,i)=>!technologyPreset||m.name!=="MIM"?i:null).filter(i=>i!==null),top=routing.at(-1),lower=routing.at(-2)??top;
  function fill(selector,options,selected) {
    $(selector).replaceChildren(...options.map(([value,text])=>new Option(text,value,false,value===String(selected))));
  }
  fill("#metal",metalOptions,top);
  fill("#exit-metal",[["-1","No exit lead"],...metalOptions],-1);
  fill("#bottom-metal",metalOptions,lower);
  fill("#secondary-metal",metalOptions,lower);
  fill("#via",technology.vias.map((v,i)=>[String(i),v.name]),0);
  fill("#model-ground-metal",metalOptions,0);
  fill("#transformer-ground-metal",metalOptions,0);
  for(const id of ["model-pad1-metal","model-pad2-metal"])fill("#"+id,metalOptions,technology.metals.length-1);
  const table=document.createElement("table");
  const head=table.createTHead().insertRow();
  for (const name of ["Metal","Height µm","Thick. µm","Rsh Ω/□"]) { const cell=document.createElement("th");cell.textContent=name;head.append(cell); }
  const body=table.createTBody();
  for (const m of technology.metals) { const row=body.insertRow();for(const value of [m.name,fmt(m.height),fmt(m.thickness),fmt(m.resistance)]) row.insertCell().textContent=value; }
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
  ground.options[0].textContent=["pi4","pix"].includes(model)?"Device reference (native default)":"Substrate only";
  ground.options[1].disabled=!current||current.windings.length!==2;
  if(required && ground.value==="none")ground.value="strip";
  if(ground.value==="other" && ground.options[1].disabled)ground.value=required?"strip":"none";
  $("#model-ground-fields").hidden=ground.value!=="strip"||model==="pi";
  $("#model-pad-fields").hidden=model!=="pi4";
  $("#pi2").textContent="Run "+MODEL_NAMES[model];
  $("#model-note").textContent={
    pi:"The supplied ASITIC fast Pi command faults on conductor coils before it produces circuit values. The topology is shown here; numerical fast-Pi results are unavailable in this reference.",
    pi2:"Distributed filament and layered-substrate model. The diagram shows series L/R and two series RC shunts. Uses the frequency above and shared mesh settings.",
    pi3:"Original Pi3: the distributed model with an explicit ground structure. Choose the other winding or define a ground strip.",
    pi4:"Original Pi4: solve the device with its pads, subtract the pads’ capacitive contribution, and extract the three-terminal circuit. Define two pad strips and a reference.",
    pix:"Original PiX extended two-port model. Solves coupled segment voltages and currents, then extracts the three-terminal circuit. Uses the frequency, reference and shared mesh settings."
  }[model]+(model==="pi"?"":eddyEnabled()?" Native eddy correction is enabled; convergence diagnostics appear with results.":" Eddy currents are disabled.");
  if(clear)resetModel();controls();
}
function stripDefinition(prefix,suffix){
  return {kind:"wire",native_keyword:true,parameters:{name:current.name.slice(0,55)+suffix,metal:$("#"+prefix+"-metal").value,
    length:numeric("#"+prefix+"-length"),width:numeric("#"+prefix+"-width"),x:numeric("#"+prefix+"-x"),y:numeric("#"+prefix+"-y")}};
}
function modelPayload(model,frequency,ghz=frequency/1e9){
  const mode=$("#model-ground-mode").value;
  if(model==="pi3"&&mode==="none")throw new Error("Choose a ground strip or the other winding for Pi3.");
  if(mode==="other" && current.windings.length!==2)throw new Error("This layout has no other winding; choose a ground strip.");
  const ground=mode==="other"?{...currentDefinition,winding:1-(currentDefinition.winding||0)}:mode==="strip"?stripDefinition("model-ground","_ground"):null;
  return {action:model,...currentDefinition,ground,technology:technologyText,...frequencyFields(frequency,ghz),eddy:eddyEnabled(),
    ...(model==="pi4"?{first_pad:stripDefinition("model-pad1","_pad1"),second_pad:stripDefinition("model-pad2","_pad2")} : {}),
    mesh:meshSettings()};
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
for(const id of ["dimension-mode","rectangular-input-mode"])$("#"+id).addEventListener("change",()=>{showFields();if(current)status("Dimension settings changed. Generate layout to apply them.");});
$("#metal").addEventListener("change",()=>showFields());
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
  const result=await request({action:"simulate",...currentDefinition,technology:technologyText,...frequencyInput()});
  $("#result-l").textContent=fmt(result.inductance_nh,6)+" nH";
  $("#result-r").textContent=fmt(result.hf_ohm,6)+" Ω";
  $("#result-q").textContent=result.qlf===null?"Undefined":fmt(result.qlf,6);
  status(`Complete at ${fmt(result.frequency_hz/1e9)} GHz. ${result.warnings.join(" ")}`);
}));
$("#sweep").addEventListener("click",()=>task(async()=>{
  const firstGHz=numeric("#sweep-first"),lastGHz=numeric("#sweep-last"),first=firstGHz*1e9,last=lastGHz*1e9,count=numeric("#sweep-count"),model=$("#sweep-model").value;
  if(!(first>0&&last>first&&Number.isInteger(count)&&count>=2&&count<=101))throw new Error("Sweep needs 0 < start < stop and 2–101 points.");
  const log=$("#sweep-scale").value==="log";
  const base=model==="estimates"?{action:"simulate",...currentDefinition,technology:technologyText}:modelPayload(model,first,firstGHz);
  sweepRows=[];sweepModels=[];sweepContext={model,firstHz:first,lastHz:last,eddy:model!=="estimates"&&base.eddy};
  for(let i=0;i<count;i++){
    const f=log?first*(last/first)**(i/(count-1)):first+(last-first)*i/(count-1);
    status(`Running ${model==="estimates"?"conductor estimates":MODEL_NAMES[model]} sweep: ${i+1} / ${count} · ${fmt(f/1e9)} GHz…`);
    const ghz=i===0?firstGHz:i===count-1?lastGHz:f/1e9;
    const result=await request({...base,...frequencyFields(f,ghz)});
    if(model==="estimates")sweepRows.push({frequency_hz:result.frequency_hz,inductance_nh:result.inductance_nh,resistance_ohm:result.hf_ohm,q:result.qlf});
    else {
      const p=result.pi;
      sweepRows.push({frequency_hz:result.frequency_hz,inductance_nh:p.inductance_h===null?null:p.inductance_h*1e9,resistance_ohm:p.resistance_ohm,q:p.q_first});
      sweepModels.push(result);
    }
    sweepContext.firstHz=sweepRows[0].frequency_hz;
    sweepContext.lastHz=i===count-1?result.frequency_hz:last;
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
  const model=$("#pi-model").value;if(model!=="pi")$("#sweep-model").value=model;
  if(model==="pi4"&&$("#model-ground-mode").value==="none")$("#model-ground-mode").value="strip";
  if(model!=="pi")$("#sweep-count").value="11";resetSweep();updateModelControls();
});
$("#model-ground-mode").addEventListener("change",()=>updateModelControls());
$("#eddy-mode")?.addEventListener("change",()=>{
  updateModelControls();resetSweep();resetSelfres();resetTransformer();matrixResult=null;$("#matrix-table").replaceChildren();$("#lmat-result").textContent="";controls();
});
$("#selfres").addEventListener("click",()=>task(async()=>{
  const firstGHz=numeric("#selfres-first"),lastGHz=numeric("#selfres-last"),stepGHz=numeric("#selfres-step"),first=firstGHz*1e9,last=lastGHz*1e9,step=stepGHz*1e9;
  if(!(first>0&&last>0&&step>0))throw new Error("Enter positive SELFRES bounds and resolution.");
  const base=modelPayload("pi2",first,firstGHz),useModel=$("#selfres-reference").value==="model";
  if(useModel&&!base.ground)throw new Error("Choose a ground strip or the other winding in the model reference settings below.");
  resetSelfres();status("Searching self-resonance with repeated distributed network solves…");
  const result=await request({...base,action:"selfres",first_hz:first,first_ghz:firstGHz,last_hz:last,last_ghz:lastGHz,step_hz:step,step_ghz:stepGHz,ground:useModel?base.ground:null,differential:$("#selfres-mode").value==="differential"},point=>{
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
  const result=await request({action:"lmat",...currentDefinition,technology:technologyText,...frequencyInput(),eddy:eddyEnabled(),
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
  const result=await request({action:"capacitance",...currentDefinition,ground,technology:technologyText,...frequencyInput(),
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
function updateTransformerControls(){
  const paired=current?.windings.length===2,first=currentDefinition?.winding||0;
  $("#transformer-ground-fields").hidden=$("#transformer-ground-mode").value!=="strip";
  $("#transformer-circuit").hidden=!paired;
  $("#transformer-note").textContent=paired?`Port 1: ${current.windings[first]} · Port 2: ${current.windings[1-first]}. Uses the selected frequency, CAP/LMAT mesh and native eddy setting.`:"Choose a transformer, balun or 3D transformer to analyze both windings.";
}
function resetTransformer(){
  transformerResult=null;transformerRequest=null;transformerRows=[];transformerSamples=[];transformerRange=null;
  $("#transformer-result").textContent="";$("#transformer-diagnostics").hidden=true;$("#transformer-metrics").replaceChildren();
  $("#transformer-circuit").innerHTML=transformerSVG();updateTransformerControls();renderTransformerSweep();
}
function transformerPayload(frequency,ghz=frequency/1e9){
  if(current?.windings.length!==2)throw Error("Choose a layout with two windings for CALCTRANS.");
  const first=currentDefinition.winding||0,mode=$("#transformer-ground-mode").value;
  const ground=mode==="first"?{...currentDefinition,winding:first}:mode==="strip"?stripDefinition("transformer-ground","_ground"):null;
  const termination_ohm=Math.fround(numeric("#transformer-termination")),f=frequency;
  if(!Number.isFinite(termination_ohm)||!Number.isFinite(f)||f<=0)throw Error("Frequency or termination exceeds the native command range.");
  const mesh=Object.fromEntries(Object.entries(meshSettings()).map(([k,v])=>[k,Math.fround(v)]));
  return {action:"calctrans",...currentDefinition,first_winding:first,second_winding:1-first,technology:technologyText,ground,...frequencyFields(f,ghz),termination_ohm,eddy:eddyEnabled(),mesh};
}
const transformerMetrics=[
  ["First inductance","first_inductance_h",1e9,"nH"],["Second inductance","second_inductance_h",1e9,"nH"],
  ["Mutual inductance","mutual_h",1e9,"nH"],["Coupling k","coupling",1,""],
  ["First resistance","first_resistance_ohm",1,"Ω"],["Second resistance","second_resistance_ohm",1,"Ω"],["Ground resistance","ground_resistance_ohm",1,"Ω"]
];
function renderTransformerResult(result,payload){
  transformerResult=result;transformerRequest=payload;
  $("#transformer-result").textContent=`${fmt(result.frequency_hz/1e9)} GHz · ${result.first_winding} / ${result.second_winding} · ${result.filaments} filaments / ${result.contacts} contacts · Termination ${fmt(result.termination_ohm,7)} Ω · Eddy ${result.eddy?"on":"off"}`;
  $("#transformer-circuit").innerHTML=transformerSVG(result.model,{frequencyHz:result.frequency_hz,first:result.first_winding,second:result.second_winding});
  $("#transformer-diagnostics").textContent=result.warnings.join(" ");$("#transformer-diagnostics").hidden=!result.warnings.length;
  const table=document.createElement("table"),head=table.createTHead().insertRow(),body=table.createTBody();
  for(const title of["CALCTRANS metric","Value"]){const th=document.createElement("th");th.textContent=title;head.append(th);}
  for(const [label,key,scale,unit]of transformerMetrics){const row=body.insertRow(),v=result.model[key];row.insertCell().textContent=label;row.insertCell().textContent=v===null?"Undefined":`${fmt(v*scale,7)} ${unit}`;}
  $("#transformer-metrics").replaceChildren(table);
}
function renderTransformerSweep(){
  $("#transformer-chart").innerHTML=sweepSVG(transformerRows,$("#transformer-sweep-metric").value,{model:"CALCTRANS",scale:$("#sweep-scale").value,...(transformerRange||{})});
}
$("#transformer-run").addEventListener("click",()=>task(async()=>{
  const ghz=numeric("#frequency"),payload=transformerPayload(ghz*1e9,ghz);resetTransformer();status("Solving both windings with CALCTRANS…");
  renderTransformerResult(await request(payload),payload);status("Coupled model complete. Values are specific to the displayed frequency.");
}));
$("#transformer-sweep").addEventListener("click",()=>task(async()=>{
  const firstGHz=numeric("#sweep-first"),lastGHz=numeric("#sweep-last"),first=firstGHz*1e9,last=lastGHz*1e9,count=numeric("#sweep-count"),log=$("#sweep-scale").value==="log";
  if(!(first>0&&last>first&&Number.isInteger(count)&&count>=2&&count<=101))throw Error("Sweep needs 0 < start < stop and 2–101 points.");
  resetTransformer();
  transformerRange={firstHz:first,lastHz:last};
  for(let i=0;i<count;i++){
    const frequency=log?first*(last/first)**(i/(count-1)):first+(last-first)*i/(count-1),ghz=i===0?firstGHz:i===count-1?lastGHz:frequency/1e9,payload=transformerPayload(frequency,ghz);
    status(`CALCTRANS sweep: ${i+1} / ${count} · ${fmt(payload.frequency_hz/1e9)} GHz…`);
    const result=await request(payload),m=result.model,scaled=(key)=>m[key]===null?null:m[key]*1e9;
    transformerSamples.push({result,payload});transformerRows.push({frequency_hz:result.frequency_hz,first_inductance_nh:scaled("first_inductance_h"),second_inductance_nh:scaled("second_inductance_h"),mutual_nh:scaled("mutual_h"),coupling:m.coupling,first_resistance_ohm:m.first_resistance_ohm,second_resistance_ohm:m.second_resistance_ohm,ground_resistance_ohm:m.ground_resistance_ohm});
    transformerRange={firstHz:transformerRows[0].frequency_hz,lastHz:i===count-1?result.frequency_hz:last};renderTransformerSweep();
  }
  const firstSample=transformerSamples[0];$("#frequency").value=String(firstSample.result.frequency_hz/1e9);renderTransformerResult(firstSample.result,firstSample.payload);status(`${count}-point CALCTRANS sweep plotted. Select a sample to inspect its coupled model.`);
}));
$("#transformer-sweep-metric").addEventListener("change",renderTransformerSweep);
$("#sweep-scale").addEventListener("change",renderTransformerSweep);
for(const el of document.querySelectorAll("#transformer-termination,#transformer-ground-mode,#transformer-ground-fields input,#transformer-ground-fields select"))el.addEventListener("change",()=>{resetTransformer();controls();});
function inspectTransformerPoint(event){
  const point=event.target.closest?.("[data-index]");if(!point||busy)return;
  const sample=transformerSamples[Number(point.dataset.index)];if(!sample)return;
  $("#frequency").value=String(sample.result.frequency_hz/1e9);renderTransformerResult(sample.result,sample.payload);controls();
}
$("#transformer-chart").addEventListener("click",inspectTransformerPoint);
$("#transformer-chart").addEventListener("keydown",event=>{if(event.key==="Enter"||event.key===" "){event.preventDefault();inspectTransformerPoint(event);}});
$("#download-transformer").addEventListener("click",()=>download(JSON.stringify({...transformerResult,inputs:transformerRequest},null,2),"application/json",filename("-calctrans.json")));
$("#download-transformer-svg").addEventListener("click",()=>download($("#transformer-circuit").innerHTML,"image/svg+xml",filename("-calctrans.svg")));
$("#download-transformer-ports").addEventListener("click",()=>{
  const rows=["parameter,row,column,real,imaginary"];
  for(const [name,m]of[["Y",transformerResult.admittance_matrix],["Z",transformerResult.impedance_matrix],["S",transformerResult.scattering_matrix]])m.forEach((row,i)=>row.forEach((z,j)=>rows.push([name,i+1,j+1,...z.map(v=>v??"")].join(","))));
  download(rows.join("\n"),"text/csv",filename("-calctrans-ports.csv"));
});
$("#download-transformer-sweep").addEventListener("click",()=>{
  const keys=["frequency_hz","first_inductance_nh","second_inductance_nh","mutual_nh","coupling","first_resistance_ohm","second_resistance_ohm","ground_resistance_ohm"];
  download("model,eddy,termination_ohm,"+keys.join(",")+"\n"+transformerRows.map((row,i)=>["CALCTRANS",transformerSamples[i].result.eddy,transformerSamples[i].result.termination_ohm,...keys.map(k=>row[k]??"")].join(",")).join("\n"),"text/csv",filename("-calctrans-sweep.csv"));
});
$("#download-transformer-plot").addEventListener("click",()=>download($("#transformer-chart").innerHTML,"image/svg+xml",filename("-calctrans-plot.svg")));

$("#pi2").addEventListener("click",()=>task(async()=>{
  const model=$("#pi-model").value;
  status(`Running ${MODEL_NAMES[model]} with the selected reference, pads and mesh…`);
  const ghz=numeric("#frequency"),result=await request(modelPayload(model,ghz*1e9,ghz));
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
$("#download-project").addEventListener("click",()=>task(async()=>download(inputJSON({format:"reasitic-project",version:1,shape:currentDefinition,technology:technologyText,mesh:meshSettings()},2),"application/json",filename(".json"))));
$("#project-file").addEventListener("change",event=>task(async()=>{
  const file=event.target.files[0];if(!file)return;
  const data=JSON.parse(await file.text());
  if(data.format!=="reasitic-project"||data.version!==1||!data.shape) throw new Error("Unsupported project file.");
  const restoredMesh=data.mesh?Object.fromEntries(Object.keys(MESH_FIELDS).map(key=>[key,Number(data.mesh[key])])):null;
  if(restoredMesh&&Object.values(restoredMesh).some(v=>!Number.isFinite(v)||v<=0))throw Error("Project mesh cells must be finite and positive.");
  const text=data.technology||"";
  const init=await request({action:"init",technology:text});
  // Verify geometry before replacing the current project.
  const restored=await request({action:"build",...data.shape,technology:text});
  technologyText=text;fillTechnology(init);
  $("#kind").value=data.shape.kind;
  $("#dimension-mode").value=["square","multimetal"].includes(data.shape.kind)&&!("length"in data.shape.parameters)&&"inner_length"in data.shape.parameters?"inner":"outer";
  $("#rectangular-input-mode").value=data.shape.native_interactive?"interactive":"keyword";showFields(data.shape);
  const symmetric=["symmetric_square","symmetric_polygon"].includes(data.shape.kind);
  const symmetricDefaults=symmetric?{name:restored.name,length:restored.parameters.length??100,radius:50,width:5,spacing:2,turns:2,sides:16,inner_gap:restored.parameters.inner_gap??((restored.parameters.width??5)+(restored.parameters.spacing??2)),
    metal:technology.metals.length-1,secondary_metal:restored.parameters.secondary_metal??Math.max(0,(restored.segments.find(s=>s.metal<technology.metals.length)?.metal??technology.metals.length-1)-1),angle:0,phase:1,x:restored.origin[0],y:restored.origin[1]}:{};
  const multimetal=data.shape.kind==="multimetal";
  const multimetalDefaults=multimetal?{name:restored.name,length:100,height:data.shape.parameters.length??100,width:5,spacing:2,turns:2,
    metal:technology.metals.length-1,bottom_metal:restored.parameters.bottom_metal??0,angle:0,phase:1,x:0,y:0}:{};
  const primitive=["capacitor","via"].includes(data.shape.kind),plate=data.shape.kind==="capacitor";
  const primitiveDefaults=primitive?{name:restored.name,length:plate?(data.shape.parameters.length??(data.shape.native_keyword?data.shape.parameters.width:undefined)??100):100,
    width:plate?(data.shape.parameters.width??(data.shape.native_keyword?data.shape.parameters.length:undefined)??5):5,metal:technology.metals.length-1,
    bottom_metal:restored.segments[1]?.metal??Math.max(0,technology.metals.length-2),via:0,nx:2,ny:2,angle:0,phase:1,x:0,y:restored.parameters.y??0}:{};
  const paired=["transformer","balun","transformer3d"].includes(data.shape.kind);
  const pairedDefaults=paired?{name:data.shape.parameters.name??"T1",primary_name:"",secondary_name:"",length:100,height:data.shape.parameters.length??100,
    width:3,secondary_width:data.shape.parameters.width??3,spacing:data.shape.kind==="transformer3d"?8:2,turns:data.shape.kind==="balun"?3:data.shape.kind==="transformer3d"?2:1.5,
    secondary_turns:data.shape.parameters.turns??1.5,metal:technology.metals.length-1,exit_metal:restored.parameters.exit_metal??-1,
    secondary_metal:restored.parameters.secondary_metal??Math.max(0,technology.metals.length-2),angle:0,phase:1,x:0,y:0}:{};
  const rectangularDefaults=["square","multimetal"].includes(data.shape.kind)?{name:restored.name,length:restored.parameters.length??100,height:restored.parameters.height??restored.parameters.length??100,
    inner_length:data.shape.parameters.inner_length??30,inner_height:data.shape.parameters.inner_height??data.shape.parameters.inner_length??30,
    width:5,spacing:2,turns:2,metal:technology.metals.length-1,exit_metal:restored.parameters.exit_metal??-1,
    bottom_metal:restored.parameters.bottom_metal??0,angle:0,phase:1,x:0,y:0}:{};
  const restoredParameters=data.shape.kind==="wire"?{name:restored.name,length:100,width:5,metal:technology.metals.length-1,angle:0,phase:1,x:0,y:restored.parameters.y??0,...data.shape.parameters}:{...symmetricDefaults,...multimetalDefaults,...primitiveDefaults,...pairedDefaults,...rectangularDefaults,...data.shape.parameters};
  if(data.shape.kind==="via")for(const key of ["nx","ny"])restoredParameters[key]=restored.parameters[key]??restored.segments[0][key];
  for(const [key,value] of Object.entries(restoredParameters))restoreFormParameter(key,key==="phase"&&(data.shape.kind==="wire"||symmetric||multimetal||primitive||paired||data.shape.kind==="square")?((restored.parameters.phase??value)<0?-1:1):value);
  if(restoredMesh)applyMesh(restoredMesh);
  currentDefinition=data.shape;current=restored;showFields(data.shape);render(current);resetResults();status("Project restored. Run analysis on the selected winding.");
  event.target.value="";
}));
$("#technology-file").addEventListener("change",event=>task(async()=>{
  const file=event.target.files[0];if(!file)return;
  const text=await file.text(),init=await request({action:"init",technology:text});
  technologyText=text;fillTechnology(init);$("#tech-name").textContent=file.name;
  current=null;currentDefinition=null;$("#drawing").replaceChildren();resetResults();status("Technology loaded. Generate a new layout.");event.target.value="";
}));
async function chooseTechnology(){
  const id=$("#technology-preset").value;
  const loaded=await request({action:"technology",preset:id,mim_density:$("#mim-density").value,
    substrate_rho:numeric("#substrate-rho"),substrate_thickness:numeric("#substrate-thickness")});
  technologyText=id==="sample-cmos"?"":loaded.text;fillTechnology(loaded);
  current=null;currentDefinition=null;$("#drawing").replaceChildren();resetResults();
  status("Technology loaded. Generate a new layout.");
}
for(const id of ["technology-preset","mim-density","substrate-rho","substrate-thickness"]){
  $("#"+id).addEventListener("change",()=>task(async()=>{
    const previous=technologyPreset?.id||(technologyText?"custom":"sample-cmos");
    try{await chooseTechnology();}catch(error){$("#technology-preset").value=previous;throw error;}
  }));
}
$("#download-technology").addEventListener("click",()=>task(async()=>{
  const text=technologyText||(await request({action:"technology",preset:"sample-cmos"})).text;
  download(text,"text/plain",String(technology.chip.techfile||"custom.tek").replace(/[^\w.-]/g,"_"));
}));
$("#reset-technology").addEventListener("click",()=>task(async()=>{
  const init=await request({action:"init"});technologyText="";fillTechnology(init);current=null;await generate();
}));
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
