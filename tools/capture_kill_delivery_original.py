"""Read-only full kill entry -> native SIGQUIT handler entry, all jobs."""
import argparse,gzip,hashlib,json,os,subprocess,sys,tempfile
from pathlib import Path
import capture_signal_frames_original as parent

ROOT=Path(__file__).resolve().parents[1]
OBSERVER=parent.OBSERVER+r'''
kill_calls=[];kill_current=None
def u32(p):return struct.unpack('<I',mem(p,4))[0]
def tls_base():
 desc=ctypes.create_string_buffer(16)
 if libc.ptrace(25,gdb.selected_inferior().pid,reg('gs')>>3,ctypes.byref(desc)):raise OSError(ctypes.get_errno())
 return struct.unpack_from('<I',desc.raw,4)[0]
def libc_base():
 for line in open('/proc/%d/maps'%gdb.selected_inferior().pid):
  p=line.split()
  if p[-1].endswith('/libc.so.6')and int(p[2],16)==0:return int(p[0].split('-')[0],16)
 raise RuntimeError('Missing libc base')
def kill_state(context):
 return dict(registers=registers(),xstate=regset(0x202).hex(),fpregs=regset(2).hex(),mask=mask(),regions=[dict(address=r['address'],data=mem(r['address'],len(r['data'])//2).hex())for r in context['regions']])
class KillBoundary(gdb.Breakpoint):
 def __init__(self,pc,kind,esp):self.kind=kind;self.esp=esp;super().__init__('*'+hex(pc),internal=True)
 def stop(self):
  if kill_current is None or self.kind in kill_current or reg('esp')!=self.esp:return False
  kill_current[self.kind]=kill_state(kill_current['entry']);return False
class KillEntry(gdb.Breakpoint):
 def stop(self):
  global kill_current
  base=libc_base()
  if reg('pc')!=base+0x3c390:return False
  if action is None:raise RuntimeError('kill before the earlier SIGQUIT action')
  env=environment();tls=tls_base();stack=mapping('[stack]');vdso=mapping('[vdso]');s=reg('esp');pc=u32(tls+16);code=mem(pc,12)
  if code.startswith(bytes.fromhex('0f1f0051525589cd0f05cd80')):offset=8
  elif code.startswith(bytes.fromhex('51525589e50f34cd805d5a59')):offset=5
  else:raise RuntimeError('Unrecognized earlier VDSO')
  stat=open('/proc/%d/stat'%gdb.selected_inferior().pid).read().rsplit(')',1)[1].split()
  process=dict(pid=gdb.selected_inferior().pid,pgrp=int(stat[2]),session=int(stat[3]))
  regions=[stack,vdso,dict(address=tls,data=mem(tls,32).hex())]
  context=dict(registers=registers(),xstate=regset(0x202).hex(),fpregs=regset(2).hex(),mask=mask(),regions=regions,libc_base=base,tls_base=tls,vdso=dict(address=vdso['address'],size=len(vdso['data'])//2),action=dict(action),number=u32(s+8),process=process,thread=dict(trapno=1,error_code=0,cr2=0),environment=env)
  kill_current=dict(entry=context);kill_calls.append(kill_current)
  KillBoundary(pc,'vdso',s-4);KillBoundary(pc+offset,'kernel',s-16);return False
KillEntry('kill',internal=True)
_kill_before_signal=before_signal
def before_signal():
 _kill_before_signal()
 if kill_current is None:raise RuntimeError('SIGQUIT without earlier kill entry')
 kill_current['interrupted']=kill_state(kill_current['entry'])
class KillHandler(gdb.Breakpoint):
 def stop(self):
  if kill_current is None:raise RuntimeError('Handler without earlier kill entry')
  kill_current['handler']=kill_state(kill_current['entry']);return False
KillHandler('*0x804c33c',internal=True)
'''


def commands():
    return parent.commands().replace(parent.OBSERVER,OBSERVER).replace('result=dict(arrivals=', 'result=dict(kill_calls=kill_calls,arrivals=')


def jobs():
    for job in parent.jobs():
        job['parent']=ROOT/'tests/fixtures/signal_frames_original.json.gz';yield job


def main():
    p=argparse.ArgumentParser(add_help=False);p.add_argument('--cc',default='cc');p.add_argument('--libc',type=Path,default=Path('/lib/i386-linux-gnu/libc.so.6'));p.add_argument('--output',type=Path,default=ROOT/'tests/fixtures/kill_delivery_original.json.gz');own,remaining=p.parse_known_args();sys.argv=[sys.argv[0],*remaining];blobs={}
    with tempfile.TemporaryDirectory(prefix='pyasitic-kill-delivery-cpu-')as directory:
        binary=Path(directory)/'probe';subprocess.run([own.cc,'-x','c','-','-o',str(binary)],input=parent.CPU_PROBE,text=True,check=True)
        cpu=json.loads(subprocess.check_output([str(binary)],env=parent.lifetime.native_environment(''),text=True,start_new_session=True))
    def project(case):
        for call in case['kill_calls']:
            for point in call.values():
                for r in point['regions']:
                    raw=bytes.fromhex(r.pop('data'));key=hashlib.sha256(raw).hexdigest();blobs[key]=raw.hex();r.update(size=len(raw),sha256=key)
        return case
    parent.lifetime.main(commands=commands(),fixture_name=str(own.output.resolve()),job_factory=jobs,case_transform=project,finalize_metadata=lambda:dict(loader_regions=blobs),
        extra_metadata=dict(kill_delivery_provenance=dict(observer=OBSERVER,cpu_probe=parent.CPU_PROBE,cpu_probe_sha256=hashlib.sha256(parent.CPU_PROBE.encode()).hexdigest(),cpu=cpu,libc_sha256=hashlib.sha256(own.libc.read_bytes()).hexdigest(),kernel_release=os.uname().release,kernel_notes_sha256=hashlib.sha256(Path('/sys/kernel/notes').read_bytes()).hexdigest(),reference='All unchanged 134 histories and their native outcomes. Earlier resolved kill entry owns actual GP/XSAVE, mask, prior installed action, process-group facts, thread debug-trap state, complete stack/VDSO and TLS controls. VDSO/syscall/interrupted/handler states are complete assertions, never operation inputs. The independent existing pre-signal/handler capture is retained too. No native instruction, register, memory, allocation, signal, CPU affinity or returned syscall result is substituted. These component snapshots do not initialize the continuing driver replay.')))


if __name__=='__main__':main()
