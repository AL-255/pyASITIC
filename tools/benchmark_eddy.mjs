// Complete eddy-enabled analyses; one interpreter/version, three requests/case.
// Usage: node tools/benchmark_eddy.mjs /path/to/pyodide.mjs output.json [site-dir] [--layered]
import {readFileSync,writeFileSync} from "node:fs";
import {pathToFileURL,fileURLToPath} from "node:url";
import {resolve,join} from "node:path";
const layered=process.argv.includes("--layered"),args=process.argv.slice(2).filter(v=>v!=="--layered");
if(![2,3].includes(args.length))throw Error("Expected pyodide.mjs, output.json and optional site-directory");
const root=fileURLToPath(new URL("../",import.meta.url)),site=args[2]?resolve(args[2]):join(root,"dist");
const {installNumericalKernels}=await import(pathToFileURL(join(site,"numeric-kernels.mjs")).href);
const {loadPyodide}=await import(pathToFileURL(args[0]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(join(site,"reasitic.zip"))),"zip");
await installNumericalKernels(py,readFileSync(join(site,"numeric.wasm")));
py.runPython("from reasitic.bridge import request_json");const call=py.globals.get("request_json");
const fixture=name=>JSON.parse(readFileSync(join(root,"tests/fixtures/"+name+".json")));
const report={site_version:JSON.parse(readFileSync(join(site,"version.json"))).version,runtime:"Pyodide 314.0.7",method:"Three identical complete requests per case in listed order; one interpreter, geometry/table caches persist between cases. Interpreter loading and DOM rendering excluded. No original-binary timing is claimed.",cases:[]};
for(const [i,c]of fixture("network_eddy").cases.entries())if(c.process===(layered?"BiCMOS":"CMOS")){
 const request={action:"pi2",...Object.fromEntries(["kind","parameters","technology","frequency_hz","eddy","mesh","ground"].map(k=>[k,c[k]]))};
 report.cases.push({label:`Pi2 ${i} ${c.kind}`,request});
}
for(const i of layered?[]:[5,8,11]){
 const c=fixture("transformer_network").cases[i],request={action:"calctrans",...Object.fromEntries(["first","second","ground","frequency_hz","technology","mesh","eddy","termination_ohm"].map(k=>[k,c[k]]))};
 report.cases.push({label:`CALCTRANS ${i} ${c.first.kind}`,request});
}
if(layered){
 for(const [i,c]of fixture("eddy").cases.entries())if(c.process==="BiCMOS"){
  const request={action:"lmat",kind:c.kind,parameters:c.parameters,technology:c.technology,frequency_hz:2e9,eddy:true,mesh:{length_cell:50,width_cell:3,thickness_cell:.5,capacitance_length_cell:50,capacitance_width_cell:1000}};
  report.cases.push({label:`LMAT ${i} ${c.kind}`,request});
 }
 for(const [i,c]of fixture("pix").cases.entries())if(c.process==="BiCMOS"){
  const request={action:"pix",...Object.fromEntries(["kind","parameters","technology","frequency_hz","eddy","mesh","ground"].map(k=>[k,c[k]]))};
  report.cases.push({label:`PiX ${i} ${c.kind}`,request});
 }
}
for(const c of report.cases){
 c.seconds=[];
 for(let i=0;i<3;i++){
  const start=performance.now(),response=JSON.parse(call(JSON.stringify(c.request)));c.seconds.push((performance.now()-start)/1000);
  if(response.error)throw Error(response.error);c.result=response.result;
 }
 console.log(JSON.stringify({label:c.label,seconds:c.seconds,filaments:c.result.filaments,contacts:c.result.contacts}));
}
call.destroy();writeFileSync(args[1],JSON.stringify(report,null,2)+"\n");
