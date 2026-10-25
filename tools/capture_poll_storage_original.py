"""Read-only REPL polling and timeval-adapter boundaries, all histories."""
import argparse,hashlib,struct,subprocess,sys,tempfile
from pathlib import Path
import capture_dispatch_storage_original as dispatch
import capture_trailing_via_heap_original as lifetime

ROOT=Path(__file__).resolve().parents[1]
CPU_PROBE=r'''
typedef unsigned U;
void _start(void) {
 U rows[6][4];U n=0;
 for(U f=0;f<2;f++)for(U i=0;i<3;i++) {
  U value=(U[]){100,0x80000000,0x40000000}[i],input=value,before,after;
  __asm__ volatile("pushfl; popl %0":"=r"(before));
  before=(before&~16u)|(f*16u);
  __asm__ volatile("pushl %2; popfl; sarl $31,%0; pushfl; popl %1":"+r"(value),"=r"(after):"r"(before):"cc");
  rows[n][0]=input;rows[n][1]=before;rows[n][2]=value;rows[n][3]=after;n++;
 }
 __asm__ volatile("int $0x80"::"a"(4),"b"(1),"c"(rows),"d"(sizeof rows):"memory");
 __asm__ volatile("int $0x80"::"a"(1),"b"(0));
}
'''


def integer_cpu(cc):
    with tempfile.TemporaryDirectory(prefix='pyasitic-poll-cpu-')as directory:
        binary=Path(directory)/'probe'
        subprocess.run([cc,'-m32','-x','c','-','-nostdlib','-static','-fno-stack-protector','-fno-pic','-Wl,-e,_start','-o',str(binary)],input=CPU_PROBE,text=True,check=True)
        raw=subprocess.check_output([str(binary)],env=lifetime.native_environment(''),start_new_session=True)
    if len(raw)!=96:raise ValueError('Incomplete i386 SAR CPU observation')
    rows=[dict(zip(('input','flags_before','result','flags_after'),row))for row in struct.iter_unpack('<4I',raw)]
    af={row['flags_after']&16 for row in rows}
    if len(af)!=1:raise NotImplementedError('CPU has an input-dependent undefined SAR AF')
    return dict(probe=CPU_PROBE,observations=rows,sar31_af=af.pop())


OBSERVER=dispatch.transition.COMMON+'\n'+dispatch.ELF_PLT+r'''
poll_calls=[];poll_current=None;poll_active=False;poll_seen=False;poll_next=None;poll_exit=None;poll_exit_signal=0
def poll_context():
 block=gdb.block_for_pc(int(gdb.parse_and_eval('&_dl_lookup_symbol_x')));typ=gdb.lookup_type('struct link_map',block);assert typ.sizeof==632
 main=u32(int(gdb.parse_and_eval('&_r_debug'))+4);context=plt_inputs(main,typ);context['main_map']=main
 for item in context['maps']:
  item['plt']=elf_plt(item['name']or'/proc/%d/exe'%gdb.selected_inferior().pid,u32(item['address']))
 return context
def poll_state(context):
 return dict(registers=registers(),xstate=regset(0x202).hex(),regions=[dict(address=r['address'],data=mem(r['address'],len(r['data'])//2).hex())for r in context['regions']])
class PollPoint(gdb.Breakpoint):
 def __init__(self,pc,kind,return_pc):self.kind=kind;self.return_pc=return_pc;super().__init__('*'+hex(pc),internal=True)
 def stop(self):
  if poll_current is None or self.kind in poll_current or u32(reg('esp'))!=self.return_pc:return False
  poll_current[self.kind]=poll_state(poll_current['entry']);return False
class PollEntry(gdb.Breakpoint):
 def stop(self):
  global poll_current
  if not poll_active:return False
  env=environment();context=poll_context();context.update(registers=registers(),xstate=regset(0x202).hex(),environment=env)
  poll_current=dict(entry=context);poll_calls.append(poll_current)
  base=u32(next(m['address']for m in context['maps']if m['name'].endswith('/libc.so.6')))
  PollPoint(base+0x121390,'select',0x804be06);PollPoint(base+0x120f90,'select64',base+0x1213f4);return False
class PollDriverReturn(gdb.Breakpoint):
 def stop(self):
  global poll_active
  poll_active=True;return False
class PollDriver(gdb.Breakpoint):
 def stop(self):
  global poll_seen,poll_next
  if poll_active:poll_next=dict(pc=reg('pc'),esp=reg('esp'));return True
  if not poll_seen:poll_seen=True;PollDriverReturn('*'+hex(u32(reg('esp'))),internal=True,temporary=True)
  return False
for pc in (0x8050b2c,0x8051280):PollDriver('*'+hex(pc),internal=True)
PollEntry('*0x804bdc4',internal=True)
def poll_exited(event):
 global poll_exit,poll_exit_signal
 poll_exit=getattr(event,'exit_code',None)
 if poll_exit is None:
  try:poll_exit_signal=int(gdb.parse_and_eval('$_exitsignal'))
  except gdb.error:pass
gdb.events.exited.connect(poll_exited)
'''


def commands(debug_directory):
    return ('set pagination off\nset confirm off\nset debuginfod enabled off\nset breakpoint pending on\n'
            'set debug-file-directory '+str(debug_directory)+'\nhandle SIGQUIT nostop noprint pass\npython\n'+OBSERVER+
            '\nend\nrun -g -t process.tek -x input.asit < answers.txt\npython\n'
            'signal=poll_exit_signal\nif poll_next is None and gdb.selected_inferior().pid:\n'
            ' try:signal=int(gdb.parse_and_eval("$_siginfo.si_signo"))\n except gdb.error:pass\n'
            'result=dict(poll_calls=poll_calls,next_driver=poll_next,native_exit=poll_exit,events=[],node=None,signal=signal)\n'
            'open("heap.json","w").write(json.dumps(result))\n'
            'if gdb.selected_inferior().pid:gdb.execute("kill",to_string=True)\nend\nquit\n')


def jobs():
    for job in dispatch.jobs():
        job['parent']=ROOT/'tests/fixtures/dispatch_storage_original.json.gz';yield job


def main():
    p=argparse.ArgumentParser(add_help=False);p.add_argument('--debug-directory',type=Path,required=True);p.add_argument('--libc',type=Path,default=Path('/lib/i386-linux-gnu/libc.so.6'));p.add_argument('--cc',default='cc')
    own,remaining=p.parse_known_args();sys.argv=[sys.argv[0],*remaining];blobs={};cpu=integer_cpu(own.cc)
    def project(case):
        for call in case['poll_calls']:
            for point in call.values():
                for r in point['regions']:
                    raw=bytes.fromhex(r.pop('data'));key=hashlib.sha256(raw).hexdigest();blobs[key]=raw.hex();r.update(size=len(raw),sha256=key)
        return case
    lifetime.main(commands=commands(own.debug_directory),fixture_name='poll_storage_original.json.gz',job_factory=jobs,case_transform=project,finalize_metadata=lambda:dict(loader_regions=blobs),
        extra_metadata=dict(integer_cpu=cpu,poll_storage_provenance=dict(observer=OBSERVER,libc_sha256=hashlib.sha256(own.libc.read_bytes()).hexdigest(),reference='All unchanged 134 histories retained. Capture native poll entry, resolved select target entry and select64 entry before the function executes. Full earlier stack/registers/ELF/TLS/XSAVE and an independent earlier i386 SAR CPU probe are component inputs; later states are assertions only. These snapshots never seed the continuing replay. Native faults and absent polling remain explicit. Minimal environment guard precedes capture. No inferior instructions, memory, registers, returned allocations or kernel results are substituted.')))


if __name__=='__main__':main()
