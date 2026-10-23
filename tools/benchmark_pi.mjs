// Usage: node tools/benchmark_pi.mjs native-benchmark.json /path/to/pyodide.mjs output.json
import {readFileSync,writeFileSync} from "node:fs";
import {pathToFileURL} from "node:url";
import {installNumericalKernels} from "../web/numeric-kernels.mjs";
if(process.argv.length!==5)throw Error("Expected native-benchmark.json, pyodide.mjs and output.json");
const {loadPyodide}=await import(pathToFileURL(process.argv[3]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL("../dist/reasitic.zip",import.meta.url))),"zip");
await installNumericalKernels(py,readFileSync(new URL("../dist/numeric.wasm",import.meta.url)));
py.runPython("from reasitic.bridge import request_json");
const call=py.globals.get("request_json");
const report=JSON.parse(readFileSync(process.argv[2]));
for(const c of report.cases){
  c.wasm_seconds=[];
  for(let i=0;i<3;i++){
    const start=performance.now(),result=JSON.parse(call(JSON.stringify(c.request)));
    c.wasm_seconds.push((performance.now()-start)/1000);
    if(result.error)throw Error(result.error);
    c.wasm_result=result.result;
  }
  console.log(JSON.stringify({fft:c.fft,native_cold_seconds:c.native_cold_seconds,native_warm_seconds:c.native_warm_seconds,python_seconds:c.python_seconds,wasm_seconds:c.wasm_seconds}));
}
call.destroy();
writeFileSync(process.argv[4],JSON.stringify(report,null,2)+"\n");
