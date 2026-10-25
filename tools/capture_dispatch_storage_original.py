"""Unchanged dispatch history, normalization and quit caller ABI boundaries."""
import argparse,hashlib,os,sys
from pathlib import Path
import capture_loader_transition_original as transition

ROOT=Path(__file__).resolve().parents[1]
ELF_PLT='def elf_plt('+transition.OBSERVER.split('def elf_plt(',1)[1].split('_loader_transition_snapshot',1)[0]
OBSERVER=transition.COMMON+'\n'+ELF_PLT+r'''
dispatch_calls=[];dispatch_current=None;dispatch_active=False;dispatch_seen=False;dispatch_next=None;dispatch_exit=None;dispatch_exit_signal=0
def dispatch_context():
 block=gdb.block_for_pc(int(gdb.parse_and_eval('&_dl_lookup_symbol_x')));typ=gdb.lookup_type('struct link_map',block);assert typ.sizeof==632
 main=u32(int(gdb.parse_and_eval('&_r_debug'))+4);context=plt_inputs(main,typ);context['main_map']=main
 for item in context['maps']:
  item['plt']=elf_plt(item['name']or'/proc/%d/exe'%gdb.selected_inferior().pid,u32(item['address']))
 context['characters']=dict(classification=mem(u32(0x80d7dd8)-256,768).hex(),uppercase=mem(u32(0x80d7dc0)-512,1536).hex(),lowercase=mem(u32(0x80d7cb0)-512,1536).hex())
 return context
def dispatch_state(context):
 return dict(registers=registers(),xstate=regset(0x202).hex(),regions=[dict(address=r['address'],data=mem(r['address'],len(r['data'])//2).hex())for r in context['regions']])
class DispatchPoint(gdb.Breakpoint):
 def __init__(self,pc,kind):self.kind=kind;super().__init__('*'+hex(pc),internal=True)
 def stop(self):
  if dispatch_current is None or self.kind in dispatch_current:return False
  if self.kind=='parse'and u32(reg('esp'))!=0x804c5d8:return False
  if self.kind=='kill'and u32(reg('esp'))!=0x804c5eb:return False
  dispatch_current[self.kind]=dispatch_state(dispatch_current['entry']);return False
class DispatchEntry(gdb.Breakpoint):
 def stop(self):
  global dispatch_current
  if not dispatch_active:return False
  env=environment();context=dispatch_context();context.update(registers=registers(),xstate=regset(0x202).hex(),environment=env)
  dispatch_current=dict(entry=context);dispatch_calls.append(dispatch_current)
  base=u32(next(m['address']for m in context['maps']if m['name'].endswith('/libc.so.6')));DispatchPoint(base+0x3c390,'kill');return False
class DispatchDriverReturn(gdb.Breakpoint):
 def stop(self):
  global dispatch_active
  dispatch_active=True;return False
class DispatchDriver(gdb.Breakpoint):
 def stop(self):
  global dispatch_seen,dispatch_next
  if dispatch_active:dispatch_next=dict(pc=reg('pc'),esp=reg('esp'));return True
  if not dispatch_seen:dispatch_seen=True;DispatchDriverReturn('*'+hex(u32(reg('esp'))),internal=True,temporary=True)
  return False
for pc in (0x8050b2c,0x8051280):DispatchDriver('*'+hex(pc),internal=True)
DispatchEntry('*0x804c598',internal=True)
for pc,kind in ((0x804c5c0,'history'),(0x8086fc0,'parse'),(0x804c5d8,'parsed')):DispatchPoint(pc,kind)
def dispatch_exited(event):
 global dispatch_exit,dispatch_exit_signal
 dispatch_exit=getattr(event,'exit_code',None)
 if dispatch_exit is None:
  try:dispatch_exit_signal=int(gdb.parse_and_eval('$_exitsignal'))
  except gdb.error:pass
gdb.events.exited.connect(dispatch_exited)
'''


def commands(debug_directory):
    return ('set pagination off\nset confirm off\nset debuginfod enabled off\nset breakpoint pending on\n'
            'set debug-file-directory '+str(debug_directory)+'\nhandle SIGQUIT nostop noprint pass\npython\n'+OBSERVER+
            '\nend\nrun -g -t process.tek -x input.asit < answers.txt\npython\n'
            'signal=dispatch_exit_signal\nif dispatch_next is None and gdb.selected_inferior().pid:\n'
            ' try:signal=int(gdb.parse_and_eval("$_siginfo.si_signo"))\n except gdb.error:pass\n'
            'result=dict(dispatch_calls=dispatch_calls,next_driver=dispatch_next,native_exit=dispatch_exit,events=[],node=None,signal=signal)\n'
            'open("heap.json","w").write(json.dumps(result))\n'
            'if gdb.selected_inferior().pid:gdb.execute("kill",to_string=True)\nend\nquit\n')


def jobs():
    for job in transition.jobs():
        job['parent']=ROOT/'tests/fixtures/loader_transition_original.json.gz';yield job


def main():
    parser=argparse.ArgumentParser(add_help=False);parser.add_argument('--debug-directory',type=Path,required=True);parser.add_argument('--reference',type=Path,required=True)
    own,remaining=parser.parse_known_args();sys.argv=[sys.argv[0],'--reference',str(own.reference),*remaining];blobs={}
    def project(case):
        for call in case['dispatch_calls']:
            for point in call.values():
                for r in point['regions']:
                    raw=bytes.fromhex(r.pop('data'));key=hashlib.sha256(raw).hexdigest();blobs[key]=raw.hex();r.update(size=len(raw),sha256=key)
        return case
    transition.plt.lookup.install.signals.lifetime.main(commands=commands(own.debug_directory),fixture_name='dispatch_storage_original.json.gz',job_factory=jobs,case_transform=project,finalize_metadata=lambda:dict(loader_regions=blobs),
        extra_metadata=dict(dispatch_storage_provenance=dict(observer=OBSERVER,history_shim_sha256=hashlib.sha256((own.reference/'run/libs/libreadline.so.3').read_bytes()).hexdigest(),reference='All unchanged 134 histories retained. Capture dispatch entry, post-history return, pre-parser entry, parser return and resolved kill target entry. Full stacks, earlier ELF/locale/TLS/registers/XSAVE at each operation entry are independent component inputs; later phase outputs are assertions only. The full continuing replay never loads these call snapshots. Native faults and histories without dispatch remain explicit. Minimal environment and guard precede capture. No inferior memory, instructions, registers, return values or allocation outcomes are replaced.')))


if __name__=='__main__':main()
