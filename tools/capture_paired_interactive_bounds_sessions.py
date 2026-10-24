"""Complete original coupled stores at interactive paired input boundaries."""
import argparse,gzip,hashlib,json,os,re,subprocess,tempfile
from pathlib import Path
from capture_original_symmetric import ORIGINAL_SHA256,LEGACY_SHA256
from capture_transformer import TAP
from capture_paired_interactive_bounds_original import answers
ROOT=Path(__file__).resolve().parents[1]
COMMANDS=r'''
set pagination off
set confirm off
set environment TERM dumb
set environment INPUTRC /dev/null
set environment LD_PRELOAD TAP_PATH
handle SIGQUIT nostop noprint pass
python
import gdb,struct,json
records=[];nodes=[];pending={};returns={}
def mem(a,n):return bytes(gdb.selected_inferior().read_memory(a,n))
def reg(k):return int(gdb.parse_and_eval('$'+k))&0xffffffff
def u32(a):return struct.unpack('<I',mem(a,4))[0]
def ports():return [mem(a,8).hex()for a in(0x80d8da8,0x80d8db0,0x80d8db8,0x80d8dc0,0x80d8dd8,0x80d8de0,0x80d8de8,0x80d8df0)]
class Observe(gdb.Breakpoint):
 def stop(self):
  pc=reg('pc');esp=reg('esp')
  if pc==0x8087d14:
   ret=u32(esp);pending.setdefault(ret,[]).append(dict(Y=ports(),control_before=reg('fctrl')))
   if ret not in returns:returns[ret]=Observe('*'+hex(ret),internal=True)
  elif pc==0x8053e00:
   n=u32(esp+12);assert 0<n<=256;nodes.append(dict(size=n,capacitance=mem(u32(esp+4),16*n*n).hex(),inductance=mem(u32(esp+8),16*n*n).hex()))
  else:
   r=pending[pc].pop();r.update(S=[mem(a,8).hex()for base in(0x80d8d58,0x80d8d28,0x80d8d48,0x80d8d18)for a in(base,base+8)],control_after=reg('fctrl'));records.append(r)
  return False
for a in(0x8087d14,0x8053e00):Observe('*'+hex(a),internal=True)
end
run -g -t process.tek -x input.asit < answers.txt
python
signal=0
if gdb.selected_inferior().pid:signal=int(gdb.parse_and_eval('$_siginfo.si_signo'));gdb.execute('kill',to_string=True)
open('raw.json','w').write(json.dumps(dict(records=records,nodes=nodes,signal=signal,pending=sum(map(len,pending.values())))))
end
quit
'''


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--reference',type=Path,required=True);p.add_argument('--library-path',required=True);a=p.parse_args();ref=a.reference.resolve();original=ref/'run/asitic.linux.2.2'
 for path,expected in((original,ORIGINAL_SHA256),(ref/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so',LEGACY_SHA256)):
  if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise ValueError('Unexpected original checksum')
 parent=ROOT/'tests/fixtures/paired_interactive_bounds_original.json.gz';f=json.loads(gzip.decompress(parent.read_bytes()));records=[]
 with tempfile.TemporaryDirectory(prefix='pyasitic-original-paired-input-models-')as d:
  root=Path(d);(root/'tap.cpp').write_text(TAP);subprocess.run(['g++','-m32','-O2','-fPIC','-shared','-nostdlib','-fno-builtin',str(root/'tap.cpp'),'/lib/i386-linux-gnu/libc.so.6','-o',str(root/'tap.so')],check=True)
  for ordinal,index in enumerate((2,6,18)):
   c=f['cases'][index];parameters=dict(c['parameters'],x=40.,y=40.);technology=c['technology']
   for key,value in(('chipx',256),('chipy',256),('fftx',128),('ffty',128)):technology=re.sub(rf'(?im)^(\s*{key}\s*=\s*)[\d.]+',rf'\g<1>{value}',technology)
   first,second=[w['name']for w in c['windings']];frequency=[.1234567,1.23456789,2.34567891][ordinal];text=format(frequency,'.17g');stdin=answers(c['kind'],parameters)
   script='CELL 1000 1000 1000\nCCELL 1000 1000\nEDDY OFF\n'+c['script']+f'CALCTRANS {first} {second} {text}\n2PORTTRANS {first} {second} {text} {text} 1 S RECT s.out\n';work=root/str(index);work.mkdir()
   for name,value in(('process.tek',technology),('input.asit',script),('answers.txt',stdin),('capture.gdb',COMMANDS.replace('TAP_PATH',str(root/'tap.so')))):(work/name).write_text(value)
   run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=a.library_path),capture_output=True,text=True,start_new_session=True,timeout=180)
   if run.returncode or not(work/'raw.json').exists()or'Python Exception'in run.stderr or'Traceback'in run.stderr:raise RuntimeError(c['label']+': '+run.stdout[-2200:]+run.stderr[-1500:])
   raw=json.loads((work/'raw.json').read_text());data=(work/'transformer-raw.out').read_bytes()if(work/'transformer-raw.out').exists()else b''
   records.append(dict(parent_index=index,label=c['label'],request=dict(action='calctrans',kind=c['kind'],parameters=parameters,native_interactive=True,native_mesh=True,technology=technology,frequency_ghz=frequency,first_winding=0,second_winding=1,eddy=False,termination_ohm=0,mesh={k:1000 for k in('length_cell','width_cell','thickness_cell','capacitance_length_cell','capacitance_width_cell')}),script=script,stdin=stdin,stdout=run.stdout,stderr=run.stderr,raw_output_bits=[data[i:i+8].hex()for i in range(0,len(data),8)],**raw));print(index,c['label'],'signal',raw['signal'],'SI words',len(data)//8,'S events',len(raw['records']),flush=True)
 result=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,parent_sha256=hashlib.sha256(parent.read_bytes()).hexdigest(),tap=TAP,gdb_commands=COMMANDS,reference='Unchanged complete original interactive TRANS/BALUN -> CALCTRANS/2PORTTRANS histories. SI Y/Z/model globals observed before sprintf formatting via a nonnumerical output observer; read-only node and actual scattering entry/return observers. No numerical instructions/inputs changed. All selected capacity-boundary cases, including native nonfinite results, retained.',cases=records)
 with gzip.GzipFile(str(ROOT/'tests/fixtures/paired_interactive_bounds_sessions_original.json.gz'),'wb',mtime=0)as out:out.write((json.dumps(result,separators=(',',':'),allow_nan=False)+'\n').encode())

if __name__=='__main__':main()
