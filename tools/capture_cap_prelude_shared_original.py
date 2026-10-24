"""Combined contact/cache history and projected shared-memory observations."""
import argparse,gzip,hashlib,json,shutil,sys
from pathlib import Path
import capture_allocator_original as arena
import capture_cap_prelude_original as prefix
from capture_mapping_allocator_original import OBSERVER as MAPPING_OBSERVER
from capture_shared_memory_original import OBSERVER as SHARED_OBSERVER,project
assert prefix.OBSERVER.startswith(MAPPING_OBSERVER)
OBSERVER=SHARED_OBSERVER+prefix.OBSERVER[len(MAPPING_OBSERVER):]


if __name__=='__main__':
    parser=argparse.ArgumentParser(add_help=False);parser.add_argument('--full-output',type=Path)
    options,remaining=parser.parse_known_args();sys.argv=[sys.argv[0],*remaining]
    parents={name:hashlib.sha256((arena.lifetime.ROOT/'tests/fixtures'/name).read_bytes()).hexdigest()for name in ('cap_prelude_original.json.gz','shared_heap_original.json.gz')}
    name='cap_prelude_shared_original.json.gz'
    arena.main(observer=OBSERVER,fixture_name=name,extra_metadata=dict(prelude_shared_parents=parents),command_builder=prefix.commands)
    target=arena.lifetime.ROOT/'tests/fixtures'/name
    if options.full_output:shutil.copyfile(target,options.full_output)
    raw=target.read_bytes();fixture=project(json.loads(gzip.decompress(raw)));fixture['full_capture_sha256']=hashlib.sha256(raw).hexdigest()
    with gzip.GzipFile(str(target),'wb',mtime=0)as stream:stream.write((json.dumps(fixture,separators=(',',':'))+'\n').encode())
