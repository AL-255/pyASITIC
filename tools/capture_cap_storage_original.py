"""Read-only final CAP buffers before any contact or matrix cleanup."""
import hashlib
import capture_allocator_original as arena
import capture_cap_prelude_original as prelude

OBSERVER=prelude.OBSERVER+r'''
cap_storage=None
class CapStorage(gdb.Breakpoint):
 def stop(self):
  global cap_storage
  if not prefix_seen or cap_frame is None or cap_storage is not None:return False
  cap_storage={}
  for name in ('cap_full','cap_reduced','cap_folded','cap_output'):
   descriptor=matrix(cap_output)if name=='cap_output'else matrices[name]
   n=descriptor['size'];data=descriptor['data'];stride=descriptor['stride']
   cap_storage[name]=dict(descriptor,data_bytes=b''.join(mem(data+16*j*stride,16*n)for j in range(n)).hex())
  return False
CapStorage('*0x8056524',internal=True)
'''


def commands(directory,observer=OBSERVER):
    text=prelude.commands(directory,observer);before='result=dict(prefix_events=prefix_events,'
    assert text.count(before)==1
    return text.replace(before,'result=dict(cap_storage=cap_storage,prefix_events=prefix_events,')


def main():
    parent=arena.lifetime.ROOT/'tests/fixtures/cap_prelude_original.json.gz'
    arena.main(observer=OBSERVER,fixture_name='cap_storage_original.json.gz',command_builder=commands,
               extra_metadata=dict(cap_storage_parent_sha256=hashlib.sha256(parent.read_bytes()).hexdigest(),
               cap_storage_reference='Unchanged native histories; read-only complete column-major full CAP admittance, reduced, folded and output buffers at release_potential_contacts entry 0x8056524, before their first contact or matrix free. Every selected history, cache state, native plain outcome and later node fault remains present. No data or numerical instruction is replaced.'))


if __name__=='__main__':main()
