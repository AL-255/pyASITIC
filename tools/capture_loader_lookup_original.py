"""Read-only lazy-symbol lookup inputs and complete returns for all histories."""
import argparse,hashlib,os,sys
from pathlib import Path
import capture_signal_install_original as install

ROOT=Path(__file__).resolve().parents[1]
OBSERVER=install.COMMON+r'''
lookup_calls=[];lookup_pending={};lookup_returns={};lookup_active=False;driver_seen=False;next_driver=None;native_exit=None
def u32(a):return struct.unpack('<I',mem(a,4))[0]
def string(p):
 if not p:return b''
 out=bytearray()
 for i in range(1048576):
  c=mem(p+i,1);out.extend(c)
  if c==b'\0':return bytes(out)
 raise RuntimeError('Unterminated loader string')
def layout(typ,offset=0):
 out={}
 for f in typ.fields():
  if f.name:out[f.name]=dict(offset=offset+f.bitpos//8,bit=f.bitpos%8,bits=f.bitsize,size=f.type.sizeof)
  else:out.update(layout(f.type,offset+f.bitpos//8))
 return out
def loader_inputs(args,typ):
 regions={};seen=set();maps=[];scopes=[]
 def include(p,n):
  if p and n:regions[(p,n)]=dict(address=p,data=mem(p,n).hex())
 def cstr(p):
  if p:include(p,len(string(p)))
 def provider(address):
  if address in seen:return
  seen.add(address);m=gdb.Value(address).cast(typ.pointer()).dereference();include(address,typ.sizeof);cstr(int(m['l_name']))
  maps.append(dict(address=address,name=string(int(m['l_name']))[:-1].decode(errors='surrogateescape')))
  addr=int(m['l_addr']);relative=bool(m['l_ld_readonly']);info=m['l_info'];dynamic={}
  for i in range(80):
   p=int(info[i])
   if p:include(p,8);dynamic[u32(p)]=u32(p+4)
  def dptr(tag):return dynamic.get(tag,0)+(addr if relative and dynamic.get(tag,0)else 0)
  symtab,strtab=dptr(6),dptr(5);include(strtab,dynamic.get(10,0));oldhash=dptr(4)
  if oldhash:
   buckets,nsyms=u32(oldhash),u32(oldhash+4);include(oldhash,8+4*(buckets+nsyms))
  elif int(m['l_gnu_bitmask']):
   header=dptr(0x6ffffef5);include(header,16);nsyms=u32(header+4)
   p=int(m['l_gnu_buckets']);n=int(m['l_nbuckets']);last=max([u32(p+4*i)for i in range(n)],default=0)
   if last:
    while not u32(int(m['l_gnu_chain_zero'])+4*last)&1:last+=1
    nsyms=last+1
  else:nsyms=0
  if int(m['l_gnu_bitmask']):
   p=int(m['l_gnu_buckets']);n=int(m['l_nbuckets']);include(int(m['l_gnu_bitmask']),4*(int(m['l_gnu_bitmask_idxbits'])+1));include(p,4*n)
   first=min((u32(p+4*i)for i in range(n)if u32(p+4*i)),default=nsyms)
   include(int(m['l_gnu_chain_zero'])+4*first,4*(nsyms-first))
  include(symtab,16*nsyms);include(int(m['l_versyms']),2*nsyms)
  versions=int(m['l_versions']);count=int(m['l_nversions']);include(versions,16*count)
  for i in range(count):cstr(u32(versions+16*i));cstr(u32(versions+16*i+12))
  p=int(m['l_libname']);names=set()
  while p:
   assert p not in names;names.add(p);include(p,12);cstr(u32(p));p=u32(p+4)
  real=int(m['l_real'])
  if real!=address:provider(real)
 p=args[3]
 while u32(p):
  elem=u32(p);lst=u32(elem);count=u32(elem+4);include(elem,8);include(lst,4*count)
  scopes.append(dict(address=elem,count=count))
  for i in range(count):provider(u32(lst+4*i))
  p+=4
 include(args[3],p-args[3]+4);provider(args[1]);cstr(args[0]);include(args[2],4)
 if args[4]:include(args[4],16);cstr(u32(args[4]));cstr(u32(args[4]+12))
 ld=next(m['address']for m in maps if m['name'].endswith('/ld-linux.so.2'));base=u32(ld);got=base+0x33fe8
 for p in (got-0x488,got-0x454,got+0x5f4):include(p,4)
 stack=mapping('[stack]');include(stack['address'],len(stack['data'])//2)
 return dict(loader_base=base,regions=list(regions.values()),maps=maps,scopes=scopes)
class LookupReturn(gdb.Breakpoint):
 def __init__(self,pc):self.pc=pc;super().__init__('*'+hex(pc),internal=True)
 def stop(self):
  if self.pc in lookup_pending and lookup_pending[self.pc]:
   item=lookup_pending[self.pc].pop();a=item['before']
   item['after']=dict(registers=registers(),xstate=regset(0x202).hex(),regions=[dict(address=r['address'],data=mem(r['address'],len(r['data'])//2).hex())for r in a['regions']])
  return False
class LookupEntry(gdb.Breakpoint):
 def stop(self):
  if not lookup_active:return False
  env=environment();s=reg('esp');args=[u32(s+4+4*i)for i in range(8)];typ=gdb.lookup_type('struct link_map',gdb.selected_frame().block())
  item=dict(name=string(args[0])[:-1].decode(errors='surrogateescape'),arguments=args,link_map_layout=dict(size=typ.sizeof,fields=layout(typ)),before=dict(registers=registers(),environment=env,xstate=regset(0x202).hex(),**loader_inputs(args,typ)))
  lookup_calls.append(item);pc=u32(s);lookup_pending.setdefault(pc,[]).append(item)
  if pc not in lookup_returns:lookup_returns[pc]=LookupReturn(pc)
  return False
class FirstDriverReturn(gdb.Breakpoint):
 def stop(self):
  global lookup_active
  lookup_active=True;return False
class Driver(gdb.Breakpoint):
 def stop(self):
  global driver_seen,next_driver
  if lookup_active:next_driver=dict(pc=reg('pc'),esp=reg('esp'));return True
  if not driver_seen:driver_seen=True;FirstDriverReturn('*'+hex(u32(reg('esp'))),internal=True,temporary=True)
  return False
for pc in (0x8050b2c,0x8051280):Driver('*'+hex(pc),internal=True)
LookupEntry('_dl_lookup_symbol_x',internal=True)
def exited(event):
 global native_exit
 native_exit=event.exit_code
gdb.events.exited.connect(exited)
'''


def commands(debug_directory):
    return ('set pagination off\nset confirm off\nset debuginfod enabled off\nset breakpoint pending on\n'
            'set debug-file-directory '+str(debug_directory)+'\nhandle SIGQUIT nostop noprint pass\npython\n'+OBSERVER+
            '\nend\nrun -g -t process.tek -x input.asit < answers.txt\npython\n'
            'signal=0\nif next_driver is None and gdb.selected_inferior().pid:\n'
            ' try:signal=int(gdb.parse_and_eval("$_siginfo.si_signo"))\n except gdb.error:pass\n'
            'result=dict(lookup_calls=lookup_calls,lookup_pending=sum(map(len,lookup_pending.values())),next_driver=next_driver,native_exit=native_exit,events=[],node=None,signal=signal)\n'
            'open("heap.json","w").write(json.dumps(result))\n'
            'if gdb.selected_inferior().pid:gdb.execute("kill",to_string=True)\nend\nquit\n')


def jobs():
    for job in install.jobs():
        job['parent']=ROOT/'tests/fixtures/signal_install_original.json.gz';yield job


def main():
    parser=argparse.ArgumentParser(add_help=False);parser.add_argument('--debug-directory',type=Path,required=True);parser.add_argument('--loader',type=Path,default=Path('/lib/i386-linux-gnu/ld-linux.so.2'))
    own,remaining=parser.parse_known_args();sys.argv=[sys.argv[0],*remaining];blobs={}
    def project(case):
        for call in case['lookup_calls']:
            for phase in ('before','after'):
                if phase not in call:continue
                for r in call[phase]['regions']:
                    raw=bytes.fromhex(r.pop('data'));key=hashlib.sha256(raw).hexdigest();blobs[key]=raw.hex();r.update(size=len(raw),sha256=key)
        return case
    install.signals.lifetime.main(commands=commands(own.debug_directory),fixture_name='loader_lookup_original.json.gz',job_factory=jobs,case_transform=project,finalize_metadata=lambda:dict(loader_regions=blobs),
        extra_metadata=dict(loader_lookup_provenance=dict(observer=OBSERVER,loader_sha256=hashlib.sha256(own.loader.read_bytes()).hexdigest(),kernel_release=os.uname().release,reference='Every unchanged original job is run cold and warm. Observe every lazy symbol lookup after first driver return, ending at the next driver entry or original terminal outcome. Earlier inputs comprise full stack, ELF symbol/hash/version metadata, scopes, link maps, loader globals, registers and XSAVE. Complete return regions/registers/XSAVE are assertions only. No code image or observed return is used by the Python resolver. All original faults and histories without calls remain explicit. Environment is whitelisted before any stack capture. No inferior registers, memory, instructions or results are replaced. Component inputs are never used to seed the continuing driver comparison.')))


if __name__=='__main__':main()
