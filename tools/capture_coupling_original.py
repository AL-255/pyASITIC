"""Read-only complete original COUPLING calls, including mutable translation history."""
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
result=dict(calls=[],reports=[]);active=None;indices={}
def mem(a,n):return bytes(gdb.selected_inferior().read_memory(a,n))
def reg(k):return int(gdb.parse_and_eval('$'+k))&0xffffffff
def u32(a):return struct.unpack('<I',mem(a,4))[0]
def i32(a):return struct.unpack('<i',mem(a,4))[0]
def raw():return bytes(gdb.parse_and_eval('$st0').bytes).hex()
def string(a):return gdb.Value(a).cast(gdb.lookup_type('char').pointer()).string()
def shape(a):
 out=dict(name=string(a),origin_bits=mem(a+0x54,16).hex(),segments=[]);s=u32(a+0xa8);metals=i32(0x80d8904);m=u32(0x80d8910);v=u32(0x80d8914)
 while s:
  assert len(out['segments'])<20000;indices[s]=len(out['segments']);metal=i32(s+0xdc)
  r=dict(endpoints_bits=mem(s,48).hex(),width_bits=mem(s+0xcc,8).hex(),metal=metal,via=metal>=metals,edges_bits=b''.join(mem(s+o,24)for o in(0x44,0x5c,0x88,0xa0)).hex())
  if metal<metals:r.update(primary_width_bits=mem(s+0x30,8).hex(),primary_thickness_bits=mem(s+0x38,8).hex(),thickness_bits=mem(m+236*metal+0xb0,8).hex(),resistance_bits=mem(m+236*metal+0xb8,8).hex())
  else:r.update(via_width_bits=mem(v+240*(metal-metals)+0xa0,8).hex(),via_spacing_bits=mem(v+240*(metal-metals)+0xa8,8).hex(),resistance_bits=mem(v+240*(metal-metals)+0xc0,8).hex(),nx=i32(s+0xe0),ny=i32(s+0xe4))
  out['segments'].append(r);s=u32(s+0xec)
 return out
class Observe(gdb.Breakpoint):
 def stop(self):
  global active
  pc=reg('pc');esp=reg('esp');ebp=reg('ebp')
  if pc==0x804d03c:
   assert active is None;a,b,out=u32(esp+4),u32(esp+8),u32(esp+12)
   active=dict(first_before=shape(a),second_before=shape(b),control_before=reg('fctrl'),pairs=[]);active['_pointers']=(a,b,out)
  elif pc==0x804d07c:
   assert active is not None;active['inductance_bits']=[mem(ebp-16,8).hex(),mem(ebp-24,8).hex()]
  elif pc==0x804d10e:
   a,b=u32(esp),u32(esp+4);active['pairs'].append(dict(first=indices[a],second=indices[b],input_bits=mem(a,64).hex()+mem(b,64).hex()))
  elif pc==0x804d113:
   active['pairs'][-1].update(status=reg('eax')if reg('eax')<0x80000000 else reg('eax')-0x100000000,value_bits=mem(ebp-8,8).hex())
  elif pc==0x804d12d:active['pairs'][-1]['sum_bits']=mem(ebp-32,8).hex()
  elif pc==0x804d1e0:
   a,b,out=active.pop('_pointers');active.update(extended_bits=raw(),mutual_bits=mem(out,8).hex(),first_after=shape(a),second_after=shape(b),control_after=reg('fctrl'));result['calls'].append(active);active=None
  elif pc==0x804ae04:
   fmt=string(u32(esp+8))
   if fmt.startswith('Coupling coefficient of %s'):
    result['reports'].append(dict(first=string(u32(esp+12)),second=string(u32(esp+16)),coefficient_bits=mem(esp+20,8).hex(),mutual_bits=mem(esp+28,8).hex(),control=reg('fctrl')))
  return False
for a in(0x804d03c,0x804d07c,0x804d10e,0x804d113,0x804d12d,0x804d1e0,0x804ae04):Observe('*'+hex(a),internal=True)
end
run -g -t process.tek -x input.asit < answers.txt
python
signal=0
if gdb.selected_inferior().pid:signal=int(gdb.parse_and_eval('$_siginfo.si_signo'));gdb.execute('kill',to_string=True)
result.update(signal=signal,unfinished=active)
open('coupling.json','w').write(json.dumps(result))
end
quit
'''


def jobs():
    f=json.loads((ROOT/'tests/fixtures/paired_original.json').read_text())
    for i,c in enumerate(f['cases']):
        public={k:c[k]for k in('kind','parameters','native_keyword','native_interactive')if k in c}
        yield dict(label=f'paired_original/{i}',public=public,technology=f['technology'],creation=c['script'],stdin=c['stdin'],names=[w['name']for w in c['windings']])
    f=json.loads((ROOT/'tests/fixtures/transformer3d_sessions_original.json').read_text())
    for i,c in enumerate(f['cases']):
        r=c['request'];public={k:r[k]for k in('kind','parameters','native_keyword','native_interactive')if k in r}
        yield dict(label=f'transformer3d_sessions_original/{i}',public=public,technology=r['technology'],creation=c['script'].split('LMAT',1)[0],stdin=c['stdin'],names=[w['name']for w in c['lmat']])
    tech=json.loads((ROOT/'tests/fixtures/paired_original.json').read_text())['technology']
    for i,(origin,length,phase,angle)in enumerate([(0.,40.,1,0),(12.345,40.,1,17),(1e10,40.,-1,-35.5),(-1e10,40.,1,90),(40.,.00001,1,0),(40.,.0001,1,0),(40.,1.,1,0),(40.,1000.,-1,17)]):
        defs=[];script=''
        for j,name in enumerate(('A','B')):
            p=dict(name=name,length=length,width=5.,metal='M4'if j==0 else'M3',phase=phase if j else 1,angle=angle,x=origin+10*j,y=origin+20*j)
            defs.append(dict(kind='wire',parameters=p,native_keyword=True));script+=f'WIRE NAME={name}:LEN={length:.17g}:WID=5:METAL={p["metal"]}:PHASE={p["phase"]}:ORIENT={angle}:XORG={p["x"]:.17g}:YORG={p["y"]:.17g}\n'
        yield dict(label=f'wire/{i}',first=defs[0],second=defs[1],technology=tech,creation=script,stdin='quit\n',names=['A','B'])


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--reference',type=Path,required=True);parser.add_argument('--library-path',required=True);args=parser.parse_args();ref=args.reference.resolve();original=ref/'run/asitic.linux.2.2'
    for path,want in[(original,ORIGINAL_SHA256),(ref/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so',LEGACY_SHA256)]:
        if hashlib.sha256(path.read_bytes()).hexdigest()!=want:raise ValueError('Unexpected original checksum')
    cases=[]
    with tempfile.TemporaryDirectory(prefix='pyasitic-original-coupling-')as d:
        for i,c in enumerate(jobs()):
            a,b=c['names'];order=[(a,b),(a,b),(b,a),(a,b)];script=c['creation']+''.join(f'COUPLING {x} {y}\n'for x,y in order);work=Path(d)/str(i);work.mkdir()
            for name,value in [('process.tek',c['technology']),('input.asit',script),('answers.txt',c['stdin']),('capture.gdb',COMMANDS)]:(work/name).write_text(value)
            run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=args.library_path),capture_output=True,text=True,start_new_session=True,timeout=180)
            if run.returncode or not(work/'coupling.json').exists()or'Python Exception'in run.stderr or'Traceback'in run.stderr:raise RuntimeError(f'Original coupling {i}/{c["label"]}: '+run.stdout[-2400:]+run.stderr[-1600:])
            observed=json.loads((work/'coupling.json').read_text())
            if not observed['signal']and len(observed['calls'])not in(0,4):raise RuntimeError('Incomplete coupling history '+run.stdout[-2000:])
            if len(observed['calls'])!=len(observed['reports']):raise RuntimeError('Missing coupling reports')
            cases.append(dict(c,script=script,order=order,stdout=run.stdout,stderr=run.stderr,**observed));print(f'Original coupling {i}/{c["label"]}: {len(observed["calls"])} calls, {sum(len(e["pairs"])for e in observed["calls"])} cross pairs, signal {observed["signal"]}',flush=True)
    out=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,parents={n:hashlib.sha256((ROOT/f'tests/fixtures/{n}.json').read_bytes()).hexdigest()for n in('paired_original','transformer3d_sessions_original')},gdb_commands=COMMANDS,reference='Unmodified original complete COUPLING CLI histories: A/B, A/B repeated, B/A reversed, A/B repeated. Data-only static entry/instruction/return observers record all segment/technology inputs and post-call geometry, inductance F64 stores, actual translated pair inputs, statuses, pair/sum F64 stores, raw coefficient return, actual sprintf M/k stores and FPU control. No numerical, descriptor, input, runtime or allocator patching. Rejected same-name histories, faults and nonfinite words are retained.',cases=cases)
    (ROOT/'tests/fixtures/coupling_original.json.gz').write_bytes(gzip.compress((json.dumps(out,separators=(',',':'),allow_nan=False)+'\n').encode(),mtime=0))


if __name__=='__main__':main()
