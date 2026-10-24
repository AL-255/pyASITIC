"""Original allocator boundaries with byte-exact heap and tcache-key inputs."""
import argparse,gzip,hashlib,json,shutil,sys
from pathlib import Path
import capture_allocator_original as arena
from capture_mapping_allocator_original import OBSERVER as MAPPING_OBSERVER

OBSERVER=MAPPING_OBSERVER+r'''
_mapping_snapshot=allocator_snapshot
def allocator_snapshot(label):
 _mapping_snapshot(label)
 state=allocator_states[-1]
 state['tcache_key']=int(gdb.parse_and_eval('tcache_key'))
 state['heap_regions']=[dict(address=m['start'],data=mem(m['start'],m['end']-m['start']).hex())for m in state['maps']if m['path']=='[heap]']
'''


def project(fixture):
    """Keep exact observable byte ranges; unknown bytes remain unknown.

    All cases, events, raw headers and outcomes are retained. Full heap
    manifests identify the larger raw observation, which can be reproduced
    with the recorded observer. Ranges contain every current chunk's header
    and first two user words, cache controls, and each actual via target.
    """
    for case in fixture['cases']:
        via=case['via']
        for state in case['allocator_states']:
            full=[(region['address'],bytes.fromhex(region['data']))for region in state.pop('heap_regions')]
            state['full_heap_manifest']=[dict(address=address,size=len(data),sha256=hashlib.sha256(data).hexdigest())for address,data in full]
            ranges=[(chunk['address'],chunk['address']+16)for chunk in state['chunks']]
            if state['tcache_address']:ranges.append((state['tcache_address'],state['tcache_address']+384))
            if state['label']!='scope':
                ranges.extend((cell['address'],cell['address']+16)for cell in via['cells'])
                n=via['matrix']['size']
                for matrix in (case['matrices']['cap_output'],via['matrix']):ranges.append((matrix['data'],matrix['data']+16*n*n))
            merged=[]
            for start,end in sorted(ranges):
                if merged and start<=merged[-1][1]:merged[-1][1]=max(merged[-1][1],end)
                else:merged.append([start,end])
            projected=[]
            for start,end in merged:
                for address,data in full:
                    lo=max(start,address);hi=min(end,address+len(data))
                    if lo<hi:projected.append(dict(address=lo,data=data[lo-address:hi-address].hex()))
            state['memory_regions']=projected
    fixture['memory_projection']='Every observed heap chunk header and first eight user bytes and the complete tcache control object. After scope, also the CAP and reduced-inductance outputs and each via target, intersected with mapped heap bytes. Other bytes are unknown, not zero. Every selected case and outcome remains present.'
    return fixture


if __name__=='__main__':
    parser=argparse.ArgumentParser(add_help=False);parser.add_argument('--full-output',type=Path)
    options,remaining=parser.parse_known_args();sys.argv=[sys.argv[0],*remaining]
    parent=arena.lifetime.ROOT/'tests/fixtures/allocator_mappings_original.json.gz'
    arena.main(observer=OBSERVER,fixture_name='shared_heap_original.json.gz',extra_metadata=dict(shared_parent_sha256=hashlib.sha256(parent.read_bytes()).hexdigest()))
    target=arena.lifetime.ROOT/'tests/fixtures/shared_heap_original.json.gz'
    if options.full_output:shutil.copyfile(target,options.full_output)
    raw=target.read_bytes();fixture=project(json.loads(gzip.decompress(raw)));fixture['full_capture_sha256']=hashlib.sha256(raw).hexdigest()
    with gzip.GzipFile(str(target),'wb',mtime=0)as stream:stream.write((json.dumps(fixture,separators=(',',':'))+'\n').encode())
