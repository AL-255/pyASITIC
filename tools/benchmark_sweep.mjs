// Measure the webpage's eleven sequential, distinct-frequency Pi2 requests.
// Usage: node tools/benchmark_sweep.mjs native-pi.json /path/pyodide.mjs site-directory output.json
import {readFileSync,writeFileSync} from "node:fs";
import {resolve,join} from "node:path";
import {pathToFileURL} from "node:url";
if(process.argv.length!==6)throw Error("Expected native-pi.json, pyodide.mjs, site-directory, output.json");
const site=resolve(process.argv[4]),report=JSON.parse(readFileSync(process.argv[2]));
const {loadPyodide}=await import(pathToFileURL(resolve(process.argv[3])).href);
const {installNumericalKernels}=await import(pathToFileURL(join(site,"numeric-kernels.mjs")).href);
const py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(join(site,"reasitic.zip"))),"zip");
await installNumericalKernels(py,readFileSync(join(site,"numeric.wasm")));
py.runPython("from reasitic.bridge import request_json");const call=py.globals.get("request_json");
const result={site_version:JSON.parse(readFileSync(join(site,"version.json"))).version,runtime:"Pyodide 314.0.7",first_hz:1e8,last_hz:2e10,count:11,scale:"linear",method:"Eleven distinct frequencies, one interpreter shared across FFT cases. Includes geometry/table work and Python JSON transport; excludes interpreter loading and DOM rendering. Browser timing only; original binary sweep timing is not measured here.",cases:[]};
for(const c of report.cases){
  const item={fft:c.fft,request:c.request,points:[]};const begin=performance.now();
  for(let i=0;i<result.count;i++){
    const frequency_hz=result.first_hz+(result.last_hz-result.first_hz)*i/(result.count-1),start=performance.now();
    const response=JSON.parse(call(JSON.stringify({...c.request,frequency_hz})));
    if(response.error)throw Error(response.error);
    const model=response.result;
    item.points.push({frequency_hz,seconds:(performance.now()-start)/1000,filaments:model.filaments,contacts:model.contacts,inductance_h:model.pi.inductance_h,resistance_ohm:model.pi.resistance_ohm,q:model.pi.q_first});
  }
  item.seconds=(performance.now()-begin)/1000;result.cases.push(item);
  console.log(JSON.stringify({version:result.site_version,fft:item.fft,filaments:item.points[0].filaments,contacts:item.points[0].contacts,points:item.points.length,seconds:item.seconds}));
}
call.destroy();writeFileSync(process.argv[5],JSON.stringify(result,null,2)+"\n");
