"""Earlier cache allocations/file inputs and independent final table digests."""
import argparse,gzip,hashlib,json,sys
from pathlib import Path
import capture_libio_storage_original as libio

OBSERVER=libio.OBSERVER+r'''
import hashlib
cache_inputs=None;cache_outputs=None
_cache_snapshot=allocator_snapshot
def cache_ranges():
 nx=i32(0x80ce990);ny=i32(0x80ce994);metals=i32(0x80d8904);count=metals*(metals+1)//2;result={}
 for name,global_address,size in (('xy',0x80d8acc,16*(nx+1)*(ny+1)),('x',0x80d8ad0,32*nx),('y',0x80d8ad4,32*ny)):
  pointers=u32(global_address)
  result[name]=dict(pointer_address=pointers,pointers=[u32(pointers+4*i)for i in range(count)],size=size)
 return dict(nx=nx,ny=ny,metals=metals,arrays=result)
def allocator_snapshot(label):
 global cache_inputs,cache_outputs
 _cache_snapshot(label)
 if label=='driver_entry':
  cache_inputs=cache_ranges();initial=[]
  for group in cache_inputs['arrays'].values():
   for address in group['pointers']:
    data=mem(address,group['size']);record=dict(address=address,size=len(data),sha256=hashlib.sha256(data).hexdigest(),zero=not any(data))
    if not record['zero']:record['data']=data.hex()
    initial.append(record)
  cache_inputs['initial_regions']=initial
  cache_inputs['technology']=[mem(u32(0x80d890c),40*i32(0x80d8900)).hex(),mem(u32(0x80d8910),236*i32(0x80d8904)).hex()]
  cache_inputs['files']=[dict(name=name,data=open(name,'rb').read().hex())for name in sorted(n for n in os.listdir('.')if n.endswith('.dat'))]
 elif label=='scope':
  cache_outputs=[]
  for name,group in cache_ranges()['arrays'].items():
   for i,address in enumerate(group['pointers']):cache_outputs.append(dict(name=name,index=i,address=address,size=group['size'],sha256=hashlib.sha256(mem(address,group['size'])).hexdigest()))
'''


def commands(directory,observer=OBSERVER):
    text=libio.commands(directory,observer);before='result=dict(libio_inputs='
    assert text.count(before)==1
    return text.replace(before,'result=dict(cache_inputs=cache_inputs,cache_outputs=cache_outputs,libio_inputs=')


def expand_files(fixture,case):
    for record in case['cache_inputs']['files']:
        if 'data'in record:yield record['name'],bytes.fromhex(record['data']);continue
        data=b''.join(bytes.fromhex(fixture['cache_file_pages'][key])for key in record['pages'])
        assert len(data)==record['size']and hashlib.sha256(data).hexdigest()==record['sha256']
        yield record['name'],data


def main(*,fixture_name='cache_storage_original.json.gz',parent_name='libio_storage_original.json.gz',job_factory=None):
    parser=argparse.ArgumentParser(add_help=False);parser.add_argument('--full-output',type=Path)
    args,remaining=parser.parse_known_args();sys.argv=[sys.argv[0],*remaining]
    root=libio.prelude.geometry.arena.lifetime.ROOT;pages={}
    def project_case(case):
        for record in case['cache_inputs']['files']:
            data=bytes.fromhex(record.pop('data'));keys=[]
            for offset in range(0,len(data),4096):
                part=data[offset:offset+4096];key=hashlib.sha256(part).hexdigest();value=part.hex()
                if key in pages:assert pages[key]==value
                else:pages[key]=value
                keys.append(key)
            record.update(size=len(data),sha256=hashlib.sha256(data).hexdigest(),pages=keys)
        return case
    libio.prelude.geometry.arena.main(observer=OBSERVER,fixture_name=fixture_name,command_builder=commands,job_factory=job_factory,case_transform=project_case,finalize_metadata=lambda:dict(cache_file_pages=pages),
                                    extra_metadata=dict(cache_storage_parent_sha256=hashlib.sha256((root/'tests/fixtures'/parent_name).read_bytes()).hexdigest(),cache_storage_reference='All selected histories retained. At driver entry observe preexisting cache pointer arrays, complete initial array contents (lossless zero representation), raw technology records and every byte of initial external cache files. File pages are losslessly deduplicated between observations as each case finishes. At CAP entry independently hash every complete declared output table. No inferior function or instruction/allocator result is replaced.'))
    path=root/'tests/fixtures'/fixture_name;raw=path.read_bytes()
    if args.full_output:args.full_output.write_bytes(raw)
    fixture=libio.prelude.project(json.loads(gzip.decompress(raw)),hashlib.sha256(raw).hexdigest())
    with gzip.GzipFile(str(path),'wb',mtime=0)as stream:stream.write((json.dumps(fixture,separators=(',',':'))+'\n').encode())


if __name__=='__main__':main()
