"""Read-only earlier libio ABI/globals and initial cache headers."""
import argparse,gzip,hashlib,json,sys
from pathlib import Path
import capture_prelude_storage_original as prelude

OBSERVER=prelude.OBSERVER+r'''
libio_inputs=None
_libio_snapshot=allocator_snapshot
def libio_layout(name):
 t=gdb.lookup_type(name)
 return dict(size=int(t.sizeof),fields={f.name:dict(offset=int(f.bitpos)//8,size=int(f.type.sizeof))for f in t.fields()})
def allocator_snapshot(label):
 global libio_inputs
 _libio_snapshot(label)
 if label=='driver_entry':
  import hashlib,re,subprocess
  mappings=[m for m in allocator_states[-1]['maps']if m['path'].endswith('/libc.so.6')]
  libc_path=mappings[0]['path'];libc_base=min(m['start']-m['offset']for m in mappings)
  dynamic=subprocess.check_output(['readelf','--dyn-syms','--wide',libc_path],text=True)
  symbols={}
  for name in ('_IO_list_all','_IO_file_jumps','_IO_wfile_jumps'):
   rows=[line.split()for line in dynamic.splitlines()if line.split()and line.split()[-1].split('@')[0]==name]
   assert len(rows)==1
   offset=int(rows[0][1],16);symbols[name]=dict(offset=offset,address=libc_base+offset)
  text=open('process.tek').read()
  layers=len(re.findall(r'(?im)^\s*<layer>',text));metals=len(re.findall(r'(?im)^\s*<metal>',text));header_size=16+40*layers+236*metals
  files=[]
  for name in sorted(n for n in os.listdir('.')if n.endswith('.dat')):
   data=open(name,'rb').read();assert len(data)>=header_size
   files.append(dict(name=name,size=len(data),sha256=hashlib.sha256(data).hexdigest(),header=data[:header_size].hex()))
  libio_inputs=dict(file=libio_layout('struct _IO_FILE'),plus=libio_layout('struct _IO_FILE_plus'),wide=libio_layout('struct _IO_wide_data'),lock_size=int(gdb.parse_and_eval('sizeof(_IO_stdfile_0_lock)')),list_head=u32(symbols['_IO_list_all']['address']),unqualified_list_head=int(gdb.parse_and_eval('_IO_list_all')),file_jumps=symbols['_IO_file_jumps']['address'],wide_jumps=symbols['_IO_wfile_jumps']['address'],needs_locking=int(gdb.parse_and_eval('stdio_needs_locking')),cache_files=files,substrate_count=layers,metal_count=metals,libc_symbols=symbols,libc_path=libc_path,libc_base=libc_base)
'''


def commands(directory,observer=OBSERVER):
    text=prelude.commands(directory,observer);before='result=dict(prelude_storage='
    assert text.count(before)==1
    return text.replace(before,'result=dict(libio_inputs=libio_inputs,prelude_storage=')


def main(*,fixture_name='libio_storage_original.json.gz',parent_name='prelude_storage_original.json.gz',job_factory=None):
    parser=argparse.ArgumentParser(add_help=False);parser.add_argument('--full-output',type=Path)
    options,remaining=parser.parse_known_args();sys.argv=[sys.argv[0],*remaining]
    root=prelude.geometry.arena.lifetime.ROOT;parent=root/'tests/fixtures'/parent_name
    prelude.geometry.arena.main(observer=OBSERVER,fixture_name=fixture_name,command_builder=commands,job_factory=job_factory,
                                extra_metadata=dict(libio_storage_parent_sha256=hashlib.sha256(parent.read_bytes()).hexdigest(),libio_storage_reference='All native histories and outcomes are retained. Driver-entry libio type layouts, symbol addresses, global list head/locking mode and initial external cache-file header bytes are independent earlier component inputs. Header lengths follow the initial technology record counts, never later targets/results. All pre-free buffers and whole initial/final heaps remain separate observations. No inferior function, instruction result or allocation is replaced.'))
    target=root/'tests/fixtures'/fixture_name;raw=target.read_bytes()
    if options.full_output:options.full_output.write_bytes(raw)
    fixture=prelude.project(json.loads(gzip.decompress(raw)),hashlib.sha256(raw).hexdigest())
    with gzip.GzipFile(str(target),'wb',mtime=0)as stream:stream.write((json.dumps(fixture,separators=(',',':'))+'\n').encode())


if __name__=='__main__':main()
