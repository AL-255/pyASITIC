"""Read-only legacy SIGQUIT delivery for every existing original history."""
import argparse,hashlib,json,os,subprocess,sys,tempfile
from pathlib import Path
import capture_trailing_via_heap_original as lifetime
from capture_prelude_storage_extended_original import jobs as extra_jobs

ROOT=Path(__file__).resolve().parents[1]
CPU_PROBE=r'''
#include <cpuid.h>
#include <stdio.h>
int main(void) {
 unsigned a,b,c,d,pkru=0;
 __cpuid_count(0xd,0,a,b,c,d);
 printf("{\"features\":%u,\"size\":%u,\"components\":[",a,b);
 int first=1;
 for(unsigned i=2;i<32;i++) if(a&(1u<<i)) {
  unsigned x,y,z,w;__cpuid_count(0xd,i,x,y,z,w);
  printf("%s{\"bit\":%u,\"offset\":%u,\"size\":%u}",first?"":",",i,y,x);first=0;
 }
 __cpuid_count(7,0,a,b,c,d);
 if(c&(1<<3)) __asm__ volatile("rdpkru":"=a"(pkru),"=d"(d):"c"(0));
 printf("],\"initial_pkru\":%u}\n",pkru);
}
'''
OBSERVER=r'''
import gdb,ctypes,struct,json,os
arrivals=[];pending=None;action=None
libc=ctypes.CDLL(None,use_errno=True)
class Iovec(ctypes.Structure):_fields_=[('base',ctypes.c_void_p),('size',ctypes.c_size_t)]
def reg(k):return int(gdb.parse_and_eval('$'+k))&0xffffffff
def mem(a,n):return bytes(gdb.selected_inferior().read_memory(a,n))
def registers():return {k:reg(k)for k in ('eax','ebx','ecx','edx','esi','edi','ebp','esp','eip','eflags','cs','ss','ds','es','fs','gs','orig_eax')}
def regset(note):
 data=ctypes.create_string_buffer(65536);vec=Iovec(ctypes.addressof(data),len(data))
 if libc.ptrace(0x4204,gdb.selected_inferior().pid,note,ctypes.byref(vec)):raise OSError(ctypes.get_errno())
 return data.raw[:vec.size]
def mapping(name):
 for line in open('/proc/%d/maps'%gdb.selected_inferior().pid):
  if line.split()[-1]==name:
   lo,hi=(int(s,16)for s in line.split()[0].split('-'));return dict(address=lo,data=mem(lo,hi-lo).hex())
 raise RuntimeError('Missing '+name+' mapping')
def mask():
 data=ctypes.create_string_buffer(8)
 if libc.ptrace(0x420a,gdb.selected_inferior().pid,8,ctypes.byref(data)):raise OSError(ctypes.get_errno())
 return int.from_bytes(data.raw,'little')
def environment():
 values={item.split(b'=',1)[0].decode():item.split(b'=',1)[1].decode()for item in open('/proc/%d/environ'%gdb.selected_inferior().pid,'rb').read().split(b'\0')if item}
 assert not set(values)-{'PATH','HOME','LANG','LC_ALL','LD_LIBRARY_PATH','TERM','INPUTRC','LINES','COLUMNS','PWD','SHLVL','_'}
 return values
def action_snapshot():
 global action
 if reg('eax')==0xffffffda and reg('ebx')==3 and reg('ecx'):
  handler,flags,restorer,low,high=struct.unpack('<5I',mem(reg('ecx'),20))
  action=dict(handler=handler,flags=flags,restorer=restorer,mask=low|(high<<32))
def before_signal():
 global pending
 if action is None:raise RuntimeError('Missing earlier SIGQUIT action')
 env=environment()
 pending=dict(registers=registers(),stack=mapping('[stack]'),vdso=mapping('[vdso]'),mask=mask(),xstate=regset(0x202).hex(),fpregs=regset(2).hex(),action=dict(action),environment=env,number=3,thread=dict(trapno=1,error_code=0,cr2=0))
class KillStep(gdb.Breakpoint):
 def stop(self):return False
# Stepping over this breakpoint on the unchanged kill PLT instruction
# establishes the earlier debug-trap thread state (trap 1, error 0).
KillStep('*0x804ade4',internal=True)
class Arrival(gdb.Breakpoint):
 def stop(self):
  global pending
  if pending is None:raise RuntimeError('Handler without an earlier delivery input')
  arrivals.append(dict(before=pending,after=dict(registers=registers(),stack=mapping('[stack]'),mask=mask(),xstate=regset(0x202).hex())))
  pending=None;return False
Arrival('*0x804c33c',internal=True)
'''


def commands():
    return ('set pagination off\nset confirm off\nset debuginfod enabled off\npython\n'+OBSERVER+
            '\nend\ncatch syscall rt_sigaction\ncommands\nsilent\npython action_snapshot()\ncontinue\nend\n'
            'catch signal SIGQUIT\ncommands\nsilent\npython before_signal()\ncontinue\nend\n'
            'run -g -t process.tek -x input.asit < answers.txt\npython\n'
            'signal=0\nif gdb.selected_inferior().pid:\n'
            ' try:signal=int(gdb.parse_and_eval("$_siginfo.si_signo"))\n except gdb.error:pass\n'
            'result=dict(arrivals=arrivals,signal_pending=pending,events=[],node=None,signal=signal)\n'
            'open("heap.json","w").write(json.dumps(result))\n'
            'if gdb.selected_inferior().pid:gdb.execute("kill",to_string=True)\nend\nquit\n')


def jobs():
    for factory,parent in ((lifetime.jobs,'command_transition_original.json.gz'),(extra_jobs,'command_transition_extended_original.json.gz')):
        for job in factory():
            job['parent']=ROOT/'tests/fixtures'/parent;yield job


def main():
    parser=argparse.ArgumentParser(add_help=False);parser.add_argument('--cc',default='cc')
    own,remaining=parser.parse_known_args();sys.argv=[sys.argv[0],*remaining]
    with tempfile.TemporaryDirectory(prefix='pyasitic-signal-cpu-')as directory:
        binary=Path(directory)/'probe'
        subprocess.run([own.cc,'-x','c','-','-o',str(binary)],input=CPU_PROBE,text=True,check=True)
        cpu=json.loads(subprocess.check_output([str(binary)],env=lifetime.native_environment(''),text=True))
    lifetime.main(commands=commands(),fixture_name='signal_frames_original.json.gz',job_factory=jobs,
                  extra_metadata=dict(signal_frame_provenance=dict(observer=OBSERVER,cpu_probe=CPU_PROBE,cpu_probe_sha256=hashlib.sha256(CPU_PROBE.encode()).hexdigest(),cpu=cpu,kernel_release=os.uname().release,kernel_notes_sha256=hashlib.sha256(Path('/sys/kernel/notes').read_bytes()).hexdigest(),reference='All 134 existing jobs and native terminal outcomes retained. Only PTRACE GETREGSET/GETSIGMASK, procfs reads and GDB stops are used. The unchanged kill PLT step establishes debug trap 1/error 0; this original has no earlier handled memory fault, so thread CR2 remains its zero bootstrap value. Interrupted registers/XSAVE, action, mask, stack and VDSO are earlier inputs to the independent signal ABI comparison. Handler memory/registers are outputs, never continuation seeds. This does not resolve the separate continuing command-history gate.')))


if __name__=='__main__':main()
