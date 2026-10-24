"""Read-only bounded array contents immediately before native delete[]."""
import hashlib
import capture_allocator_original as arena
import capture_cap_prelude_original as prelude

OBSERVER=prelude.OBSERVER+r'''
workspace_storage=[]
class WorkspaceStorage(gdb.Breakpoint):
 def stop(self):
  if not active or cap_frame is None:return False
  pointer=u32(reg('esp')+4)
  if not pointer:return False
  allocation=next(event for event in reversed(events)if event['kind']=='allocate'and event.get('address')==pointer)
  size=allocation['request']
  if size<=16384:
   index=len(events)
   if events and events[-1]['kind']=='free'and events[-1]['address']==pointer and events[-1]['caller']==u32(reg('esp')):index-=1
   workspace_storage.append(dict(event_index=index,address=pointer,size=size,data=mem(pointer,size).hex()))
  return False
WorkspaceStorage('*0x804ac74',internal=True)
'''


def commands(directory,observer=OBSERVER):
    text=prelude.commands(directory,observer);before='result=dict(prefix_events=prefix_events,'
    assert text.count(before)==1
    return text.replace(before,'result=dict(workspace_storage=workspace_storage,prefix_events=prefix_events,')


if __name__=='__main__':
    parent=arena.lifetime.ROOT/'tests/fixtures/cap_prelude_original.json.gz'
    arena.main(observer=OBSERVER,fixture_name='workspace_storage_original.json.gz',command_builder=commands,
               extra_metadata=dict(workspace_storage_parent_sha256=hashlib.sha256(parent.read_bytes()).hexdigest(),
               workspace_storage_reference='Unchanged native scripts and all selected outcomes. Read-only contents of every nonnull array freed after CAP scope and before first node/fault, when its last original allocation request is at most16384bytes. This includes every pivot and factor/inverse workspace in all selected cases. Larger matrix buffers remain represented by the existing complete CAP/native matrix observations. No numeric or allocator instruction/value is changed.'))
