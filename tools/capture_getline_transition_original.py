"""Earlier CPU byte-ABI inputs on all continuing original histories."""
import argparse,gzip,hashlib,json,sys
from pathlib import Path
import capture_read_transition_original as parent
import capture_input_transition_original as inputs
import capture_getline_bytes_original as component
from capture_poll_storage_original import integer_cpu

ROOT=Path(__file__).resolve().parents[1]
OBSERVER=parent.OBSERVER+r'''
_getline_transition_snapshot=allocator_snapshot
def allocator_snapshot(label):
 _getline_transition_snapshot(label)
 if label=='driver_entry':
  environment();transition_inputs['stdio_context']['input_abi']['getline_bytes_abi']=True
'''


def jobs():
    for job in parent.jobs():
        job['parent']=ROOT/'tests/fixtures/read_transition_original.json.gz';yield job


def main():
    p=argparse.ArgumentParser(add_help=False);p.add_argument('--cc',default='cc');own,remaining=p.parse_known_args();sys.argv=[sys.argv[0],*remaining];cpu=integer_cpu(own.cc);byte_cpu=component.integer_cpu(own.cc)
    inputs.stdio.loader.transition.node.console.driver.main(fixture_name='getline_transition_original.json.gz',parent_name='read_transition_original.json.gz',job_factory=jobs,observer=OBSERVER,command_builder=inputs.stdio.loader.transition.commands,
        state_fields=('allocator_states','post_states','transition_states'),buffer_fields=('post_buffers','transition_buffers'),
        extra_metadata=dict(integer_cpu=cpu,byte_cpu=byte_cpu,getline_transition_provenance=dict(observer=OBSERVER,parent_sha256=hashlib.sha256((ROOT/'tests/fixtures/read_transition_original.json.gz').read_bytes()).hexdigest(),reference='All unchanged 134 histories retained. Independent CPU SHR profile is measured before all jobs and accompanies earlier first-driver input state. Native memchr/memcpy snapshots never initialize continuing execution. Every later region/heap/event/buffer/file/descriptor position and native outcome stays an assertion. No inferior instruction, memory, register, allocation, result or signal is substituted; minimal environment guard precedes capture.')))
    target=ROOT/'tests/fixtures/getline_transition_original.json.gz';f=json.loads(gzip.decompress(target.read_bytes()));blobs={}
    for case in f['cases']:
        case['transition_inputs']['stdio_context']['sar31_af']=cpu['sar31_af']
        case['transition_inputs']['stdio_context']['input_abi']['shr1_af']=byte_cpu['shr1_af']
        for r in case['transition_inputs']['loader_context']['regions']:
            raw=bytes.fromhex(r.pop('data'));key=hashlib.sha256(raw).hexdigest();blobs[key]=raw.hex();r.update(size=len(raw),sha256=key)
    f['loader_regions']=blobs
    with gzip.GzipFile(str(target),'wb',mtime=0)as stream:stream.write((json.dumps(f,separators=(',',':'))+'\n').encode())


if __name__=='__main__':main()
