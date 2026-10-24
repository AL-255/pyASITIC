"""Read-only earlier stream bindings and independently observed console calls."""
import capture_driver_history_original as driver

OBSERVER=driver.OBSERVER+r'''
console_inputs=None;console_calls=[]
_console_snapshot=allocator_snapshot
def console_string(address):
 data=bytearray()
 while True:
  value=mem(address+len(data),1)
  if value==b'\0':return bytes(data).hex()
  data+=value
  assert len(data)<16384
def allocator_snapshot(label):
 global console_inputs
 _console_snapshot(label)
 if label=='driver_entry':
  recording=bool(mem(0x80cbab8,1)[0]);streams={}
  for name,global_address in (('stdout',0x80d7d68),('log',0x80d7e28),('recording',0x80d7e1c)):
   if name=='recording'and not recording:continue
   address=u32(global_address)
   streams[name]=dict(address=address,data=mem(address,36).hex())if address else None
  console_inputs=dict(streams=streams,recording=recording,progress=bool(mem(0x80ce5c0,1)[0]),timing=bool(mem(0x80ce5c1,1)[0]),matrix_dump=bool(mem(0x80ce5c2,1)[0]),directory=console_string(0x80d8a00),technology_name=console_string(0x80d8920))
class ConsoleCall(gdb.Breakpoint):
 def __init__(self,address,kind):
  self.kind=kind;super().__init__('*'+hex(address),internal=True)
 def stop(self):
  if console_inputs is not None:
   esp=reg('esp');record=dict(kind=self.kind,text=console_string(u32(esp+4)),setup_events=len(setup_events),prefix_events=len(prefix_events),events=len(events))
   if self.kind in ('message','error'):record['to_log']=bool(mem(esp+8,1)[0])
   console_calls.append(record)
  return False
for address,kind in ((0x804bf74,'status'),(0x804bf94,'output'),(0x804bffc,'message'),(0x804c070,'error')):ConsoleCall(address,kind)
'''


def commands(directory,observer=OBSERVER):
    text=driver.commands(directory,observer);before='result=dict(workspace_storage='
    assert text.count(before)==1
    return text.replace(before,'result=dict(console_inputs=console_inputs,console_calls=console_calls,workspace_storage=')


def main(*,extended=False):
    from capture_prelude_storage_extended_original import jobs
    suffix='_extended'if extended else''
    driver.main(fixture_name=f'console_storage{suffix}_original.json.gz',parent_name=f'driver_history{suffix}_original.json.gz',job_factory=jobs if extended else None,
                observer=OBSERVER,command_builder=commands,
                extra_metadata=dict(console_storage_reference='All unchanged driver histories and outcomes retained. Driver-entry stream bindings, common 36-byte FILE prefix, progress/timing/dump/recording controls and cache path strings are earlier inputs. Native console call kind/text/logging flag and event positions are independent comparison outputs only. No inferior call, instruction, returned pointer or memory store is replaced. Full-heap comparisons keep every byte.'))


if __name__=='__main__':main()
