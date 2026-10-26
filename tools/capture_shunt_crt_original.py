"""Earlier CRT/string/frame-registry inputs and all native main-fini targets."""
import argparse,gzip,hashlib,json,sys
from pathlib import Path
import capture_shunt_exit_original as parent
from capture_poll_storage_original import integer_cpu
from capture_getline_bytes_original import integer_cpu as byte_cpu

ROOT=Path(__file__).resolve().parents[1]
REFERENCE='All fourteen unchanged scripts cold/warm and every prior exit/cleanup/solve target remain. Genuine first-driver CRT cursor/table/completion, global string objects/pool/Rep bytes, legacy frame registry and mutex controls are earlier inputs. Observe the real main fini, CRT traversal, application destructors/member destructors, registry removal and mutex entry/return, preserving complete stack/heap/arena/stdio/exit/CRT regions, all registers, XSAVE and allocator/event state. Later destructor results, frees, callback orders, registers, return values and exit status never initialize the full source history. No inferior instruction, byte, register, allocation, return, result, outcome or affinity is replaced.'
OBSERVER=parent.OBSERVER+r'''
crt_inputs=None;crt_calls=[];crt_active=False
_crt_initial_snapshot=allocator_snapshot
def allocator_snapshot(label):
 global crt_inputs
 _crt_initial_snapshot(label)
 if label=='driver_entry':
  ctx=transition_inputs['loader_context'];regions=[]
  def include(p,n):
   if not p or not n or any(r['address']==p and r['size']==n for r in regions):return
   regions.append(dict(address=p,size=n));ctx['regions'].append(dict(address=p,data=mem(p,n).hex()))
  legacy=next(v for v in ctx['maps']if v['name'].endswith('/libstdc++-libc6.1-1.so.2'))
  if legacy['plt']['elf_sha256']!='bca97b602b1eec9f0b591bec0fa4dc5f84f1382636cc8f10094f1da8a3c77d34':raise RuntimeError('CRT capture needs the pinned legacy runtime')
  base=u32(legacy['address']);include(0x80cb984,8)
  table=u32(0x80cb984);n=0
  while u32(table+4*n):n+=1
  include(table,4*(n+1));include(0x80d7e00,28);include(0x80d8660,120);include(0x80cf1a8,16);include(0x80cf1c0,100)
  for pointer in [u32(0x80d7e00+offset)for offset in(24,20,16,12,8)]+[u32(0x80d86d4)]:include(pointer-16,u32(pointer-12)+16)
  include(base+0x351dc,4);include(base+0x351e0,24);include(base+0x4142c,4)
  nodes=[];p=u32(base+0x4142c)
  while p:
   if p in nodes:raise RuntimeError('Cyclic earlier frame registry')
   nodes.append(p);include(p,24)
   if u32(p+12):include(u32(p+12),4*u32(p+16))
   p=u32(p+20)
  # Keep every previous exit owner and append all newly observed earlier owners.
  exit_inputs['regions'].extend(regions)
  crt_inputs=dict(regions=regions,legacy_map=legacy['address'],legacy_sha256=legacy['plt']['elf_sha256'],frame_nodes=nodes)
  transition_inputs['crt_inputs']=crt_inputs
class CRTReturn(gdb.Breakpoint):
 def __init__(self,pc,item):self.item=item;super().__init__('*'+hex(pc),internal=True)
 def stop(self):
  global crt_active
  if 'after'in self.item or reg('esp')!=self.item['before']['registers']['esp']+4:return False
  self.item['after']=exit_state(self.item['kind']+'.return');self.enabled=False
  if self.item['kind']=='main.fini':crt_active=False
  return False
class CRTCall(gdb.Breakpoint):
 def __init__(self,pc,kind):self.kind=kind;super().__init__(pc,internal=True)
 def stop(self):
  global crt_active
  if self.kind=='main.fini'and shutdown_active:crt_active=True
  if not crt_active:return False
  item=dict(kind=self.kind,pc=reg('pc'),arguments=[u32(reg('esp')+4*i)for i in range(1,4)],before=exit_state(self.kind+'.entry'));crt_calls.append(item)
  CRTReturn(u32(reg('esp')),item);return False
_crt_shutdown_begin=shutdown_begin
def shutdown_begin():
 _crt_shutdown_begin()
 for pc,kind in((0x80b4784,'main.fini'),(0x804af20,'main.dtors'),(0x804bdb0,'logs.dtors'),(0x80b2240,'logs.members'),(0x8060cb0,'port.dtors'),(0x80b3b40,'port.member')):CRTCall('*'+hex(pc),kind)
 legacy=u32(crt_inputs['legacy_map']);CRTCall('*'+hex(legacy+0x3084c),'frame.deregister')
 for symbol,kind in(('pthread_mutex_lock','mutex.lock'),('pthread_mutex_unlock','mutex.unlock')):CRTCall(symbol,kind)
_crt_shutdown_finish=shutdown_finish
def shutdown_finish():
 _crt_shutdown_finish();shutdown['crt_calls']=crt_calls
'''


def commands(directory,observer=OBSERVER):return parent.commands(directory,observer)


def main():
    p=argparse.ArgumentParser(add_help=False);p.add_argument('--cc',default='cc');own,remaining=p.parse_known_args();sys.argv=[sys.argv[0],*remaining]
    cpu=integer_cpu(own.cc);byte=byte_cpu(own.cc);regions={}
    projections={name:dict(complete_regions_checked=0,bytes_checked=0,reference=parent.parent.parent.PROJECTION_REFERENCE)for name in('malloc','cleanup','exit','crt')}
    def pack(point,heap_pages,projection):
        for region in point['regions']:
            raw=bytes.fromhex(region.pop('data'));packed=heap_pages(raw)
            if(packed['size'],packed['sha256'],packed['pages'])!=(len(raw),hashlib.sha256(raw).hexdigest(),[hashlib.sha256(raw[o:o+4096]).hexdigest()for o in range(0,len(raw),4096)]):raise ValueError('CRT projection changed a complete native region')
            region.update(packed,page_bank='driver_heap_pages');projection['complete_regions_checked']+=1;projection['bytes_checked']+=len(raw)
    def project(case,heap_pages,file_pages):
        stdio=case['transition_inputs']['stdio_context'];stdio['sar31_af']=cpu['sar31_af'];stdio['input_abi']['shr1_af']=byte['shr1_af']
        checked,total=parent.parent.parent.project_malloc(case,heap_pages,file_pages,regions);projections['malloc']['complete_regions_checked']+=checked;projections['malloc']['bytes_checked']+=total
        for call in case['shutdown']['cleanup']:
            for point in [call[k]for k in('before','after')if k in call]+[v['state']for v in call.get('free',[])]:pack(point,heap_pages,projections['cleanup'])
        for kind in('exit','crt'):
            for call in case['shutdown'][kind+'_calls']:
                for phase in('before','after'):
                    if phase in call:pack(call[phase],heap_pages,projections[kind])
    driver=parent.parent.parent.parent.parent.parent.second.command.shunt.shunt.driver
    path=ROOT/'tests/fixtures/shunt_crt_original.json.gz'
    driver.main(fixture_name=path.name,parent_name='shunt_exit_original.json.gz',job_factory=parent.parent.parent.parent.parent.parent.second.command.shunt.shunt.jobs,
        observer=OBSERVER,command_builder=commands,state_fields=('allocator_states','post_states','transition_states'),buffer_fields=('post_buffers','transition_buffers'),project_extra_case=project,
        extra_metadata=dict(loader_regions=regions,**{name+'_projection':value for name,value in projections.items()},integer_cpu=cpu,byte_cpu=byte,shunt_crt_reference=REFERENCE))
    from exit_fixture import factor_file,externalize_file
    factor_file(path)
    externalize_file(path,banks=('driver_heap_pages','loader_regions','storage_pages','storage_blobs','cache_file_pages'))
    if path.stat().st_size>=100*1024**2:raise ValueError('Complete CRT root still needs lossless factoring')


if __name__=='__main__':main()
