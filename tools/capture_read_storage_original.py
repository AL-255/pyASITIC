"""Unchanged original stdin read entry/return and external descriptor inputs."""
import argparse,hashlib,sys
from pathlib import Path
import capture_dispatch_storage_original as dispatch
import capture_malloc_transition_original as parent
import capture_trailing_via_heap_original as lifetime

ROOT=Path(__file__).resolve().parents[1]
DESCRIPTOR=r'''
def stdin_position():
 fields=dict(line.split(':',1)for line in open('/proc/%d/fdinfo/0'%gdb.selected_inferior().pid))
 return int(fields['pos'])
'''
OBSERVER=dispatch.transition.COMMON+'\n'+dispatch.ELF_PLT+DESCRIPTOR+r'''
read_calls=[];read_active=False;read_seen=False;read_next=None;read_exit=None;read_exit_signal=0
def read_context():
 block=gdb.block_for_pc(int(gdb.parse_and_eval('&_dl_lookup_symbol_x')));typ=gdb.lookup_type('struct link_map',block);assert typ.sizeof==632
 main=u32(int(gdb.parse_and_eval('&_r_debug'))+4);ctx=plt_inputs(main,typ);ctx['main_map']=main
 for item in ctx['maps']:item['plt']=elf_plt(item['name']or'/proc/%d/exe'%gdb.selected_inferior().pid,u32(item['address']))
 file=u32(reg('esp')+4);sysinfo=u32(ctx['tls_base']+16)
 ctx['regions']+=[mapping('[heap]'),dict(address=file,data=mem(file,152).hex()),dict(address=sysinfo,data=mem(sysinfo,32).hex())]
 ctx['external_stdin']=dict(data=open('/proc/%d/fd/0'%gdb.selected_inferior().pid,'rb').read().hex(),position=stdin_position())
 return ctx
def read_state(ctx):
 return dict(registers=registers(),xstate=regset(0x202).hex(),position=stdin_position(),regions=[dict(address=r['address'],data=mem(r['address'],len(r['data'])//2).hex())for r in ctx['regions']])
class ReadReturn(gdb.Breakpoint):
 def __init__(self,pc,item):self.item=item;super().__init__('*'+hex(pc),internal=True,temporary=True)
 def stop(self):
  self.item['after']=read_state(self.item['before']);return False
class ReadEntry(gdb.Breakpoint):
 def stop(self):
  if not read_active or u32(u32(reg('esp')+4)+56)!=0:return False
  env=environment();ctx=read_context();ctx.update(registers=registers(),xstate=regset(0x202).hex(),environment=env)
  item=dict(before=ctx);read_calls.append(item);ReadReturn(u32(reg('esp')),item);return False
class ReadDriverReturn(gdb.Breakpoint):
 def stop(self):
  global read_active
  read_active=True;return False
class ReadDriver(gdb.Breakpoint):
 def stop(self):
  global read_seen,read_next
  if read_active:read_next=dict(pc=reg('pc'),esp=reg('esp'));return True
  if not read_seen:read_seen=True;ReadDriverReturn('*'+hex(u32(reg('esp'))),internal=True,temporary=True)
  return False
for pc in (0x8050b2c,0x8051280):ReadDriver('*'+hex(pc),internal=True)
ReadEntry('_IO_file_read',internal=True)
def read_exited(event):
 global read_exit,read_exit_signal
 read_exit=getattr(event,'exit_code',None)
 if read_exit is None:
  try:read_exit_signal=int(gdb.parse_and_eval('$_exitsignal'))
  except gdb.error:pass
gdb.events.exited.connect(read_exited)
'''


def commands(directory):
    return ('set pagination off\nset confirm off\nset debuginfod enabled off\nset breakpoint pending on\nset debug-file-directory '+str(directory)+'\nhandle SIGQUIT nostop noprint pass\npython\n'+OBSERVER+
            '\nend\nrun -g -t process.tek -x input.asit < answers.txt\npython\nsignal=read_exit_signal\n'
            'if read_next is None and gdb.selected_inferior().pid:\n try:signal=int(gdb.parse_and_eval("$_siginfo.si_signo"))\n except gdb.error:pass\n'
            'result=dict(read_calls=read_calls,next_driver=read_next,native_exit=read_exit,events=[],node=None,signal=signal)\nopen("heap.json","w").write(json.dumps(result))\n'
            'if gdb.selected_inferior().pid:gdb.execute("kill",to_string=True)\nend\nquit\n')


def jobs():
    for job in parent.jobs():
        job['parent']=ROOT/'tests/fixtures/malloc_transition_original.json.gz';yield job


def main():
    p=argparse.ArgumentParser(add_help=False);p.add_argument('--debug-directory',type=Path,required=True);own,remaining=p.parse_known_args();sys.argv=[sys.argv[0],*remaining];blobs={}
    def project(case):
        for call in case['read_calls']:
            for point in call.values():
                for r in point['regions']:
                    raw=bytes.fromhex(r.pop('data'));key=hashlib.sha256(raw).hexdigest();blobs[key]=raw.hex();r.update(size=len(raw),sha256=key)
        return case
    lifetime.main(commands=commands(own.debug_directory),fixture_name='read_storage_original.json.gz',job_factory=jobs,case_transform=project,finalize_metadata=lambda:dict(loader_regions=blobs),
        extra_metadata=dict(read_storage_provenance=dict(observer=OBSERVER,reference='All unchanged 134 jobs retained. Complete stdin _IO_file_read entry/return regions/registers/XSAVE and actual external descriptor positions. Earlier external bytes are read through an independent open, not from a later program buffer. No inferior instruction, register, memory, syscall result, allocation or signal is replaced. Minimal environment guards precede capture; component snapshots never seed continuing replay.')))


if __name__=='__main__':main()
