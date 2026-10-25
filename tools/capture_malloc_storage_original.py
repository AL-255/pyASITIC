"""Independent stdio allocation callers and complete native malloc boundaries."""
import argparse,hashlib,sys
from pathlib import Path
import capture_file_allocation_original as parent
from capture_allocator_original import OBSERVER as ALLOCATOR

ROOT=Path(__file__).resolve().parents[1]
OBSERVER=parent.OBSERVER+'\nevents=[]\n'+ALLOCATOR+r'''
def malloc_controls(ctx):
 base=u32(next(x['address']for x in ctx['maps']if x['name'].endswith('/libc.so.6')));got=base+0x22fe34
 return [(got+0x78,4),(got+0x368,4),(got+0x3bfc,4),(got+0x3c04,1),(got+0x3c14,4),(got+0x3c18,1),((ctx['tls_base']+u32(got+0x78))&0xffffffff,4)]
_malloc_allocation_context=allocation_context
def allocation_context():
 ctx=_malloc_allocation_context();allocator_snapshot('doallocbuf_entry');ctx['heap']=allocator_states.pop()
 heap=mapping('[heap]');ctx['regions'].append(heap)
 ctx['regions'].append(dict(address=ctx['heap']['arena_address'],data=ctx['heap']['arena_bytes']))
 ctx['regions']+=[dict(address=p,data=mem(p,n).hex())for p,n in malloc_controls(ctx)]
 ctx['profile']['malloc_abi']=True
 return ctx
_malloc_allocation_state=allocation_state
def allocation_state(ctx):
 state=_malloc_allocation_state(ctx);allocator_snapshot('malloc_boundary');state['heap']=allocator_states.pop();return state
'''


def commands(directory):
    text=parent.commands(directory)
    assert text.count(parent.OBSERVER)==1
    return text.replace(parent.OBSERVER,OBSERVER)


def jobs():
    for job in parent.jobs():
        job['parent']=ROOT/'tests/fixtures/stat_transition_original.json.gz';yield job


def main():
    p=argparse.ArgumentParser(add_help=False);p.add_argument('--debug-directory',type=Path,required=True);own,remaining=p.parse_known_args();sys.argv=[sys.argv[0],*remaining];blobs={}
    def project(case):
        for call in case['allocation_calls']:
            for point in call.values():
                for r in point['regions']:
                    raw=bytes.fromhex(r.pop('data'));key=hashlib.sha256(raw).hexdigest();blobs[key]=raw.hex();r.update(size=len(raw),sha256=key)
        return case
    parent.lifetime.main(commands=commands(own.debug_directory),fixture_name='malloc_storage_original.json.gz',job_factory=jobs,case_transform=project,finalize_metadata=lambda:dict(loader_regions=blobs),
        extra_metadata=dict(malloc_storage_provenance=dict(observer=OBSERVER,reference='All unchanged 134 jobs retained. Earlier complete heap, arena, malloc controls and TLS accompany all four stdio allocation boundaries. Complete later regions/registers/XSAVE/allocator snapshots remain assertions. No inferior instruction, register, result, allocation, memory or signal is substituted; minimal environment guard precedes capture. No component snapshot seeds continuing replay.')))


if __name__=='__main__':main()
