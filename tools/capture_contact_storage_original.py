"""Read-only prepared/numbered contact bytes in complete native CAP histories."""
import hashlib
import capture_allocator_original as arena
import capture_cap_prelude_original as prelude

OBSERVER=prelude.OBSERVER+r'''
contact_storage=[]
class ContactStorage(gdb.Breakpoint):
 def __init__(self,address,label):
  self.label=label;super().__init__('*'+hex(address),internal=True)
 def stop(self):
  if not prefix_seen or any(state['label']==self.label for state in contact_storage):return False
  if self.label=='numbered'and not contact_storage:return False
  groups=[];group=u32(0x80ce9a4)
  while group:
   contacts=[];contact=u32(group+128)
   while contact:
    contacts.append(dict(address=contact,data=mem(contact,60).hex()));contact=u32(contact+56)
   groups.append(dict(address=group,data=mem(group,136).hex(),contacts=contacts));group=u32(group+132)
  contact_storage.append(dict(label=self.label,head=u32(0x80ce9a4),groups=groups))
  return False
ContactStorage(0x8052ec7,'prepared');ContactStorage(0x8056524,'numbered')
'''


def commands(directory,observer=OBSERVER):
    text=prelude.commands(directory,observer);before='result=dict(prefix_events=prefix_events,'
    assert text.count(before)==1
    return text.replace(before,'result=dict(contact_storage=contact_storage,prefix_events=prefix_events,')


def main():
    parent=arena.lifetime.ROOT/'tests/fixtures/cap_prelude_original.json.gz'
    arena.main(observer=OBSERVER,fixture_name='contact_storage_original.json.gz',command_builder=commands,
               extra_metadata=dict(contact_storage_parent_sha256=hashlib.sha256(parent.read_bytes()).hexdigest(),
               contact_storage_reference='Read-only full 136-byte group and 60-byte contact records at CAP matrix entry (0x8052ec7), before matrix numbering, and at release_potential_contacts entry (0x8056524), after contact/group numbering and before their first free. All 65 selected input histories in both cache states remain present. Unknown incoming contact.index words and unwritten name padding/reserved bytes are retained in observations, not supplied to the source-generated prepared records.'))


if __name__=='__main__':main()
