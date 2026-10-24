// Usage: node tools/benchmark_pi.mjs native-benchmark.json /path/to/pyodide.mjs output.json [site-directory]
import {readFileSync,writeFileSync} from "node:fs";
import {pathToFileURL,fileURLToPath} from "node:url";
import {resolve,join} from "node:path";
if(![5,6].includes(process.argv.length))throw Error("Expected native-benchmark.json, pyodide.mjs, output.json and optional site-directory");
const site=process.argv[5]?resolve(process.argv[5]):fileURLToPath(new URL("../dist/",import.meta.url));
const {installNumericalKernels}=await import(pathToFileURL(join(site,"numeric-kernels.mjs")).href);
const {loadPyodide}=await import(pathToFileURL(process.argv[3]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(join(site,"reasitic.zip"))),"zip");
await installNumericalKernels(py,readFileSync(join(site,"numeric.wasm")));
py.runPython("from reasitic.bridge import request_json");
const call=py.globals.get("request_json");
const report=JSON.parse(readFileSync(process.argv[2]));
report.site_version=JSON.parse(readFileSync(join(site,"version.json"))).version;
for(const c of report.cases){
  c.wasm_seconds=[];
  for(let i=0;i<3;i++){
    const start=performance.now(),result=JSON.parse(call(JSON.stringify(c.request)));
    c.wasm_seconds.push((performance.now()-start)/1000);
    if(result.error)throw Error(result.error);
    c.wasm_result=result.result;
  }
  console.log(JSON.stringify({fft:c.fft,filaments:c.wasm_result.filaments,contacts:c.wasm_result.contacts,native_cold_seconds:c.native_cold_seconds,native_warm_seconds:c.native_warm_seconds,python_seconds:c.python_seconds,wasm_seconds:c.wasm_seconds}));
}
call.destroy();
writeFileSync(process.argv[4],JSON.stringify(report,null,2)+"\n");
