"""Read-only indexed filament arrays and pre-free buffers in every shunt run."""
import hashlib
from pathlib import Path
import capture_geometry_setup_original as setup
from capture_shunt_geometry_storage_original import jobs,ROOT
from capture_workspace_storage_original import OBSERVER as WORKSPACE
from capture_contact_storage_original import OBSERVER as CONTACTS

OBSERVER=setup.OBSERVER+'\nworkspace_storage=[]'+WORKSPACE.split('workspace_storage=[]',1)[1]+'\ncontact_storage=[]'+CONTACTS.split('contact_storage=[]',1)[1]+r'''
filament_context=None
class FilamentContext(gdb.Breakpoint):
 def stop(self):
  global filament_context
  if filament_context is not None:return False
  ctx=u32(reg('esp')+8);groups=i32(ctx+16);count=i32(ctx+32);vias=i32(ctx+40)
  def array(p,n):return dict(address=p,size=n,data=mem(p,n).hex())
  arrays=dict(extra_segments=array(u32(ctx+20),4*groups),segments=array(u32(ctx+4),4*count),width_counts=array(u32(ctx+24),4*count),thickness_counts=array(u32(ctx+28),4*count))
  if vias:arrays['via_indices']=array(u32(ctx+44),4*vias)
  filament_context=dict(groups=groups,segment_count=count,filaments=i32(ctx+36),via_count=vias,arrays=arrays,geometry=setup_shape(u32(ctx)),event_count=len(events),control=reg('fctrl'))
  return False
FilamentContext('*0x80650d4',internal=True)
'''


def commands(directory,observer=OBSERVER):
    text=setup.commands(directory,observer);before='result=dict(setup_events=setup_events,'
    assert text.count(before)==1
    return text.replace(before,'result=dict(contact_storage=contact_storage,filament_context=filament_context,workspace_storage=workspace_storage,setup_events=setup_events,')


if __name__=='__main__':
    parent=ROOT/'tests/fixtures/shunt_geometry_storage_original.json.gz'
    setup.arena.main(observer=OBSERVER,fixture_name='shunt_filament_storage_original.json.gz',command_builder=commands,job_factory=jobs,
                     extra_metadata=dict(shunt_filament_parent_sha256=hashlib.sha256(parent.read_bytes()).hexdigest(),filament_storage_reference='Every fourteen-session/cold-warm shunt geometry parent retained. Read-only prepared/numbered contact groups and records, actual group/physical-segment/filament/via counts, complete pointer/count arrays and full geometry at the first impedance fill, plus every array freed after CAP scope and before first node whose request is at most16384bytes. All allocation/free events, first node inputs, original whole initial heap and every plain outcome remain. Later counts, bytes and pointers are comparison targets only; no native instruction, memory, register, allocation, affinity or result is replaced.'))
