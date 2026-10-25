"""Original formatter calls, complete earlier data, and named helper boundaries."""
import argparse,sys
from pathlib import Path
import capture_printf_file_original as parent
import capture_printf_buffer_original as buffer
import capture_trailing_via_heap_original as lifetime
from capture_getline_bytes_original import integer_cpu
from printf_archive import read_fixture,split_archive

ROOT=Path(__file__).resolve().parents[1]
EXTRA=r'''
format_section_cache={}
def formatter_context():
 block=gdb.block_for_pc(int(gdb.parse_and_eval('&_dl_lookup_symbol_x')));typ=gdb.lookup_type('struct link_map',block);assert typ.sizeof==632
 main=u32(int(gdb.parse_and_eval('&_r_debug'))+4);ctx=plt_inputs(main,typ);ctx['main_map']=main
 for item in ctx['maps']:item['plt']=elf_plt(item['name']or'/proc/%d/exe'%gdb.selected_inferior().pid,u32(item['address']))
 s=reg('esp');buffer=u32(s+4);mode=u32(buffer+20);ctx['buffer_mode']=mode
 base=u32(next(x['address']for x in ctx['maps']if x['name'].endswith('/libc.so.6')));got=base+0x22fe34;tls=ctx['tls_base']
 allocator_snapshot('printf-format');heap=allocator_states.pop();ctx['heap']=heap;ctx['profile']={}
 ctx['regions']+=[mapping('[heap]'),dict(address=heap['arena_address'],data=heap['arena_bytes'])]
 controls=[(buffer,156 if mode==4 else 24),(got+0xa0,4),((u32(tls)+u32(got+0xa0))&0xffffffff,4),
  (got+0x1a30,4),(got+0x1c4,4),(u32(tls+16),32),(got+0x78,4),(got+0x368,4),(got+0x3bfc,4),
  (got+0x3c04,1),(got+0x3c14,4),(got+0x3c18,1),((tls+u32(got+0x78))&0xffffffff,4)]
 if mode==4:
  file=u32(buffer+24);offset=struct.unpack('<b',mem(file+70,1))[0];vt=u32(file+148+offset);fd=u32(file+56)
  controls.extend([(file,152),(u32(file+72),12),(vt,84)]);ctx['file']=file;ctx['profile']=dict(fd=fd,statx=statx_metadata(fd))
  start=u32(file+28);end=u32(file+32)
  if start and end>start:controls.append((start,end-start))
 start=u32(buffer);end=u32(buffer+8)
 if start and end>start:
  owner=next(x for x in heap['maps']if x['start']<=start<x['end'])
  p,n=(start,end-start)if end<=owner['end']else(owner['start'],owner['end']-owner['start'])
  controls.append((p,n));ctx['output_owner']=dict(address=p,size=n,declared_start=start,declared_end=end)
 ctx['regions']+=[dict(address=p,data=mem(p,n).hex())for p,n in controls if p and n]
 format_inputs(ctx);return ctx
def format_elf_data(path,base):
 if path not in format_section_cache:
  raw=open(path,'rb').read();assert raw[:6]==b'\x7fELF\x01\x01'
  offset=struct.unpack_from('<I',raw,32)[0];size,count,names=struct.unpack_from('<HHH',raw,46)
  headers=[raw[offset+i*size:offset+(i+1)*size]for i in range(count)]
  p,n=struct.unpack_from('<II',headers[names],16);strings=raw[p:p+n];sections=[]
  for header in headers:
   name=strings[struct.unpack_from('<I',header)[0]:].split(b'\0',1)[0]
   if name in (b'.rodata',b'.data.rel.ro',b'.got',b'.got.plt',b'.data',b'.bss'):
    address=struct.unpack_from('<I',header,12)[0];length=struct.unpack_from('<I',header,20)[0]
    sections.append(dict(name=name.decode(),offset=address,size=length))
  format_section_cache[path]=dict(elf_sha256=__import__('hashlib').sha256(raw).hexdigest(),sections=sections)
 result=dict(path=path,base=base,**format_section_cache[path]);result['sections']=[dict(s,address=base+s['offset'])for s in result['sections']]
 return result
def format_inputs(ctx):
 regions=ctx['regions'];elf=[]
 for item in ctx['maps']:
  name=item['name']
  if item['address']!=ctx['main_map']and not name.endswith(('/libc.so.6','/ld-linux.so.2','/libstdc++-libc6.1-1.so.2')):continue
  path=name or'/proc/%d/exe'%gdb.selected_inferior().pid;data=format_elf_data(path,u32(item['address']));elf.append(data)
  for section in data['sections']:regions.append(dict(address=section['address'],data=mem(section['address'],section['size']).hex()))
 s=reg('esp');fmt=u32(s+8);raw=gdb.Value(fmt).cast(gdb.lookup_type('char').pointer()).string(encoding='latin1').encode('latin1')
 start=fmt&~3;end=(fmt+len(raw)+4)&~3;regions.append(dict(address=start,data=mem(start,end-start).hex()))
 tls=ctx['tls_base'];base=u32(next(x['address']for x in ctx['maps']if x['name'].endswith('/libc.so.6')));got=base+0x22fe34
 thread=u32(tls);size=gdb.lookup_type('struct pthread').sizeof;regions.append(dict(address=tls,data=mem(tls,size).hex()))
 slot=(thread+u32(got+0x16c))&0xffffffff;regions.append(dict(address=slot,data=mem(slot,4).hex()))
 ro=gdb.parse_and_eval('_rtld_global_ro');static_size=int(ro['_dl_tls_static_size']);static_align=int(ro['_dl_tls_static_align'])
 assert static_size>=size and static_align>0 and static_align&(static_align-1)==0
 static_start=tls-(static_size-size);regions.append(dict(address=static_start,data=mem(static_start,static_size).hex()))
 ctx['format_inputs']=dict(elf_data=elf,pthread_size=size,format=fmt,format_bytes=len(raw)+1,format_owner=dict(address=start,size=end-start),locale_slot=slot,locale=u32(slot),
  static_tls=dict(address=static_start,size=static_size,alignment=static_align,tcb_size=size,loader_ro=int(ro.address),size_address=int(ro['_dl_tls_static_size'].address)))
class FormatPoint(gdb.Breakpoint):
 def __init__(self,pc):super().__init__('*'+hex(pc),internal=True)
 def stop(self):
  if file_current is None:return False
  if 'initial_write'in file_current:raise RuntimeError('Repeated initial formatter write boundary')
  file_current['initial_write']=dict(before=file_state(file_current['before']),children_start=len(file_current['children']));return False
'''

OBSERVER=parent.OBSERVER.replace(
 "for off,kind in ((0x586c0,'init'),(0x58710,'done')):FileEntry(base+off,kind)",
 "FileEntry(base+0x60530,'format');FormatPoint(base+0x605b3)").replace(
 "env=environment();ctx=file_context(self.kind)",
 "env=environment();ctx=formatter_context()").replace(
 "((0x58570,'switch')",
 "((0xa3cb0,'strchrnul'),(0x58750,'write'),(0x58390,'pad'),(0x58440,'putc'),(0x584b0,'puts'),(0x58230,'flush'),(0x5a990,'fp-l-buffer'),(0x58920,'fp-buffer'),(0xbc470,'strlen-ia32'),(0xa9630,'strlen-sse2-bsf'),(0x19ccc0,'strlen-sse2'),(0xbb390,'strnlen-ia32'),(0x19ea20,'strnlen-sse2'),(0x56dd0,'itoa-word'),(0x56ec0,'itoa'),(0x58570,'switch')")
OBSERVER+='\n'+EXTRA


def commands(directory):return parent.commands(directory).replace(parent.OBSERVER,OBSERVER)


def jobs():
    for job in parent.jobs():
        job['parent']=ROOT/'tests/fixtures/vfprintf_original.manifest.json';yield job


class Projection(buffer.PrintfProjection):
    def case(self,case):
        calls=case['printf_calls'];count=len(calls)
        calls.extend(call['initial_write']for call in list(calls)if 'initial_write'in call)
        try:super().case(case)
        finally:del calls[count:]
        return case


def main():
    p=argparse.ArgumentParser(add_help=False);p.add_argument('--debug-directory',type=Path,required=True);p.add_argument('--cc',default='cc');p.add_argument('--output',type=Path,default=ROOT/'tests/fixtures/printf_format_original.json.gz');own,remaining=p.parse_known_args()
    archive=own.output.resolve()
    if not archive.name.endswith('.json.gz'):raise ValueError('Formatter capture output must end with .json.gz')
    archive.parent.mkdir(parents=True,exist_ok=True);sys.argv=[sys.argv[0],*remaining];projection=Projection();cpu=integer_cpu(own.cc)
    lifetime.main(commands=commands(own.debug_directory),fixture_name=str(archive),job_factory=jobs,case_transform=projection.case,finalize_metadata=projection.metadata,
        extra_metadata=dict(integer_cpu=cpu,printf_format_provenance=dict(observer=OBSERVER,reference='Every formatter call in all unchanged jobs cold/warm. Complete earlier owned stack/heap/ELF/TLS/FILE/arena/error data includes actual ELF read-only/GOT/data sections and aligned native format bytes. Full later owners/registers/XSAVE/heap and named helper registers remain required. The initial source-write boundary is separately retained without dropping any parent/child target. Independent earlier i386 SHR profile precedes jobs. No inferior instruction, memory, register, allocation, result or signal is replaced; minimal environment guards precede capture. No call snapshot seeds continuing replay.')))
    fixture=read_fixture(archive);histories=len(fixture['cases']);parents=fixture['parents'];del fixture
    split_archive(archive,archive.with_name(archive.name.removesuffix('.json.gz')+'.manifest.json'),histories=histories,parents=parents);archive.unlink()


if __name__=='__main__':main()
