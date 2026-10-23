const $ = selector => document.querySelector(selector);
const form = $("#geometry-form");
const NS = "http://www.w3.org/2000/svg";
const COLORS = ["#e8bd65", "#81b4ef", "#b899eb", "#8fd1ae", "#e89971", "#e88fbd", "#64cbd1", "#cecf86"];
let worker, ready = false, busy = false, nextId = 0, current = null, currentDefinition = null, technology = null, technologyText = "", sweepRows = null, matrixResult = null, capacitanceResult = null, pi2Result = null;
const pending = new Map();
const fmt = (value, digits=4) => Number(value).toLocaleString(undefined, { maximumSignificantDigits: digits });

function error(message="") { $("#error").hidden = !message; $("#error").textContent = message; }
function status(message) { $("#analysis-status").textContent = message; }
function controls() {
  $("#generate").disabled = !ready || busy;
  for (const id of ["simulate", "sweep", "lmat", "capacitance", "pi2", "download-gds", "download-project"]) $("#"+id).disabled = !ready || busy || !current;
  $("#download-csv").disabled = busy || !sweepRows;
  $("#download-matrix").disabled = busy || !matrixResult;
  $("#download-capacitance").disabled = busy || !capacitanceResult;
  for(const id of ["download-pi2","download-ports"]) $("#"+id).disabled = busy || !pi2Result;
  $("#active-winding").disabled = busy;
  $("#coupling").disabled = busy || !current || current.windings.length!==2;
}
function request(payload) {
  const id = ++nextId;
  return new Promise((resolve, reject) => { pending.set(id, {resolve,reject}); worker.postMessage({id,request:payload}); });
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
  $("#pi2-ground-control").hidden=shape.windings.length<2;
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
  sweepRows=null; $("#sweep-table").replaceChildren(); $("#sweep-chart").hidden=true;
  matrixResult=null; $("#matrix-table").replaceChildren(); $("#lmat-result").textContent="";
  capacitanceResult=null; $("#capacitance-table").replaceChildren(); $("#capacitance-result").textContent="";
  pi2Result=null; $("#pi2-metrics").replaceChildren(); $("#pi2-ports").replaceChildren(); $("#pi2-result").textContent="";
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
function numeric(selector) { const value=Number($(selector).value);if(!Number.isFinite(value)||!$(selector).value) throw new Error("Enter a valid frequency.");return value; }
function renderSweep(rows) {
  const chart=$("#sweep-chart");chart.replaceChildren();chart.hidden=false;
  const minF=rows[0].frequency_hz,maxF=rows.at(-1).frequency_hz;
  const maxR=Math.max(...rows.map(r=>r.hf_ohm))*1.15;
  const x=f=>55+610*Math.log(f/minF)/Math.log(maxF/minF), y=r=>155-125*r/maxR;
  chart.append(svgElement("path",{d:"M 55 20 V 155 H 665",stroke:"#41515f",fill:"none"}));
  for (let i=0;i<=4;i++) {
    const resistance=maxR*i/4;
    chart.append(svgElement("path",{d:`M 55 ${y(resistance)} H 665`,stroke:"#263542",fill:"none"}));
    chart.append(svgElement("text",{x:47,y:y(resistance)+3,"text-anchor":"end"},fmt(resistance,3)));
  }
  chart.append(svgElement("path",{d:rows.map((r,i)=>`${i?"L":"M"} ${x(r.frequency_hz)} ${y(r.hf_ohm)}`).join(" "),fill:"none",stroke:"#f0b567","stroke-width":2}));
  chart.append(svgElement("text",{x:55,y:180},`${fmt(minF/1e9)} GHz`),svgElement("text",{x:665,y:180,"text-anchor":"end"},`${fmt(maxF/1e9)} GHz (log)`),svgElement("text",{x:65,y:15},"HF resistance · Ω"));
  const table=document.createElement("table"),head=table.createTHead().insertRow();
  for(const title of ["GHz","L est. (nH)","R HF (Ω)","QLF"]) { const th=document.createElement("th");th.textContent=title;head.append(th); }
  const body=table.createTBody();
  for(const r of rows) {const tr=body.insertRow();for(const value of [r.frequency_hz/1e9,r.inductance_nh,r.hf_ohm,r.qlf]) tr.insertCell().textContent=fmt(value,5);}
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
  status("Running frequency sweep…");
  const result=await request({action:"sweep",...currentDefinition,technology:technologyText,first_hz:numeric("#sweep-first")*1e9,last_hz:numeric("#sweep-last")*1e9,count:31});
  sweepRows=result.rows;renderSweep(sweepRows);status("31-point sweep complete. Inductance estimate is frequency independent.");
}));
$("#download-csv").addEventListener("click",()=>{
  const keys=["frequency_hz","inductance_nh","dc_ohm","hf_ohm","qlf"];
  download(keys.join(",")+"\n"+sweepRows.map(row=>keys.map(key=>row[key]).join(",")).join("\n"),"text/csv",filename("-sweep.csv"));
});
$("#lmat").addEventListener("click",()=>task(async()=>{
  status("Assembling and solving filament impedance matrix…");
  const result=await request({action:"lmat",...currentDefinition,technology:technologyText,frequency_hz:numeric("#frequency")*1e9,
    mesh:{length_cell:numeric("#mesh-length"),width_cell:numeric("#mesh-width"),thickness_cell:numeric("#mesh-thickness")}});
  matrixResult=result;
  $("#lmat-result").textContent=`L = ${fmt(result.inductance_h*1e9,6)} nH · R = ${fmt(result.resistance_ohm,6)} Ω · Series Q = ${fmt(result.series_q,6)} · ${result.filaments} filaments / ${result.segments} metal segments`;
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
  status("Combining the filament and substrate matrices and solving Pi2 node equations…");
  const ground=current.windings.length===2 && $("#pi2-ground").checked ? {...currentDefinition,winding:1-(currentDefinition.winding||0)} : null;
  const result=await request({action:"pi2",...currentDefinition,ground,technology:technologyText,frequency_hz:numeric("#frequency")*1e9,
    mesh:{length_cell:numeric("#mesh-length"),width_cell:numeric("#mesh-width"),thickness_cell:numeric("#mesh-thickness"),
      capacitance_length_cell:numeric("#cap-length"),capacitance_width_cell:numeric("#cap-width")}});
  pi2Result=result;
  $("#pi2-result").textContent=`${fmt(result.frequency_hz/1e9)} GHz · ${result.segments} metal segments · ${result.filaments} filaments · ${result.contacts} contacts · Eddy currents disabled`;
  const p=result.pi,table=document.createElement("table"),head=table.createTHead().insertRow();
  for(const title of ["Pi2 metric","Value"]){const th=document.createElement("th");th.textContent=title;head.append(th);}
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
  status(`Pi2 complete. Resonance is an estimate from the model at this frequency. ${ground?"The other winding is grounded. ":""}${result.warnings.join(" ")}`);
}));
$("#download-pi2").addEventListener("click",()=>download(JSON.stringify(pi2Result,null,2),"application/json",filename("-pi2.json")));
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
try {
  worker=new Worker(new URL("worker.js",import.meta.url),{type:"module"});
  worker.onerror=event=>fatal(event.message||"Runtime load failed.");
  worker.onmessage=async({data})=>{
    if(data.fatal){fatal(data.fatal);return;}
    if(data.ready){
      ready=true;$("#runtime").replaceChildren();const dot=document.createElement("i");dot.className="led";$("#runtime").append(dot,document.createTextNode("Python ready"));
      await task(async()=>{fillTechnology(await request({action:"init"}));await generate();});return;
    }
    const promise=pending.get(data.id);if(!promise)return;pending.delete(data.id);
    data.error ? promise.reject(new Error(data.error)) : promise.resolve(data.result);
  };
} catch(e){fatal(e.message);}
