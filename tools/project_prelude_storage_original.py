"""Deduplicate complete initial/output heaps and pre-free buffers losslessly."""
import argparse,gzip,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def project(fixture,full_sha256):
    pages={};blobs={}
    def heap(regions):
        result=[]
        for region in regions:
            data=bytes.fromhex(region['data']);assert len(data)%4096==0;keys=[]
            for offset in range(0,len(data),4096):
                page=data[offset:offset+4096];key=hashlib.sha256(page).hexdigest();value=page.hex()
                if key in pages:assert pages[key]==value
                else:pages[key]=value
                keys.append(key)
            result.append(dict(address=region['address'],size=len(data),sha256=hashlib.sha256(data).hexdigest(),pages=keys))
        return result
    for case in fixture['cases']:
        case['setup_context']['memory_regions']=heap(case['setup_context']['memory_regions'])
        case['prelude_final_heap']=heap(case['prelude_final_heap'])if case['prelude_final_heap']is not None else None
        for record in case['prelude_storage']:
            data=record.pop('data');key=hashlib.sha256(bytes.fromhex(data)).hexdigest()
            if key in blobs:assert blobs[key]==data
            else:blobs[key]=data
            record['sha256']=key
    fixture.update(storage_pages=pages,storage_blobs=blobs,full_capture_sha256=full_sha256,
                   storage_projection='Every byte of all original initial mapped heap regions, all final CAP-entry mapped heap regions and every observed pre-free request. No range or buffer is excluded. Exact4096byte heap pages and complete buffer payloads are deduplicated by SHA256 only; this does not select future targets or initialize any runtime calculation.')
    return fixture


def expand_case(fixture,case):
    if 'storage_pages'not in fixture:return case
    def heap(regions):
        result=[]
        for region in regions:
            data=b''.join(bytes.fromhex(fixture['storage_pages'][key])for key in region['pages'])
            assert len(data)==region['size']and hashlib.sha256(data).hexdigest()==region['sha256']
            result.append(dict(address=region['address'],data=data.hex()))
        return result
    result=dict(case);result['setup_context']=dict(case['setup_context'],memory_regions=heap(case['setup_context']['memory_regions']))
    result['prelude_final_heap']=heap(case['prelude_final_heap'])if case['prelude_final_heap']is not None else None;records=[]
    for record in case['prelude_storage']:
        data=fixture['storage_blobs'][record['sha256']]
        assert len(data)==2*record['size']and hashlib.sha256(bytes.fromhex(data)).hexdigest()==record['sha256']
        records.append(dict(record,data=data))
    result['prelude_storage']=records;return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--full-capture',type=Path,required=True);args=parser.parse_args()
    raw=args.full_capture.read_bytes();fixture=project(json.loads(gzip.decompress(raw)),hashlib.sha256(raw).hexdigest())
    target=ROOT/'tests/fixtures/prelude_storage_original.json.gz'
    with gzip.GzipFile(str(target),'wb',mtime=0)as stream:stream.write((json.dumps(fixture,separators=(',',':'))+'\n').encode())
    print(json.dumps(dict(cases=len(fixture['cases']),pages=len(fixture['storage_pages']),blobs=len(fixture['storage_blobs']),compressed_bytes=target.stat().st_size)))


if __name__=='__main__':main()
