"""Read-only earlier exit-list/loader inputs and complete exit-call targets."""
import argparse,gzip,hashlib,json,sys
from pathlib import Path
import capture_shunt_cleanup_original as parent
from capture_poll_storage_original import integer_cpu
from capture_getline_bytes_original import integer_cpu as byte_cpu

ROOT=Path(__file__).resolve().parents[1]
REFERENCE='All fourteen unchanged scripts cold/warm and every prior target remain. Genuine first-driver exit-list, TLS-destructor and loader/global/dependency/fini metadata are earlier inputs. Observe libc exit and each originally registered callback, loader fini and per-object fini boundaries, plus every existing cleanup point: all complete stacks/heaps/arena and owned earlier exit regions, registers, XSAVE and allocator states. Later callbacks/orders/frees/returns/status never supply source input. No inferior instruction, byte, register, allocation, result, return, signal or affinity is replaced.'
OBSERVER=parent.OBSERVER+r'''
exit_inputs=None;exit_calls=[];exit_active=[];exit_watch=[]
def exit_symbol(name):
 value=gdb.parse_and_eval(name);return dict(address=int(value.address),size=int(value.type.sizeof))
def exit_field(typ,name):
 field=next(f for f in typ.fields()if f.name==name)
 return dict(offset=int(field.bitpos)//8,bit=int(field.bitpos)%8,bits=int(field.bitsize),size=int(field.type.sizeof))
_exit_initial_snapshot=allocator_snapshot
def allocator_snapshot(label):
 global exit_inputs,exit_watch
 _exit_initial_snapshot(label)
 if label=='driver_entry':
  ctx=transition_inputs['loader_context'];regions=[]
  def include(p,n):
   if not p or not n:return
   if any(r['address']==p and r['size']==n for r in regions):return
   regions.append(dict(address=p,size=n));ctx['regions'].append(dict(address=p,data=mem(p,n).hex()))
  controls={name:exit_symbol(name)for name in('__exit_funcs','__exit_funcs_lock','__exit_funcs_done','__new_exitfn_called','tls_dtor_list','__quick_exit_funcs','_rtld_global','_rtld_global_ro')}
  for item in controls.values():include(item['address'],item['size'])
  list_type=gdb.lookup_type('struct exit_function_list');function_type=gdb.lookup_type('struct exit_function');assert(list_type.sizeof,function_type.sizeof)==(520,16)
  guard=u32(ctx['tls_base']+24);functions=[]
  for head in('__exit_funcs','__quick_exit_funcs'):
   p=u32(controls[head]['address']);seen=set()
   while p:
    if p in seen:raise RuntimeError('Cyclic earlier exit list')
    seen.add(p);include(p,int(list_type.sizeof));count=u32(p+4)
    if count>32:raise RuntimeError('Earlier exit list index exceeds its structure')
    if head=='__exit_funcs':
     for i in range(count):
      f=p+8+16*i;flavor=u32(f)
      if flavor in(2,3,4):
       encoded=u32(f+4);pointer=(((encoded>>9)|(encoded<<23))&0xffffffff)^guard
       functions.append(dict(address=f,flavor=flavor,function=pointer));exit_watch.append(pointer)
    p=u32(p)
  block=gdb.block_for_pc(int(gdb.parse_and_eval('&_dl_lookup_symbol_x')));link_type=gdb.lookup_type('struct link_map',block)
  link_fields={name:exit_field(link_type,name)for name in('l_next','l_real','l_idx','l_init_called','l_direct_opencount','l_initfini','l_reldeps','l_visited','l_faked','l_main_map','l_auditing','l_tls_dtor_count')}
  rtld=gdb.parse_and_eval('_rtld_global');rtld_ro=gdb.parse_and_eval('_rtld_global_ro');ns=rtld['_dl_ns']
  thread=gdb.Value(ctx['tls_base']).cast(gdb.lookup_type('struct pthread').pointer()).dereference()
  controls['thread_tid']=dict(address=int(thread['tid'].address),size=int(thread['tid'].type.sizeof));include(controls['thread_tid']['address'],controls['thread_tid']['size'])
  fini=[];maps=[];all_seen=set()
  for namespace in range(int(rtld['_dl_nns'])):
   cursor=int(ns[namespace]['_ns_loaded'])
   while cursor:
    if cursor in all_seen:raise RuntimeError('Cyclic or aliased earlier loader namespace list')
    all_seen.add(cursor);link=gdb.Value(cursor).cast(link_type.pointer()).dereference();base=u32(cursor);include(cursor,int(link_type.sizeof))
    maps.append(dict(address=cursor,name=string(int(link['l_name']))[:-1].decode(errors='surrogateescape'),namespace=namespace))
    p=int(link['l_initfini'])
    if p:
     i=0
     while u32(p+4*i):i+=1
     include(p,4*(i+1))
    p=int(link['l_reldeps'])
    if p:include(p,4+4*int(link['l_reldeps']['act']))
    info=link['l_info'];array=int(info[26]);length=int(info[28]);old=int(info[13]);callbacks=[]
    for pointer in(array,length,old):
     if pointer:include(pointer,8)
    if array:
     start=base+u32(array+4);size=u32(length+4);include(start,size)
     callbacks+=[u32(start+offset)for offset in reversed(range(0,size,4))]
    if old:callbacks.append(base+u32(old+4))
    fini.append(dict(map=cursor,callbacks=callbacks));exit_watch.extend(callbacks)
    cursor=int(link['l_next'])
  exit_inputs=dict(controls=controls,regions=regions,functions=functions,fini=fini,maps=maps,link_fields=link_fields,rtld_fields={name:exit_field(rtld.type,name)for name in('_dl_ns','_dl_nns','_dl_load_lock')},rtld_ro_fields={name:exit_field(rtld_ro.type,name)for name in('_dl_dso_sort_algo','_dl_naudit','_dl_debug_mask')},namespace_size=int(ns[0].type.sizeof),namespace_fields={name:exit_field(ns[0].type,name)for name in('_ns_loaded','_ns_nloaded')},sort_algorithm=int(rtld_ro['_dl_dso_sort_algo']))
  transition_inputs['exit_inputs']=exit_inputs
_exit_state_parent=cleanup_state
def exit_state(label):
 result=_exit_state_parent(label)
 for region in exit_inputs['regions']:result['regions'].append(dict(address=region['address'],data=mem(region['address'],region['size']).hex()))
 return result
class ExitReturn(gdb.Breakpoint):
 def __init__(self,pc,item):self.item=item;super().__init__('*'+hex(pc),internal=True)
 def stop(self):
  if 'after'in self.item or reg('esp')!=self.item['before']['registers']['esp']+4:return False
  self.item['after']=exit_state(self.item['kind']+'.return');self.enabled=False;return False
class ExitCall(gdb.Breakpoint):
 def __init__(self,pc,kind,returns=True):self.kind=kind;self.returns=returns;super().__init__(pc,internal=True)
 def stop(self):
  if not shutdown_active:return False
  item=dict(kind=self.kind,pc=reg('pc'),arguments=[u32(reg('esp')+4*i)for i in range(1,4)],before=exit_state(self.kind+'.entry'));exit_calls.append(item)
  if self.returns:ExitReturn(u32(reg('esp')),item)
  return False
_exit_shutdown_begin=shutdown_begin
def shutdown_begin():
 _exit_shutdown_begin();ExitCall('exit','exit',False)
 for pc in sorted(set(v['function']for v in exit_inputs['functions'])):ExitCall('*'+hex(pc),'registered')
 for pc in sorted(set(v for item in exit_inputs['fini']for v in item['callbacks'])):ExitCall('*'+hex(pc),'fini')
 for symbol,kind in(('_dl_fini','loader'),('_dl_call_fini','object')):ExitCall(symbol,kind)
_exit_shutdown_finish=shutdown_finish
def shutdown_finish():
 _exit_shutdown_finish();shutdown['exit_calls']=exit_calls
'''


def commands(directory,observer=OBSERVER):return parent.commands(directory,observer)


def main():
    p=argparse.ArgumentParser(add_help=False);p.add_argument('--cc',default='cc');own,remaining=p.parse_known_args();sys.argv=[sys.argv[0],*remaining]
    cpu=integer_cpu(own.cc);byte=byte_cpu(own.cc);regions={};malloc=dict(complete_regions_checked=0,bytes_checked=0,reference=parent.parent.PROJECTION_REFERENCE);cleanup=dict(complete_regions_checked=0,bytes_checked=0,reference=parent.parent.PROJECTION_REFERENCE);exit_projection=dict(complete_regions_checked=0,bytes_checked=0,reference=parent.parent.PROJECTION_REFERENCE)
    def pack(point,heap_pages,projection):
        for region in point['regions']:
            raw=bytes.fromhex(region.pop('data'));packed=heap_pages(raw)
            if(packed['size'],packed['sha256'],packed['pages'])!=(len(raw),hashlib.sha256(raw).hexdigest(),[hashlib.sha256(raw[o:o+4096]).hexdigest()for o in range(0,len(raw),4096)]):raise ValueError('Exit projection changed a complete native region')
            region.update(packed,page_bank='driver_heap_pages');projection['complete_regions_checked']+=1;projection['bytes_checked']+=len(raw)
    def project(case,heap_pages,file_pages):
        stdio=case['transition_inputs']['stdio_context'];stdio['sar31_af']=cpu['sar31_af'];stdio['input_abi']['shr1_af']=byte['shr1_af']
        checked,total=parent.parent.project_malloc(case,heap_pages,file_pages,regions);malloc['complete_regions_checked']+=checked;malloc['bytes_checked']+=total
        for call in case['shutdown']['cleanup']:
            for point in [call[k]for k in('before','after')if k in call]+[v['state']for v in call.get('free',[])]:pack(point,heap_pages,cleanup)
        for call in case['shutdown']['exit_calls']:
            for phase in('before','after'):
                if phase in call:pack(call[phase],heap_pages,exit_projection)
    driver=parent.parent.parent.parent.parent.second.command.shunt.shunt.driver
    driver.main(fixture_name='shunt_exit_original.json.gz',parent_name='shunt_cleanup_original.json.gz',job_factory=parent.parent.parent.parent.parent.second.command.shunt.shunt.jobs,
        observer=OBSERVER,command_builder=commands,state_fields=('allocator_states','post_states','transition_states'),buffer_fields=('post_buffers','transition_buffers'),project_extra_case=project,
        extra_metadata=dict(loader_regions=regions,malloc_projection=malloc,cleanup_projection=cleanup,exit_projection=exit_projection,integer_cpu=cpu,byte_cpu=byte,shunt_exit_reference=REFERENCE))

    from exit_fixture import factor_file,externalize_file
    factor_file(ROOT/'tests/fixtures/shunt_exit_original.json.gz')
    externalize_file(ROOT/'tests/fixtures/shunt_exit_original.json.gz')


if __name__=='__main__':main()
