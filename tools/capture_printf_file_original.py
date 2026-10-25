"""Every native printf FILE-buffer initialization and completion boundary."""
import argparse,sys
from pathlib import Path
import capture_dispatch_storage_original as dispatch
import capture_printf_buffer_original as parent
import capture_trailing_via_heap_original as lifetime
from capture_allocator_original import OBSERVER as ALLOCATOR
from capture_statx_metadata import OBSERVER as STATX
from printf_archive import read_fixture,split_archive

ROOT=Path(__file__).resolve().parents[1]
FILE_STATX=STATX.replace('def statx_metadata():','def statx_metadata(fd):').replace("'/proc/%d/fd/0'%gdb.selected_inferior().pid","'/proc/%d/fd/%d'%(gdb.selected_inferior().pid,fd)")
OBSERVER=dispatch.transition.COMMON+'\n'+dispatch.ELF_PLT+'\nevents=[]\n'+ALLOCATOR+'\n'+FILE_STATX+r'''
file_calls=[];file_current=None;file_active=False;file_seen=False;file_next=None;file_exit=None;file_exit_signal=0
def file_context(kind):
 block=gdb.block_for_pc(int(gdb.parse_and_eval('&_dl_lookup_symbol_x')));typ=gdb.lookup_type('struct link_map',block);assert typ.sizeof==632
 main=u32(int(gdb.parse_and_eval('&_r_debug'))+4);ctx=plt_inputs(main,typ);ctx['main_map']=main
 for item in ctx['maps']:item['plt']=elf_plt(item['name']or'/proc/%d/exe'%gdb.selected_inferior().pid,u32(item['address']))
 s=reg('esp');buffer=u32(s+4);file=u32(s+8)if kind=='init'else u32(buffer+24)
 base=u32(next(x['address']for x in ctx['maps']if x['name'].endswith('/libc.so.6')));got=base+0x22fe34;tls=ctx['tls_base']
 lock=u32(file+72);offset=struct.unpack('<b',mem(file+70,1))[0];vt=u32(file+148+offset)
 allocator_snapshot('printf-file');heap=allocator_states.pop();ctx['heap']=heap
 ctx['regions']+=[mapping('[heap]'),dict(address=heap['arena_address'],data=heap['arena_bytes'])]
 controls=[(buffer,156),(file,152),(lock,12),(vt,84),(got+0xa0,4),((u32(tls)+u32(got+0xa0))&0xffffffff,4),
  (got+0x1a30,4),(got+0x1c4,4),(u32(tls+16),32),(got+0x78,4),(got+0x368,4),(got+0x3bfc,4),
  (got+0x3c04,1),(got+0x3c14,4),(got+0x3c18,1),((tls+u32(got+0x78))&0xffffffff,4)]
 start=u32(file+28);end=u32(file+32)
 if start and end>start:controls.append((start,end-start))
 ctx['regions']+=[dict(address=p,data=mem(p,n).hex())for p,n in controls if p and n]
 fd=u32(file+56);ctx['file']=file;ctx['profile']=dict(fd=fd,statx=statx_metadata(fd))
 return ctx
def file_state(ctx):
 allocator_snapshot('printf-file');heap=allocator_states.pop()
 regions=[dict(address=r['address'],data=mem(r['address'],len(r['data'])//2).hex())for r in ctx['regions']]
 current=mapping('[heap]')
 if not any(r['address']==current['address']and len(r['data'])==len(current['data'])for r in regions):regions.append(current)
 return dict(registers=registers(),xstate=regset(0x202).hex(),heap=heap,regions=regions)
class FileReturn(gdb.Breakpoint):
 def __init__(self,pc,item):self.item=item;super().__init__('*'+hex(pc),internal=True)
 def stop(self):
  global file_current
  if 'after'in self.item or reg('esp')!=self.item['before']['registers']['esp']+4:return False
  self.item['after']=file_state(self.item['before']);file_current=None;self.enabled=False;return False
class FileEntry(gdb.Breakpoint):
 def __init__(self,pc,kind):self.kind=kind;super().__init__('*'+hex(pc),internal=True)
 def stop(self):
  global file_current
  if not file_active:return False
  if file_current is not None:raise RuntimeError('Nested printf FILE helpers need a nested observer')
  env=environment();ctx=file_context(self.kind);ctx.update(registers=registers(),xstate=regset(0x202).hex(),environment=env)
  file_current=dict(kind=self.kind,before=ctx,children=[]);file_calls.append(file_current);FileReturn(u32(reg('esp')),file_current);return False
class FileChildReturn(gdb.Breakpoint):
 def __init__(self,pc,item):self.item=item;super().__init__('*'+hex(pc),internal=True)
 def stop(self):
  if 'after'in self.item or reg('esp')!=self.item['before']['esp']+4:return False
  self.item['after']=registers();self.enabled=False;return False
class FileChild(gdb.Breakpoint):
 def __init__(self,pc,kind):self.kind=kind;super().__init__('*'+hex(pc),internal=True)
 def stop(self):
  if file_current is None:return False
  item=dict(kind=self.kind,before=registers());file_current['children'].append(item);FileChildReturn(u32(reg('esp')),item);return False
class FileDriverReturn(gdb.Breakpoint):
 def stop(self):
  global file_active
  file_active=True;base=int(gdb.parse_and_eval('&_IO_getline_info'))-0x772e0
  for off,kind in ((0x586c0,'init'),(0x58710,'done')):FileEntry(base+off,kind)
  for off,kind in ((0x58570,'switch'),(0x585a0,'flush-to-file'),(0x58190,'buffer-done'),(0x83fc0,'xsputn'),(0x831f0,'overflow'),(0x85440,'doallocbuf'),(0x75490,'doallocate'),(0x83eb0,'file-stat'),(0x853e0,'setb'),(0x9ea00,'malloc'),(0xbbae0,'memcpy')):FileChild(base+off,kind)
  return False
class FileDriver(gdb.Breakpoint):
 def stop(self):
  global file_seen,file_next
  if file_active:file_next=dict(pc=reg('pc'),esp=reg('esp'));return True
  if not file_seen:file_seen=True;FileDriverReturn('*'+hex(u32(reg('esp'))),internal=True,temporary=True)
  return False
for pc in (0x8050b2c,0x8051280):FileDriver('*'+hex(pc),internal=True)
def file_exited(event):
 global file_exit,file_exit_signal
 file_exit=getattr(event,'exit_code',None)
 if file_exit is None:
  try:file_exit_signal=int(gdb.parse_and_eval('$_exitsignal'))
  except gdb.error:pass
gdb.events.exited.connect(file_exited)
'''


def commands(directory):
    return ('set pagination off\nset confirm off\nset debuginfod enabled off\nset breakpoint pending on\nset debug-file-directory '+str(directory)+'\nhandle SIGQUIT nostop noprint pass\npython\n'+OBSERVER+
            '\nend\nrun -g -t process.tek -x input.asit < answers.txt\npython\nsignal=file_exit_signal\n'
            'if file_next is None and gdb.selected_inferior().pid:\n try:signal=int(gdb.parse_and_eval("$_siginfo.si_signo"))\n except gdb.error:pass\n'
            'result=dict(printf_calls=file_calls,next_driver=file_next,native_exit=file_exit,events=[],node=None,signal=signal)\nopen("heap.json","w").write(json.dumps(result))\n'
            'if gdb.selected_inferior().pid:gdb.execute("kill",to_string=True)\nend\nquit\n')


def jobs():
    for job in parent.jobs():
        job['parent']=ROOT/'tests/fixtures/printf_buffer_original.manifest.json';yield job


def main():
    p=argparse.ArgumentParser(add_help=False);p.add_argument('--debug-directory',type=Path,required=True);own,remaining=p.parse_known_args();sys.argv=[sys.argv[0],*remaining];projection=parent.PrintfProjection()
    lifetime.main(commands=commands(own.debug_directory),fixture_name='printf_file_original.json.gz',job_factory=jobs,case_transform=projection.case,finalize_metadata=projection.metadata,
        extra_metadata=dict(printf_file_provenance=dict(observer=OBSERVER,reference='All unchanged 134 histories retained. Every post-driver FILE-buffer init/done call records complete earlier stack/ELF/TLS/heap/arena/buffer/FILE/lock/vtable/control regions, allocator state and independent external file statx facts. Full later regions/registers/XSAVE/heap and every nested helper entry/return register remain assertions. No inferior instruction, memory, register, allocation, result or signal is replaced; minimal environment guards precede capture. No per-call snapshot initializes continuing replay.')))
    archive=ROOT/'tests/fixtures/printf_file_original.json.gz';fixture=read_fixture(archive);histories=len(fixture['cases']);parents=fixture['parents'];del fixture
    split_archive(archive,ROOT/'tests/fixtures/printf_file_original.manifest.json',histories=histories,parents=parents);archive.unlink()


if __name__=='__main__':main()
