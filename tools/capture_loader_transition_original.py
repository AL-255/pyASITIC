"""Continuing original simulation histories with earlier loader metadata."""
import argparse,gzip,hashlib,json,sys
from pathlib import Path
import capture_command_transition_original as transition
import capture_plt_fixup_original as plt

ROOT=Path(__file__).resolve().parents[1]
COMMON=plt.OBSERVER.split('class PltTarget',1)[0].replace('arrivals=[];pending=None;action=None','arrivals=[]')
OBSERVER=transition.OBSERVER+'\n'+COMMON+r'''
def elf_plt(path,base):
 raw=open(path,'rb').read();assert raw[:5]==b'\x7fELF\x01'
 offset=struct.unpack_from('<I',raw,32)[0];size,count,names=struct.unpack_from('<HHH',raw,46)
 headers=[raw[offset+i*size:offset+(i+1)*size]for i in range(count)]
 p,n=struct.unpack_from('<II',headers[names],16);strings=raw[p:p+n]
 for header in headers:
  name=struct.unpack_from('<I',header)[0]
  if strings[name:].split(b'\0',1)[0]==b'.plt':
   address=struct.unpack_from('<I',header,12)[0];length=struct.unpack_from('<I',header,20)[0]
   return dict(address=base+address,size=length,elf_sha256=__import__('hashlib').sha256(raw).hexdigest())
 return None
_loader_transition_snapshot=allocator_snapshot
def allocator_snapshot(label):
 _loader_transition_snapshot(label)
 if label=='driver_entry':
  environment()
  block=gdb.block_for_pc(int(gdb.parse_and_eval('&_dl_lookup_symbol_x')))
  typ=gdb.lookup_type('struct link_map',block)
  assert typ.sizeof==632
  main=u32(int(gdb.parse_and_eval('&_r_debug'))+4);context=plt_inputs(main,typ)
  stack=mapping('[stack]');context['regions']=[r for r in context['regions']if r['address']!=stack['address']]
  for item in context['maps']:
   path=item['name']or'/proc/%d/exe'%gdb.selected_inferior().pid;item['plt']=elf_plt(path,u32(item['address']))
   if item['name'].endswith('/libc.so.6'):
    p=u32(item['address'])+0x22fe34+0xa0;context['regions'].append(dict(address=p,data=mem(p,4).hex()))
  context['main_map']=main
  transition_inputs['loader_context']=context
'''


def jobs():
    for job in plt.jobs():
        job['parent']=ROOT/'tests/fixtures/command_transition_original.json.gz';yield job


def main():
    transition.node.console.driver.main(fixture_name='loader_transition_original.json.gz',parent_name='command_transition_original.json.gz',job_factory=jobs,observer=OBSERVER,command_builder=transition.commands,
        state_fields=('allocator_states','post_states','transition_states'),buffer_fields=('post_buffers','transition_buffers'),
        extra_metadata=dict(loader_transition_provenance=dict(observer=OBSERVER,parents={name:hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest()for name in ('command_transition_original.json.gz','command_transition_extended_original.json.gz','plt_fixup_original.json.gz')},reference='All unchanged 134 original histories retained. Loader ELF/hash/version/scope/GOT/CPU/TLS metadata is read at the earlier first-driver entry, alongside the existing earlier stack. Later command/driver heaps, component regions, events, buffers, output files and all terminal outcomes remain assertions only. Per-call PLT/lookup snapshots are not loaded. No inferior instruction, register, returned allocation or memory byte is replaced. Environment guard precedes any new capture.')))
    target=ROOT/'tests/fixtures/loader_transition_original.json.gz';f=json.loads(gzip.decompress(target.read_bytes()));blobs={}
    for case in f['cases']:
        for r in case['transition_inputs']['loader_context']['regions']:
            raw=bytes.fromhex(r.pop('data'));key=hashlib.sha256(raw).hexdigest();blobs[key]=raw.hex();r.update(size=len(raw),sha256=key)
    f['loader_regions']=blobs
    with gzip.GzipFile(str(target),'wb',mtime=0)as stream:stream.write((json.dumps(f,separators=(',',':'))+'\n').encode())


if __name__=='__main__':main()
