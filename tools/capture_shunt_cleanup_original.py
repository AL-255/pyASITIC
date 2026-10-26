"""Read-only complete log-close and X11 finalizer targets in all histories."""
import argparse,gzip,hashlib,json,sys
from pathlib import Path
import capture_shunt_malloc_original as parent
from capture_poll_storage_original import integer_cpu
from capture_getline_bytes_original import integer_cpu as byte_cpu

ROOT=Path(__file__).resolve().parents[1]
REFERENCE='All fourteen unchanged scripts cold/warm and every prior target remain. Genuine first-driver recording/log global controls and pinned X11 finalizer/global pointer bytes are new earlier inputs. Observe all later log/recording fclose entries/returns, internal buffer/FILE free entries, and XFreeThreads entry/return: complete stacks/heaps/arena/FILE/stdio regions, registers, XSAVE and allocator states. Later targets never supply continuing source input. No inferior instruction, byte, register, allocation, result, return, signal or affinity is replaced.'
X11_SHA256='efb792871e2695991f2cde2ad3b76371eeaae001e382aa1d31b66f563d5ab1e3'
OBSERVER=parent.OBSERVER+r'''
cleanup_calls=[];cleanup_active=[]
_cleanup_initial_snapshot=allocator_snapshot
def allocator_snapshot(label):
 _cleanup_initial_snapshot(label)
 if label=='driver_entry':
  ctx=transition_inputs['loader_context'];stdio=transition_inputs['stdio_context']
  def include(p,n):
   if any(r['address']==p and r['size']==n for r in stdio['regions']):return
   ctx['regions'].append(dict(address=p,data=mem(p,n).hex()));stdio['regions'].append(dict(address=p,size=n))
  x=next(item for item in ctx['maps']if item['name'].endswith('/libX11.so.6'))
  if x['plt']['elf_sha256']!='efb792871e2695991f2cde2ad3b76371eeaae001e382aa1d31b66f563d5ab1e3':raise RuntimeError('X11 cleanup capture requires its pinned original image')
  base=u32(x['address'])
  for p,n in((0x80cbab8,1),(0x80d7e1c,16),(base+0x150e44,12),(base+0x14e838,8),(base+0x150e00,1),(base+0x14f220,4)):include(p,n)
  transition_inputs['cleanup_context']=dict(x11_map=x['address'],x11_sha256=x['plt']['elf_sha256'])
def cleanup_state(label,file=None):
 n=second_namespace;n['allocator_snapshot'](label);state=n['allocator_states'].pop()
 regions=[mapping('[stack]'),*state.pop('memory_regions'),dict(address=state['arena_address'],data=state['arena_bytes'])]
 head=libio_inputs['libc_symbols']['_IO_list_all']['address'];regions.append(dict(address=head,data=mem(head,4).hex()))
 if file is not None:regions.append(dict(address=file,data=mem(file,304).hex()))
 for region in transition_inputs['stdio_context']['regions']:regions.append(dict(address=region['address'],data=mem(region['address'],region['size']).hex()))
 return dict(registers=registers(),xstate=regset(0x202).hex(),heap=state,regions=regions,shutdown_event_count=len(shutdown_events))
class CleanupReturn(gdb.Breakpoint):
 def __init__(self,pc,item,file):self.item=item;self.file=file;super().__init__('*'+hex(pc),internal=True)
 def stop(self):
  if 'after'in self.item or reg('esp')!=self.item['before']['registers']['esp']+4:return False
  self.item['after']=cleanup_state(self.item['kind']+'.return',self.file)
  if self.item in cleanup_active:cleanup_active.remove(self.item)
  self.enabled=False;return False
class CleanupClose(gdb.Breakpoint):
 def stop(self):
  if not shutdown_active:return False
  a=u32(reg('esp')+4);bindings=[('log.input',u32(0x80d7e24)),('log.output',u32(0x80d7e28))]
  if mem(0x80cbab8,1)!=b'\0':bindings+=[('recording.output',u32(0x80d7e20)),('recording.input',u32(0x80d7e1c))]
  kind=next((name for name,p in bindings if p==a),None)
  if kind is None:return False
  item=dict(kind=kind,file=a,before=cleanup_state(kind+'.entry',a),free=[]);cleanup_calls.append(item);cleanup_active.append(item)
  CleanupReturn(u32(reg('esp')),item,a);return False
class CleanupFree(gdb.Breakpoint):
 def stop(self):
  if not shutdown_active or not cleanup_active:return False
  item=cleanup_active[-1];a=item['file'];p=u32(reg('esp')+4)
  item['free'].append(dict(address=p,state=cleanup_state(item['kind']+'.free',a)));return False
class CleanupX11(gdb.Breakpoint):
 def stop(self):
  if not shutdown_active:return False
  item=dict(kind='XFreeThreads',before=cleanup_state('XFreeThreads.entry'));cleanup_calls.append(item)
  CleanupReturn(u32(reg('esp')),item,None);return False
_cleanup_shutdown_begin=shutdown_begin
def shutdown_begin():
 _cleanup_shutdown_begin();CleanupClose('__new_fclose',internal=True);CleanupFree('__libc_free',internal=True);CleanupX11('XFreeThreads',internal=True)
_cleanup_shutdown_finish=shutdown_finish
def shutdown_finish():
 _cleanup_shutdown_finish();shutdown['cleanup']=cleanup_calls
'''


def commands(directory,observer=OBSERVER):return parent.commands(directory,observer)


def main():
    p=argparse.ArgumentParser(add_help=False);p.add_argument('--cc',default='cc');own,remaining=p.parse_known_args();sys.argv=[sys.argv[0],*remaining]
    cpu=integer_cpu(own.cc);byte=byte_cpu(own.cc);regions={};projection=dict(complete_regions_checked=0,bytes_checked=0,reference=parent.PROJECTION_REFERENCE);cleanup=dict(complete_regions_checked=0,bytes_checked=0,reference=parent.PROJECTION_REFERENCE)
    def project(case,heap_pages,file_pages):
        stdio=case['transition_inputs']['stdio_context'];stdio['sar31_af']=cpu['sar31_af'];stdio['input_abi']['shr1_af']=byte['shr1_af']
        checked,total=parent.project_malloc(case,heap_pages,file_pages,regions);projection['complete_regions_checked']+=checked;projection['bytes_checked']+=total
        for call in case['shutdown']['cleanup']:
            points=[call[k]for k in('before','after')if k in call]+[v['state']for v in call.get('free',[])]
            for point in points:
                for region in point['regions']:
                    raw=bytes.fromhex(region.pop('data'));packed=heap_pages(raw)
                    if(packed['size'],packed['sha256'],packed['pages'])!=(len(raw),hashlib.sha256(raw).hexdigest(),[hashlib.sha256(raw[o:o+4096]).hexdigest()for o in range(0,len(raw),4096)]):raise ValueError('Cleanup projection changed a complete native region')
                    region.update(packed,page_bank='driver_heap_pages');cleanup['complete_regions_checked']+=1;cleanup['bytes_checked']+=len(raw)
    driver=parent.parent.parent.parent.second.command.shunt.shunt.driver
    driver.main(fixture_name='shunt_cleanup_original.json.gz',parent_name='shunt_malloc_original.json.gz',job_factory=parent.parent.parent.parent.second.command.shunt.shunt.jobs,
        observer=OBSERVER,command_builder=commands,state_fields=('allocator_states','post_states','transition_states'),buffer_fields=('post_buffers','transition_buffers'),project_extra_case=project,
        extra_metadata=dict(loader_regions=regions,malloc_projection=projection,cleanup_projection=cleanup,integer_cpu=cpu,byte_cpu=byte,shunt_cleanup_reference=REFERENCE))


if __name__=='__main__':main()
