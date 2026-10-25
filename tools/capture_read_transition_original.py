"""Continuing histories with earlier read ABI and external descriptor offsets."""
import argparse,gzip,hashlib,json,sys
from pathlib import Path
import capture_malloc_transition_original as parent
import capture_input_transition_original as inputs
from capture_read_storage_original import DESCRIPTOR
from capture_poll_storage_original import integer_cpu

ROOT=Path(__file__).resolve().parents[1]
POINT="transition_points.append(dict(kind=self.kind,"
assert parent.OBSERVER.count(POINT)==1
OBSERVER=parent.OBSERVER.replace(POINT,"transition_points.append(dict(stdin_position=stdin_position(),kind=self.kind,")+'\n'+DESCRIPTOR+r'''
_read_transition_snapshot=allocator_snapshot
def allocator_snapshot(label):
 _read_transition_snapshot(label)
 if label=='driver_entry':
  environment();transition_inputs['stdio_context']['input_abi']['read_abi']=True
  transition_inputs['stdin_stream']['file_position']=stdin_position()
_read_final_snapshot=transition_snapshot
def transition_snapshot(label):
 _read_final_snapshot(label);transition_states[-1]['stdin_position']=stdin_position()
'''


def jobs():
    for job in parent.jobs():
        job['parent']=ROOT/'tests/fixtures/malloc_transition_original.json.gz';yield job


def main():
    p=argparse.ArgumentParser(add_help=False);p.add_argument('--cc',default='cc');own,remaining=p.parse_known_args();sys.argv=[sys.argv[0],*remaining];cpu=integer_cpu(own.cc)
    inputs.stdio.loader.transition.node.console.driver.main(fixture_name='read_transition_original.json.gz',parent_name='malloc_transition_original.json.gz',job_factory=jobs,observer=OBSERVER,command_builder=inputs.stdio.loader.transition.commands,
        state_fields=('allocator_states','post_states','transition_states'),buffer_fields=('post_buffers','transition_buffers'),
        extra_metadata=dict(integer_cpu=cpu,read_transition_provenance=dict(observer=OBSERVER,parent_sha256=hashlib.sha256((ROOT/'tests/fixtures/malloc_transition_original.json.gz').read_bytes()).hexdigest(),reference='All unchanged 134 jobs retained. Earlier first-driver descriptor offset supplements prior stdin bytes, loader/VDSO and caller inputs. Every later descriptor position, complete region/heap/event/buffer/file and native outcome remains an assertion. No component read snapshot or later syscall result seeds continuation. No inferior instruction, result, allocation, register, memory or signal is substituted; minimal environment guards precede capture.')))
    target=ROOT/'tests/fixtures/read_transition_original.json.gz';f=json.loads(gzip.decompress(target.read_bytes()));blobs={}
    for case in f['cases']:
        case['transition_inputs']['stdio_context']['sar31_af']=cpu['sar31_af']
        for r in case['transition_inputs']['loader_context']['regions']:
            raw=bytes.fromhex(r.pop('data'));key=hashlib.sha256(raw).hexdigest();blobs[key]=raw.hex();r.update(size=len(raw),sha256=key)
    f['loader_regions']=blobs
    with gzip.GzipFile(str(target),'wb',mtime=0)as stream:stream.write((json.dumps(f,separators=(',',':'))+'\n').encode())


if __name__=='__main__':main()
