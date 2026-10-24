// Complete eddy-enabled analyses; one interpreter/version, three requests/case.
// Usage: node tools/benchmark_eddy.mjs /path/to/pyodide.mjs output.json [site-dir]
import {readFileSync,writeFileSync} from "node:fs";
import {pathToFileURL,fileURLToPath} from "node:url";
import {resolve,join} from "node:path";
if(![4,5].includes(process.argv.length))throw Error("Expected pyodide.mjs, output.json and optional site-directory");
const root=fileURLToPath(new URL("../",import.meta.url)),site=process.argv[4]?resolve(process.argv[4]):join(root,"dist");
const {installNumericalKernels}=await import(pathToFileURL(join(site,"numeric-kernels.mjs")).href);
const {loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(join(site,"reasitic.zip"))),"zip");
await installNumericalKernels(py,readFileSync(join(site,"numeric.wasm")));
py.runPython("from reasitic.bridge import request_json");const call=py.globals.get("request_json");
const fixture=name=>JSON.parse(readFileSync(join(root,"tests/fixtures/"+name+".json")));
const report={site_version:JSON.parse(readFileSync(join(site,"version.json"))).version,runtime:"Pyodide 314.0.7",method:"Three identical complete requests per case in listed order; one interpreter, geometry/table caches persist between cases. Interpreter loading and DOM rendering excluded. No original-binary timing is claimed.",cases:[]};
for(const [i,c]of fixture("network_eddy").cases.entries())if(c.process==="CMOS"){
 const request={action:"pi2",...Object.fromEntries(["kind","parameters","technology","frequency_hz","eddy","mesh","ground"].map(k=>[k,c[k]]))};
 report.cases.push({label:`Pi2 ${i} ${c.kind}`,request});
}
for(const i of[5,8,11]){
 const c=fixture("transformer_network").cases[i],request={action:"calctrans",...Object.fromEntries(["first","second","ground","frequency_hz","technology","mesh","eddy","termination_ohm"].map(k=>[k,c[k]]))};
 report.cases.push({label:`CALCTRANS ${i} ${c.first.kind}`,request});
}
for(const c of report.cases){
 c.seconds=[];
 for(let i=0;i<3;i++){
  const start=performance.now(),response=JSON.parse(call(JSON.stringify(c.request)));c.seconds.push((performance.now()-start)/1000);
  if(response.error)throw Error(response.error);c.result=response.result;
 }
 console.log(JSON.stringify({label:c.label,seconds:c.seconds,filaments:c.result.filaments,contacts:c.result.contacts}));
}
call.destroy();writeFileSync(process.argv[3],JSON.stringify(report,null,2)+"\n");
