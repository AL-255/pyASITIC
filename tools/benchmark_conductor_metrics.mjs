// Reproduce the prior Python-per-pair path versus the complete compiled batch.
import{readFileSync,writeFileSync}from'node:fs';
import{execFileSync}from'node:child_process';
import{createHash}from'node:crypto';
import{pathToFileURL}from'node:url';
import{installNumericalKernels}from'../web/numeric-kernels.mjs';
const baseline='ced6e871c02b7b71e983c32869a8f10c32a1bd1a',root=new URL('../',import.meta.url);
const{loadPyodide}=await import(pathToFileURL(process.argv[2]).href),py=await loadPyodide();
py.unpackArchive(new Uint8Array(readFileSync(new URL('dist/reasitic.zip',root))),'zip');const wasm=readFileSync(new URL('dist/numeric.wasm',root));await installNumericalKernels(py,wasm);
py.globals.set('baseline_source',execFileSync('git',['show',baseline+':src/reasitic/inductance.py'],{cwd:root,encoding:'utf8'}));
const fixture=readFileSync(new URL('tests/fixtures/conductor_metrics_original.json',root));py.globals.set('fixture',fixture.toString());
const report=JSON.parse(py.runPython(`
import json,time,statistics,struct
from reasitic import Technology
from reasitic.bridge import _shape
from reasitic import conductor_metrics,mutual_kernel
namespace={'__name__':'reasitic._baseline_conductor','__package__':'reasitic'};exec(compile(baseline_source,'baseline_conductor','exec'),namespace)
c=json.loads(fixture)['cases'][54];tech=Technology.from_text(c['technology']);shape=_shape(c['public'],tech)
def previous():
 mutual_kernel._pair.cache_clear();return namespace['inductance_estimate'](shape,tech)
def current():
 conductor_metrics._evaluate.cache_clear();return float(conductor_metrics.retained_estimates(shape,tech)[0])
previous();current();samples={'previous':[],'current':[]};outputs={}
for repeat in range(5):
 for name,call in [('previous',previous),('current',current)]:
  start=time.perf_counter();value=call();samples[name].append(1000*(time.perf_counter()-start));outputs[name]=struct.pack('<d',value).hex()
assert outputs['current']==c['reports'][0]['output_bits']
json.dumps(dict(case=c['label'],segments=len(shape.segments),repeats=5,samples_ms=samples,median_ms={key:statistics.median(values)for key,values in samples.items()},speedup=statistics.median(samples['previous'])/statistics.median(samples['current']),output_bits=outputs,original_output_bits=c['reports'][0]['output_bits']))
`));
Object.assign(report,{scope:'Uncached conductor geometry evaluation, warm pinned Pyodide numerical plans; prior per-pair Python orchestration versus complete compiled batch.',baseline_commit:baseline,node_version:process.version,pyodide_version:py.version,original_sha256:JSON.parse(fixture).original_sha256,kernel_sha256:createHash('sha256').update(wasm).digest('hex'),fixture_sha256:createHash('sha256').update(fixture).digest('hex')});
const text=JSON.stringify(report,null,2)+'\n';if(process.argv[3])writeFileSync(process.argv[3],text);process.stdout.write(text);
