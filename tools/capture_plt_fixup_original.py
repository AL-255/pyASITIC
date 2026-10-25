"""Read-only i386 lazy PLT entry -> resolved function entry, all histories."""
import argparse,hashlib,os,sys
from pathlib import Path
import capture_loader_lookup_original as lookup

ROOT=Path(__file__).resolve().parents[1]
COMMON=lookup.OBSERVER.split('class LookupReturn',1)[0]
OBSERVER=COMMON+r'''
plt_calls=[];plt_pending=[];plt_active=False;plt_seen=False;plt_next_driver=None;plt_native_exit=None;plt_exit_signal=0;plt_returns={}
def tls_base():
 desc=ctypes.create_string_buffer(16)
 if libc.ptrace(25,gdb.selected_inferior().pid,reg('gs')>>3,ctypes.byref(desc)):raise OSError(ctypes.get_errno())
 return struct.unpack_from('<I',desc.raw,4)[0]
def plt_inputs(map_,typ):
 context=loader_inputs([0,map_,0,u32(map_+488),0,1,1,0],typ);regions=context['regions']
 def include(p,n):
  if p and n:regions.append(dict(address=p,data=mem(p,n).hex()))
 for item in context['maps']:
  m=gdb.Value(item['address']).cast(typ.pointer()).dereference();info=m['l_info'];addr=int(m['l_addr'])if bool(m['l_ld_readonly'])else 0
  def dyn(tag):return u32(int(info[tag])+4)if int(info[tag])else 0
  rel=dyn(23)+addr if dyn(23)else 0;size=dyn(2)
  include(rel,size)
  if rel:
   if dyn(20)!=17:raise RuntimeError('Non-REL PLT needs a different observer')
   for offset in range(0,size,8):include(int(m['l_addr'])+u32(rel+offset),4)
  got=dyn(3)+addr if dyn(3)else 0;include(got,12)
  if item['name'].endswith('/libc.so.6'):
   cgot=int(m['l_addr'])+0x22fe34;include(cgot+0x10c,4);cpu=u32(cgot+0x10c)
   for offset in (0x75,0x7b,0x19c):include(cpu+offset,1)
 base=context['loader_base'];include(base+0x33fe8-0x458,4);tls=tls_base();include(tls,32)
 context['tls_base']=tls
 return context
class PltTarget(gdb.Breakpoint):
 def __init__(self,pc,item):self.item=item;super().__init__('*'+hex(pc),internal=True,temporary=True)
 def stop(self):
  if 'after'in self.item:return False
  a=self.item['before'];r=registers()
  assert r['esp']==a['registers']['esp']+8
  assert all(r[k]==a['registers'][k]for k in ('eax','ebx','ecx','edx','esi','edi','ebp'))
  self.item['after']=dict(registers=r,xstate=regset(0x202).hex(),regions=[dict(address=v['address'],data=mem(v['address'],len(v['data'])//2).hex())for v in a['regions']])
  self.enabled=False
  return False
class PltFixed(gdb.Breakpoint):
 def stop(self):
  if plt_pending:
   item=plt_pending.pop();PltTarget(reg('eax'),item)
  return False
class PltEntry(gdb.Breakpoint):
 def stop(self):
  if not plt_active:return False
  env=environment();s=reg('esp');map_=u32(s);typ=gdb.lookup_type('struct link_map',gdb.selected_frame().block())
  before=dict(registers=registers(),environment=env,xstate=regset(0x202).hex(),**plt_inputs(map_,typ));item=dict(before=before)
  plt_calls.append(item);plt_pending.append(item);base=before['loader_base']
  if base not in plt_returns:plt_returns[base]=PltFixed('*'+hex(base+0x11bb0),internal=True)
  return False
class PltDriverReturn(gdb.Breakpoint):
 def stop(self):
  global plt_active
  plt_active=True;return False
class PltDriver(gdb.Breakpoint):
 def stop(self):
  global plt_seen,plt_next_driver
  if plt_active:plt_next_driver=dict(pc=reg('pc'),esp=reg('esp'));return True
  if not plt_seen:plt_seen=True;PltDriverReturn('*'+hex(u32(reg('esp'))),internal=True,temporary=True)
  return False
for pc in (0x8050b2c,0x8051280):PltDriver('*'+hex(pc),internal=True)
PltEntry('_dl_runtime_resolve',internal=True)
def plt_exited(event):
 global plt_native_exit,plt_exit_signal
 plt_native_exit=getattr(event,'exit_code',None)
 if plt_native_exit is None:
  try:plt_exit_signal=int(gdb.parse_and_eval('$_exitsignal'))
  except gdb.error:pass
gdb.events.exited.connect(plt_exited)
'''


def commands(debug_directory):
    return ('set pagination off\nset confirm off\nset debuginfod enabled off\nset breakpoint pending on\n'
            'set debug-file-directory '+str(debug_directory)+'\nhandle SIGQUIT nostop noprint pass\npython\n'+OBSERVER+
            '\nend\nrun -g -t process.tek -x input.asit < answers.txt\npython\n'
            'signal=plt_exit_signal\nif plt_next_driver is None and gdb.selected_inferior().pid:\n'
            ' try:signal=int(gdb.parse_and_eval("$_siginfo.si_signo"))\n except gdb.error:pass\n'
            'result=dict(plt_calls=plt_calls,plt_pending=len(plt_pending),next_driver=plt_next_driver,native_exit=plt_native_exit,events=[],node=None,signal=signal)\n'
            'open("heap.json","w").write(json.dumps(result))\n'
            'if gdb.selected_inferior().pid:gdb.execute("kill",to_string=True)\nend\nquit\n')


def jobs():
    for job in lookup.jobs():
        job['parent']=ROOT/'tests/fixtures/loader_lookup_original.json.gz';yield job


def main():
    parser=argparse.ArgumentParser(add_help=False);parser.add_argument('--debug-directory',type=Path,required=True);parser.add_argument('--loader',type=Path,default=Path('/lib/i386-linux-gnu/ld-linux.so.2'));parser.add_argument('--libc',type=Path,default=Path('/lib/i386-linux-gnu/libc.so.6'))
    own,remaining=parser.parse_known_args();sys.argv=[sys.argv[0],*remaining];blobs={}
    def project(case):
        for call in case['plt_calls']:
            for phase in ('before','after'):
                if phase not in call:continue
                for r in call[phase]['regions']:
                    raw=bytes.fromhex(r.pop('data'));key=hashlib.sha256(raw).hexdigest();blobs[key]=raw.hex();r.update(size=len(raw),sha256=key)
        return case
    lookup.install.signals.lifetime.main(commands=commands(own.debug_directory),fixture_name='plt_fixup_original.json.gz',job_factory=jobs,case_transform=project,finalize_metadata=lambda:dict(loader_regions=blobs),
        extra_metadata=dict(plt_fixup_provenance=dict(observer=OBSERVER,loader_sha256=hashlib.sha256(own.loader.read_bytes()).hexdigest(),libc_sha256=hashlib.sha256(own.libc.read_bytes()).hexdigest(),kernel_release=os.uname().release,reference='All unchanged jobs/cold/warm states retained. Observe every lazy PLT resolver entry after the first driver and its actual target function entry, before the target runs. Earlier memory includes ELF metadata/GOT, CPU feature flags, TLS and full stack/registers/XSAVE. Later target-entry memory/registers/XSAVE are assertions only. CPU-dependent IFUNC results are never inputs. Minimal environment guard precedes capture. No code image, instruction, inferior register, memory or returned result is replaced. Independent PLT snapshots are not continuing-replay seeds.')))


if __name__=='__main__':main()
