"""Observe original INDUCTANCE/QLF retained arithmetic and printed stores."""
import argparse,hashlib,json,os,re,subprocess,tempfile
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
result=dict(inductance=[],dc=[],reports=[]);active=None;indices={}
def mem(a,n):return bytes(gdb.selected_inferior().read_memory(a,n))
def reg(k):return int(gdb.parse_and_eval('$'+k))&0xffffffff
def u32(a):return struct.unpack('<I',mem(a,4))[0]
def i32(a):return struct.unpack('<i',mem(a,4))[0]
def f64(a):return struct.unpack('<d',mem(a,8))[0]
def raw(i):return bytes(gdb.parse_and_eval('$st'+str(i)).bytes).hex()
def string(a):return gdb.Value(a).cast(gdb.lookup_type('char').pointer()).string()
def inputs(shape):
 out=[];a=u32(shape+0xa8);metals=i32(0x80d8904);m=u32(0x80d8910);v=u32(0x80d8914)
 while a:
  assert len(out)<20000;metal=i32(a+0xdc);indices[a]=len(out)
  r=dict(endpoints_bits=mem(a,48).hex(),width_bits=mem(a+0xcc,8).hex(),metal=metal,via=metal>=metals)
  if metal<metals:r.update(primary_width_bits=mem(a+0x30,8).hex(),primary_thickness_bits=mem(a+0x38,8).hex(),thickness_bits=mem(m+236*metal+0xb0,8).hex(),resistance_bits=mem(m+236*metal+0xb8,8).hex())
  else:r.update(via_width_bits=mem(v+240*(metal-metals)+0xa0,8).hex(),via_spacing_bits=mem(v+240*(metal-metals)+0xa8,8).hex(),resistance_bits=mem(v+240*(metal-metals)+0xc0,8).hex(),nx=i32(a+0xe0),ny=i32(a+0xe4))
  out.append(r);a=u32(a+0xec)
 return out
class Observe(gdb.Breakpoint):
 def stop(self):
  global active
  pc=reg('pc');esp=reg('esp')
  if pc==0x804ce78:
   assert active is None;shape=u32(esp+4);r=inputs(shape)
   if 'inputs'not in result:result.update(inputs=r,name=string(shape),origin_bits=mem(shape+0x54,16).hex())
   else:assert result['inputs']==r
   active=dict(control_before=reg('fctrl'))
   if not result['inductance']:active.update(self_terms=[],pairs=[])
  elif pc==0x804d038:
   active.update(extended_bits=raw(0),control_after=reg('fctrl'));result['inductance'].append(active);active=None
  elif pc==0x804efa4:result['dc'].append(dict(extended_bits=raw(0),control=reg('fctrl')))
  elif pc==0x804ae04:
   fmt=string(u32(esp+8))
   if fmt.startswith('LF Extrapolated Q of %s')or fmt.startswith('Inductance of %s ='):
    result['reports'].append(dict(format=fmt,name=string(u32(esp+12)),output_bits=mem(esp+16,8).hex(),control=reg('fctrl')))
  elif active is not None and'self_terms'in active:
   if pc==0x804cf48:active['self_terms'].append(dict(segment=indices[reg('ebx')],length=raw(0),width=raw(1),thickness=raw(2)))
   elif pc==0x804cf6a:active['self_terms'][-1]['log_argument']=raw(0)
   elif pc==0x804cf6c:active['self_terms'][-1]['log_return']=raw(0)
   elif pc==0x804cf8e:active['self_terms'][-1]['accumulator']=raw(1)
   elif pc==0x804cfe7:active['pairs'].append(dict(first=indices[reg('esi')],second=indices[reg('ebx')],status=reg('eax')if reg('eax')<0x80000000 else reg('eax')-0x100000000,value_bits=mem(reg('ebp')-8,8).hex()))
   elif pc==0x804d017:
    if active['pairs']:active['pairs'][-1]['accumulator']=raw(1)
   elif pc==0x804d02b:active.update(self_total=raw(0),mutual_total=raw(1))
  return False
for a in(0x804ce78,0x804d038,0x804efa4,0x804ae04,0x804cf48,0x804cf6a,0x804cf6c,0x804cf8e,0x804cfe7,0x804d017,0x804d02b):Observe('*'+hex(a),internal=True)
end
run -g -t process.tek -x input.asit < answers.txt
python
signal=0
if gdb.selected_inferior().pid:signal=int(gdb.parse_and_eval('$_siginfo.si_signo'));gdb.execute('kill',to_string=True)
result.update(signal=signal,unfinished=active)
open('metrics.json','w').write(json.dumps(result))
end
quit
'''


def jobs():
    f=json.loads((ROOT/'tests/fixtures/resistance_original.json').read_text())
    for c in f['cases']:yield dict(label=c['label'],public=c['public'],technology=c['technology'],creation=c['creation'],stdin=c['stdin'],name='A')
    for filename in ['symmetric_interactive_sessions_original','primitive_sessions_original','transformer3d_sessions_original']:
        path=ROOT/f'tests/fixtures/{filename}.json'
        f=json.loads(path.read_text())
        for i,c in enumerate(f['cases']):
            r=c['request'];public={k:r[k]for k in('kind','parameters','native_keyword','native_interactive','technology')if k in r}
            stop='LMAT'if filename.startswith('transformer3d')else'PI2';creation=c['script'].split(stop,1)[0]
            if filename.startswith('transformer3d'):
                for j,m in enumerate(c['lmat']):yield dict(label=f'{filename}/{i}/{j}',public=dict(public,winding=j),technology=r['technology'],creation=creation,stdin=c.get('stdin','quit\n'),name=m['name'])
            else:yield dict(label=f'{filename}/{i}',public=public,technology=r['technology'],creation=creation,stdin=c.get('stdin','quit\n'),name='A')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--reference',type=Path,required=True);parser.add_argument('--library-path',required=True);args=parser.parse_args();ref=args.reference.resolve();original=ref/'run/asitic.linux.2.2'
    for path,want in[(original,ORIGINAL_SHA256),(ref/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so',LEGACY_SHA256)]:
        if hashlib.sha256(path.read_bytes()).hexdigest()!=want:raise ValueError('Unexpected original checksum')
    records=[];frequencies=[.001,.1234567,1.,10.,100.,1000.,1000000.]
    with tempfile.TemporaryDirectory(prefix='pyasitic-original-conductor-metrics-')as d:
        for i,c in enumerate(jobs()):
            script=c['creation']+f'INDUCTANCE {c["name"]}\n'+''.join(f'Q {c["name"]} {f:.17g}\n'for f in frequencies);work=Path(d)/str(i);work.mkdir()
            for name,value in [('process.tek',c['technology']),('input.asit',script),('answers.txt',c['stdin']),('capture.gdb',COMMANDS)]:(work/name).write_text(value)
            run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=args.library_path),capture_output=True,text=True,start_new_session=True,timeout=180)
            if run.returncode or not(work/'metrics.json').exists()or'Python Exception'in run.stderr or'Traceback'in run.stderr:raise RuntimeError(f'Original conductor capture {i}/{c["label"]}: '+run.stdout[-2400:]+run.stderr[-1600:])
            observed=json.loads((work/'metrics.json').read_text())
            if not observed['signal']and tuple(len(observed[k])for k in('inductance','dc','reports'))!=(8,7,8):raise RuntimeError('Incomplete original metric history: '+run.stdout[-2000:])
            records.append(dict(c,script=script,frequency_ghz=frequencies,stdout=run.stdout,stderr=run.stderr,**observed));print(f'Original conductor {i}/{c["label"]}: {len(observed.get("inputs",[]))} segments, signal {observed["signal"]}',flush=True)
    parents=['resistance_original','symmetric_interactive_sessions_original','primitive_sessions_original','transformer3d_sessions_original']
    out=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,parents={n:hashlib.sha256((ROOT/f'tests/fixtures/{n}.json').read_bytes()).hexdigest()for n in parents},gdb_commands=COMMANDS,reference='Unmodified original complete INDUCTANCE/QLF CLI histories. Data-only static entry/instruction/return observers retain all consumed segment/technology records, self/log and pair accumulators, complete ST0 returns, DC returns and actual binary64 sprintf arguments. No numerical, descriptor, input, runtime or allocator patching. Faults and nonfinite records retained.',cases=records)
    (ROOT/'tests/fixtures/conductor_metrics_original.json').write_text(json.dumps(out,separators=(',',':'),allow_nan=False)+'\n')


if __name__=='__main__':main()
