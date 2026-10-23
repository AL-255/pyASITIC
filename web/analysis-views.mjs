const escape = value => String(value).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&apos;"}[c]));
const number = value => {
  if(!Number.isFinite(value))return "—";
  const a=Math.abs(value);
  return a>=1e6 || (a>0 && a<.001)?value.toExponential(3).replace("e+","e"):value.toLocaleString("en-US",{maximumSignificantDigits:5});
};
const text=(x,y,value,extra="")=>`<text x="${x}" y="${y}" ${extra}>${escape(value)}</text>`;
const unit=(value,scale,suffix)=>Number.isFinite(value)?`${number(value*scale)} ${suffix}`:"—";

export function circuitSVG(pi={},options={}){
  const model=options.model||"Pi2",frequency=options.frequencyHz;
  const title=`${model} three-terminal equivalent circuit${Number.isFinite(frequency)?` at ${number(frequency/1e9)} GHz`:""}`;
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 360" role="img" aria-label="${escape(title)}">
  <title>${escape(title)}</title><rect width="760" height="360" fill="#101820" rx="7"/>
  <g fill="none" stroke="#a5bdcc" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M60 90H200 M280 90H350 M450 90H700 M140 90V150 M125 150H155 M125 164H155 M140 164V190 M140 270V300H620V270 M620 190V164 M605 164H635 M605 150H635 M620 150V90 M380 300V322 M362 322H398 M368 330H392 M375 338H385"/>
  <path stroke="#f0b567" d="M200 90l8 -9 12 18 12 -18 12 18 12 -18 12 18 12 -9 M350 90c0 -25 25 -25 25 0c0 -25 25 -25 25 0c0 -25 25 -25 25 0c0 -25 25 -25 25 0"/>
  <path d="M140 190l-9 8 18 12 -18 12 18 12 -18 12 18 12 -9 12 M620 190l-9 8 18 12 -18 12 18 12 -18 12 18 12 -9 12"/>
  <g fill="#101820" stroke="#f0b567"><circle cx="60" cy="90" r="7"/><circle cx="700" cy="90" r="7"/><circle cx="380" cy="300" r="6"/></g>
  <g fill="#a5bdcc"><circle cx="140" cy="90" r="3"/><circle cx="620" cy="90" r="3"/></g></g>
  <g font-family="monospace" font-size="12" fill="#9cabb9">
  ${text(24,22,model+(Number.isFinite(frequency)?` · ${number(frequency/1e9)} GHz`:""))}
  ${text(60,65,"1",'text-anchor="middle"')}${text(700,65,"2",'text-anchor="middle"')}${text(415,326,"3 / Ground")}
  ${text(240,36,"Rs",'text-anchor="middle"')}${text(400,36,"Ls",'text-anchor="middle"')}
  ${text(175,145,"Cs1")}${text(175,225,"Rs1")}${text(585,145,"Cs2",'text-anchor="end"')}${text(585,225,"Rs2",'text-anchor="end"')}
  </g><g font-family="monospace" font-size="14" fill="#f1ca94">
  ${text(240,57,unit(pi.resistance_ohm,1,"Ω"),'text-anchor="middle"')}${text(400,57,unit(pi.inductance_h,1e9,"nH"),'text-anchor="middle"')}
  ${text(175,166,unit(pi.capacitance_first_f,1e15,"fF"))}${text(175,246,unit(pi.resistance_first_ohm,1,"Ω"))}
  ${text(585,166,unit(pi.capacitance_second_f,1e15,"fF"),'text-anchor="end"')}${text(585,246,unit(pi.resistance_second_ohm,1,"Ω"),'text-anchor="end"')}
  </g><g font-family="monospace" font-size="10" fill="#9cabb9">${text(380,355,options.note||"Frequency-specific series L/R and series RC shunts",'text-anchor="middle"')}</g></svg>`;
}

export const SWEEP_METRICS={
  inductance_nh:{title:"Inductance",unit:"nH",color:"#81b4ef"},
  resistance_ohm:{title:"Resistance",unit:"Ω",color:"#f0b567"},
  q:{title:"Quality factor",unit:"",color:"#8fd1ae"}
};

export function sweepSVG(rows,metric="q",options={}){
  const setting=SWEEP_METRICS[metric];
  if(!setting)throw new Error("Unknown sweep metric");
  const valid=rows.filter(row=>Number.isFinite(row.frequency_hz)&&row.frequency_hz>0);
  const first=options.firstHz||valid[0]?.frequency_hz||1e8;
  const last=options.lastHz||valid.at(-1)?.frequency_hz||first*10;
  const lowF=first,highF=last>first?last:first*10;
  const log=options.scale!=="linear";
  const x=f=>90+640*(log?Math.log(f/lowF)/Math.log(highF/lowF):(f-lowF)/(highF-lowF));
  const values=valid.map(row=>row[metric]).filter(Number.isFinite);
  let low=Math.min(0,...values),high=Math.max(0,...values);
  if(low===high)high=low+1;
  const range=high-low;
  if(low<0)low-=range*.08;
  high+=range*.1;
  const y=value=>270-240*(value-low)/(high-low);
  const label=options.label||`${setting.title}${setting.unit?` (${setting.unit})`:""}`;
  const title=`${label} versus frequency · ${options.model||"ASITIC"}`;
  let grid="",points="",curve="",drawing=false;
  for(let i=0;i<=4;i++){
    const v=low+(high-low)*i/4;
    grid+=`<path d="M90 ${y(v)}H730" stroke="#283744"/>${text(80,y(v)+4,number(v),'text-anchor="end"')}`;
    const frequency=log?lowF*(highF/lowF)**(i/4):lowF+(highF-lowF)*i/4;
    grid+=`<path d="M${x(frequency)} 30V270" stroke="#1e2e3a"/>${text(x(frequency),292,number(frequency/1e9),'text-anchor="middle"')}`;
  }
  rows.forEach((row,i)=>{
    const value=row[metric],f=row.frequency_hz;
    if(!Number.isFinite(value)||!Number.isFinite(f)||f<=0){drawing=false;return;}
    curve+=`${drawing?"L":"M"}${x(f)} ${y(value)} `;drawing=true;
    const caption=`${number(f/1e9)} GHz: ${number(value)} ${setting.unit}`;
    points+=`<g class="plot-point" data-index="${i}" tabindex="0" role="button" aria-label="${escape(caption)}"><title>${escape(caption)}</title><circle cx="${x(f)}" cy="${y(value)}" r="10" fill="transparent"/><circle cx="${x(f)}" cy="${y(value)}" r="3" fill="${setting.color}"/></g>`;
  });
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 320" role="img" aria-label="${escape(title)}"><title>${escape(title)}</title><rect width="760" height="320" fill="#101820" rx="7"/>
  <g font-family="monospace" font-size="12" fill="#9cabb9">${grid}${text(90,18,label)}${text(730,18,options.model||"ASITIC",'text-anchor="end"')}${text(730,314,`Frequency · GHz${log?" (log)":""}`,'text-anchor="end"')}</g>
  <path d="M90 30V270H730" fill="none" stroke="#61788b"/>
  <g><path class="sweep-curve" d="${curve}" fill="none" stroke="${setting.color}" stroke-width="2"/>${points}</g>
  ${values.length?"":`<g font-family="monospace" font-size="13" fill="#9cabb9">${text(400,150,"Run a sweep to plot the selected metric",'text-anchor="middle"')}</g>`}</svg>`;
}
