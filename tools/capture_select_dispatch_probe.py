"""Independent native select64 null/normalized/time64/overflow/EINVAL inputs."""
import argparse,gzip,hashlib,json,subprocess,tempfile
from pathlib import Path
import capture_poll_storage_original as parent
from capture_printf_integer_original import PROBE as STARTUP,LIBC_SHA256

ROOT=Path(__file__).resolve().parents[1]


def requests():
    values=[(0,0,True),(0,0,False),(0,100,False),(1,999999,False),(1,1000000,False),(0x7fffffff,0x7fffffff,False),(0x80000000,0,False),(0x7fffffffffffffff,0x7fffffff,False),(0x7fffffff00000000,1,False),(-1,0,False),(0,-1,False),(-0x8000000000000000,0,False),(0,0x7fffffff,False)]
    return [dict(seconds=s,microseconds=u,null_timeout=n)for s,u,n in values]


def source():
    rows=',\n'.join('{%su,%su,%su,%su}'%(r['seconds']&0xffffffff,(r['seconds']>>32)&0xffffffff,r['microseconds']&0xffffffff,int(r['null_timeout']))for r in requests())
    return r'''
struct tv64 { unsigned low,high; int micro,pad; };
extern int __select64(int,void *,void *,void *,struct tv64 *);
int main(void) {
 const unsigned rows[][4]={'''+rows+r'''};
 for(unsigned i=0;i<sizeof(rows)/sizeof(rows[0]);i++) {
  unsigned readfds[32]={1};struct tv64 timeout={rows[i][0],rows[i][1],(int)rows[i][2],0};
  volatile int result=__select64(1,readfds,0,0,rows[i][3]?0:&timeout);(void)result;
 }
 return 0;
}
'''+STARTUP[STARTUP.index('__asm__('):]


OBSERVER=parent.OBSERVER.split('poll_calls=[]',1)[0]+'def poll_context():'+parent.OBSERVER.split('def poll_context():',1)[1].split('class PollPoint',1)[0]+r'''
probe_calls=[];probe_current=None;probe_exit=None
class ProbeAfter(gdb.Breakpoint):
 def __init__(self,pc,kind):self.kind=kind;super().__init__('*'+hex(pc),internal=True)
 def stop(self):
  if probe_current is None or'after'in probe_current:return False
  s=probe_current['entry']['registers']['esp']
  if self.kind=='syscall'and reg('esp')!=s-128:return False
  if self.kind=='return'and reg('esp')!=s+4:return False
  probe_current['boundary']=self.kind;probe_current['after']=poll_state(probe_current['entry']);return False
class ProbeEntry(gdb.Breakpoint):
 def stop(self):
  global probe_current
  context=poll_context();context.update(registers=registers(),xstate=regset(0x202).hex(),environment=environment())
  base=u32(next(m['address']for m in context['maps']if m['name'].endswith('/libc.so.6')));got=base+0x22fe34
  for p in(got+0xa0,(u32(context['tls_base'])+u32(got+0xa0))&0xffffffff):context['regions'].append(dict(address=p,data=mem(p,4).hex()))
  probe_current=dict(entry=context);probe_calls.append(probe_current);ProbeAfter(u32(reg('esp')),'return');return False
class ProbeMain(gdb.Breakpoint):
 def stop(self):
  context=poll_context();base=u32(next(m['address']for m in context['maps']if m['name'].endswith('/libc.so.6')))
  ProbeEntry('*'+hex(base+0x120f90),internal=True);ProbeAfter(base+0x117bb0,'syscall');ProbeVDSO(u32(context['tls_base']+16),base);return False
class ProbeVDSO(gdb.Breakpoint):
 def __init__(self,pc,base):self.base=base;super().__init__('*'+hex(pc),internal=True)
 def stop(self):
  if probe_current is None or probe_current.get('boundary')!='syscall'or'vdso'in probe_current or u32(reg('esp'))!=self.base+0x117bc2:return False
  probe_current['vdso']=poll_state(probe_current['entry']);return False
ProbeMain('main',internal=True)
def probe_exited(event):
 global probe_exit
 probe_exit=getattr(event,'exit_code',None)
gdb.events.exited.connect(probe_exited)
'''


def commands(directory):
    return ('set pagination off\nset confirm off\nset debuginfod enabled off\nset breakpoint pending on\nset debug-file-directory '+str(directory)+'\npython\n'+OBSERVER+'\nend\nrun < answers.txt\npython\nopen("probe.json","w").write(json.dumps(dict(calls=probe_calls,native_exit=probe_exit)))\nend\nquit\n')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cc',default='cc');p.add_argument('--debug-directory',type=Path,required=True);p.add_argument('--libc',type=Path,default=Path('/lib/i386-linux-gnu/libc.so.6'));p.add_argument('--output',type=Path,default=ROOT/'tests/fixtures/select_dispatch_probe.json.gz');args=p.parse_args();libc=args.libc.resolve()
    if hashlib.sha256(libc.read_bytes()).hexdigest()!=LIBC_SHA256:raise ValueError('Probe libc differs from original')
    program=source();gdb_commands=commands(args.debug_directory);env=parent.lifetime.native_environment(str(libc.parent));blobs={}
    with tempfile.TemporaryDirectory(prefix='pyasitic-select-dispatch-')as directory:
        d=Path(directory);binary=d/'probe';(d/'probe.c').write_text(program);(d/'capture.gdb').write_text(gdb_commands);(d/'answers.txt').write_bytes(b'input\n')
        command=[args.cc,'-m32','-O2','-std=c11','-fno-builtin','-fno-pie','-no-pie','-nostdlib',str(d/'probe.c'),str(libc),'-Wl,-e,_start','-Wl,--dynamic-linker=/lib/i386-linux-gnu/ld-linux.so.2','-o',str(binary)]
        built=subprocess.run(command,capture_output=True,text=True,check=True)
        with(d/'answers.txt').open('rb')as stdin:plain=subprocess.run([str(binary)],cwd=d,env=env,stdin=stdin,capture_output=True,check=True,start_new_session=True,timeout=60)
        native=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(binary)],cwd=d,env=env,capture_output=True,text=True,check=True,start_new_session=True,timeout=180)
        if 'Python Exception'in native.stderr:raise ValueError(native.stderr)
        captured=json.loads((d/'probe.json').read_text())
        if captured['native_exit']!=0 or len(captured['calls'])!=len(requests())or any('after'not in c for c in captured['calls']):raise ValueError('Incomplete select dispatch probe')
        for call in captured['calls']:
            for phase in('entry','after','vdso'):
                if phase not in call:continue
                for r in call[phase]['regions']:
                    raw=bytes.fromhex(r.pop('data'));key=hashlib.sha256(raw).hexdigest();blobs[key]=raw.hex();r.update(size=len(raw),sha256=key)
        record=dict(libc_sha256=LIBC_SHA256,source=program,source_sha256=hashlib.sha256(program.encode()).hexdigest(),requests=requests(),compile_command=command,compile_stderr=built.stderr,executable_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),gdb_commands=gdb_commands,observer=OBSERVER,environment=env,plain=dict(returncode=plain.returncode,stdout=plain.stdout.hex(),stderr=plain.stderr.hex()),native=dict(stdout=native.stdout,stderr=native.stderr),native_exit=captured['native_exit'],cases=[dict(label='independent-select64-dispatch',cache_mode='native',signal=0,poll_calls=captured['calls'])],loader_regions=blobs)
    with gzip.GzipFile(str(args.output),'wb',mtime=0)as stream:stream.write((json.dumps(record,separators=(',',':'))+'\n').encode())
    print(len(requests()),'complete independent select64 dispatch calls',args.output)


if __name__=='__main__':main()
