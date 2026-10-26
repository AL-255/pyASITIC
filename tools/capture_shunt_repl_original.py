"""Read-only shutdown histories with genuine earlier loader/stdio inputs."""
import argparse,gzip,hashlib,json,sys
from pathlib import Path
import capture_shunt_shutdown_original as parent
import capture_printf_transition_original as earlier
import capture_loader_transition_original as loader
from capture_poll_storage_original import integer_cpu
from capture_getline_bytes_original import integer_cpu as byte_cpu

ROOT=Path(__file__).resolve().parents[1]
LOADER_SUFFIX=loader.OBSERVER[len(loader.transition.OBSERVER):]
assert earlier.OBSERVER.count(LOADER_SUFFIX)==1
EARLIER=earlier.OBSERVER[earlier.OBSERVER.index(LOADER_SUFFIX):]
OBSERVER=parent.OBSERVER+'\n'+EARLIER+r'''
shutdown_printf=[];shutdown_io=[]
cache_mapping_inputs=[]
def add_cache_mapping_targets(state):
 records={r['address']:r for r in state.get('mapped_chunks',[])}
 for item in cache_mapping_inputs:
  address=item['address'];start=address-item['prev_size'];end=address+(item['size_word']&~7)
  if not any(region['start']<=start and end<=region['end']for region in state['maps']):continue
  previous,word=struct.unpack('<II',mem(address,8))
  if not word&2:raise RuntimeError('Earlier cache mapping lost its mapped chunk header')
  records[address]=dict(item,prev_size=previous,size_word=word)
 state['mapped_chunks']=sorted(records.values(),key=lambda item:item['address'])
_repl_initial_snapshot=allocator_snapshot
def allocator_snapshot(label):
 _repl_initial_snapshot(label)
 if label=='driver_entry':
  heap_ranges=[r for r in allocator_states[-1]['maps']if r['path']=='[heap]']
  for group in cache_inputs['arrays'].values():
   for pointer in group['pointers']:
    if any(r['start']<=pointer<r['end']for r in heap_ranges):continue
    address=pointer-8;previous,word=struct.unpack('<II',mem(address,8));assert word&2
    item=dict(address=address,prev_size=previous,size_word=word,request=group['size']);cache_mapping_inputs.append(item)
    start=address-previous;size=previous+(word&~7)
    transition_inputs['initial_regions'].append(dict(address=start,data=mem(start,size).hex()))
  transition_inputs['cache_mapping_inputs']=list(cache_mapping_inputs)
 add_cache_mapping_targets(allocator_states[-1])
_repl_second_begin=second_begin
def second_begin():
 _repl_second_begin()
 native=second_namespace['allocator_snapshot']
 def snapshot(label):
  native(label);add_cache_mapping_targets(second_namespace['allocator_states'][-1])
 second_namespace['allocator_snapshot']=snapshot
 # The already-stopped entry has just been observed by the original second
 # observer; extend that assertion without executing an inferior instruction.
 add_cache_mapping_targets(second_namespace['allocator_states'][-1])
_repl_shutdown_snapshot=shutdown_snapshot
def shutdown_snapshot(label):
 _repl_shutdown_snapshot(label)
 state=shutdown_states[-1];state['stdin_position']=stdin_position()
 state['component_regions']+=[dict(address=r['address'],data=mem(r['address'],r['size']).hex())for r in transition_inputs['stdio_context']['regions']]
def shutdown_io_state():
 stdin=transition_inputs['stdin_stream']['address']
 return dict(registers=registers(),stdin_position=stdin_position(),regions=[mapping('[stack]'),dict(address=stdin,data=mem(stdin,152).hex())])
class ShutdownIOReturn(gdb.Breakpoint):
 def __init__(self,pc,item):self.item=item;super().__init__('*'+hex(pc),internal=True)
 def stop(self):
  if 'after'in self.item or reg('esp')!=self.item['before']['registers']['esp']+4:return False
  self.item['after']=shutdown_io_state();self.enabled=False;return False
class ShutdownIO(gdb.Breakpoint):
 def __init__(self,pc,kind,descriptor=False):self.kind=kind;self.descriptor=descriptor;super().__init__('*'+hex(pc),internal=True)
 def stop(self):
  if not shutdown_active:return False
  s=reg('esp');argument=u32(s+(12 if self.kind=='fgets'else 4))
  if argument!=(0 if self.descriptor else transition_inputs['stdin_stream']['address']):return False
  item=dict(kind=self.kind,before=shutdown_io_state());shutdown_io.append(item);ShutdownIOReturn(u32(s),item);return False
class ShutdownPrintfReturn(gdb.Breakpoint):
 def __init__(self,pc,item):self.item=item;super().__init__('*'+hex(pc),internal=True)
 def stop(self):
  if 'after'in self.item or reg('esp')!=self.item['before']['esp']+4:return False
  self.item['after']=registers();self.enabled=False;return False
class ShutdownPrintf(gdb.Breakpoint):
 def __init__(self,pc,kind):self.kind=kind;super().__init__('*'+hex(pc),internal=True)
 def stop(self):
  if not shutdown_active:return False
  pc=u32(reg('esp'))
  if pc not in(0x804c012,0x804be86,0x804bea3):return False
  item=dict(kind=self.kind,before=registers());shutdown_printf.append(item);ShutdownPrintfReturn(pc,item);return False
_repl_shutdown_begin=shutdown_begin
def shutdown_begin():
 _repl_shutdown_begin()
 base=libio_inputs['libc_base']
 ShutdownPrintf(base+0x57db0,'printf');ShutdownPrintf(base+0x57670,'fprintf')
 for offset,kind in((0x75b80,'fflush'),(0x833f0,'sync'),(0x75f70,'fgets'),(0x82de0,'underflow'),(0x83e80,'file_seek'),(0x83e40,'read')):ShutdownIO(base+offset,kind)
 ShutdownIO(base+0x115600,'llseek',True)
_repl_shutdown_finish=shutdown_finish
def shutdown_finish():
 _repl_shutdown_finish();shutdown.update(printf=shutdown_printf,io=shutdown_io)
'''


def commands(directory,observer=OBSERVER):
    return parent.commands(directory,observer)


def project_repl(case,heap_pages,file_pages,regions):
    parent.project_shutdown(case,heap_pages,file_pages)
    def pack(region):
        raw=bytes.fromhex(region.pop('data'));key=hashlib.sha256(raw).hexdigest()
        if key in regions and regions[key]!=raw.hex():raise ValueError('Conflicting complete native region')
        regions[key]=raw.hex();region.update(size=len(raw),sha256=key)
    for region in case['transition_inputs']['loader_context']['regions']:pack(region)
    for point in case['transition_points']+case['transition_states']:
        for region in point.get('regions',point.get('component_regions',[])):pack(region)
    for state in case['shutdown']['states']:
        for region in state['component_regions']:pack(region)
    for call in case['shutdown']['io']:
        for phase in('before','after'):
            if phase in call:
                for region in call[phase]['regions']:pack(region)


def main():
    p=argparse.ArgumentParser(add_help=False);p.add_argument('--cc',default='cc');own,remaining=p.parse_known_args();sys.argv=[sys.argv[0],*remaining]
    cpu=integer_cpu(own.cc);byte=byte_cpu(own.cc);regions={}
    def project(case,heap_pages,file_pages):
        stdio=case['transition_inputs']['stdio_context'];stdio['sar31_af']=cpu['sar31_af'];stdio['input_abi']['shr1_af']=byte['shr1_af']
        project_repl(case,heap_pages,file_pages,regions)
    parent.parent.second.command.shunt.shunt.driver.main(fixture_name='shunt_repl_original.json.gz',parent_name='shunt_shutdown_original.json.gz',job_factory=parent.parent.second.command.shunt.shunt.jobs,
        observer=OBSERVER,command_builder=commands,state_fields=('allocator_states','post_states','transition_states'),buffer_fields=('post_buffers','transition_buffers'),project_extra_case=project,
        extra_metadata=dict(loader_regions=regions,integer_cpu=cpu,byte_cpu=byte,shunt_repl_reference='All fourteen unchanged scripts, cold/warm, retain original outcomes and the full shutdown horizon. Only genuine first-driver loader/ELF/GOT/TLS/stdio/stat/descriptor inputs supplement prior inputs. Every new owned region is asserted at later command/shutdown boundaries. Native public printf registers and stdin fflush/sync/llseek/fgets/underflow full stacks, FILEs, descriptor positions and registers are later targets only. No per-call/later observation seeds source execution. No inferior instruction, memory, register, allocation, result, return, signal or affinity is replaced.'))


if __name__=='__main__':main()
