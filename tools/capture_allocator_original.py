"""Read-only glibc allocator state around the original CAP/LMAT lifetimes.

Matching detached libc symbols must be extracted beforehand. No inferior
functions are called, and no register or byte in the original is changed.
"""
import argparse,hashlib,subprocess,sys
from pathlib import Path
import capture_trailing_via_heap_original as lifetime

BUILD_ID='9596d2907557f8966ee5796efe796849ce95de88'
OBSERVER=r'''
allocator_states=[]
def allocator_snapshot(label):
 arena=gdb.parse_and_eval('main_arena');params=gdb.parse_and_eval('mp_');cache=gdb.parse_and_eval('tcache')
 top=int(arena['top']);base=int(params['sbrk_base']);chunks=[];errors=[]
 # i386 malloc aligns user pointers to 16, after its eight-byte header.
 cursor=base+(-(base+8)%16)
 while cursor<=top:
  prev,word=struct.unpack('<II',mem(cursor,8));size=word&~7
  if size<16 or (cursor!=top and size%16):
   errors.append(dict(section='chunks',address=cursor,size_word=word));break
  chunks.append(dict(address=cursor,prev_size=prev,size_word=word))
  if cursor==top:break
  if cursor+size>top:
   errors.append(dict(section='chunks',address=cursor,size_word=word));break
  cursor+=size
 def chain_at(head,end,offset,safe,section):
  chain=[];p=head
  while p!=end:
   if p in chain or len(chain)>=100000:
    errors.append(dict(section=section,address=p,reason='cycle-or-limit'));break
   try:following=u32(p+offset)
   except gdb.MemoryError as error:
    errors.append(dict(section=section,address=p,reason=str(error)));break
   chain.append(p);p=following^((p+offset)>>12)if safe else following
  return chain
 bins=[]
 for index in range(1,128):
  head=int((arena['bins'][2*(index-1)]).address)-8
  chain=chain_at(u32(head+8),head,8,False,'bin.%d'%index);previous=head
  for p in chain:
   if u32(p+12)!=previous:errors.append(dict(section='bin.%d'%index,address=p,reason='backlink'))
   previous=p
  if u32(head+12)!=previous:errors.append(dict(section='bin.%d'%index,address=head,reason='tail'))
  bins.append(chain)
 fastbins=[]
 for index in range(11):
  chain=chain_at(int(arena['fastbinsY'][index]),0,8,True,'fastbin.%d'%index)
  fastbins.append(chain)
 tcache=[]
 for index in range(64):
  chain=chain_at(int(cache['entries'][index])if int(cache)else 0,0,0,True,'tcache.%d'%index)
  if len(chain)!=(int(cache['counts'][index])if int(cache)else 0):errors.append(dict(section='tcache.%d'%index,reason='count',count=int(cache['counts'][index]),observed=len(chain)))
  tcache.append(chain)
 maps=[]
 for line in open('/proc/%d/maps'%gdb.selected_inferior().pid):
  fields=line.split();start,end=(int(v,16)for v in fields[0].split('-'))
  maps.append(dict(start=start,end=end,permissions=fields[1],offset=int(fields[2],16),path=' '.join(fields[5:])))
 state=dict(label=label,event_count=len(events),arena_address=int(arena.address),arena_bytes=mem(int(arena.address),int(arena.type.sizeof)).hex(),parameters={field.name:int(params[field.name])for field in params.type.fields()},top=top,last_remainder=int(arena['last_remainder']),flags=int(arena['flags']),have_fastchunks=int(arena['have_fastchunks']),system_mem=int(arena['system_mem']),max_fast=int(gdb.parse_and_eval('global_max_fast')),tcache_address=int(cache),tcache_counts=[int(cache['counts'][i])if int(cache)else 0 for i in range(64)],tcache=tcache,fastbins=fastbins,bins=bins,chunks=chunks,maps=maps,errors=errors)
 allocator_states.append(state)
'''


def commands(debug_directory,observer=OBSERVER):
    text=lifetime.COMMANDS
    replacements=[
        ('set pagination off','set debug-file-directory '+str(debug_directory)+'\nset debuginfod enabled off\nset pagination off'),
        ('class Observe(gdb.Breakpoint):',observer+'\nclass Observe(gdb.Breakpoint):'),
        ("events.append(dict(kind='scope',contacts=i32(cap_frame-0xbc),groups=i32(cap_frame-0xb4),control=reg('fctrl')))","events.append(dict(kind='scope',contacts=i32(cap_frame-0xbc),groups=i32(cap_frame-0xb4),control=reg('fctrl')))\n   allocator_snapshot('scope')"),
        ("events.append(dict(kind='via_entry',**out,indices=indices));", "allocator_snapshot('via_entry')\n   events.append(dict(kind='via_entry',**out,indices=indices));"),
        ("node=dict(size=n,cap_address=cap", "allocator_snapshot('node')\n   node=dict(size=n,cap_address=cap"),
        ('result=dict(events=events,','result=dict(allocator_states=allocator_states,events=events,'),
    ]
    for before,after in replacements:
        assert text.count(before)==1,before
        text=text.replace(before,after)
    return text


def main(*,observer=OBSERVER,fixture_name='allocator_state_original.json.gz',extra_metadata=None,command_builder=None,job_factory=None):
    parser=argparse.ArgumentParser(add_help=False)
    parser.add_argument('--debug-directory',type=Path,required=True)
    parser.add_argument('--libc',type=Path,default=Path('/lib/i386-linux-gnu/libc.so.6'))
    options,remaining=parser.parse_known_args()
    debug=options.debug_directory/'.build-id'/BUILD_ID[:2]/(BUILD_ID[2:]+'.debug')
    if not debug.is_file():parser.error('Matching libc debug file is missing: '+str(debug))
    for path in (options.libc,debug):
        notes=subprocess.run(['readelf','-n',str(path)],check=True,capture_output=True,text=True).stdout
        if 'Build ID: '+BUILD_ID not in notes:parser.error('Unexpected ELF build ID: '+str(path))
    sys.argv=[sys.argv[0],*remaining]
    metadata=dict(allocator_provenance=dict(libc_sha256=hashlib.sha256(options.libc.read_bytes()).hexdigest(),libc_build_id=BUILD_ID,debug_sha256=hashlib.sha256(debug.read_bytes()).hexdigest(),libc_version='Ubuntu GLIBC 2.39-0ubuntu8.9',pointer_bytes=4,alignment=16,observer=observer,parent_sha256=hashlib.sha256((lifetime.ROOT/'tests/fixtures/trailing_via_heap_original.json.gz').read_bytes()).hexdigest()))
    if extra_metadata:metadata.update(extra_metadata)
    builder=commands if command_builder is None else command_builder
    lifetime.main(commands=builder(options.debug_directory,observer),fixture_name=fixture_name,extra_metadata=metadata,job_factory=job_factory)


if __name__=='__main__':main()
