"""Read-only driver-to-contacts allocation and full geometry observations."""
import hashlib
import capture_allocator_original as arena
import capture_cap_prelude_original as prelude

OBSERVER=prelude.OBSERVER+r'''
setup_events=[];setup_active=False;setup_seen=False;setup_pending={};setup_returns={};setup_interfaces=[];setup_context=None;setup_output=None
def setup_shape(address):
 segments=[];p=u32(address+0xa8);seen=set()
 while p:
  assert p not in seen and len(seen)<20000;seen.add(p)
  children=[];child=u32(p+0xe8)
  while child:
   assert child not in seen and len(seen)<20000;seen.add(child)
   children.append(dict(address=child,data=mem(child,240).hex()));child=u32(child+0xe8)
  segments.append(dict(address=p,data=mem(p,240).hex(),children=children));p=u32(p+0xec)
 return dict(address=address,data=mem(address,188).hex(),segments=segments)
def setup_strings():
 chains=[]
 for i in range(16):
  chain=[];p=u32(0x80cf1c0+4*i);seen=set()
  while p:
   assert p not in seen and len(seen)<10000;seen.add(p)
   chain.append(dict(address=p,data=mem(p,8*(i+1)).hex()));p=u32(p)
  chains.append(chain)
 return dict(nil_address=0x80cf1a8,pool_address=0x80cf1c0,address=0x80cf1a8,data=mem(0x80cf1a8,100).hex(),chains=chains)
class SetupReturn(gdb.Breakpoint):
 def __init__(self,address):
  self.address=address;super().__init__('*'+hex(address),internal=True)
 def stop(self):
  if setup_active:
   if self.address in setup_pending and setup_pending[self.address]:setup_pending[self.address].pop()['address']=reg('eax')
   if setup_interfaces and setup_interfaces[-1][0]==self.address:setup_interfaces.pop()
  return False
def setup_return(address):
 if address not in setup_returns:setup_returns[address]=SetupReturn(address)
class GeometrySetup(gdb.Breakpoint):
 def __init__(self,spec,kind):
  self.kind=kind;super().__init__(spec,internal=True)
 def stop(self):
  global setup_active,setup_seen,setup_context,setup_output
  esp=reg('esp')
  if self.kind=='begin':
   if setup_seen:return False
   setup_seen=True;setup_active=True;driver='pi2'if reg('pc')==0x8050b2c else'calctrans'
   args=[u32(esp+4),u32(esp+8)]+([u32(esp+12)]if driver=='calctrans'else[])
   scene=[];head=u32(0x80ce558);p=head;seen=set()
   while p:
    assert p not in seen and len(seen)<100;seen.add(p);scene.append(setup_shape(p));p=u32(p+0xb0)
   setup_context=dict(driver=driver,arguments=args,head=head,scene=scene,control=reg('fctrl'))
   allocator_snapshot('driver_entry');allocator_states[-1]['setup_event_count']=len(setup_events)
   setup_context['memory_regions']=[dict(address=m['start'],data=mem(m['start'],m['end']-m['start']).hex())for m in allocator_states[-1]['maps']if m['path']=='[heap]']
   setup_context['strings']=setup_strings()
  elif self.kind=='end':
   if not setup_active:return False
   setup_active=False
   setup_output=dict(first=setup_shape(u32(esp+4)),second=setup_shape(u32(esp+8)),head=u32(0x80ce558),control=reg('fctrl'),strings=setup_strings())
  elif not setup_active:return False
  elif self.kind in('scalar','array'):
   caller=u32(esp);setup_interfaces.append((caller,self.kind));setup_return(caller)
  elif self.kind=='malloc':
   caller=u32(esp);item=dict(kind='allocate',request=u32(esp+4),allocator=setup_interfaces[-1][1]if setup_interfaces else'malloc',caller=caller)
   setup_events.append(item);setup_pending.setdefault(caller,[]).append(item);setup_return(caller)
  elif self.kind=='free':
   pointer=u32(esp+4);setup_events.append(dict(kind='free',address=pointer,allocator=setup_interfaces[-1][1]if setup_interfaces else'malloc',caller=u32(esp),chunk_size=(u32(pointer-4)&~7)if pointer else None))
  return False
GeometrySetup('*0x8050b2c','begin');GeometrySetup('*0x8051280','begin');GeometrySetup('*0x8053580','end')
for address,kind in ((0x804ab74,'array'),(0x804adb4,'scalar'),(0x804ac74,'array'),(0x804ad84,'scalar')):GeometrySetup('*'+hex(address),kind)
GeometrySetup('__libc_malloc','malloc');GeometrySetup('__libc_free','free')
'''


def commands(directory,observer=OBSERVER):
    text=prelude.commands(directory,observer);before='result=dict(prefix_events=prefix_events,'
    assert text.count(before)==1
    return text.replace(before,'result=dict(setup_events=setup_events,setup_context=setup_context,setup_output=setup_output,setup_pending=sum(map(len,setup_pending.values())),setup_interfaces=len(setup_interfaces),prefix_events=prefix_events,')


if __name__=='__main__':
    parent=arena.lifetime.ROOT/'tests/fixtures/cap_prelude_original.json.gz'
    arena.main(observer=OBSERVER,fixture_name='geometry_setup_original.json.gz',command_builder=commands,
               extra_metadata=dict(geometry_setup_parent_sha256=hashlib.sha256(parent.read_bytes()).hexdigest(),geometry_setup_reference='Unchanged native scripts observed from the first combined-network/CALCTRANS driver entry before cloning, through contact preparation and the existing first-node/fault boundaries. Read-only full source/final shape records, raw libc allocation/free calls with scalar/array interfaces, and allocator snapshots. No inferior function, numerical instruction or returned allocation is replaced.'))
