"""Observe unmodified original GEOM and METALAREA consumed words and output stores."""
import argparse,gzip,hashlib,json,os,subprocess,tempfile
from pathlib import Path
from capture_original_symmetric import ORIGINAL_SHA256,LEGACY_SHA256
ROOT=Path(__file__).resolve().parents[1]
COMMANDS=r'''
set pagination off
set confirm off
set environment TERM dumb
set environment INPUTRC /dev/null
handle SIGQUIT nostop noprint pass
python
import gdb,struct,json
result=dict(geom=[],metalarea=[],reports=[]);active=None;indices={}
def mem(a,n):return bytes(gdb.selected_inferior().read_memory(a,n))
def reg(k):return int(gdb.parse_and_eval('$'+k))&0xffffffff
def u32(a):return struct.unpack('<I',mem(a,4))[0]
def raw(i=0):return bytes(gdb.parse_and_eval('$st'+str(i)).bytes).hex()
def string(a):return gdb.Value(a).cast(gdb.lookup_type('char').pointer()).string()
def records(a):
 out=[];s=u32(a+0xa8)
 while s:
  assert len(out)<20000;indices[s]=len(out);out.append((mem(s,48)+mem(s+0xcc,8)).hex());s=u32(s+0xec)
 return out
class Observe(gdb.Breakpoint):
 def stop(self):
  global active
  pc=reg('pc');esp=reg('esp');ebp=reg('ebp')
  if pc in(0x804c620,0x804ee74):
   assert active is None;a=u32(esp+4);active=dict(name=string(a),records=records(a),control_before=reg('fctrl'),terms=[])
  elif pc==0x804c67c:active['terms'].append(dict(segment=indices[reg('eax')],length=raw(),width=raw(1)))
  elif pc==0x804c693:active['terms'][-1].update(length_sum_bits=mem(ebp-16,8).hex(),area_sum_bits=mem(ebp-8,8).hex())
  elif pc==0x804cb8e:active.update(control_after=reg('fctrl'));result['geom'].append(active);active=None
  elif pc==0x804eebb:active['terms'].append(dict(segment=indices[reg('edx')],length=raw(),width=raw(1)))
  elif pc==0x804eece:active['terms'][-1]['accumulator']=raw(1)
  elif pc==0x804eedb:active.update(extended_bits=raw(),control_after=reg('fctrl'));result['metalarea'].append(active);active=None
  elif pc==0x804ae04:
   fmt=string(u32(esp+8))
   if fmt.startswith('Total length ='):result['reports'].append(dict(kind='geom',length_bits=mem(esp+12,8).hex(),area_bits=mem(esp+20,8).hex(),control=reg('fctrl')))
   elif fmt.startswith('Total Metal Area of %s'):result['reports'].append(dict(kind='metalarea',area_bits=mem(esp+16,8).hex(),control=reg('fctrl')))
  return False
for a in(0x804c620,0x804c67c,0x804c693,0x804cb8e,0x804ee74,0x804eebb,0x804eece,0x804eedb,0x804ae04):Observe('*'+hex(a),internal=True)
end
run -g -t process.tek -x input.asit < answers.txt
python
signal=0
if gdb.selected_inferior().pid:signal=int(gdb.parse_and_eval('$_siginfo.si_signo'));gdb.execute('kill',to_string=True)
result.update(signal=signal,unfinished=active)
open('geometry-metrics.json','w').write(json.dumps(result))
end
quit
'''


def jobs():
    f=json.loads((ROOT/'tests/fixtures/conductor_metrics_original.json').read_text())
    for i,c in enumerate(f['cases']):yield dict(label=f'conductor_metrics_original/{i}',public=c['public'],technology=c['technology'],creation=c['creation'],stdin=c['stdin'],name=c['name'])
    f=json.loads((ROOT/'tests/fixtures/paired_original.json').read_text())
    for i,c in enumerate(f['cases']):
        public={k:c[k]for k in('kind','parameters','native_keyword','native_interactive')if k in c}
        candidates=[''.join(s['coordinates_bits'][:96]+s['width_bits']for s in w['segments'])for w in c['windings']]
        for j,w in enumerate(c['windings']):yield dict(label=f'paired_original/{i}/{j}',public=dict(public,winding=j),technology=f['technology'],creation=c['script'],stdin=c['stdin'],name=w['name'],native_candidates=candidates,requested_winding=j)
    for filename in('symmetric_sessions_original','inner_sessions_original'):
        f=json.loads((ROOT/f'tests/fixtures/{filename}.json').read_text())
        for i,c in enumerate(f['cases']):
            r=c['request'];public={k:r[k]for k in('kind','parameters','native_keyword','native_interactive')if k in r}
            yield dict(label=f'{filename}/{i}',public=public,technology=r['technology'],creation=c['script'].split('PI2',1)[0],stdin=c['stdin'],name='A')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--reference',type=Path,required=True);parser.add_argument('--library-path',required=True);args=parser.parse_args();ref=args.reference.resolve();original=ref/'run/asitic.linux.2.2'
    for path,want in[(original,ORIGINAL_SHA256),(ref/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so',LEGACY_SHA256)]:
        if hashlib.sha256(path.read_bytes()).hexdigest()!=want:raise ValueError('Unexpected original checksum')
    cases=[]
    with tempfile.TemporaryDirectory(prefix='pyasitic-original-geometry-metrics-')as d:
        for i,c in enumerate(jobs()):
            script=c['creation']+f'GEOM {c["name"]}\nMETALAREA {c["name"]}\n';work=Path(d)/str(i);work.mkdir()
            for name,value in [('process.tek',c['technology']),('input.asit',script),('answers.txt',c['stdin']),('capture.gdb',COMMANDS)]:(work/name).write_text(value)
            run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=args.library_path),capture_output=True,text=True,start_new_session=True,timeout=120)
            if run.returncode or not(work/'geometry-metrics.json').exists()or'Python Exception'in run.stderr or'Traceback'in run.stderr:raise RuntimeError(f'Original geometry metrics {i}/{c["label"]}: '+run.stdout[-2000:]+run.stderr[-1500:])
            observed=json.loads((work/'geometry-metrics.json').read_text())
            if not observed['signal']and tuple(len(observed[k])for k in('geom','metalarea','reports'))not in((1,1,2),(0,0,0)):raise RuntimeError('Incomplete original geometry history '+run.stdout[-2000:])
            candidates=c.pop('native_candidates',None)
            if candidates and observed['geom']:
                actual=''.join(observed['geom'][0]['records']);matches=[j for j,v in enumerate(candidates)if v==actual];assert matches
                c['actual_winding_matches']=matches
                if c['public']['winding']not in matches:c['public']['winding']=matches[0]
            cases.append(dict(c,script=script,stdout=run.stdout,stderr=run.stderr,**observed));print(f'Original geometry metrics {i}/{c["label"]}: {len(observed["geom"])} reports, signal {observed["signal"]}',flush=True)
    parents=['conductor_metrics_original','paired_original','symmetric_sessions_original','inner_sessions_original']
    out=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,parents={n:hashlib.sha256((ROOT/f'tests/fixtures/{n}.json').read_bytes()).hexdigest()for n in parents},gdb_commands=COMMANDS,reference='Unmodified complete original GEOM and METALAREA CLI histories. Data-only static entry/instruction/return observers capture each consumed centerline/width word, length/width R80 operands, every GEOM F64 running store, every METALAREA R80 accumulator/return, actual sprintf output stores and FPU control. No numerical, input, descriptor, runtime or allocator changes. Duplicate-name lookup is identified against the original parent constructor records, with requested index and actual matches retained. Rejections and faults retained.',cases=cases)
    (ROOT/'tests/fixtures/geometry_metrics_original.json.gz').write_bytes(gzip.compress((json.dumps(out,separators=(',',':'),allow_nan=False)+'\n').encode(),mtime=0))


if __name__=='__main__':main()
