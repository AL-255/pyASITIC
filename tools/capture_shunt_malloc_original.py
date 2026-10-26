"""All continuing histories with complete stdin malloc entry/return targets."""
import argparse,gzip,hashlib,json,sys
from pathlib import Path
import capture_shunt_repl_original as parent
from capture_poll_storage_original import integer_cpu
from capture_getline_bytes_original import integer_cpu as byte_cpu

ROOT=Path(__file__).resolve().parents[1]
PROJECTION_REFERENCE='Every complete captured malloc region expands byte for byte before its original dense representation is removed. All ordered owners and original SHA256/size remain; only repeated content is factored into the existing immutable page bank.'
OBSERVER=parent.OBSERVER+r'''
shutdown_malloc=[]
def stdin_malloc_state(label):
 n=second_namespace;n['allocator_snapshot'](label);state=n['allocator_states'].pop()
 regions=[mapping('[stack]'),*state.pop('memory_regions'),dict(address=state['arena_address'],data=state['arena_bytes'])]
 return dict(registers=registers(),xstate=regset(0x202).hex(),heap=state,regions=regions)
class StdinMallocReturn(gdb.Breakpoint):
 def __init__(self,pc,item):self.item=item;super().__init__('*'+hex(pc),internal=True)
 def stop(self):
  if 'after'in self.item or reg('esp')!=self.item['before']['registers']['esp']+4:return False
  self.item['after']=stdin_malloc_state('stdin.malloc.return');self.enabled=False;return False
class StdinMalloc(gdb.Breakpoint):
 def stop(self):
  if not shutdown_active or u32(reg('esp'))!=libio_inputs['libc_base']+0x75523:return False
  item=dict(before=stdin_malloc_state('stdin.malloc.entry'));shutdown_malloc.append(item)
  StdinMallocReturn(u32(reg('esp')),item);return False
_malloc_shutdown_begin=shutdown_begin
def shutdown_begin():
 _malloc_shutdown_begin();StdinMalloc('__libc_malloc',internal=True)
_malloc_shutdown_finish=shutdown_finish
def shutdown_finish():
 _malloc_shutdown_finish();shutdown['malloc']=shutdown_malloc
'''


def commands(directory,observer=OBSERVER):return parent.commands(directory,observer)


def project_malloc(case,heap_pages,file_pages,regions):
    parent.project_repl(case,heap_pages,file_pages,regions)
    checked=total=0
    for call in case['shutdown']['malloc']:
        for point in call.values():
            for region in point['regions']:
                raw=bytes.fromhex(region.pop('data'));packed=heap_pages(raw)
                if(packed['size'],packed['sha256'],packed['pages'])!=(len(raw),hashlib.sha256(raw).hexdigest(),[hashlib.sha256(raw[o:o+4096]).hexdigest()for o in range(0,len(raw),4096)]):raise ValueError('Malloc projection changed a complete native region')
                region.update(packed,page_bank='driver_heap_pages');checked+=1;total+=len(raw)
    return checked,total


def main():
    p=argparse.ArgumentParser(add_help=False);p.add_argument('--cc',default='cc');own,remaining=p.parse_known_args();sys.argv=[sys.argv[0],*remaining]
    cpu=integer_cpu(own.cc);byte=byte_cpu(own.cc);regions={};projection=dict(complete_regions_checked=0,bytes_checked=0,reference=PROJECTION_REFERENCE)
    def project(case,heap_pages,file_pages):
        stdio=case['transition_inputs']['stdio_context'];stdio['sar31_af']=cpu['sar31_af'];stdio['input_abi']['shr1_af']=byte['shr1_af']
        checked,total=project_malloc(case,heap_pages,file_pages,regions);projection['complete_regions_checked']+=checked;projection['bytes_checked']+=total
    parent.parent.parent.second.command.shunt.shunt.driver.main(fixture_name='shunt_malloc_original.json.gz',parent_name='shunt_repl_original.json.gz',job_factory=parent.parent.parent.second.command.shunt.shunt.jobs,
        observer=OBSERVER,command_builder=commands,state_fields=('allocator_states','post_states','transition_states'),buffer_fields=('post_buffers','transition_buffers'),project_extra_case=project,
        extra_metadata=dict(loader_regions=regions,malloc_projection=projection,integer_cpu=cpu,byte_cpu=byte,shunt_malloc_reference='All fourteen original scripts, cold/warm, and the complete previous shutdown horizon retained. Genuine first-driver inputs are unchanged in role. Observe every stdin doallocate malloc public entry/return, complete stacks/heaps/arena bytes, registers and XSAVE. All these later states are assertion targets only, never full-replay inputs. No inferior instruction, byte, register, allocation, result, return, signal or affinity is replaced.'))


if __name__=='__main__':main()
