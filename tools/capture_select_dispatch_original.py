"""Read-only select64 setup before the original syscall helper executes."""
import argparse,gzip,hashlib,json,sys
from pathlib import Path
import capture_poll_storage_original as parent

ROOT=Path(__file__).resolve().parents[1]
OBSERVER=parent.OBSERVER.replace("PollPoint(base+0x121390,'select',0x804be06);", "SelectSyscallPoint(base);PollPoint(base+0x121390,'select',0x804be06);")+r'''
class SelectSyscallPoint(gdb.Breakpoint):
 def __init__(self,base):self.base=base;super().__init__('*'+hex(base+0x117bb0),internal=True)
 def stop(self):
  if poll_current is None or 'syscall'in poll_current:return False
  if u32(reg('esp'))not in(self.base+0x12109e,self.base+0x12113f,self.base+0x1211a2,self.base+0x121222):return False
  context=poll_current['entry'];poll_current['syscall']=poll_state(context)
  PollPoint(u32(context['tls_base']+16),'vdso',self.base+0x117bc2);return False
'''


def commands(debug_directory):return parent.commands(debug_directory,OBSERVER)


def jobs():
    for job in parent.jobs():
        job['parent']=ROOT/'tests/fixtures/poll_storage_original.json.gz';yield job


def main():
    p=argparse.ArgumentParser(add_help=False);p.add_argument('--debug-directory',type=Path,required=True);p.add_argument('--libc',type=Path,default=Path('/lib/i386-linux-gnu/libc.so.6'));p.add_argument('--cc',default='cc');p.add_argument('--output',type=Path,default=ROOT/'tests/fixtures/select_dispatch_original.json.gz')
    own,remaining=p.parse_known_args();sys.argv=[sys.argv[0],*remaining];blobs={};cpu=parent.integer_cpu(own.cc)
    def project(case):
        for call in case['poll_calls']:
            for point in call.values():
                for r in point['regions']:
                    raw=bytes.fromhex(r.pop('data'));key=hashlib.sha256(raw).hexdigest();blobs[key]=raw.hex();r.update(size=len(raw),sha256=key)
        return case
    parent.lifetime.main(commands=commands(own.debug_directory),fixture_name=str(own.output.resolve()),job_factory=jobs,case_transform=project,finalize_metadata=lambda:dict(loader_regions=blobs),
        extra_metadata=dict(integer_cpu=cpu,select_dispatch_provenance=dict(observer=OBSERVER,libc_sha256=hashlib.sha256(own.libc.read_bytes()).hexdigest(),reference='All unchanged jobs cold/warm, with original observed and plain outcomes. Retain the complete poll/select/select64 states and add the public syscall helper entry before it executes. Only each earlier component boundary initializes its independent operation. Later memory, GP and FP are required assertions; no syscall result, kernel timing, CPU affinity, native memory, allocation, instruction or return is substituted. These per-call snapshots never initialize the continuing command replay.')))


if __name__=='__main__':main()
