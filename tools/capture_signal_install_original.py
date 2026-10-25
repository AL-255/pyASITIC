"""Read-only BSD signal-wrapper entry/return stacks for all original jobs."""
import argparse,hashlib,os,sys
from pathlib import Path
import capture_signal_frames_original as signals

ROOT=Path(__file__).resolve().parents[1]
COMMON=signals.OBSERVER.split('def action_snapshot():',1)[0]
OBSERVER=COMMON+r'''
bsd_calls=[];bsd_pending={};native_exit=None
def u32(a):return struct.unpack('<I',mem(a,4))[0]
def libc_base():
 for line in open('/proc/%d/maps'%gdb.selected_inferior().pid):
  p=line.split()
  if p[-1].endswith('/libc.so.6')and int(p[2],16)==0:return int(p[0].split('-')[0],16)
 raise RuntimeError('Missing libc base')
def dispositions(sig):
 values=dict(line.split(':',1)for line in open('/proc/%d/status'%gdb.selected_inferior().pid)if ':'in line)
 caught,ignored=int(values['SigCgt'],16),int(values['SigIgn'],16);bit=1<<(sig-1)
 if caught&bit:raise RuntimeError('Previously caught signal requires earlier action state')
 return dict(caught=caught,ignored=ignored),dict(handler=1 if ignored&bit else 0,flags=0,restorer=0,mask=0)
class BsdReturn(gdb.Breakpoint):
 def __init__(self,pc):self.pc=pc;super().__init__('*'+hex(pc),internal=True)
 def stop(self):
  if self.pc in bsd_pending:
   item=bsd_pending.pop(self.pc);item['after']=dict(registers=registers(),stack=mapping('[stack]'),xstate=regset(0x202).hex())
  return False
for pc in (0x804c23b,0x804c26c,0x804c29c):BsdReturn(pc)
class BsdEntry(gdb.Breakpoint):
 def stop(self):
  s=reg('esp');pc=u32(s)
  if pc not in (0x804c23b,0x804c26c,0x804c29c):return False
  env=environment();base=libc_base();sig=u32(s+4);status,old=dispositions(sig)
  item=dict(before=dict(registers=registers(),stack=mapping('[stack]'),main_frame=u32(reg('ebp')),libc_base=base,intr_mask=int.from_bytes(mem(base+0x231100,8),'little'),old_action=old,dispositions=status,xstate=regset(0x202).hex(),environment=env))
  bsd_calls.append(item);bsd_pending[pc]=item;return False
BsdEntry('__bsd_signal',internal=True)
def exited(event):
 global native_exit
 native_exit=event.exit_code
gdb.events.exited.connect(exited)
'''


def commands(debug_directory):
    return ('set pagination off\nset confirm off\nset debuginfod enabled off\nset breakpoint pending on\n'
            'set debug-file-directory '+str(debug_directory)+'\nhandle SIGQUIT nostop noprint pass\npython\n'+OBSERVER+
            '\nend\nrun -g -t process.tek -x input.asit < answers.txt\npython\n'
            'signal=0\nif gdb.selected_inferior().pid:\n'
            ' try:signal=int(gdb.parse_and_eval("$_siginfo.si_signo"))\n except gdb.error:pass\n'
            'result=dict(bsd_calls=bsd_calls,bsd_pending=len(bsd_pending),native_exit=native_exit,events=[],node=None,signal=signal)\n'
            'open("heap.json","w").write(json.dumps(result))\n'
            'if gdb.selected_inferior().pid:gdb.execute("kill",to_string=True)\nend\nquit\n')


def jobs():
    for job in signals.jobs():
        job['parent']=ROOT/'tests/fixtures/signal_frames_original.json.gz';yield job


def main():
    parser=argparse.ArgumentParser(add_help=False);parser.add_argument('--debug-directory',type=Path,required=True);parser.add_argument('--libc',type=Path,default=Path('/lib/i386-linux-gnu/libc.so.6'))
    own,remaining=parser.parse_known_args();sys.argv=[sys.argv[0],*remaining]
    signals.lifetime.main(commands=commands(own.debug_directory),fixture_name='signal_install_original.json.gz',job_factory=jobs,
        extra_metadata=dict(signal_install_provenance=dict(observer=OBSERVER,libc_sha256=hashlib.sha256(own.libc.read_bytes()).hexdigest(),kernel_release=os.uname().release,reference='All unchanged original jobs and terminal outcomes retained. Observe BSD signal entry after PLT resolution and return before the caller executes its next instruction. Stack, registers, startup argv/auxv, libc base and siginterrupt mask are earlier component inputs. Uncaught default/ignored dispositions are derived from the earlier proc status under the fresh executable launch; other caught actions are rejected. Guard derives from AT_RANDOM, not a later canary observation. Complete return stack and registers are outputs only. No inferior memory, registers, instructions or allocation results are replaced. This component boundary is not loaded into the continuing driver replay.')))


if __name__=='__main__':main()
