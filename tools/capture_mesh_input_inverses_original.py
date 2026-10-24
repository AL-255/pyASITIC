"""Read-only original ZSYTF2/ZSYTRI stores for captured mesh command histories."""
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
result=dict(events=[]);pending={};returns={}
def mem(a,n):return bytes(gdb.selected_inferior().read_memory(a,n))
def reg(k):return int(gdb.parse_and_eval('$'+k))&0xffffffff
def u32(a):return struct.unpack('<I',mem(a,4))[0]
def i32(a):return struct.unpack('<i',mem(a,4))[0]
def upper(a,n,ld):return b''.join(mem(a+16*(j*ld+i),16)for j in range(n)for i in range(j+1)).hex()
class Observe(gdb.Breakpoint):
 def stop(self):
  pc=reg('pc');esp=reg('esp')
  if pc in(0x809bcf8,0x8095bf8):
   args=[u32(esp+4+4*i)for i in range(6 if pc==0x809bcf8 else 7)];kind='factor'if pc==0x809bcf8 else'inverse';n=i32(args[1]);ld=i32(args[3]);assert 0<n<=256
   item=dict(kind=kind,n=n,stride=ld,uplo=mem(args[0],1).hex(),input_bits=upper(args[2],n,ld),control_before=reg('fctrl'))
   destination=u32(esp);pending.setdefault(destination,[]).append((item,args))
   if destination not in returns:returns[destination]=Observe('*'+hex(destination),internal=True)
  else:
   item,args=pending[pc].pop();item.update(output_bits=upper(args[2],item['n'],item['stride']),pivots=[i32(args[4]+4*i)for i in range(item['n'])],info=i32(args[-1]),control_after=reg('fctrl'));result['events'].append(item)
  return False
for a in(0x809bcf8,0x8095bf8):Observe('*'+hex(a),internal=True)
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
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--reference',type=Path,required=True);p.add_argument('--library-path',required=True);a=p.parse_args();original=a.reference.resolve()/'run/asitic.linux.2.2';legacy=a.reference.resolve()/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so'
 for path,expected in((original,ORIGINAL_SHA256),(legacy,LEGACY_SHA256)):
  if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise ValueError('Unexpected original checksum')
 target=ROOT/'tests/fixtures/mesh_inputs_original.json.gz';fixture=json.loads(gzip.decompress(target.read_bytes()))
 with tempfile.TemporaryDirectory(prefix='pyasitic-original-mesh-inverses-')as d:
  for index,c in enumerate(fixture['cases']):
   work=Path(d)/str(index);work.mkdir()
   for name,value in(('process.tek',c['request']['technology']),('input.asit',c['lmat']['script']),('answers.txt','quit\n'),('capture.gdb',COMMANDS)):(work/name).write_text(value)
   run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=a.library_path),capture_output=True,text=True,start_new_session=True,timeout=120)
   if run.returncode or not(work/'raw.json').exists()or'Python Exception'in run.stderr or'Traceback'in run.stderr:raise RuntimeError(run.stdout[-2000:]+run.stderr[-1500:])
   c['inversions']=dict(json.loads((work/'raw.json').read_text()),stdout=run.stdout,stderr=run.stderr);print(index,[(e['kind'],e['n'],e['info'])for e in c['inversions']['events']],flush=True)
 fixture['inverse_commands']=COMMANDS
 with gzip.GzipFile(str(target),'wb',mtime=0)as f:f.write((json.dumps(fixture,separators=(',',':'),allow_nan=False)+'\n').encode())

if __name__=='__main__':main()
