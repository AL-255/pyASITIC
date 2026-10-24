// Complete scene/model JSON requests. No timing thresholds or native-speed claim.
import{readFileSync}from'node:fs';import{gunzipSync}from'node:zlib';import{pathToFileURL}from'node:url';import{performance}from'node:perf_hooks';import{createHash}from'node:crypto';
import{installNumericalKernels}from'../web/numeric-kernels.mjs';
if(!process.argv[2])throw Error('Usage: node tools/benchmark_copy_links.mjs /path/to/pyodide.mjs');
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide(),wasm=readFileSync(new URL('../dist/numeric.wasm',import.meta.url));
py.unpackArchive(new Uint8Array(readFileSync(new URL('../dist/reasitic.zip',import.meta.url))),'zip');await installNumericalKernels(py,wasm);
py.runPython('from reasitic.bridge import request_json\nfrom reasitic.precision import _cached_rotate_xy,_trig\nfrom reasitic.potential import _cached_tables,_cached_contact_groups');const call=py.globals.get('request_json');
const fixture=name=>JSON.parse(gunzipSync(readFileSync(new URL('../tests/fixtures/'+name+'.json.gz',import.meta.url)))),scene=fixture('copy_links_original').cases.find(c=>c.label==='transformer3d'),models=fixture('copy_sessions_original').cases;
console.log(JSON.stringify({node:process.version,pyodide:py.version,wasm_sha256:createHash('sha256').update(wasm).digest('hex'),scope:'Complete JSON requests, excludes runtime startup/download/render; geometry/contact/table caches cleared before each case; first call and five repeats'}));
for(const[label,request]of[
 ['six-object 3D scene',{action:'build',...scene.public,edits:scene.operations,technology:scene.technology}],
 ['copied BALUN coupled model',models.find(c=>c.label==='balun/calctrans').request],
 ['metal-converted VIA Pi2',models.find(c=>c.label==='via/copied-metal-pi2').request]
]){
 py.runPython('_cached_rotate_xy.cache_clear();_trig.cache_clear();_cached_tables.cache_clear();_cached_contact_groups.cache_clear()');
 const input=JSON.stringify(request),times=[];let result;
 for(let i=0;i<6;i++){const start=performance.now();result=JSON.parse(call(input));times.push(performance.now()-start);if(result.error)throw Error(result.error);}
 const warm=times.slice(1).sort((a,b)=>a-b),r=result.result;
 console.log(JSON.stringify({label,input_sha256:createHash('sha256').update(input).digest('hex'),first_ms:times[0],warm_median_ms:warm[2],warm_samples_ms:times.slice(1),frequency_hz:r.frequency_hz,filaments:r.filaments,segments:r.segments?.length??r.segments,windings:r.windings?.length}));
}
call.destroy();
