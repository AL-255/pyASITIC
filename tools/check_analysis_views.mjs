import assert from "node:assert/strict";
import { mkdirSync,writeFileSync,readFileSync } from "node:fs";
import { circuitSVG,sweepSVG } from "../web/analysis-views.mjs";

const model={inductance_h:1.02175e-9,resistance_ohm:5.0983,capacitance_first_f:24.33e-15,
  capacitance_second_f:21.8e-15,resistance_first_ohm:-2.97,resistance_second_ohm:5.55};
const circuit=circuitSVG(model,{model:"Pi4",frequencyHz:2e9,note:"Pad capacitance de-embedded · eddy currents disabled"});
assert.ok(circuit.includes("24.33 fF"));
assert.ok(circuit.includes("1.0218 nH"));
assert.ok(circuit.includes("-2.97 Ω"));
assert.ok(circuit.includes("3 / Ground"));
assert.ok(!circuit.includes("NaN"));
assert.ok(circuitSVG({}, {model:"Pi <unsafe>",note:"A & B"}).includes("Pi &lt;unsafe&gt;"));
assert.ok(circuitSVG({}, {note:"A & B"}).includes("A &amp; B"));

const rows=[{frequency_hz:1e8,inductance_nh:1.2,resistance_ohm:2,q:4},
  {frequency_hz:1e9,inductance_nh:1.2,resistance_ohm:3,q:6},
  {frequency_hz:2e9,inductance_nh:null,resistance_ohm:4,q:null},
  {frequency_hz:5e9,inductance_nh:-.4,resistance_ohm:5,q:-2}];
const plot=sweepSVG(rows,"q",{model:"Pi3",firstHz:1e8,lastHz:5e9});
assert.equal((plot.match(/class="plot-point"/g)||[]).length,3);
const curve=plot.match(/class="sweep-curve" d="([^"]*)"/)[1];
assert.equal((curve.match(/M/g)||[]).length,2,"Undefined samples break the curve");
assert.ok(plot.includes("(log)"));
for(const metric of ["q","inductance_nh","resistance_ohm"]){
  for(const scale of ["linear","log"]){
    const svg=sweepSVG(rows,metric,{scale,model:"A < B"});
    assert.ok(!/NaN|Infinity/.test(svg));
    assert.ok(svg.includes("A &lt; B"));
  }
}
assert.ok(!/NaN|Infinity/.test(sweepSVG([],"q")));
assert.ok(!/NaN|Infinity/.test(sweepSVG([{frequency_hz:1e9,q:0}],"q")));
const resonanceCase=JSON.parse(readFileSync(new URL("../tests/fixtures/resonance_physical.json",import.meta.url))).cases[0];
const resonanceRows=resonanceCase.progress.map(point=>({frequency_hz:point[2]*1e9,reactance_ohm:point[3]})).sort((a,b)=>a.frequency_hz-b.frequency_hz);
const resonance=sweepSVG(resonanceRows,"reactance_ohm",{model:"SELFRES SLOW",scale:"linear",interactive:false});
assert.ok(resonance.includes("Input reactance (Ω)"));
assert.ok(resonance.includes('class="zero-axis"'));
assert.ok(!resonance.includes('role="button"'));
assert.ok(!/NaN|Infinity/.test(resonance));
if(process.argv[2]){
  mkdirSync(process.argv[2],{recursive:true});
  writeFileSync(process.argv[2]+"/circuit.svg",circuit);
  writeFileSync(process.argv[2]+"/plot.svg",plot);
  writeFileSync(process.argv[2]+"/resonance.svg",resonance);
}
console.log("Circuit units, SVG escaping, plot gaps, negative values and finite axes passed.");
