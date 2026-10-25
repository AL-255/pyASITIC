"""Every printf buffer write and nested memcpy after first driver return."""
import argparse,sys
from pathlib import Path
import capture_dispatch_storage_original as dispatch
import capture_flush_transition_original as parent
import capture_trailing_via_heap_original as lifetime
from capture_getline_bytes_original import pack_region,integer_cpu
from getline_fixture import record_id
from printf_fixture import pack_state,compact_pages
from printf_archive import read_fixture,split_archive

ROOT=Path(__file__).resolve().parents[1]
OBSERVER=dispatch.transition.COMMON+'\n'+dispatch.ELF_PLT+r'''
printf_calls=[];printf_current=None;printf_active=False;printf_seen=False;printf_next=None;printf_exit=None;printf_exit_signal=0
def printf_context():
 block=gdb.block_for_pc(int(gdb.parse_and_eval('&_dl_lookup_symbol_x')));typ=gdb.lookup_type('struct link_map',block);assert typ.sizeof==632
 main=u32(int(gdb.parse_and_eval('&_r_debug'))+4);ctx=plt_inputs(main,typ);ctx['main_map']=main
 for item in ctx['maps']:item['plt']=elf_plt(item['name']or'/proc/%d/exe'%gdb.selected_inferior().pid,u32(item['address']))
 s=reg('esp');buffer=u32(s+4);source=u32(s+8);count=u32(s+12)
 ctx['regions']+=[mapping('[heap]'),dict(address=buffer,data=mem(buffer,24).hex())]
 if count:ctx['regions'].append(dict(address=source,data=mem(source,count).hex()))
 # Some formatters target a static libc buffer, outside the heap/stack.
 # Retain its complete declared writable extent as an earlier input and
 # later assertion, including bytes which this call does not overwrite.
 start=u32(buffer);end=u32(buffer+8)
 if start and end>start:ctx['regions'].append(dict(address=start,data=mem(start,end-start).hex()))
 return ctx
def printf_state(ctx):return dict(registers=registers(),xstate=regset(0x202).hex(),regions=[dict(address=r['address'],data=mem(r['address'],len(r['data'])//2).hex())for r in ctx['regions']])
class PrintfReturn(gdb.Breakpoint):
 def __init__(self,pc,item):self.item=item;super().__init__('*'+hex(pc),internal=True)
 def stop(self):
  global printf_current
  if 'after'in self.item or reg('esp')!=self.item['before']['registers']['esp']+4:return False
  self.item['after']=printf_state(self.item['before']);printf_current=None;self.enabled=False;return False
class PrintfEntry(gdb.Breakpoint):
 def stop(self):
  global printf_current
  if not printf_active:return False
  if printf_current is not None:raise RuntimeError('Nested printf buffer write needs its nested observer')
  env=environment();ctx=printf_context();ctx.update(registers=registers(),xstate=regset(0x202).hex(),environment=env)
  printf_current=dict(before=ctx,children=[]);printf_calls.append(printf_current);PrintfReturn(u32(reg('esp')),printf_current);return False
class PrintfChildReturn(gdb.Breakpoint):
 def __init__(self,pc,item):self.item=item;super().__init__('*'+hex(pc),internal=True)
 def stop(self):
  if 'after'in self.item or reg('esp')!=self.item['before']['esp']+4:return False
  self.item['after']=registers();self.enabled=False;return False
class PrintfChild(gdb.Breakpoint):
 def __init__(self,pc,kind):self.kind=kind;super().__init__('*'+hex(pc),internal=True)
 def stop(self):
  if printf_current is None:return False
  item=dict(kind=self.kind,before=registers());printf_current['children'].append(item);PrintfChildReturn(u32(reg('esp')),item);return False
class PrintfDriverReturn(gdb.Breakpoint):
 def stop(self):
  global printf_active
  printf_active=True;base=int(gdb.parse_and_eval('&_IO_getline_info'))-0x772e0
  PrintfEntry('*'+hex(base+0x58750),internal=True)
  for off,kind in ((0xbbae0,'memcpy'),(0x58230,'flush')):PrintfChild(base+off,kind)
  return False
class PrintfDriver(gdb.Breakpoint):
 def stop(self):
  global printf_seen,printf_next
  if printf_active:printf_next=dict(pc=reg('pc'),esp=reg('esp'));return True
  if not printf_seen:printf_seen=True;PrintfDriverReturn('*'+hex(u32(reg('esp'))),internal=True,temporary=True)
  return False
for pc in (0x8050b2c,0x8051280):PrintfDriver('*'+hex(pc),internal=True)
def printf_exited(event):
 global printf_exit,printf_exit_signal
 printf_exit=getattr(event,'exit_code',None)
 if printf_exit is None:
  try:printf_exit_signal=int(gdb.parse_and_eval('$_exitsignal'))
  except gdb.error:pass
gdb.events.exited.connect(printf_exited)
'''


def commands(directory):
    return ('set pagination off\nset confirm off\nset debuginfod enabled off\nset breakpoint pending on\nset debug-file-directory '+str(directory)+'\nhandle SIGQUIT nostop noprint pass\npython\n'+OBSERVER+
            '\nend\nrun -g -t process.tek -x input.asit < answers.txt\npython\nsignal=printf_exit_signal\n'
            'if printf_next is None and gdb.selected_inferior().pid:\n try:signal=int(gdb.parse_and_eval("$_siginfo.si_signo"))\n except gdb.error:pass\n'
            'result=dict(printf_calls=printf_calls,next_driver=printf_next,native_exit=printf_exit,events=[],node=None,signal=signal)\nopen("heap.json","w").write(json.dumps(result))\n'
            'if gdb.selected_inferior().pid:gdb.execute("kill",to_string=True)\nend\nquit\n')


def jobs():
    for job in parent.jobs():
        job['parent']=ROOT/'tests/fixtures/flush_transition_original.json.gz';yield job


class PrintfProjection:
    """Verify and compact each complete native snapshot before retaining it."""
    def __init__(self):
        self.storage=dict(loader_pages={},loader_records={},loader_record_keys=[]);self.indices={};self.templates={};self.states=0

    def case(self,case):
        storage=self.storage;records=storage['loader_records'];keys=storage['loader_record_keys']
        for call in case['printf_calls']:
            for point in (call['before'],call.get('after',{})):
                if 'regions'not in point:continue
                ids=[]
                for region in point.pop('regions'):
                    pack_region(region,bytes.fromhex(region.pop('data')),storage['loader_pages']);key=record_id(region)
                    if key in records:
                        if records[key]!=region:raise ValueError('Conflicting native printf region record')
                    else:
                        self.indices[key]=len(keys);keys.append(key);records[key]=region
                    ids.append(self.indices[key])
                point['region_ids']=ids;pack_state(storage,point,self.templates);self.states+=1
        return case

    def metadata(self):
        pages=compact_pages(self.storage)
        return dict(self.storage,printf_projection=dict(states_checked=self.states,pages_checked=pages,reference='Every native state is losslessly factored while collecting the capture. All context/FP fields and ordered region references expand identically before the dense state is discarded; page conversion separately verifies every page byte and ordered page list. No owner or target byte is removed.'))


def main():
    p=argparse.ArgumentParser(add_help=False);p.add_argument('--debug-directory',type=Path,required=True);p.add_argument('--cc',default='cc');own,remaining=p.parse_known_args();sys.argv=[sys.argv[0],*remaining];cpu=integer_cpu(own.cc);projection=PrintfProjection()
    lifetime.main(commands=commands(own.debug_directory),fixture_name='printf_buffer_original.json.gz',job_factory=jobs,case_transform=projection.case,finalize_metadata=projection.metadata,
        extra_metadata=dict(integer_cpu=cpu,printf_buffer_provenance=dict(observer=OBSERVER,reference='All unchanged 134 histories retained. Every post-driver printf buffer write records complete earlier stack/ELF/TLS/heap/buffer state and later full regions/registers/XSAVE. Every nested scalar memcpy and buffer flush records all entry/return registers. Independent CPU flags probe precedes all jobs. No inferior instruction, memory, register, allocation, result or signal is replaced; minimal environment guards precede capture. No per-call snapshot initializes continuing replay.')))
    archive=ROOT/'tests/fixtures/printf_buffer_original.json.gz';fixture=read_fixture(archive);histories=len(fixture['cases']);parents=fixture['parents'];del fixture
    split_archive(archive,ROOT/'tests/fixtures/printf_buffer_original.manifest.json',histories=histories,parents=parents);archive.unlink()


if __name__=='__main__':main()
