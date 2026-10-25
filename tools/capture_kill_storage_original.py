"""Read-only native kill/VDSO prefixes across all unchanged ASITIC jobs."""
import argparse,hashlib,sys
from pathlib import Path
import capture_dispatch_storage_original as parent

ROOT=Path(__file__).resolve().parents[1]
OBSERVER=parent.OBSERVER.replace("context['characters']=dict(","p=u32(context['tls_base']+16);context['regions'].append(dict(address=p,data=mem(p,16).hex()))\n context['characters']=dict(")
old="dispatch_current[self.kind]=dispatch_state(dispatch_current['entry']);return False"
assert OBSERVER.count(old)==1
OBSERVER=OBSERVER.replace(old,"dispatch_current[self.kind]=dispatch_state(dispatch_current['entry'])\n  if self.kind=='kill':KillVDSO(dispatch_current['entry'])\n  return False")+r'''
class KillKernel(gdb.Breakpoint):
 def __init__(self,pc,esp):self.esp=esp;super().__init__('*'+hex(pc),internal=True)
 def stop(self):
  if dispatch_current is None or'kill_kernel'in dispatch_current or reg('esp')!=self.esp:return False
  dispatch_current['kill_kernel']=dispatch_state(dispatch_current['entry']);return False
class KillVDSO(gdb.Breakpoint):
 def __init__(self,context):
  self.context=context;self.base=u32(next(m['address']for m in context['maps']if m['name'].endswith('/libc.so.6')))
  super().__init__('*'+hex(u32(context['tls_base']+16)),internal=True)
 def stop(self):
  if dispatch_current is None or'kill_vdso'in dispatch_current or u32(reg('esp'))!=self.base+0x3c3a6:return False
  dispatch_current['kill_vdso']=dispatch_state(self.context);pc=reg('pc');data=mem(pc,12)
  if data.startswith(bytes.fromhex('0f1f0051525589cd0f05cd80')):offset=8
  elif data.startswith(bytes.fromhex('51525589e50f34cd805d5a59')):offset=5
  else:raise RuntimeError('Unrecognized native VDSO syscall prefix')
  KillKernel(pc+offset,reg('esp')-12);return False
'''


def commands(directory):return parent.commands(directory).replace(parent.OBSERVER,OBSERVER)


def jobs():
    for job in parent.jobs():
        job['parent']=ROOT/'tests/fixtures/dispatch_storage_original.json.gz';yield job


def main():
    p=argparse.ArgumentParser(add_help=False);p.add_argument('--debug-directory',type=Path,required=True);p.add_argument('--libc',type=Path,default=Path('/lib/i386-linux-gnu/libc.so.6'));p.add_argument('--output',type=Path,default=ROOT/'tests/fixtures/kill_storage_original.json.gz');own,remaining=p.parse_known_args();sys.argv=[sys.argv[0],*remaining];blobs={}
    def project(case):
        for call in case['dispatch_calls']:
            for point in call.values():
                for r in point['regions']:
                    raw=bytes.fromhex(r.pop('data'));key=hashlib.sha256(raw).hexdigest();blobs[key]=raw.hex();r.update(size=len(raw),sha256=key)
        return case
    parent.transition.plt.lookup.install.signals.lifetime.main(commands=commands(own.debug_directory),fixture_name=str(own.output.resolve()),job_factory=jobs,case_transform=project,finalize_metadata=lambda:dict(loader_regions=blobs),
        extra_metadata=dict(kill_storage_provenance=dict(observer=OBSERVER,libc_sha256=hashlib.sha256(own.libc.read_bytes()).hexdigest(),reference='All unchanged 134 histories retained, with native signals and plain outcomes. Add the earlier immutable VDSO prefix to dispatch-owned inputs and assert it at every later boundary. Observe resolved kill entry, VDSO entry and the actual syscall instruction before execution. Entire owned memory, GP and XSAVE remain targets; later values never initialize continuing replay. No kernel result, allocation, native instruction, memory, register, CPU affinity or signal is substituted.')))


if __name__=='__main__':main()
