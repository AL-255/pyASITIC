"""Read-only continuation from node entry through the first driver return/fault."""
import hashlib
import capture_console_storage_original as console

OBSERVER=(console.OBSERVER.replace('console_calls.append(record)',"record['post_events']=len(post_events);console_calls.append(record)")
          .replace('for event in events:\n',"for event in events+[e for e in post_events if e.get('returned')]:\n"))+r'''
post_events=[];post_states=[];post_buffers=[];post_active=False;post_seen=False;post_pending={};post_returns={};post_interfaces=[]
post_node=None;post_output=None;post_driver=None;post_driver_seen=False;post_node_done=False
def post_snapshot(label):
 allocator_snapshot(label);state=allocator_states.pop();state['post_event_count']=len(post_events);post_states.append(state)
def post_ports():return [dict(address=address,data=mem(address,16).hex())for address in (0x80d8da8,0x80d8db8,0x80d8dd8,0x80d8de8)]
class PostReturn(gdb.Breakpoint):
 def __init__(self,address):
  self.address=address;super().__init__('*'+hex(address),internal=True)
 def stop(self):
  if post_active:
   if self.address in post_pending and post_pending[self.address]:
    item=post_pending[self.address].pop();item['returned']=True
    if item['kind']=='allocate':item['address']=reg('eax')
   if post_interfaces and post_interfaces[-1][0]==self.address:post_interfaces.pop()
  return False
def post_return(address):
 if address not in post_returns:post_returns[address]=PostReturn(address)
class NodeDone(gdb.Breakpoint):
 def stop(self):
  global post_node_done,post_output
  if not post_active or post_node_done:return False
  post_node_done=True
  post_output=dict(status=reg('eax')&255,ports=post_ports(),capacitance=mem(post_node['cap_address'],16*post_node['size']**2).hex())
  post_snapshot('node_return');return False
class DriverDone(gdb.Breakpoint):
 def stop(self):
  global post_active,post_driver
  if not post_active:return False
  post_driver=dict(status=reg('eax')&255,ports=post_ports());post_snapshot('driver_return');post_active=False;return True
class PostNode(gdb.Breakpoint):
 def __init__(self,spec,kind):
  self.kind=kind;super().__init__(spec,internal=True)
 def stop(self):
  global post_active,post_seen,post_node,post_driver_seen
  esp=reg('esp')
  if self.kind=='driver':
   if not post_driver_seen:post_driver_seen=True;DriverDone('*'+hex(u32(esp)),internal=True)
   return False
  if self.kind=='node':
   if post_seen:return False
   post_seen=True;post_active=True;post_node=dict(cap_address=u32(esp+4),ind_address=u32(esp+8),size=u32(esp+12),ports=post_ports())
   NodeDone('*'+hex(u32(esp)),internal=True);return False
  if not post_active:return False
  if self.kind in ('array','scalar'):
   caller=u32(esp);post_interfaces.append((caller,self.kind));post_return(caller)
  elif self.kind=='malloc':
   caller=u32(esp);item=dict(kind='allocate',allocator=post_interfaces[-1][1]if post_interfaces else'malloc',request=u32(esp+4),caller=caller)
   post_events.append(item);post_pending.setdefault(caller,[]).append(item);post_return(caller)
  elif self.kind=='free':
   pointer=u32(esp+4);index=len(post_events)
   if pointer:
    allocation=next(event for event in reversed(events+post_events)if event['kind']=='allocate'and event.get('address')==pointer)
    post_buffers.append(dict(event_index=index,address=pointer,size=allocation['request'],data=mem(pointer,allocation['request']).hex()))
   caller=u32(esp);item=dict(kind='free',allocator=post_interfaces[-1][1]if post_interfaces else'malloc',address=pointer,caller=caller)
   post_events.append(item);post_pending.setdefault(caller,[]).append(item);post_return(caller)
   if not post_node_done and len(post_buffers)==1:post_snapshot('node_release')
  return False
PostNode('*0x8050b2c','driver');PostNode('*0x8051280','driver');PostNode('*0x8053e00','node')
for address,kind in ((0x804ab74,'array'),(0x804adb4,'scalar'),(0x804ac74,'array'),(0x804ad84,'scalar')):PostNode('*'+hex(address),kind)
PostNode('__libc_malloc','malloc');PostNode('__libc_free','free')
'''


def commands(directory,observer=OBSERVER):
    text=console.commands(directory,observer)
    before='signal=0\nif node is None and gdb.selected_inferior().pid:'
    assert text.count(before)==1
    text=text.replace(before,"if node is not None and gdb.selected_inferior().pid:gdb.execute('continue')\nsignal=0\nif post_driver is None and gdb.selected_inferior().pid:")
    before='result=dict(console_inputs='
    assert text.count(before)==1
    return text.replace(before,"if post_seen and post_driver is None and gdb.selected_inferior().pid:post_snapshot('post_fault')\nresult=dict(post_events=post_events,post_states=post_states,post_buffers=post_buffers,post_node=post_node,post_output=post_output,post_driver=post_driver,post_pending=sum(map(len,post_pending.values())),post_interfaces=len(post_interfaces),console_inputs=")


def expand_case(fixture,entry):
    case=console.driver.expand_case(fixture,entry)
    def region(record):
        data=b''.join(bytes.fromhex(fixture['driver_heap_pages'][key])for key in record['pages'])
        assert len(data)==record['size']and hashlib.sha256(data).hexdigest()==record['sha256']
        return dict(record,data=data.hex())
    case['post_states']=[dict(state,memory_regions=[region(r)for r in state['memory_regions']])for state in case['post_states']]
    case['post_buffers']=[region(record)for record in case['post_buffers']]
    return case


def main(*,extended=False):
    from capture_prelude_storage_extended_original import jobs
    suffix='_extended'if extended else''
    console.driver.main(fixture_name=f'node_history{suffix}_original.json.gz',parent_name=f'console_storage{suffix}_original.json.gz',job_factory=jobs if extended else None,
                        observer=OBSERVER,command_builder=commands,state_fields=('allocator_states','post_states'),buffer_fields=('post_buffers',),
                        extra_metadata=dict(node_history_reference='Every unchanged parent history retained. Original first-node stop is followed by read-only continuation to first driver return or native fault. Observe all node/cleanup raw libc allocations and frees, every freed array byte, complete heaps before node release/after node return/after driver return, native ports and full CAP mutation. No inferior call, instruction, allocation result, return or byte is replaced. All later outputs are comparison-only.'))


if __name__=='__main__':main()
