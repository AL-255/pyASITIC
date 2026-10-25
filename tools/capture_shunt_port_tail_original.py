"""Read-only port record, fclose and export return after both branch solves."""
import capture_shunt_second_driver_original as second

OBSERVER=second.OBSERVER+r'''
port_tail=None;tail_events=[];tail_buffers=[];tail_states=[];tail_printf=[];tail_pending={};tail_returns={};tail_end=None;tail_file=None;tail_active=False
_tail_initial_snapshot=allocator_snapshot
def allocator_snapshot(label):
 _tail_initial_snapshot(label)
 if label=='driver_entry':
  transition_inputs['initial_regions'].extend(dict(address=a,data=mem(a,16).hex())for a in(0x80d8d58,0x80d8d28,0x80d8d48,0x80d8d18))
  import ctypes
  host=ctypes.CDLL(None,use_errno=True);host.ptrace.argtypes=[ctypes.c_ulong,ctypes.c_int,ctypes.c_void_p,ctypes.c_void_p];host.ptrace.restype=ctypes.c_long
  descriptor=ctypes.create_string_buffer(16)
  if host.ptrace(25,gdb.selected_inferior().pid,reg('gs')>>3,ctypes.byref(descriptor)):raise OSError(ctypes.get_errno())
  tls=struct.unpack_from('<I',descriptor.raw,4)[0]
  transition_inputs['port_tail_abi']=dict(tls_base=tls)
  transition_inputs['initial_regions'].append(dict(address=tls,data=mem(tls,16).hex()))
def tail_snapshot(label):
 n=second_namespace;n['allocator_snapshot'](label);state=n['allocator_states'].pop();state['tail_event_count']=len(tail_events)
 state['component_regions']=[dict(address=a,data=mem(a,size).hex())for a,size in((tail_file,304),(u32(tail_file+28)if label not in('free.file','export_return')else tail_buffer,4096),(libio_inputs['libc_symbols']['_IO_list_all']['address'],4),*((a,16)for a in(0x80d8d58,0x80d8d28,0x80d8d48,0x80d8d18)))]
 tail_states.append(state)
class TailReturn(gdb.Breakpoint):
 def __init__(self,address):self.address=address;super().__init__('*'+hex(address),internal=True)
 def stop(self):
  if tail_active and tail_pending.get(self.address):
   event=tail_pending[self.address].pop();event['returned']=True
   if event['kind']=='allocate':event['address']=reg('eax')
  return False
class TailRecordReturn(gdb.Breakpoint):
 def stop(self):tail_snapshot('record_return');return False
class TailObserve(gdb.Breakpoint):
 def __init__(self,spec,kind):self.kind=kind;super().__init__(spec,internal=True)
 def stop(self):
  global tail_end,tail_active,tail_file,tail_buffer
  if not tail_active:return False
  esp=reg('esp');caller=u32(esp)
  if self.kind=='record':
   tail_file=u32(esp+4);tail_buffer=u32(tail_file+28);tail_snapshot('record_entry');TailRecordReturn('*'+hex(caller),internal=True,temporary=True)
  elif self.kind=='close':tail_snapshot('close_entry')
  elif self.kind=='printf':tail_printf.append(dict(file=u32(esp+4),format=console_string(u32(esp+8)),arguments=mem(esp+12,72).hex(),caller=caller,events=len(tail_events)))
  elif self.kind=='end':
   tail_snapshot('export_return');tail_end=dict(files=[dict(name=n,data=open(n,'rb').read().hex())for n in sorted(n for n in __import__('os').listdir('.')if n.endswith('.out'))]);tail_active=False;return True
  elif self.kind in('malloc','calloc','free'):
   event=dict(kind='free'if self.kind=='free'else'allocate',allocator=self.kind,caller=caller)
   if self.kind=='free':
    address=u32(esp+4);event['address']=address
    if address:
     word=u32(address-4);size=(word&~7)-(8 if word&2 else 4);tail_buffers.append(dict(event_index=len(tail_events),address=address,size=size,data=mem(address,size).hex()))
    tail_snapshot('free.buffer'if address==tail_buffer else'free.file')
   else:event['request']=u32(esp+4)*(u32(esp+8)if self.kind=='calloc'else 1)
   tail_events.append(event);tail_pending.setdefault(caller,[]).append(event)
   if caller not in tail_returns:tail_returns[caller]=TailReturn(caller)
  return False
def tail_begin():
 global tail_active
 for breakpoint in gdb.breakpoints():breakpoint.enabled=False
 tail_active=True
 for address,kind in((0x8088c9c,'record'),(0x804a754,'printf'),(0x804abc4,'close'),(0x805f369,'end'),(0x805f739,'end')):TailObserve('*'+hex(address),kind)
 TailObserve('__libc_malloc','malloc');TailObserve('__libc_calloc','calloc');TailObserve('__libc_free','free')
def tail_finish():
 global port_tail
 signal=0
 if tail_end is None and gdb.selected_inferior().pid:
  try:signal=int(gdb.parse_and_eval('$_siginfo.si_signo'))
  except gdb.error:pass
  tail_snapshot('tail_fault')
 port_tail=dict(events=tail_events,buffers=tail_buffers,states=tail_states,printf=tail_printf,end=tail_end,signal=signal,pending=sum(map(len,tail_pending.values())))
'''


def commands(directory,observer=OBSERVER):
    text=second.commands(directory,observer)
    before=' second_finish()\n'
    assert text.count(before)==1
    text=text.replace(before,before+" if second['post_driver']is not None and gdb.selected_inferior().pid:\n  tail_begin()\n  gdb.execute('continue')\n  tail_finish()\n")
    return text.replace('result=dict(second=second,','result=dict(port_tail=port_tail,second=second,')


def project_tail(case,heap_pages,file_pages):
    second.project_second(case,heap_pages,file_pages)
    tail=case['port_tail']
    if tail is None:return
    for state in tail['states']:
        for region in state['memory_regions']:region.update(heap_pages(bytes.fromhex(region.pop('data'))))
    for record in tail['buffers']:record.update(heap_pages(bytes.fromhex(record.pop('data'))))


if __name__=='__main__':
    second.command.shunt.shunt.driver.main(fixture_name='shunt_port_tail_original.json.gz',parent_name='shunt_second_driver_original.json.gz',job_factory=second.command.shunt.shunt.jobs,
        observer=OBSERVER,command_builder=commands,state_fields=('allocator_states','post_states','transition_states'),buffer_fields=('post_buffers','transition_buffers'),project_extra_case=project_tail,
        extra_metadata=dict(shunt_port_tail_reference='All fourteen unchanged scripts, each cold/warm, and original plain outcomes retained. Continue the same inferior after the second solve through native S-parameter conversion/record, fclose and port-export return, or original fault. Earlier first-driver S globals are explicit inputs. Every later heap, FILE/buffer/global byte, freed usable byte, printf format/argument, event and complete output file is an assertion target. No inferior instruction, value, allocation, register, byte, result, return or affinity is replaced.'))
