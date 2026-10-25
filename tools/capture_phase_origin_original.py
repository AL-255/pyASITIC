"""Read-only startup strcmp binding -> interactive capacitor phase provenance."""
import argparse,gzip,hashlib,json,subprocess,tempfile
from pathlib import Path
import capture_plt_fixup_original as plt
from capture_primitive_original import jobs as primitives
from capture_original_symmetric import ORIGINAL_SHA256,LEGACY_SHA256
from capture_trailing_via_heap_original import native_environment
ROOT=Path(__file__).resolve().parents[1]

OBSERVER=plt.OBSERVER.replace('plt_active=False','plt_active=True',1).replace("for pc in (0x8050b2c,0x8051280):PltDriver('*'+hex(pc),internal=True)",'')
ENTRY="env=environment();s=reg('esp');map_=u32(s);typ=gdb.lookup_type('struct link_map',gdb.selected_frame().block())"
FILTER=ENTRY+r'''
  lm=gdb.Value(map_).cast(typ.pointer()).dereference();info=lm['l_info'];off=u32(s+4)
  rel=u32(int(info[23])+4)+off;sym=u32(int(info[6])+4)+16*(u32(rel+4)>>8);name=string(u32(int(info[5])+4)+u32(sym))
  if int(lm['l_addr'])!=0 or name!=b'strcmp\0':return False'''
assert OBSERVER.count(ENTRY)==1
OBSERVER=OBSERVER.replace(ENTRY,FILTER).replace('for offset in (0x75,0x7b,0x19c):include(cpu+offset,1)','include(cpu+0x74,4)\n   for offset in (0x75,0x7b,0x19c):include(cpu+offset,1)')
OBSERVER=OBSERVER.replace("self.enabled=False\n  return False", "self.enabled=False\n  PhaseWatch(a['registers']['esp']-140)\n  return False",1)
OBSERVER+=r'''
phase_context=None;final_context=None;phase_writes=[]
class PhaseWatch(gdb.Breakpoint):
 def __init__(self,address):
  self.address=address
  super().__init__('*(unsigned int*)'+hex(address),type=gdb.BP_WATCHPOINT,wp_class=gdb.WP_WRITE,internal=True)
 def stop(self):
  phase_writes.append(dict(address=self.address,pc=reg('pc'),value=u32(self.address)));return False
class Capacitor(gdb.Breakpoint):
 def stop(self):
  global phase_context
  s=reg('esp');arg=u32(s+4)
  phase_context=dict(address=arg+0xac,phase=u32(arg+0xac),argument_address=arg,argument_data=mem(arg,188).hex(),registers=registers(),control=reg('fctrl'),environment=environment(),write_count=len(phase_writes))
  self.enabled=False;return False
class Completed(gdb.Breakpoint):
 def stop(self):
  global final_context
  if u32(reg('esp')+4)!=224:return False
  head=u32(0x80ce558);final_context=dict(address=head,descriptor=mem(head,188).hex(),phase=u32(head+0xac),control=reg('fctrl'),environment=environment(),write_count=len(phase_writes))
  return True
Capacitor('*0x8057998',internal=True);Completed('*0x805bd40',internal=True)
'''


def commands(debug):
    return ('set pagination off\nset confirm off\nset debuginfod enabled off\nset breakpoint pending on\nset debug-file-directory '+str(debug)+'\nhandle SIGQUIT nostop noprint pass\npython\n'+OBSERVER+
            '\nend\nrun -g -t process.tek -x input.asit < answers.txt\npython\n'
            'open("phase.json","w").write(json.dumps(dict(phase_context=phase_context,final_context=final_context,phase_writes=phase_writes,plt_calls=plt_calls,plt_pending=len(plt_pending))))\nend\nkill\nquit\n')


def jobs():
    for c in primitives():
        if c['kind']=='capacitor'and c.get('native_interactive'):yield c


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--reference',type=Path,required=True);parser.add_argument('--library-path',required=True);parser.add_argument('--debug-directory',type=Path,required=True);args=parser.parse_args()
    original=args.reference/'run/asitic.linux.2.2';legacy=args.reference/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so'
    for path,digest in((original,ORIGINAL_SHA256),(legacy,LEGACY_SHA256)):
        if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('Unexpected native binary: '+str(path))
    parent=ROOT/'tests/fixtures/primitive_original.json';technology=json.loads(parent.read_text())['technology'];gdb_commands=commands(args.debug_directory);cases=[];blobs={}
    with tempfile.TemporaryDirectory(prefix='pyasitic-phase-origin-')as directory:
        for c in jobs():
            work=Path(directory)/str(len(cases));work.mkdir();script=c['script']+'WHO\n';env=native_environment(args.library_path)
            for name,value in(('process.tek',technology),('input.asit',script),('answers.txt',c['stdin']),('capture.gdb',gdb_commands)):(work/name).write_text(value)
            plain=subprocess.run([str(original),'-g','-t','process.tek','-x','input.asit'],cwd=work,env=env,input=c['stdin'],capture_output=True,text=True,start_new_session=True,timeout=120)
            run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=env,capture_output=True,text=True,start_new_session=True,timeout=120)
            if run.returncode or not(work/'phase.json').exists()or'Python Exception'in run.stderr:raise RuntimeError(c['label']+run.stdout[-1200:]+run.stderr[-1200:])
            result=json.loads((work/'phase.json').read_text())
            for call in result['plt_calls']:
                for phase in('before','after'):
                    for region in call[phase]['regions']:
                        data=bytes.fromhex(region.pop('data'));key=hashlib.sha256(data).hexdigest();blobs[key]=data.hex();region.update(size=len(data),sha256=key)
            cases.append(dict(c,script=script,technology=technology,plain=dict(returncode=plain.returncode,stdout=plain.stdout,stderr=plain.stderr),stdout=run.stdout,stderr=run.stderr,**result));print(c['label'],len(result['plt_calls']),'resolver calls; phase',hex(result['phase_context']['phase']),'changed writes',len(result['phase_writes']),flush=True)
    fixture=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,parents={parent.name:hashlib.sha256(parent.read_bytes()).hexdigest()},gdb_commands=gdb_commands,observer=OBSERVER,loader_sha256=hashlib.sha256(Path('/lib/i386-linux-gnu/ld-linux.so.2').read_bytes()).hexdigest(),libc_sha256=hashlib.sha256(Path('/lib/i386-linux-gnu/libc.so.6').read_bytes()).hexdigest(),environment_overrides=native_environment(args.library_path),reference='Four unchanged interactive capacitor creators. Observe earlier native strcmp lazy-binding entry and target entry with complete ELF lookup data, CPU feature inputs, TLS, stack/registers/XSAVE; then constructor arguments and completed WHO descriptor. A hardware write watch observes subsequent changes of the loader ESI-save slot; no register, numerical instruction, memory, allocation or result is replaced. Earlier resolver memory is component input; later target and constructor/descriptor values are independent assertions, never execution seeds. Does not emulate all intervening startup/prompt operations or arbitrary previous command histories.',loader_regions=blobs,cases=cases)
    with gzip.GzipFile(str(ROOT/'tests/fixtures/phase_origin_original.json.gz'),'wb',mtime=0)as output:output.write((json.dumps(fixture,separators=(',',':'))+'\n').encode())


if __name__=='__main__':main()
