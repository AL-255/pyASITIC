// Compare identical retained builds in Pyodide; electrical solves are excluded.
import{readFileSync}from"node:fs";
import{pathToFileURL}from"node:url";
import os from"node:os";
import{installNumericalKernels}from"../web/numeric-kernels.mjs";
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL("../dist/reasitic.zip",import.meta.url))),"zip");
await installNumericalKernels(py,readFileSync(new URL("../dist/numeric.wasm",import.meta.url)));
const result=JSON.parse(py.runPython(`
import hashlib,json,struct
from time import perf_counter
from statistics import median
from reasitic import build
import reasitic.symmetric_geometry as sg
compiled=sg._compiled_geometry
parameters=dict(radius=120,sides=32,width=3.25,spacing=2.125,inner_gap=15.375,turns=3,metal='M4',secondary_metal='M3')
results=[]
try:
 for name,backend in [('portable retained Python',None),('compiled retained batch',compiled)]:
  sg._compiled_geometry=backend;times=[]
  for i in range(7):
   start=perf_counter();shape=build('symmetric_polygon',**parameters);times.append((perf_counter()-start)*1000)
  digest=hashlib.sha256(b''.join(struct.pack('<18d',*(v for p in s.points for v in p))+struct.pack('<di',s.width,s.metal)for s in shape.segments)).hexdigest()
  results.append(dict(backend=name,segments=len(shape.segments),samples_ms=times,first_ms=times[0],warm_median_ms=median(times[1:]),geometry_sha256=digest))
 assert results[0]['geometry_sha256']==results[1]['geometry_sha256']
finally:sg._compiled_geometry=compiled
json.dumps(dict(kind='symmetric_polygon',parameters=parameters,results=results))
`));
console.log(JSON.stringify({scope:"Geometry build only, in one Pyodide instance; seven consecutive builds per backend, first excluded from warm median. Compares the two retained implementations, not the original native executable or complete electrical solve.",version:JSON.parse(readFileSync(new URL("../dist/version.json",import.meta.url))).version,node:process.version,pyodide:py.version,cpu:os.cpus()[0].model,...result},null,2));
