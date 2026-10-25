"""Complete continuing histories with earlier log stream and flush ABI state."""
import argparse,gzip,hashlib,json,sys
from pathlib import Path
import capture_getline_transition_original as parent
import capture_input_transition_original as inputs
import capture_getline_bytes_original as component
from capture_poll_storage_original import integer_cpu

ROOT=Path(__file__).resolve().parents[1]
OBSERVER=parent.OBSERVER+r'''
_flush_transition_snapshot=allocator_snapshot
def allocator_snapshot(label):
 _flush_transition_snapshot(label)
 if label=='driver_entry':
  environment();ctx=transition_inputs['loader_context'];stdio=transition_inputs['stdio_context'];stdio['flush_abi']=True
  def include(p,n):
   if any(r['address']==p and r['size']==n for r in stdio['regions']):return
   ctx['regions'].append(dict(address=p,data=mem(p,n).hex()));stdio['regions'].append(dict(address=p,size=n))
  for binding in (0x80d7e24,0x80d7e28):
   include(binding,4);file=u32(binding)
   if file:
    lock=u32(file+72);offset=struct.unpack('<b',mem(file+70,1))[0];vt=u32(file+148+offset)
    for p,n in ((file,152),(lock,12),(vt,84)):include(p,n)
'''


def jobs():
    for job in parent.jobs():
        job['parent']=ROOT/'tests/fixtures/getline_transition_original.json.gz';yield job


def main():
    p=argparse.ArgumentParser(add_help=False);p.add_argument('--cc',default='cc');own,remaining=p.parse_known_args();sys.argv=[sys.argv[0],*remaining];cpu=integer_cpu(own.cc);byte_cpu=component.integer_cpu(own.cc)
    inputs.stdio.loader.transition.node.console.driver.main(fixture_name='flush_transition_original.json.gz',parent_name='getline_transition_original.json.gz',job_factory=jobs,observer=OBSERVER,command_builder=inputs.stdio.loader.transition.commands,
        state_fields=('allocator_states','post_states','transition_states'),buffer_fields=('post_buffers','transition_buffers'),
        extra_metadata=dict(integer_cpu=cpu,byte_cpu=byte_cpu,flush_transition_provenance=dict(observer=OBSERVER,parent_sha256=hashlib.sha256((ROOT/'tests/fixtures/getline_transition_original.json.gz').read_bytes()).hexdigest(),reference='All unchanged 134 histories retained. Earlier first-driver log FILEs, their locks/vtables and global bindings supplement prior inputs. Every added region is a complete later assertion. Independent CPU profiles precede all jobs. Per-call native fflush snapshots and write return counts never initialize continuing execution. All later heaps, regions, events, buffers, files, descriptor positions and terminal outcomes remain required. No inferior instruction, register, memory, allocation, result or signal is replaced; minimal environment guards precede capture.')))
    target=ROOT/'tests/fixtures/flush_transition_original.json.gz';f=json.loads(gzip.decompress(target.read_bytes()));blobs={}
    for case in f['cases']:
        stdio=case['transition_inputs']['stdio_context'];stdio['sar31_af']=cpu['sar31_af'];stdio['input_abi']['shr1_af']=byte_cpu['shr1_af']
        for r in case['transition_inputs']['loader_context']['regions']:
            raw=bytes.fromhex(r.pop('data'));key=hashlib.sha256(raw).hexdigest();blobs[key]=raw.hex();r.update(size=len(raw),sha256=key)
    f['loader_regions']=blobs
    with gzip.GzipFile(str(target),'wb',mtime=0)as stream:stream.write((json.dumps(f,separators=(',',':'))+'\n').encode())


if __name__=='__main__':main()
