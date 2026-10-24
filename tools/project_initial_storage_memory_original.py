"""Project complete earlier arena bytes before CAP matrix allocation.

This is an earlier component-test memory precondition, never a runtime lookup.
The rule does not depend on later via locations or numerical output values.
"""
import argparse,gzip,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def project(full,parent,*,full_sha256,parent_sha256):
    assert full_sha256==parent['full_capture_sha256']
    assert full['gdb_commands']==parent['gdb_commands']
    assert len(full['cases'])==len(parent['cases'])
    cases=[];pages={}
    for case,prior in zip(full['cases'],parent['cases']):
        for key in ('label','cache_mode','request','script','stdin','initial_files','initial_cache'):assert case[key]==prior[key]
        state=next(state for state in case['allocator_states']if state['label']=='scope')
        heaps=[(region['address'],bytes.fromhex(region['data']))for region in state['heap_regions']]
        regions=[]
        for address,data in heaps:
            assert len(data)%4096==0
            keys=[]
            for offset in range(0,len(data),4096):
                page=data[offset:offset+4096];key=hashlib.sha256(page).hexdigest();value=page.hex()
                if key in pages:assert pages[key]==value
                else:pages[key]=value
                keys.append(key)
            regions.append(dict(address=address,size=len(data),pages=keys))
        cases.append(dict(label=case['label'],cache_mode=case['cache_mode'],initial_regions=regions))
    return dict(parent_sha256=parent_sha256,full_capture_sha256=full_sha256,
                projection='Complete initial mapped arena heap regions at scope, before CAP full-matrix allocation. All preexisting object bytes and padding are explicit earlier component-test preconditions. No later target, node matrix, via-entry bytes or numerical outcome selects or initializes these regions. Exact4096-byte pages are deduplicated bySHA256 without changing any byte.',pages=pages,cases=cases)


def expand(fixture,case):
    result=[]
    for region in case['initial_regions']:
        data=b''.join(bytes.fromhex(fixture['pages'][key])for key in region['pages'])
        assert len(data)==region['size'];result.append((region['address'],data))
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--full-capture',type=Path,required=True);options=parser.parse_args()
    parent_path=ROOT/'tests/fixtures/cap_prelude_shared_original.json.gz';parent_raw=parent_path.read_bytes();raw=options.full_capture.read_bytes()
    fixture=project(json.loads(gzip.decompress(raw)),json.loads(gzip.decompress(parent_raw)),full_sha256=hashlib.sha256(raw).hexdigest(),parent_sha256=hashlib.sha256(parent_raw).hexdigest())
    target=ROOT/'tests/fixtures/initial_storage_memory_original.json.gz'
    with gzip.GzipFile(str(target),'wb',mtime=0)as stream:stream.write((json.dumps(fixture,separators=(',',':'))+'\n').encode())
    print(json.dumps(dict(cases=len(fixture['cases']),regions=sum(len(c['initial_regions'])for c in fixture['cases']),bytes=sum(r['size']for c in fixture['cases']for r in c['initial_regions']),unique_pages=len(fixture['pages']),compressed_bytes=target.stat().st_size)))


if __name__=='__main__':main()
