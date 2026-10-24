"""Observe MAXNW/counts/filaments and LMAT reports in unchanged original CLI runs."""
import argparse,hashlib,json,os,subprocess,tempfile
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
import gdb,json,struct
result=dict(counts=[],filaments=[],reports=[])
def mem(a,n):return bytes(gdb.selected_inferior().read_memory(a,n))
def reg(k):return int(gdb.parse_and_eval('$'+k))&0xffffffff
def u32(a):return struct.unpack('<I',mem(a,4))[0]
def i32(a):return struct.unpack('<i',mem(a,4))[0]
def string(a):return gdb.Value(a).cast(gdb.lookup_type('char').pointer()).string()
pending={};returns={}
class Observe(gdb.Breakpoint):
 def stop(self):
  pc=reg('pc');esp=reg('esp')
  if pc in(0x8064f6c,0x806597c):
   destination=u32(esp);kind='counts'if pc==0x8064f6c else'filament';pointer=u32(esp+(4 if kind=='counts'else 8))
   pending.setdefault(destination,[]).append((kind,pointer))
   if destination not in returns:returns[destination]=Observe('*'+hex(destination),internal=True)
  elif pc in returns:
   kind,p=pending[pc].pop()
   if kind=='filament':result['filaments'].append(dict(bits=mem(p,64).hex(),metal=i32(p+64)))
   else:
    n=i32(p+0x20);w=u32(p+0x18);t=u32(p+0x1c)
    result['counts'].append(dict(total=i32(p+0x24),width=[i32(w+4*i)for i in range(n)],thickness=[i32(t+4*i)for i in range(n)],maxnw=i32(0x80ce5a8),width_cell_bits=mem(0x80ce588,8).hex(),thickness_cell_bits=mem(0x80ce590,8).hex(),control=reg('fctrl')))
  else:
   fmt=string(u32(esp+8))
   if fmt.startswith('L = '):result['reports'].append(dict(format=fmt,bits=mem(esp+12,16).hex()))
  return False
for a in(0x8064f6c,0x806597c,0x804ae04):Observe('*'+hex(a),internal=True)
end
run -g -t process.tek -x input.asit < answers.txt
python
signal=0
if gdb.selected_inferior().pid:signal=int(gdb.parse_and_eval('$_siginfo.si_signo'));gdb.execute('kill',to_string=True)
result.update(signal=signal,pending=sum(map(len,pending.values())))
open('raw.json','w').write(json.dumps(result))
end
quit
'''

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--reference',type=Path,required=True);p.add_argument('--library-path',required=True);a=p.parse_args()
 original=a.reference.resolve()/'run/asitic.linux.2.2';legacy=a.reference.resolve()/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so'
 for path,expected in((original,ORIGINAL_SHA256),(legacy,LEGACY_SHA256)):
  if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise ValueError('Unexpected original checksum')
 tech=(ROOT/'src/reasitic/CMOS.tek').read_text();cases=[]
 with tempfile.TemporaryDirectory(prefix='pyasitic-original-mesh-cli-')as d:
  for maximum in(None,500,65536,2147483647,9,1):
   label='default'if maximum is None else str(maximum);work=Path(d)/label;work.mkdir()
   script=(''if maximum is None else f'SETMAXNW {maximum}\n')+'MAXNW\nCELL 1000 1 1000\nCCELL 1000 1000\nWIRE NAME=A:LEN=40:WID=20:METAL=M5:XORG=40:YORG=40\nLMAT A 1\n'
   for name,value in(('process.tek',tech),('input.asit',script),('answers.txt','quit\n'),('capture.gdb',COMMANDS)):(work/name).write_text(value)
   run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=a.library_path),capture_output=True,text=True,start_new_session=True,timeout=120)
   if run.returncode or not(work/'raw.json').exists()or'Python Exception'in run.stderr or'Traceback'in run.stderr:raise RuntimeError(run.stdout[-2400:]+run.stderr[-1800:])
   raw=json.loads((work/'raw.json').read_text());cases.append(dict(label=label,maximum=maximum,script=script,stdout=run.stdout,stderr=run.stderr,**raw));print(label,'counts',len(raw['counts']),'filaments',len(raw['filaments']),'reports',len(raw['reports']),'signal',raw['signal'],flush=True)
 out=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,technology=tech,gdb_commands=COMMANDS,reference='Unchanged complete original CLI histories with read-only entry/return/data observers; original commands, globals, count stores, all constructed filament stores and actual binary64 LMAT report arguments. No numerical, allocator or runtime replacements. Native nonfinite results retained.',cases=cases)
 (ROOT/'tests/fixtures/mesh_sessions_original.json').write_text(json.dumps(out,separators=(',',':'),allow_nan=False)+'\n')

if __name__=='__main__':main()
