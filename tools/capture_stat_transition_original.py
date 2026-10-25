"""Continuing histories with earlier named statx facts and VDSO prefix."""
import argparse,gzip,hashlib,json,sys
from pathlib import Path
import capture_input_transition_original as parent
from capture_poll_storage_original import integer_cpu
from capture_statx_metadata import OBSERVER as STATX

ROOT=Path(__file__).resolve().parents[1]
OBSERVER=parent.OBSERVER+'\n'+STATX+r'''
_stat_transition_snapshot=allocator_snapshot
def allocator_snapshot(label):
 _stat_transition_snapshot(label)
 if label=='driver_entry':
  environment();ctx=transition_inputs['loader_context'];stdio=transition_inputs['stdio_context']
  stdio['input_abi']['statx']=statx_metadata();sysinfo=u32(ctx['tls_base']+16)
  ctx['regions'].append(dict(address=sysinfo,data=mem(sysinfo,32).hex()));stdio['regions'].append(dict(address=sysinfo,size=32))
  base=u32(next(x['address']for x in ctx['maps']if x['name'].endswith('/libc.so.6')));slot=base+0x22fe34+0x1c4
  ctx['regions'].append(dict(address=slot,data=mem(slot,4).hex()));stdio['regions'].append(dict(address=slot,size=4))
'''


def jobs():
    for job in parent.jobs():
        job['parent']=ROOT/'tests/fixtures/input_transition_original.json.gz';yield job


def main():
    p=argparse.ArgumentParser(add_help=False);p.add_argument('--cc',default='cc');own,remaining=p.parse_known_args();sys.argv=[sys.argv[0],*remaining];cpu=integer_cpu(own.cc)
    parent.stdio.loader.transition.node.console.driver.main(fixture_name='stat_transition_original.json.gz',parent_name='input_transition_original.json.gz',job_factory=jobs,observer=OBSERVER,command_builder=parent.stdio.loader.transition.commands,
        state_fields=('allocator_states','post_states','transition_states'),buffer_fields=('post_buffers','transition_buffers'),
        extra_metadata=dict(integer_cpu=cpu,stat_transition_provenance=dict(observer=OBSERVER,parent_sha256=hashlib.sha256((ROOT/'tests/fixtures/input_transition_original.json.gz').read_bytes()).hexdigest(),reference='All unchanged 134 jobs retained. Earlier first-driver named file statx facts and VDSO prefix supplement the preceding earlier input context. Statx facts are queried from the external file independently, never read from a later program stat buffer. Complete later memory targets and all outcomes remain assertions. No inferior results, instructions, memory or registers are substituted; minimal environment guards precede capture.')))
    target=ROOT/'tests/fixtures/stat_transition_original.json.gz';f=json.loads(gzip.decompress(target.read_bytes()));blobs={}
    for case in f['cases']:
        case['transition_inputs']['stdio_context']['sar31_af']=cpu['sar31_af']
        for r in case['transition_inputs']['loader_context']['regions']:
            raw=bytes.fromhex(r.pop('data'));key=hashlib.sha256(raw).hexdigest();blobs[key]=raw.hex();r.update(size=len(raw),sha256=key)
    f['loader_regions']=blobs
    with gzip.GzipFile(str(target),'wb',mtime=0)as stream:stream.write((json.dumps(f,separators=(',',':'))+'\n').encode())


if __name__=='__main__':main()
