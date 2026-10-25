"""All native fflush boundaries and write effects after first driver return."""
import argparse,hashlib,sys
from pathlib import Path
import capture_dispatch_storage_original as dispatch
import capture_getline_transition_original as parent
import capture_trailing_via_heap_original as lifetime
from capture_getline_bytes_original import pack_region
from getline_fixture import pack_state

ROOT=Path(__file__).resolve().parents[1]
OBSERVER=dispatch.transition.COMMON+'\n'+dispatch.ELF_PLT+r'''
flush_calls=[];flush_current=None;flush_active=False;flush_seen=False;flush_next=None;flush_exit=None;flush_exit_signal=0
def flush_context():
 block=gdb.block_for_pc(int(gdb.parse_and_eval('&_dl_lookup_symbol_x')));typ=gdb.lookup_type('struct link_map',block);assert typ.sizeof==632
 main=u32(int(gdb.parse_and_eval('&_r_debug'))+4);ctx=plt_inputs(main,typ);ctx['main_map']=main
 for item in ctx['maps']:item['plt']=elf_plt(item['name']or'/proc/%d/exe'%gdb.selected_inferior().pid,u32(item['address']))
 base=u32(next(x['address']for x in ctx['maps']if x['name'].endswith('/libc.so.6')));got=base+0x22fe34
 ctx['regions']+=[mapping('[heap]'),dict(address=got+0x1a30,data=mem(got+0x1a30,4).hex()),dict(address=u32(ctx['tls_base']+16),data=mem(u32(ctx['tls_base']+16),32).hex())]
 files=[];file=u32(reg('esp')+4);pointer=u32(int(gdb.parse_and_eval('&_IO_list_all')));seen=set()
 if file:files.append(file)
 while pointer:
  assert pointer not in seen;seen.add(pointer)
  if pointer not in files:files.append(pointer)
  pointer=u32(pointer+52)
 ctx['streams']=[]
 for file in files:
  lock=u32(file+72);offset=struct.unpack('<b',mem(file+70,1))[0];vt=u32(file+148+offset)
  ctx['streams'].append(dict(address=file,lock=lock,vtable=vt))
  ctx['regions']+=[dict(address=p,data=mem(p,n).hex())for p,n in ((file,152),(lock,12),(vt,84))if p]
 return ctx
def flush_state(ctx):return dict(registers=registers(),xstate=regset(0x202).hex(),regions=[dict(address=r['address'],data=mem(r['address'],len(r['data'])//2).hex())for r in ctx['regions']])
class FlushReturn(gdb.Breakpoint):
 def __init__(self,pc,item):self.item=item;super().__init__('*'+hex(pc),internal=True)
 def stop(self):
  global flush_current
  if 'after'in self.item or reg('esp')!=self.item['before']['registers']['esp']+4:return False
  self.item['after']=flush_state(self.item['before']);flush_current=None;self.enabled=False;return False
class FlushEntry(gdb.Breakpoint):
 def stop(self):
  global flush_current
  if not flush_active:return False
  if flush_current is not None:raise RuntimeError('Nested fflush needs a nested observer')
  env=environment();ctx=flush_context();ctx.update(registers=registers(),xstate=regset(0x202).hex(),environment=env)
  flush_current=dict(before=ctx,writes=[]);flush_calls.append(flush_current);FlushReturn(u32(reg('esp')),flush_current);return False
class WriteReturn(gdb.Breakpoint):
 def __init__(self,pc,item,esp):self.item=item;self.esp=esp;super().__init__('*'+hex(pc),internal=True)
 def stop(self):
  if 'returned'in self.item or reg('esp')!=self.esp+4:return False
  self.item['returned']=reg('eax');self.enabled=False;return False
class WriteEntry(gdb.Breakpoint):
 def stop(self):
  if flush_current is None:return False
  s=reg('esp');fd,buffer,count=(u32(s+4+4*i)for i in range(3));item=dict(fd=fd,address=buffer,count=count,data=mem(buffer,count).hex())
  flush_current['writes'].append(item);WriteReturn(u32(s),item,s);return False
class FlushDriverReturn(gdb.Breakpoint):
 def stop(self):
  global flush_active
  flush_active=True;return False
class FlushDriver(gdb.Breakpoint):
 def stop(self):
  global flush_seen,flush_next
  if flush_active:flush_next=dict(pc=reg('pc'),esp=reg('esp'));return True
  if not flush_seen:flush_seen=True;FlushDriverReturn('*'+hex(u32(reg('esp'))),internal=True,temporary=True)
  return False
for pc in (0x8050b2c,0x8051280):FlushDriver('*'+hex(pc),internal=True)
FlushEntry('_IO_fflush',internal=True);WriteEntry('__write',internal=True);WriteEntry('__write_nocancel',internal=True)
def flush_exited(event):
 global flush_exit,flush_exit_signal
 flush_exit=getattr(event,'exit_code',None)
 if flush_exit is None:
  try:flush_exit_signal=int(gdb.parse_and_eval('$_exitsignal'))
  except gdb.error:pass
gdb.events.exited.connect(flush_exited)
'''


def commands(directory):
    return ('set pagination off\nset confirm off\nset debuginfod enabled off\nset breakpoint pending on\nset debug-file-directory '+str(directory)+'\nhandle SIGQUIT nostop noprint pass\npython\n'+OBSERVER+
            '\nend\nrun -g -t process.tek -x input.asit < answers.txt\npython\nsignal=flush_exit_signal\n'
            'if flush_next is None and gdb.selected_inferior().pid:\n try:signal=int(gdb.parse_and_eval("$_siginfo.si_signo"))\n except gdb.error:pass\n'
            'result=dict(flush_calls=flush_calls,next_driver=flush_next,native_exit=flush_exit,events=[],node=None,signal=signal)\nopen("heap.json","w").write(json.dumps(result))\n'
            'if gdb.selected_inferior().pid:gdb.execute("kill",to_string=True)\nend\nquit\n')


def jobs():
    for job in parent.jobs():
        job['parent']=ROOT/'tests/fixtures/getline_transition_original.json.gz';yield job


def main():
    p=argparse.ArgumentParser(add_help=False);p.add_argument('--debug-directory',type=Path,required=True);own,remaining=p.parse_known_args();sys.argv=[sys.argv[0],*remaining];pages={};records={};indices={}
    def project(case):
        for call in case['flush_calls']:
            for point in (call['before'],call.get('after',{})):
                for r in point.get('regions',[]):pack_region(r,bytes.fromhex(r.pop('data')),pages)
                if 'regions'in point:pack_state(point,records,indices)
        return case
    lifetime.main(commands=commands(own.debug_directory),fixture_name='flush_storage_original.json.gz',job_factory=jobs,case_transform=project,finalize_metadata=lambda:dict(loader_pages=pages,loader_records=records,loader_record_keys=list(indices)),
        extra_metadata=dict(flush_storage_provenance=dict(observer=OBSERVER,reference='All unchanged 134 histories retained. Every post-driver fflush entry and first matching caller return includes complete stack/ELF/TLS/heap/stream/lock/vtable regions, all registers and XSAVE. Native write operands and returned counts are assertions only. No inferior instruction, memory, register, syscall result, allocation or signal is substituted; minimal environment guards precede capture. No call snapshot seeds continuing replay.')))


if __name__=='__main__':main()
