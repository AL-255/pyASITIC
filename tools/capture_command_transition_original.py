"""Read-only script/port setup between first driver return and next entry/fault."""
import hashlib
import capture_node_history_original as node

OBSERVER=(node.OBSERVER
          .replace("for event in events+[e for e in post_events if e.get('returned')]:", "for event in events+[e for e in post_events+transition_events if e.get('returned')]:")
          .replace('global post_active,post_driver\n','global post_active,post_driver,transition_active,transition_console_start\n')
          .replace("post_active=False;return True", "post_active=False;transition_console_start=len(console_calls);transition_active=True;return True"))+r'''
transition_inputs=None;transition_active=False;transition_console_start=None;transition_events=[];transition_states=[];transition_buffers=[]
transition_pending={};transition_returns={};transition_interfaces=[];transition_end=None;transition_calendar=[];transition_points=[]
_transition_snapshot=allocator_snapshot
def transition_regions():
 workspace=transition_inputs['workspace_address']
 return [dict(address=workspace,data=mem(workspace,4460).hex()),dict(address=0x80d8660,data=mem(0x80d8660,120).hex())]
def allocator_snapshot(label):
 global transition_inputs
 _transition_snapshot(label)
 if label=='driver_entry':
  state=allocator_states[-1];esp=reg('esp');frame=reg('ebp');workspace=u32(frame+12)
  assert bytes.fromhex(console_string(workspace))in (b'PI2',b'CALCTRANS')
  stack=next(m for m in state['maps']if m['path']=='[stack]');regions=[dict(address=stack['start'],data=mem(stack['start'],stack['end']-stack['start']).hex()),dict(address=0x80d8660,data=mem(0x80d8660,120).hex())]
  script=None;pointer=libio_inputs['list_head'];seen=set();layout=libio_inputs['file']['fields']
  while pointer:
   assert pointer not in seen;seen.add(pointer);fd=i32(pointer+layout['_fileno']['offset'])
   try:path=os.readlink('/proc/%d/fd/%d'%(gdb.selected_inferior().pid,fd))
   except OSError:path=None
   if path and path.endswith('/input.asit'):script=dict(address=pointer,data=mem(pointer,148).hex())
   pointer=u32(pointer+layout['_chain']['offset'])
  assert script is not None
  stdin_global=int(gdb.parse_and_eval('&stdin'));stdin_address=u32(stdin_global)
  old_tz_global=int(gdb.parse_and_eval('&old_tz'));old_tz=u32(old_tz_global)
  character_tables=dict(classification=mem(u32(0x80d7dd8)-256,768).hex(),uppercase=mem(u32(0x80d7dc0)-512,1536).hex(),lowercase=mem(u32(0x80d7cb0)-512,1536).hex())
  regions.extend((dict(address=stdin_address,data=mem(stdin_address,36).hex()),dict(address=old_tz_global,data=mem(old_tz_global,4).hex()),dict(address=libio_inputs['libc_symbols']['_IO_list_all']['address'],data=struct.pack('<I',libio_inputs['list_head']).hex())))
  environment={item.split(b'=',1)[0].decode():item.split(b'=',1)[1].decode()for item in open('/proc/%d/environ'%gdb.selected_inferior().pid,'rb').read().split(b'\0')if item}
  assert not set(environment)-{'PATH','HOME','LANG','LC_ALL','LD_LIBRARY_PATH','TERM','INPUTRC','LINES','COLUMNS','PWD','SHLVL','_'}
  transition_inputs=dict(workspace_address=workspace,registers={name:reg(name)for name in ('esp','ebp','ebx','esi','edi')},initial_regions=regions,script_stream=script,stdin_stream=dict(address=stdin_address,data=mem(stdin_address,36).hex(),file_data=open('answers.txt','rb').read().hex()),environment=environment,repl=dict(history_enabled=bool(mem(0x80d7e05,1)[0]),input_log=u32(0x80d7e24),line_address=0x80d7e40),character_tables=character_tables,timezone=dict(environment=environment.get('TZ'),tzfile=open('/etc/localtime','rb').read().hex(),old_tz_global=old_tz_global,old_tz=old_tz,old_tz_data=console_string(old_tz)))
def transition_snapshot(label):
 allocator_snapshot(label);state=allocator_states.pop();state['transition_event_count']=len(transition_events);state['component_regions']=transition_regions();transition_states.append(state)
class TransitionReturn(gdb.Breakpoint):
 def __init__(self,address):
  self.address=address;super().__init__('*'+hex(address),internal=True)
 def stop(self):
  if transition_active:
   if self.address in transition_pending and transition_pending[self.address]:
    item=transition_pending[self.address].pop();item['returned']=True
    if item['kind']=='allocate':item['address']=reg('eax')
   if transition_interfaces and transition_interfaces[-1][0]==self.address:transition_interfaces.pop()
  return False
def transition_return(address):
 if address not in transition_returns:transition_returns[address]=TransitionReturn(address)
class TransitionCalendarDone(gdb.Breakpoint):
 def __init__(self,address,record):
  self.record=record;super().__init__('*'+hex(address),internal=True,temporary=True)
 def stop(self):
  self.record['text']=console_string(reg('eax'));return False
class Transition(gdb.Breakpoint):
 def __init__(self,spec,kind):
  self.kind=kind;super().__init__(spec,internal=True)
 def stop(self):
  global transition_active,transition_end
  if not transition_active:return False
  esp=reg('esp');caller=u32(esp)
  if self.kind=='driver':
   driver='pi2'if reg('pc')==0x8050b2c else'calctrans'
   transition_end=dict(driver=driver,arguments=[u32(esp+4),u32(esp+8)]+([u32(esp+12)]if driver=='calctrans'else[]),registers={name:reg(name)for name in ('esp','ebp','ebx','esi','edi')},files=[dict(name=n,data=open(n,'rb').read().hex())for n in sorted(n for n in os.listdir('.')if n.endswith('.out'))])
   transition_snapshot('next_driver');transition_active=False;return True
  if self.kind in ('array','scalar'):
   transition_interfaces.append((caller,self.kind));transition_return(caller)
  elif self.kind in ('malloc','calloc'):
   request=u32(esp+4)*(u32(esp+8)if self.kind=='calloc'else 1)
   item=dict(kind='allocate',allocator=transition_interfaces[-1][1]if transition_interfaces else self.kind,request=request,caller=caller)
   transition_events.append(item);transition_pending.setdefault(caller,[]).append(item);transition_return(caller)
  elif self.kind=='free':
   pointer=u32(esp+4);index=len(transition_events)
   if pointer:
    word=u32(pointer-4);size=(word&~7)-(8 if word&2 else 4)
    transition_buffers.append(dict(event_index=index,address=pointer,size=size,data=mem(pointer,size).hex()))
   item=dict(kind='free',allocator=transition_interfaces[-1][1]if transition_interfaces else'malloc',address=pointer,caller=caller)
   transition_events.append(item);transition_pending.setdefault(caller,[]).append(item);transition_return(caller)
  elif self.kind=='calendar':
   pointer=u32(esp+4);record=dict(address=pointer,data=mem(pointer,4).hex(),frame=reg('ebp'),events=len(transition_events))
   transition_calendar.append(record);TransitionCalendarDone(caller,record)
  elif self.kind in ('header','parse'):
   transition_points.append(dict(kind=self.kind,esp=esp,ebp=reg('ebp'),events=len(transition_events),regions=transition_regions(),timestamp_address=esp-8,timestamp_data=mem(esp-8,4).hex()))
  return False
for address,kind in ((0x8050b2c,'driver'),(0x8051280,'driver'),(0x804ab74,'array'),(0x804adb4,'scalar'),(0x804ac74,'array'),(0x804ad84,'scalar'),(0x804abd4,'calendar'),(0x808aafc,'header'),(0x8086fc0,'parse')):Transition('*'+hex(address),kind)
Transition('__libc_malloc','malloc');Transition('__libc_calloc','calloc');Transition('__libc_free','free')
'''


def commands(directory,observer=OBSERVER):
    text=node.commands(directory,observer)
    before="signal=0\nif post_driver is None and gdb.selected_inferior().pid:"
    assert text.count(before)==1
    text=text.replace(before,"if post_driver is not None and gdb.selected_inferior().pid:gdb.execute('continue')\nsignal=0\nif transition_end is None and gdb.selected_inferior().pid:")
    before='result=dict(post_events='
    assert text.count(before)==1
    return text.replace(before,"if transition_active and gdb.selected_inferior().pid:transition_snapshot('transition_fault')\ntransition_calls=[]if transition_console_start is None else console_calls[transition_console_start:]\nif transition_console_start is not None:console_calls=console_calls[:transition_console_start]\nresult=dict(transition_inputs=transition_inputs,transition_events=transition_events,transition_states=transition_states,transition_buffers=transition_buffers,transition_calls=transition_calls,transition_calendar=transition_calendar,transition_points=transition_points,transition_end=transition_end,transition_pending=sum(map(len,transition_pending.values())),transition_interfaces=len(transition_interfaces),post_events=")


def expand_case(fixture,entry):
    case=node.expand_case(fixture,entry)
    def region(record):
        data=b''.join(bytes.fromhex(fixture['driver_heap_pages'][key])for key in record['pages'])
        assert len(data)==record['size']and hashlib.sha256(data).hexdigest()==record['sha256']
        return dict(record,data=data.hex())
    case['transition_states']=[dict(state,memory_regions=[region(r)for r in state['memory_regions']])for state in case['transition_states']]
    case['transition_buffers']=[region(record)for record in case['transition_buffers']]
    def component(r):
        if 'data'in r:return r
        from audit_loader_lookup_original import data
        return dict(address=r['address'],data=data(fixture,r).hex())
    case['transition_states']=[dict(s,component_regions=[component(r)for r in s['component_regions']])for s in case['transition_states']]
    case['transition_points']=[dict(p,regions=[component(r)for r in p['regions']])for p in case['transition_points']]
    return case


def main(*,extended=False):
    from capture_prelude_storage_extended_original import jobs
    suffix='_extended'if extended else''
    node.console.driver.main(fixture_name=f'command_transition{suffix}_original.json.gz',parent_name=f'node_history{suffix}_original.json.gz',job_factory=jobs if extended else None,observer=OBSERVER,command_builder=commands,
                             state_fields=('allocator_states','post_states','transition_states'),buffer_fields=('post_buffers','transition_buffers'),
                             extra_metadata=dict(command_transition_reference='All unchanged histories and all native outcomes retained. Initial driver-entry stack, script FILE and port settings are earlier inputs. Continue the original first driver through direct script parsing and port-file setup to next driver entry or native fault. Complete later heaps, component regions, raw returned allocation/free calls, every freed usable byte, console calls, output file bytes and header-calendar operands/results are comparison outputs only. No inferior instruction, memory, return value or allocation result is replaced.'))


if __name__=='__main__':main()
