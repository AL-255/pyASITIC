// Scoped Node/Pyodide timings; no thresholds and no original-speed claim.
import{readFileSync}from'node:fs';import{gunzipSync}from'node:zlib';import{pathToFileURL}from'node:url';import{performance}from'node:perf_hooks';import{createHash}from'node:crypto';
import{installNumericalKernels}from'../web/numeric-kernels.mjs';
if(!process.argv[2])throw Error('Usage: node tools/benchmark_spatial_edits.mjs /path/to/pyodide.mjs');
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide(),wasm=readFileSync(new URL('../dist/numeric.wasm',import.meta.url));
py.unpackArchive(new Uint8Array(readFileSync(new URL('../dist/reasitic.zip',import.meta.url))),'zip');await installNumericalKernels(py,wasm);
py.runPython('from reasitic.bridge import request_json\nfrom reasitic.precision import _cached_rotate_xy,_trig');const call=py.globals.get('request_json');
const read=name=>JSON.parse(gunzipSync(readFileSync(new URL('../tests/fixtures/'+name+'.json.gz',import.meta.url)))),c=read('spatial_edits_original').cases.find(c=>c.label==='transformer3d'),model=read('spatial_sessions_original').cases.find(c=>c.label==='transformer');
console.log(JSON.stringify({node:process.version,pyodide:py.version,wasm_sha256:createHash('sha256').update(wasm).digest('hex'),scope:'Complete JSON requests, excludes startup/download/render; one cold and five repeated calls per case'}));
for(const[label,request]of[['edited 3D preview',{action:'build',...c.public,edits:c.operations,technology:c.technology}],['edited coupled model',model.request]]){
 py.runPython('_cached_rotate_xy.cache_clear();_trig.cache_clear()');const text=JSON.stringify(request),times=[];let result;
 for(let i=0;i<6;i++){const start=performance.now();result=JSON.parse(call(text));times.push(performance.now()-start);if(result.error)throw Error(result.error);}
 const warm=times.slice(1).sort((a,b)=>a-b);console.log(JSON.stringify({label,cold_ms:times[0],warm_median_ms:warm[2],warm_samples_ms:times.slice(1),filaments:result.result.filaments,segments:result.result.segments?.length??result.result.segments}));
}
call.destroy();
