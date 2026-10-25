"""Every internal getline memchr/memcpy call in unchanged original histories."""
import argparse,hashlib,struct,subprocess,sys,tempfile
from pathlib import Path
import capture_dispatch_storage_original as dispatch
import capture_read_transition_original as parent
import capture_trailing_via_heap_original as lifetime
from getline_fixture import pack_state

ROOT=Path(__file__).resolve().parents[1]
CPU_PROBE=r'''
typedef unsigned U;
void _start(void) {
 U rows[24][4],n=0;
 for(U a=0;a<2;a++)for(U i=0;i<12;i++) {
  U v=(U[]){0,1,2,3,4,5,7,16,255,0x80000000,0xffffffff,0x40000000}[i],input=v,before,after;
  __asm__ volatile("pushfl; popl %0":"=r"(before));before=(before&~16u)|(a*16u);
  __asm__ volatile("pushl %2; popfl; shrl $1,%0; pushfl; popl %1":"+r"(v),"=r"(after):"r"(before):"cc");
  rows[n][0]=input;rows[n][1]=before;rows[n][2]=v;rows[n][3]=after;n++;
 }
 __asm__ volatile("int $0x80"::"a"(4),"b"(1),"c"(rows),"d"(sizeof rows):"memory");
 __asm__ volatile("int $0x80"::"a"(1),"b"(0));
}
'''


def integer_cpu(cc):
    with tempfile.TemporaryDirectory(prefix='pyasitic-getline-cpu-')as directory:
        binary=Path(directory)/'probe'
        subprocess.run([cc,'-m32','-x','c','-','-nostdlib','-static','-fno-stack-protector','-fno-pic','-Wl,-e,_start','-o',str(binary)],input=CPU_PROBE,text=True,check=True)
        raw=subprocess.check_output([str(binary)],env=lifetime.native_environment(''),start_new_session=True)
    if len(raw)!=384:raise ValueError('Incomplete i386 SHR observation')
    rows=[dict(zip(('input','flags_before','result','flags_after'),row))for row in struct.iter_unpack('<4I',raw)]
    af={r['flags_after']&16 for r in rows}
    if len(af)==1:behavior=af.pop()
    elif all(r['flags_after']&16==r['flags_before']&16 for r in rows):behavior='preserve'
    else:raise NotImplementedError('CPU SHR AF behavior needs another source model')
    return dict(probe=CPU_PROBE,observations=rows,shr1_af=behavior)


OBSERVER=dispatch.transition.COMMON+'\n'+dispatch.ELF_PLT+r'''
byte_calls=[];byte_active=False;byte_seen=False;byte_next=None;byte_exit=None;byte_exit_signal=0
def byte_context():
 block=gdb.block_for_pc(int(gdb.parse_and_eval('&_dl_lookup_symbol_x')));typ=gdb.lookup_type('struct link_map',block);assert typ.sizeof==632
 main=u32(int(gdb.parse_and_eval('&_r_debug'))+4);ctx=plt_inputs(main,typ);ctx['main_map']=main
 for item in ctx['maps']:item['plt']=elf_plt(item['name']or'/proc/%d/exe'%gdb.selected_inferior().pid,u32(item['address']))
 ctx['regions']+=[mapping('[heap]'),dict(address=reg('ebp'),data=mem(reg('ebp'),152).hex())]
 return ctx
class ByteReturn(gdb.Breakpoint):
 def __init__(self,pc,item):self.item=item;super().__init__('*'+hex(pc),internal=True,temporary=True)
 def stop(self):
  if 'after'in self.item or reg('esp')!=self.item['before']['registers']['esp']+4:return False
  a=self.item['before'];self.item['after']=dict(registers=registers(),xstate=regset(0x202).hex(),regions=[dict(address=r['address'],data=mem(r['address'],len(r['data'])//2).hex())for r in a['regions']]);return False
class ByteEntry(gdb.Breakpoint):
 def __init__(self,pc,kind,returns):self.kind=kind;self.returns=returns;super().__init__('*'+hex(pc),internal=True)
 def stop(self):
  if not byte_active or u32(reg('esp'))not in self.returns:return False
  env=environment();ctx=byte_context();ctx.update(registers=registers(),xstate=regset(0x202).hex(),environment=env)
  item=dict(kind=self.kind,before=ctx);byte_calls.append(item);ByteReturn(u32(reg('esp')),item);return False
class ByteDriverReturn(gdb.Breakpoint):
 def stop(self):
  global byte_active
  byte_active=True;base=int(gdb.parse_and_eval('&_IO_getline_info'))-0x772e0
  ByteEntry(base+0xbb650,'memchr',{base+0x77343});ByteEntry(base+0xbbae0,'memcpy',{base+0x7735e,base+0x773f6});return False
class ByteDriver(gdb.Breakpoint):
 def stop(self):
  global byte_seen,byte_next
  if byte_active:byte_next=dict(pc=reg('pc'),esp=reg('esp'));return True
  if not byte_seen:byte_seen=True;ByteDriverReturn('*'+hex(u32(reg('esp'))),internal=True,temporary=True)
  return False
for pc in (0x8050b2c,0x8051280):ByteDriver('*'+hex(pc),internal=True)
def byte_exited(event):
 global byte_exit,byte_exit_signal
 byte_exit=getattr(event,'exit_code',None)
 if byte_exit is None:
  try:byte_exit_signal=int(gdb.parse_and_eval('$_exitsignal'))
  except gdb.error:pass
gdb.events.exited.connect(byte_exited)
'''


def commands(directory):
    return ('set pagination off\nset confirm off\nset debuginfod enabled off\nset breakpoint pending on\nset debug-file-directory '+str(directory)+'\nhandle SIGQUIT nostop noprint pass\npython\n'+OBSERVER+
            '\nend\nrun -g -t process.tek -x input.asit < answers.txt\npython\nsignal=byte_exit_signal\n'
            'if byte_next is None and gdb.selected_inferior().pid:\n try:signal=int(gdb.parse_and_eval("$_siginfo.si_signo"))\n except gdb.error:pass\n'
            'result=dict(byte_calls=byte_calls,next_driver=byte_next,native_exit=byte_exit,events=[],node=None,signal=signal)\nopen("heap.json","w").write(json.dumps(result))\n'
            'if gdb.selected_inferior().pid:gdb.execute("kill",to_string=True)\nend\nquit\n')


def jobs():
    for job in parent.jobs():
        job['parent']=ROOT/'tests/fixtures/read_transition_original.json.gz';yield job


def pack_region(region,raw,pages):
    keys=[]
    for offset in range(0,len(raw),4096):
        page=raw[offset:offset+4096];key=hashlib.sha256(page).hexdigest();pages[key]=page.hex();keys.append(key)
    region.update(size=len(raw),sha256=hashlib.sha256(raw).hexdigest(),pages=keys)


def main():
    p=argparse.ArgumentParser(add_help=False);p.add_argument('--debug-directory',type=Path,required=True);p.add_argument('--cc',default='cc');own,remaining=p.parse_known_args();sys.argv=[sys.argv[0],*remaining];cpu=integer_cpu(own.cc);pages={};records={};indices={}
    def project(case):
        for call in case['byte_calls']:
            for point in (call['before'],call.get('after',{})):
                for r in point.get('regions',[]):
                    pack_region(r,bytes.fromhex(r.pop('data')),pages)
                if 'regions'in point:pack_state(point,records,indices)
        return case
    lifetime.main(commands=commands(own.debug_directory),fixture_name='getline_bytes_original.json.gz',job_factory=jobs,case_transform=project,finalize_metadata=lambda:dict(loader_pages=pages,loader_records=records,loader_record_keys=list(indices)),
        extra_metadata=dict(integer_cpu=cpu,getline_bytes_provenance=dict(observer=OBSERVER,reference='All unchanged 134 histories retained. Every post-driver internal getline memchr/memcpy call records complete earlier stack/ELF/TLS/heap/FILE regions and full later regions/registers/XSAVE assertions. Independent 32-bit CPU SHR profile precedes every job. No inferior instruction, register, memory, result, allocation or signal is substituted. Minimal environment guard precedes capture; component snapshots never seed continuing replay.')))


if __name__=='__main__':main()
