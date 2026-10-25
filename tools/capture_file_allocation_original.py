"""Independent native stdin buffer allocation before/after malloc boundaries."""
import argparse,hashlib,sys
from pathlib import Path
import capture_dispatch_storage_original as dispatch
import capture_input_transition_original as parent
import capture_trailing_via_heap_original as lifetime
from capture_statx_metadata import OBSERVER as STATX

ROOT=Path(__file__).resolve().parents[1]
OBSERVER=dispatch.transition.COMMON+'\n'+dispatch.ELF_PLT+'\n'+STATX+r'''
allocation_calls=[];allocation_current=None;allocation_active=False;allocation_seen=False;allocation_next=None;allocation_exit=None;allocation_exit_signal=0
def allocation_context():
 block=gdb.block_for_pc(int(gdb.parse_and_eval('&_dl_lookup_symbol_x')));typ=gdb.lookup_type('struct link_map',block);assert typ.sizeof==632
 main=u32(int(gdb.parse_and_eval('&_r_debug'))+4);ctx=plt_inputs(main,typ);ctx['main_map']=main
 for item in ctx['maps']:item['plt']=elf_plt(item['name']or'/proc/%d/exe'%gdb.selected_inferior().pid,u32(item['address']))
 base=u32(next(x['address']for x in ctx['maps']if x['name'].endswith('/libc.so.6')));got=base+0x22fe34;file=u32(reg('esp')+4)
 ctx['regions']+=[dict(address=p,data=mem(p,n).hex())for p,n in ((file,152),(u32(file+148),84),(got+0x1a30,4),(got+0x1c4,4),(u32(ctx['tls_base']+16),32))]
 st=os.stat('/proc/%d/fd/0'%gdb.selected_inferior().pid)
 ctx['profile']=dict(stdin_stat={name:getattr(st,name)for name in ('st_mode','st_blksize')},statx=statx_metadata())
 return ctx
def allocation_state(ctx):
 return dict(registers=registers(),xstate=regset(0x202).hex(),regions=[dict(address=r['address'],data=mem(r['address'],len(r['data'])//2).hex())for r in ctx['regions']])
class AllocationPoint(gdb.Breakpoint):
 def __init__(self,spec,kind,return_pc=None):self.kind=kind;self.return_pc=return_pc;super().__init__(spec,internal=True)
 def stop(self):
  if allocation_current is None or self.kind in allocation_current:return False
  if self.return_pc is not None and u32(reg('esp'))!=self.return_pc:return False
  allocation_current[self.kind]=allocation_state(allocation_current['entry']);return False
class AllocationEntry(gdb.Breakpoint):
 def stop(self):
  global allocation_current
  if not allocation_active or u32(u32(reg('esp')+4)+56)!=0:return False
  env=environment();ctx=allocation_context();ctx.update(registers=registers(),xstate=regset(0x202).hex(),environment=env)
  allocation_current=dict(entry=ctx);allocation_calls.append(allocation_current)
  base=u32(next(x['address']for x in ctx['maps']if x['name'].endswith('/libc.so.6')))
  AllocationPoint('__libc_malloc','malloc',base+0x75523)
  AllocationPoint('*'+hex(base+0x75523),'allocated')
  AllocationPoint('*'+hex(u32(reg('esp'))),'return');return False
class AllocationDriverReturn(gdb.Breakpoint):
 def stop(self):
  global allocation_active
  allocation_active=True;return False
class AllocationDriver(gdb.Breakpoint):
 def stop(self):
  global allocation_seen,allocation_next
  if allocation_active:allocation_next=dict(pc=reg('pc'),esp=reg('esp'));return True
  if not allocation_seen:allocation_seen=True;AllocationDriverReturn('*'+hex(u32(reg('esp'))),internal=True,temporary=True)
  return False
for pc in (0x8050b2c,0x8051280):AllocationDriver('*'+hex(pc),internal=True)
AllocationEntry('_IO_doallocbuf',internal=True)
def allocation_exited(event):
 global allocation_exit,allocation_exit_signal
 allocation_exit=getattr(event,'exit_code',None)
 if allocation_exit is None:
  try:allocation_exit_signal=int(gdb.parse_and_eval('$_exitsignal'))
  except gdb.error:pass
gdb.events.exited.connect(allocation_exited)
'''


def commands(directory):
    return ('set pagination off\nset confirm off\nset debuginfod enabled off\nset breakpoint pending on\nset debug-file-directory '+str(directory)+'\nhandle SIGQUIT nostop noprint pass\npython\n'+OBSERVER+
            '\nend\nrun -g -t process.tek -x input.asit < answers.txt\npython\nsignal=allocation_exit_signal\n'
            'if allocation_next is None and gdb.selected_inferior().pid:\n try:signal=int(gdb.parse_and_eval("$_siginfo.si_signo"))\n except gdb.error:pass\n'
            'result=dict(allocation_calls=allocation_calls,next_driver=allocation_next,native_exit=allocation_exit,events=[],node=None,signal=signal)\nopen("heap.json","w").write(json.dumps(result))\n'
            'if gdb.selected_inferior().pid:gdb.execute("kill",to_string=True)\nend\nquit\n')


def jobs():
    for job in parent.jobs():
        job['parent']=ROOT/'tests/fixtures/input_transition_original.json.gz';yield job


def main():
    p=argparse.ArgumentParser(add_help=False);p.add_argument('--debug-directory',type=Path,required=True);own,remaining=p.parse_known_args();sys.argv=[sys.argv[0],*remaining];blobs={}
    def project(case):
        for call in case['allocation_calls']:
            for point in call.values():
                for r in point['regions']:
                    raw=bytes.fromhex(r.pop('data'));key=hashlib.sha256(raw).hexdigest();blobs[key]=raw.hex();r.update(size=len(raw),sha256=key)
        return case
    lifetime.main(commands=commands(own.debug_directory),fixture_name='file_allocation_original.json.gz',job_factory=jobs,case_transform=project,finalize_metadata=lambda:dict(loader_regions=blobs),
        extra_metadata=dict(file_allocation_provenance=dict(observer=OBSERVER,reference='All unchanged 134 jobs retained. Complete doallocbuf entry, malloc entry, post-malloc and doallocbuf return regions/registers/XSAVE are independent boundaries. Earlier external statx facts are queried separately before the native stat call. No later native stat buffer is an input. No inferior result, instruction, register, allocation or memory is substituted. Minimal environment guards precede capture; no per-call snapshot seeds continuing replay.')))


if __name__=='__main__':main()
