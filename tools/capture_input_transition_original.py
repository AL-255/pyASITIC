"""Earlier stdin ABI globals, external file stat and string literals."""
import argparse,gzip,hashlib,json,sys
from pathlib import Path
import capture_stdio_transition_original as stdio
from capture_poll_storage_original import integer_cpu

ROOT=Path(__file__).resolve().parents[1]
OBSERVER=stdio.OBSERVER+r'''
_input_transition_snapshot=allocator_snapshot
def allocator_snapshot(label):
 _input_transition_snapshot(label)
 if label=='driver_entry':
  environment();context=transition_inputs['loader_context'];owners=transition_inputs['stdio_context']['regions']
  base=u32(next(x['address']for x in context['maps']if x['name'].endswith('/libc.so.6')));got=base+0x22fe34
  for address,size in ((got+0x11c,4),(got+0x1a30,4),(u32(got+0x11c),4),(0x80b4800,160)):
   context['regions'].append(dict(address=address,data=mem(address,size).hex()));owners.append(dict(address=address,size=size))
  main_line=u32(transition_inputs['workspace_address']+4460)-1024
  context['regions'].append(dict(address=main_line,data=mem(main_line,1024).hex()));owners.append(dict(address=main_line,size=1024))
  st=os.stat('/proc/%d/fd/0'%gdb.selected_inferior().pid)
  transition_inputs['stdio_context']['input_abi']=dict(stdin_stat={name:getattr(st,name)for name in ('st_dev','st_ino','st_mode','st_nlink','st_uid','st_gid','st_rdev','st_size','st_blksize','st_blocks','st_atime_ns','st_mtime_ns','st_ctime_ns')})
'''


def jobs():
    for job in stdio.jobs():
        job['parent']=ROOT/'tests/fixtures/stdio_transition_original.json.gz';yield job


def main():
    p=argparse.ArgumentParser(add_help=False);p.add_argument('--cc',default='cc');own,remaining=p.parse_known_args();sys.argv=[sys.argv[0],*remaining];cpu=integer_cpu(own.cc)
    stdio.loader.transition.node.console.driver.main(fixture_name='input_transition_original.json.gz',parent_name='stdio_transition_original.json.gz',job_factory=jobs,observer=OBSERVER,command_builder=stdio.loader.transition.commands,
        state_fields=('allocator_states','post_states','transition_states'),buffer_fields=('post_buffers','transition_buffers'),
        extra_metadata=dict(integer_cpu=cpu,input_transition_provenance=dict(observer=OBSERVER,parent_sha256=hashlib.sha256((ROOT/'tests/fixtures/stdio_transition_original.json.gz').read_bytes()).hexdigest(),reference='All unchanged 134 histories retained. Earlier first-driver stdin stat metadata, libc IO ABI globals and immutable string literals supplement the prior full stdio context. Every added memory region is asserted at all later points and final states. No later native call/output state seeds continuation and no inferior result, instruction, allocation, memory or register is substituted. Minimal environment guards precede capture.')))
    target=ROOT/'tests/fixtures/input_transition_original.json.gz';f=json.loads(gzip.decompress(target.read_bytes()));blobs={}
    for case in f['cases']:
        case['transition_inputs']['stdio_context']['sar31_af']=cpu['sar31_af']
        for r in case['transition_inputs']['loader_context']['regions']:
            raw=bytes.fromhex(r.pop('data'));key=hashlib.sha256(raw).hexdigest();blobs[key]=raw.hex();r.update(size=len(raw),sha256=key)
    f['loader_regions']=blobs
    with gzip.GzipFile(str(target),'wb',mtime=0)as stream:stream.write((json.dumps(f,separators=(',',':'))+'\n').encode())


if __name__=='__main__':main()
