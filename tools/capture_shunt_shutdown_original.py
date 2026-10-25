"""Read-only continuation from port export through script EOF and process exit."""
import capture_shunt_port_tail_original as parent

OBSERVER=parent.OBSERVER+r'''
shutdown=None;shutdown_active=False;shutdown_exit=None;shutdown_signal=0
shutdown_events=[];shutdown_buffers=[];shutdown_states=[];shutdown_calls=[]
shutdown_pending={};shutdown_returns={};shutdown_interfaces=[];shutdown_closing=None
_shutdown_initial_snapshot=allocator_snapshot
def allocator_snapshot(label):
 _shutdown_initial_snapshot(label)
 if label=='driver_entry':
  position=next(int(line.split(':',1)[1])for line in open('/proc/%d/fdinfo/0'%gdb.selected_inferior().pid)if line.startswith('pos:'))
  transition_inputs['stdin_stream']['file_position']=position
def shutdown_snapshot(label):
 n=second_namespace;n['allocator_snapshot'](label);state=n['allocator_states'].pop()
 state['shutdown_event_count']=len(shutdown_events)
 state['registers']={name:reg(name)for name in('eax','ebx','ecx','edx','esi','edi','ebp','esp','eip','eflags')}
 script=transition_inputs['script_stream']['address'];raw=bytes.fromhex(transition_inputs['script_stream']['data']);buffer=struct.unpack_from('<I',raw,28)[0]
 state['component_regions']=[dict(address=a,data=mem(a,size).hex())for a,size in((script,304),(buffer,4096),(libio_inputs['libc_symbols']['_IO_list_all']['address'],4),(transition_inputs['workspace_address'],4460))]
 shutdown_states.append(state)
class ShutdownReturn(gdb.Breakpoint):
 def __init__(self,address):self.address=address;super().__init__('*'+hex(address),internal=True)
 def stop(self):
  global shutdown_closing
  if not shutdown_active:return False
  if shutdown_pending.get(self.address):
   event=shutdown_pending[self.address].pop();event['returned']=True
   if event['kind']=='allocate':event['address']=reg('eax')
  if shutdown_interfaces and shutdown_interfaces[-1][0]==self.address:shutdown_interfaces.pop()
  return False
def shutdown_return(address):
 if address not in shutdown_returns:shutdown_returns[address]=ShutdownReturn(address)
class ShutdownObserve(gdb.Breakpoint):
 def __init__(self,spec,kind):self.kind=kind;super().__init__(spec,internal=True)
 def stop(self):
  global shutdown_closing
  if not shutdown_active:return False
  esp=reg('esp');caller=u32(esp);script=transition_inputs['script_stream']['address'];buffer=struct.unpack_from('<I',bytes.fromhex(transition_inputs['script_stream']['data']),28)[0]
  if self.kind in('script.read','script.eof','script.return','interactive.parse','exit'):
   if self.kind=='interactive.parse'and reg('pc')!=0x8086fc0:return False
   shutdown_snapshot(self.kind)
  elif self.kind=='close':
   shutdown_closing=u32(esp+4)
   if shutdown_closing==script:shutdown_snapshot('script.close')
  elif self.kind in('array','scalar'):
   shutdown_interfaces.append((caller,self.kind));shutdown_return(caller)
  elif self.kind in('malloc','calloc','free'):
   event=dict(kind='free'if self.kind=='free'else'allocate',allocator=shutdown_interfaces[-1][1]if shutdown_interfaces else self.kind,caller=caller)
   if self.kind=='free':
    address=u32(esp+4);event['address']=address
    if address:
     word=u32(address-4);size=(word&~7)-(8 if word&2 else 4)
     shutdown_buffers.append(dict(event_index=len(shutdown_events),address=address,size=size,data=mem(address,size).hex()))
    if shutdown_closing==script and address in(buffer,script):shutdown_snapshot('script.free.buffer'if address==buffer else'script.free.file')
   else:event['request']=u32(esp+4)*(u32(esp+8)if self.kind=='calloc'else 1)
   shutdown_events.append(event);shutdown_pending.setdefault(caller,[]).append(event);shutdown_return(caller)
  elif self.kind in('status','output','message','error'):
   address=u32(esp+4);text=console_string(address);shutdown_calls.append(dict(kind=self.kind,text=text,to_log=bool(mem(esp+8,1)[0])if self.kind in('message','error')else False,events=len(shutdown_events)))
  return False
def shutdown_exited(event):
 global shutdown_exit
 if shutdown_active:shutdown_exit=getattr(event,'exit_code',None)
gdb.events.exited.connect(shutdown_exited)
def shutdown_begin():
 global shutdown_active
 for breakpoint in gdb.breakpoints():breakpoint.enabled=False
 shutdown_active=True
 for address,kind in((0x8060d4f,'script.read'),(0x8060d5b,'script.eof'),(0x804abc4,'close'),(0x8060d61,'script.return'),(0x8086fc0,'interactive.parse'),(0x804bf74,'status'),(0x804bf94,'output'),(0x804bffc,'message'),(0x804c070,'error'),(0x804ab74,'array'),(0x804adb4,'scalar'),(0x804ac74,'array'),(0x804ad84,'scalar')):ShutdownObserve('*'+hex(address),kind)
 for symbol,kind in(('__libc_malloc','malloc'),('__libc_calloc','calloc'),('__libc_free','free'),('exit','exit')):ShutdownObserve(symbol,kind)
def shutdown_finish():
 global shutdown,shutdown_signal
 if gdb.selected_inferior().pid:
  try:shutdown_signal=int(gdb.parse_and_eval('$_siginfo.si_signo'))
  except gdb.error:pass
  shutdown_snapshot('shutdown_fault')
 shutdown=dict(events=shutdown_events,buffers=shutdown_buffers,states=shutdown_states,calls=shutdown_calls,exit_code=shutdown_exit,signal=shutdown_signal,pending=sum(map(len,shutdown_pending.values())),interfaces=len(shutdown_interfaces),files=[dict(name=n,data=open(n,'rb').read().hex())for n in sorted(n for n in __import__('os').listdir('.')if n.endswith('.out'))])
'''


def commands(directory,observer=OBSERVER):
    text=parent.commands(directory,observer)
    before='  tail_finish()\n'
    assert text.count(before)==1
    text=text.replace(before,before+"  if port_tail['end']is not None and gdb.selected_inferior().pid:\n   shutdown_begin()\n   gdb.execute('continue')\n   shutdown_finish()\n")
    return text.replace('result=dict(port_tail=port_tail,','result=dict(shutdown=shutdown,port_tail=port_tail,')


def project_shutdown(case,heap_pages,file_pages):
    parent.project_tail(case,heap_pages,file_pages)
    shutdown=case['shutdown']
    if shutdown is None:return
    for state in shutdown['states']:
        for region in state['memory_regions']:region.update(heap_pages(bytes.fromhex(region.pop('data'))))
    for record in shutdown['buffers']:record.update(heap_pages(bytes.fromhex(record.pop('data'))))


if __name__=='__main__':
    parent.second.command.shunt.shunt.driver.main(fixture_name='shunt_shutdown_original.json.gz',parent_name='shunt_port_tail_original.json.gz',job_factory=parent.second.command.shunt.shunt.jobs,
        observer=OBSERVER,command_builder=commands,state_fields=('allocator_states','post_states','transition_states'),buffer_fields=('post_buffers','transition_buffers'),project_extra_case=project_shutdown,
        extra_metadata=dict(shunt_shutdown_reference='All fourteen unchanged scripts, cold/warm, retain their plain outcomes. Continue the same inferior from the second port-export return through script EOF/fclose, interactive QUIT, all allocator events and process exit or original fault. Every freed usable byte and complete boundary heap, FILE/buffer/list/workspace region, register, console call and output file is a later assertion target. No later snapshot supplies execution input. No inferior instruction, memory, register, allocation, result, return, signal or affinity is replaced.'))
