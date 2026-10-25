"""Read-only cache, complete boundary heaps and numerical shunt histories."""
import capture_driver_history_original as driver
import capture_console_storage_original as console
import capture_shunt_filament_storage_original as filaments
from capture_contact_storage_original import OBSERVER as CONTACTS
from capture_shunt_geometry_storage_original import jobs

OBSERVER=(console.OBSERVER+'\ncontact_storage=[]'+CONTACTS.split('contact_storage=[]',1)[1]
          +'\nfilament_context=None'+filaments.OBSERVER.split('filament_context=None',1)[1])+r'''
contact_stack_entries=[]
_shunt_stack_snapshot=allocator_snapshot
def allocator_snapshot(label):
 _shunt_stack_snapshot(label)
 allocator_states[-1].update(esp=reg('esp'),ebp=reg('ebp'))
class ContactStackEntry(gdb.Breakpoint):
 def stop(self):
  if prefix_active:
   esp=reg('esp')
   contact_stack_entries.append(dict(esp=esp,ebp=reg('ebp'),index_address=esp-12,index=u32(esp-12),group=u32(esp+4),segment=u32(esp+8),prefix_events=len(prefix_events)))
  return False
ContactStackEntry('*0x8053a1c',internal=True)
'''


def commands(directory,observer=OBSERVER):
    text=console.commands(directory,observer);before='result=dict(console_inputs='
    assert text.count(before)==1
    return text.replace(before,'result=dict(contact_stack_entries=contact_stack_entries,contact_storage=contact_storage,filament_context=filament_context,console_inputs=')


if __name__=='__main__':
    driver.main(fixture_name='shunt_driver_history_original.json.gz',parent_name='shunt_filament_storage_original.json.gz',job_factory=jobs,observer=OBSERVER,command_builder=commands,
                extra_metadata=dict(shunt_driver_reference='All fourteen independently specified shunt requests, each cold/warm, unchanged from the filament-storage parent. Same read-only initial driver/scene/string/allocator inputs, complete cache bindings and input files, initial console stream bindings/controls/path names and driver-entry ESP/EBP. Pre-CAP released buffers, all complete mapped boundary heaps with ESP/EBP, bounded released numerical arrays, prepared/numbered contacts, original builder-entry stack/index observations, filament tables, independent console calls and first node matrices are retained. Later states and words are assertions only. No inferior instruction, memory, register, allocation, affinity or returned result is replaced.'))
