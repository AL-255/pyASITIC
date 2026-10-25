"""Continuing histories with earlier legacy standard-stream and REPL state."""
import argparse,gzip,hashlib,json,sys
from pathlib import Path
import capture_loader_transition_original as loader
from capture_poll_storage_original import integer_cpu

ROOT=Path(__file__).resolve().parents[1]
OBSERVER=loader.OBSERVER+r'''
_stdio_transition_snapshot=allocator_snapshot
def allocator_snapshot(label):
 _stdio_transition_snapshot(label)
 if label=='driver_entry':
  environment();context=transition_inputs['loader_context'];regions=context['regions'];owners=[];streams={}
  def include(p,n):
   if any(r['address']==p and len(r['data'])//2==n for r in owners):return
   item=dict(address=p,data=mem(p,n).hex());regions.append(item);owners.append(item)
  for name,address in (('stdin',0x80d7ddc),('stdout',0x80d7d68),('stderr',0x80d7d6c)):
   stream=u32(address);include(address,4);include(stream,152)
   lock=u32(stream+72);offset=struct.unpack('<b',mem(stream+70,1))[0];vtable=u32(stream+148+offset)
   include(lock,12);include(vtable,84)
   streams[name]=dict(address=stream,lock=lock,vtable=vtable,vtable_offset=offset)
  include(0x80cba60,96);include(0x80d8644,4)
  fd='/proc/%d/fd/0'%gdb.selected_inferior().pid
  position=next(int(line.split(':',1)[1])for line in open('/proc/%d/fdinfo/0'%gdb.selected_inferior().pid)if line.startswith('pos:'))
  transition_inputs['stdio_context']=dict(streams=streams,registers=registers(),stdin_regular=__import__('stat').S_ISREG(os.stat(fd).st_mode),stdin_position=position,regions=[dict(address=r['address'],size=len(r['data'])//2)for r in owners])
_stdio_transition_regions=transition_regions
def transition_regions():
 return _stdio_transition_regions()+[dict(address=r['address'],data=mem(r['address'],r['size']).hex())for r in transition_inputs['stdio_context']['regions']]
'''


def jobs():
    for job in loader.jobs():
        job['parent']=ROOT/'tests/fixtures/loader_transition_original.json.gz';yield job


def main():
    p=argparse.ArgumentParser(add_help=False);p.add_argument('--cc',default='cc');own,remaining=p.parse_known_args();sys.argv=[sys.argv[0],*remaining];cpu=integer_cpu(own.cc)
    loader.transition.node.console.driver.main(fixture_name='stdio_transition_original.json.gz',parent_name='loader_transition_original.json.gz',job_factory=jobs,observer=OBSERVER,command_builder=loader.transition.commands,
        state_fields=('allocator_states','post_states','transition_states'),buffer_fields=('post_buffers','transition_buffers'),
        extra_metadata=dict(integer_cpu=cpu,stdio_transition_provenance=dict(observer=OBSERVER,parent_sha256=hashlib.sha256((ROOT/'tests/fixtures/loader_transition_original.json.gz').read_bytes()).hexdigest(),reference='All unchanged 134 original histories retained. First-driver entry supplies earlier complete 152-byte static stream views, their actual signed-offset vtables, locks, global bindings and REPL controls, alongside all prior loader/stack/heap inputs. Every additional region is compared at every later command point and final boundary. Independent i386 CPU observations precede all native jobs. Later call snapshots and output regions never seed continuation. Minimal environment guards precede capture. No inferior memory, registers, instructions, allocations, kernel returns or terminal outcomes are substituted.')))
    target=ROOT/'tests/fixtures/stdio_transition_original.json.gz';f=json.loads(gzip.decompress(target.read_bytes()));blobs={}
    for case in f['cases']:
        case['transition_inputs']['stdio_context']['sar31_af']=cpu['sar31_af']
        for r in case['transition_inputs']['loader_context']['regions']:
            raw=bytes.fromhex(r.pop('data'));key=hashlib.sha256(raw).hexdigest();blobs[key]=raw.hex();r.update(size=len(raw),sha256=key)
    f['loader_regions']=blobs
    with gzip.GzipFile(str(target),'wb',mtime=0)as stream:stream.write((json.dumps(f,separators=(',',':'))+'\n').encode())


if __name__=='__main__':main()
