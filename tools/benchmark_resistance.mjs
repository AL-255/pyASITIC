// Six isolated direct HF-resistance calls per frequency; loading is excluded.
import{readFileSync}from'node:fs';import{pathToFileURL}from'node:url';
if(!process.argv[2]||!process.argv[3])throw Error('Usage: node tools/benchmark_resistance.mjs /path/to/pyodide.mjs /path/to/release/dist');
const root=process.argv[3],{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(root+'/reasitic.zip')),'zip');
const{installNumericalKernels}=await import(pathToFileURL(root+'/numeric-kernels.mjs').href);await installNumericalKernels(py,readFileSync(root+'/numeric.wasm'));
py.runPython(`from reasitic import build,resistance_dc,resistance_hf,Technology
shape=build('polygon',radius=120.123456789,sides=32,width=3.14159265358979,spacing=2.71828182845905,turns=2.96875,metal='M4')
tech=Technology.default()`);
const result={version:JSON.parse(readFileSync(root+'/version.json')).version,segments:py.runPython('len(shape.segments)'),cases:[]};
for(const hz of[1e9,1e11]){
 py.globals.set('frequency',hz);const samples=[];let value;
 for(let i=0;i<6;i++){const start=performance.now();value=py.runPython('resistance_hf(shape,tech,frequency)');samples.push(performance.now()-start);}
 result.cases.push({hz,value,samples_ms:samples});
}
console.log(JSON.stringify(result));
