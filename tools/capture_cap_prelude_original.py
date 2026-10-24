"""Read-only contact/cache allocator history preceding CAP matrix creation."""
import hashlib
import capture_allocator_original as arena
from capture_mapping_allocator_original import OBSERVER as MAPPING_OBSERVER

OBSERVER=MAPPING_OBSERVER+r'''
prefix_events=[];prefix_active=False;prefix_seen=False;prefix_pending={};prefix_returns={};prefix_interfaces=[]
class PrefixReturn(gdb.Breakpoint):
 def __init__(self,address):
  self.address=address;super().__init__('*'+hex(address),internal=True)
 def stop(self):
  if prefix_active:
   if self.address in prefix_pending and prefix_pending[self.address]:prefix_pending[self.address].pop()['address']=reg('eax')
   if prefix_interfaces and prefix_interfaces[-1][0]==self.address:prefix_interfaces.pop()
  return False
def prefix_return(address):
 if address not in prefix_returns:prefix_returns[address]=PrefixReturn(address)
class Prelude(gdb.Breakpoint):
 def __init__(self,spec,kind):
  self.kind=kind;super().__init__(spec,internal=True)
 def stop(self):
  global prefix_active,prefix_seen
  esp=reg('esp');pc=reg('pc')
  if self.kind=='begin':
   if prefix_seen:return False
   prefix_seen=True;prefix_active=True
   allocator_snapshot('contacts_entry')
   state=allocator_states[-1];state['prefix_event_count']=len(prefix_events)
   state['io_abi']=dict(file_plus=int(gdb.lookup_type('struct _IO_FILE_plus').sizeof),wide_data=int(gdb.lookup_type('struct _IO_wide_data').sizeof),lock=int(gdb.parse_and_eval('sizeof(_IO_stdfile_0_lock)')),buffer_default=8192,filesystem_block_size=os.stat('.').st_blksize)
  elif self.kind=='end':
   prefix_active=False
  elif not prefix_active:return False
  elif self.kind in('array','scalar'):
   caller=u32(esp);prefix_interfaces.append((caller,self.kind));prefix_return(caller)
  elif self.kind=='malloc':
   caller=u32(esp);item=dict(kind='allocate',request=u32(esp+4),allocator=prefix_interfaces[-1][1]if prefix_interfaces else'malloc',caller=caller)
   prefix_events.append(item);prefix_pending.setdefault(caller,[]).append(item);prefix_return(caller)
  elif self.kind=='free':
   pointer=u32(esp+4)
   prefix_events.append(dict(kind='free',address=pointer,chunk_size=(u32(pointer-4)&~7)if pointer else None,allocator=prefix_interfaces[-1][1]if prefix_interfaces else'malloc',caller=u32(esp)))
  return False
Prelude('*0x8053580','begin');Prelude('*0x8052ec7','end')
for address,kind in ((0x804ab74,'array'),(0x804adb4,'scalar'),(0x804ac74,'array'),(0x804ad84,'scalar')):Prelude('*'+hex(address),kind)
gdb.execute('set breakpoint pending on')
Prelude('__libc_malloc','malloc');Prelude('__libc_free','free')
'''


def commands(debug_directory,observer=OBSERVER):
    text=arena.commands(debug_directory,observer)
    before='result=dict(allocator_states=allocator_states,events=events,'
    assert text.count(before)==1
    return text.replace(before,'result=dict(prefix_events=prefix_events,prefix_pending=sum(map(len,prefix_pending.values())),prefix_interfaces=len(prefix_interfaces),allocator_states=allocator_states,events=events,')


if __name__=='__main__':
    parent=arena.lifetime.ROOT/'tests/fixtures/allocator_mappings_original.json.gz'
    arena.main(observer=OBSERVER,fixture_name='cap_prelude_original.json.gz',extra_metadata=dict(prelude_parent_sha256=hashlib.sha256(parent.read_bytes()).hexdigest()),command_builder=commands)
