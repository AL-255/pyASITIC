"""Read-only driver/cache plus raw numerical-boundary and workspace histories."""
import argparse,gzip,hashlib,json,sys
from pathlib import Path
import capture_cache_storage_original as cache
from capture_workspace_storage_original import OBSERVER as WORKSPACE_OBSERVER
from capture_cap_prelude_original import OBSERVER as PRELUDE_OBSERVER

assert WORKSPACE_OBSERVER.startswith(PRELUDE_OBSERVER)
OBSERVER=cache.OBSERVER+WORKSPACE_OBSERVER[len(PRELUDE_OBSERVER):]+r'''
_driver_snapshot=allocator_snapshot
def allocator_snapshot(label):
 _driver_snapshot(label)
 if label=='driver_entry':cache_inputs['coefficient_address']=u32(0x80d8ac8)
 state=allocator_states[-1]
 state['tcache_key']=int(gdb.parse_and_eval('tcache_key'))
 state['memory_regions']=[dict(address=m['start'],data=mem(m['start'],m['end']-m['start']).hex())for m in state['maps']if m['path']=='[heap]']
'''


def commands(directory,observer=OBSERVER):
    text=cache.commands(directory,observer);before='result=dict(cache_inputs='
    assert text.count(before)==1
    return text.replace(before,'result=dict(workspace_storage=workspace_storage,cache_inputs=')


def expand_case(fixture,entry):
    from project_prelude_storage_original import expand_case as prelude
    case=prelude(fixture,entry);states=[]
    for state in case['allocator_states']:
        regions=[]
        for region in state['memory_regions']:
            data=b''.join(bytes.fromhex(fixture['driver_heap_pages'][key])for key in region['pages'])
            assert len(data)==region['size']and hashlib.sha256(data).hexdigest()==region['sha256']
            regions.append(dict(address=region['address'],data=data.hex()))
        states.append(dict(state,memory_regions=regions))
    case['allocator_states']=states
    return case


def main(*,fixture_name='driver_history_original.json.gz',parent_name='cache_storage_original.json.gz',job_factory=None,observer=OBSERVER,command_builder=commands,extra_metadata=None):
    parser=argparse.ArgumentParser(add_help=False);parser.add_argument('--full-output',type=Path)
    options,remaining=parser.parse_known_args();sys.argv=[sys.argv[0],*remaining]
    root=cache.libio.prelude.geometry.arena.lifetime.ROOT;files={};heaps={}
    def pages(data,bank):
        keys=[]
        for offset in range(0,len(data),4096):
            part=data[offset:offset+4096];key=hashlib.sha256(part).hexdigest();value=part.hex()
            if key in bank:assert bank[key]==value
            else:bank[key]=value
            keys.append(key)
        return dict(size=len(data),sha256=hashlib.sha256(data).hexdigest(),pages=keys)
    def project_case(case):
        for record in case['cache_inputs']['files']:record.update(pages(bytes.fromhex(record.pop('data')),files))
        for state in case['allocator_states']:
            for region in state['memory_regions']:region.update(pages(bytes.fromhex(region.pop('data')),heaps))
        return case
    cache.libio.prelude.geometry.arena.main(observer=observer,fixture_name=fixture_name,command_builder=command_builder,job_factory=job_factory,case_transform=project_case,
        finalize_metadata=lambda:dict(cache_file_pages=files,driver_heap_pages=heaps),
        extra_metadata=dict(driver_history_parent_sha256=hashlib.sha256((root/'tests/fixtures'/parent_name).read_bytes()).hexdigest(),
            driver_history_reference='All selected unchanged histories and outcomes. Earlier driver/cache inputs and every pre-free prelude buffer remain. At every allocator boundary read the complete mapped heap and tcache key; observe every bounded numerical array immediately before original delete[]. Complete heap/file pages are losslessly deduplicated as each case finishes, with no target selection. No inferior instruction, function return, memory store or allocation result is changed. Later boundary heaps and workspace bytes are comparison outputs only.',**(extra_metadata or {})))
    path=root/'tests/fixtures'/fixture_name;raw=path.read_bytes()
    if options.full_output:options.full_output.write_bytes(raw)
    fixture=cache.libio.prelude.project(json.loads(gzip.decompress(raw)),hashlib.sha256(raw).hexdigest())
    with gzip.GzipFile(str(path),'wb',mtime=0)as stream:stream.write((json.dumps(fixture,separators=(',',':'))+'\n').encode())


if __name__=='__main__':main()
