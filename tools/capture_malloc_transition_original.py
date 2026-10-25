"""Continuing histories with earlier malloc controls and source ABI stores."""
import argparse,gzip,hashlib,json,sys
from pathlib import Path
import capture_stat_transition_original as parent
import capture_malloc_storage_original as component
from capture_poll_storage_original import integer_cpu

ROOT=Path(__file__).resolve().parents[1]
CONTROLS='def malloc_controls'+component.OBSERVER.split('def malloc_controls',1)[1].split('_malloc_allocation_context',1)[0]
OBSERVER=parent.OBSERVER+'\n'+CONTROLS+r'''
_malloc_transition_snapshot=allocator_snapshot
def allocator_snapshot(label):
 _malloc_transition_snapshot(label)
 if label=='driver_entry':
  environment();ctx=transition_inputs['loader_context'];stdio=transition_inputs['stdio_context']
  stdio['input_abi']['malloc_abi']=True
  for p,n in malloc_controls(ctx):
   ctx['regions'].append(dict(address=p,data=mem(p,n).hex()));stdio['regions'].append(dict(address=p,size=n))
'''


def jobs():
    for job in parent.jobs():
        job['parent']=ROOT/'tests/fixtures/stat_transition_original.json.gz';yield job


def main():
    p=argparse.ArgumentParser(add_help=False);p.add_argument('--cc',default='cc');own,remaining=p.parse_known_args();sys.argv=[sys.argv[0],*remaining];cpu=integer_cpu(own.cc)
    parent.parent.stdio.loader.transition.node.console.driver.main(fixture_name='malloc_transition_original.json.gz',parent_name='stat_transition_original.json.gz',job_factory=jobs,observer=OBSERVER,command_builder=parent.parent.stdio.loader.transition.commands,
        state_fields=('allocator_states','post_states','transition_states'),buffer_fields=('post_buffers','transition_buffers'),
        extra_metadata=dict(integer_cpu=cpu,malloc_transition_provenance=dict(observer=OBSERVER,parent_sha256=hashlib.sha256((ROOT/'tests/fixtures/stat_transition_original.json.gz').read_bytes()).hexdigest(),reference='All unchanged 134 jobs retained. Earlier first-driver malloc globals, tcache TLS binding and controls supplement prior inputs. Complete later regions, heaps, events, buffers, outputs, registers at independent boundaries and every native outcome remain assertions. No component malloc snapshot seeds continuation. No inferior instruction, result, allocation, register, memory or signal is substituted; minimal environment guards precede capture.')))
    target=ROOT/'tests/fixtures/malloc_transition_original.json.gz';f=json.loads(gzip.decompress(target.read_bytes()));blobs={}
    for case in f['cases']:
        case['transition_inputs']['stdio_context']['sar31_af']=cpu['sar31_af']
        for r in case['transition_inputs']['loader_context']['regions']:
            raw=bytes.fromhex(r.pop('data'));key=hashlib.sha256(raw).hexdigest();blobs[key]=raw.hex();r.update(size=len(raw),sha256=key)
    f['loader_regions']=blobs
    with gzip.GzipFile(str(target),'wb',mtime=0)as stream:stream.write((json.dumps(f,separators=(',',':'))+'\n').encode())


if __name__=='__main__':main()
