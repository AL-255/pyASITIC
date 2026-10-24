"""Read-only storage freed between native contacts and CAP matrix entry."""
import argparse,gzip,hashlib,json,sys
from pathlib import Path
import capture_geometry_setup_original as geometry
from project_prelude_storage_original import project

OBSERVER=geometry.OBSERVER+r'''
prelude_storage=[];prelude_final_heap=None
_prelude_storage_snapshot=allocator_snapshot
def allocator_snapshot(label):
 global prelude_final_heap
 _prelude_storage_snapshot(label)
 if label=='scope':
  prelude_final_heap=[dict(address=m['start'],data=mem(m['start'],m['end']-m['start']).hex())for m in allocator_states[-1]['maps']if m['path']=='[heap]']
class PreludeStorage(gdb.Breakpoint):
 def stop(self):
  if not prefix_active:return False
  pointer=u32(reg('esp')+4)
  if not pointer:return False
  allocation=next(event for event in reversed(prefix_events)if event['kind']=='allocate'and event.get('address')==pointer)
  size=allocation['request'];index=len(prefix_events)
  if prefix_events and prefix_events[-1]['kind']=='free'and prefix_events[-1]['address']==pointer and prefix_events[-1]['caller']==u32(reg('esp')):index-=1
  assert size<=16384
  prelude_storage.append(dict(event_index=index,address=pointer,size=size,data=mem(pointer,size).hex()))
  return False
PreludeStorage('__libc_free',internal=True)
'''


def commands(directory,observer=OBSERVER):
    text=geometry.commands(directory,observer);before='result=dict(setup_events='
    assert text.count(before)==1
    return text.replace(before,'result=dict(prelude_storage=prelude_storage,prelude_final_heap=prelude_final_heap,setup_events=')


if __name__=='__main__':
    parser=argparse.ArgumentParser(add_help=False);parser.add_argument('--full-output',type=Path)
    options,remaining=parser.parse_known_args();sys.argv=[sys.argv[0],*remaining]
    parent=geometry.arena.lifetime.ROOT/'tests/fixtures/geometry_setup_original.json.gz'
    geometry.arena.main(observer=OBSERVER,fixture_name='prelude_storage_original.json.gz',command_builder=commands,
                        extra_metadata=dict(prelude_storage_parent_sha256=hashlib.sha256(parent.read_bytes()).hexdigest(),prelude_storage_reference='All original geometry setup histories, cache states and outcomes. Before libc free, observe the full original request of every block freed from contacts entry through CAP matrix entry (each request is at most16KiB). Also retain the complete mapped heap at CAP matrix entry as an independent output observation, never an execution input. No inferior function or instruction value is replaced.'))
    target=geometry.arena.lifetime.ROOT/'tests/fixtures/prelude_storage_original.json.gz';raw=target.read_bytes()
    if options.full_output:options.full_output.write_bytes(raw)
    fixture=project(json.loads(gzip.decompress(raw)),hashlib.sha256(raw).hexdigest())
    with gzip.GzipFile(str(target),'wb',mtime=0)as stream:stream.write((json.dumps(fixture,separators=(',',':'))+'\n').encode())
