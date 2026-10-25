"""Consecutive native JOINSHUNT commands from one earlier scene/heap."""
import argparse,copy,gzip,hashlib,json,subprocess,tempfile
from pathlib import Path
import capture_geometry_setup_original as setup
from capture_shunt_original import jobs as histories,command,update_names
from capture_trailing_via_heap_original import COMMANDS as BASE,native_environment
from capture_original_symmetric import ORIGINAL_SHA256,LEGACY_SHA256
ROOT=Path(__file__).resolve().parents[1]
COMMON=BASE.split('python\n',1)[1].split('class Observe',1)[0]
SHAPES='def setup_shape'+setup.OBSERVER.split('def setup_shape',1)[1].split('class SetupReturn',1)[0]
OBSERVER=COMMON+'\n'+setup.arena.OBSERVER+'\n'+SHAPES+r'''
active=False;started=False;context=None;command_inputs=[];outputs=[];interfaces=[];allocation_pending={};allocation_returns={};command_returns={}
def environment():
 result={v.split(b'=',1)[0].decode():v.split(b'=',1)[1].decode()for v in open('/proc/%d/environ'%gdb.selected_inferior().pid,'rb').read().split(b'\0')if v}
 assert not set(result)-{'PATH','HOME','LANG','LC_ALL','LD_LIBRARY_PATH','TERM','INPUTRC','LINES','COLUMNS','PWD','SHLVL','_'}
 return result
def scene():
 head=u32(0x80ce558);shapes=[];p=head;seen=set()
 while p:
  assert p not in seen;seen.add(p);shapes.append(setup_shape(p));p=u32(p+0xb0)
 return dict(head=head,selected=u32(0x80ce55c),shapes=shapes,control=reg('fctrl'),environment=environment())
class AllocationReturn(gdb.Breakpoint):
 def __init__(self,address):self.address=address;super().__init__('*'+hex(address),internal=True)
 def stop(self):
  if active:
   if allocation_pending.get(self.address):allocation_pending[self.address].pop()['address']=reg('eax')
   if interfaces and interfaces[-1][0]==self.address:interfaces.pop()
  return False
def allocation_return(address):
 if address not in allocation_returns:allocation_returns[address]=AllocationReturn(address)
class CommandReturn(gdb.Breakpoint):
 def stop(self):
  if not active:return False
  snapshot=scene();snapshot['event_count']=len(events);outputs.append(snapshot);allocator_snapshot('command_return')
  return len(outputs)==COMMAND_COUNT
class Observe(gdb.Breakpoint):
 def __init__(self,spec,kind):self.kind=kind;super().__init__(spec,internal=True)
 def stop(self):
  global active,started,context
  s=reg('esp')
  if self.kind=='command':
   if u32(s+4)!=421:return False
   if not started:
    started=True;active=True;context=scene();allocator_snapshot('command_entry')
    context['memory_regions']=[dict(address=m['start'],data=mem(m['start'],m['end']-m['start']).hex())for m in allocator_states[-1]['maps']if m['path']=='[heap]']
   record=u32(s+8);count=u32(record+256);command_inputs.append(dict(arguments=[u32(record+260*(i+1)+256)for i in range(count)],event_count=len(events)))
   ret=u32(s)
   if ret not in command_returns:command_returns[ret]=CommandReturn('*'+hex(ret),internal=True)
  elif not active:return False
  elif self.kind in('scalar','array'):
   caller=u32(s);interfaces.append((caller,self.kind));allocation_return(caller)
  elif self.kind=='malloc':
   caller=u32(s);item=dict(kind='allocate',request=u32(s+4),allocator=interfaces[-1][1]if interfaces else'malloc',caller=caller);events.append(item);allocation_pending.setdefault(caller,[]).append(item);allocation_return(caller)
  elif self.kind=='free':
   pointer=u32(s+4);events.append(dict(kind='free',address=pointer,allocator=interfaces[-1][1]if interfaces else'malloc',caller=u32(s),chunk_size=(u32(pointer-4)&~7)if pointer else None))
  return False
Observe('*0x805bd40','command')
for pc,kind in((0x804ab74,'array'),(0x804adb4,'scalar'),(0x804ac74,'array'),(0x804ad84,'scalar')):Observe('*'+hex(pc),kind)
Observe('__libc_malloc','malloc');Observe('__libc_free','free')
'''


def commands(debug,count):
    return ('set pagination off\nset confirm off\nset debuginfod enabled off\nset breakpoint pending on\nset debug-file-directory '+str(debug)+'\nhandle SIGQUIT nostop noprint pass\npython\nimport os\nCOMMAND_COUNT='+str(count)+'\n'+OBSERVER+
            '\nend\nrun -g -t process.tek -x input.asit < answers.txt\npython\n'
            'signal=0\nif len(outputs)!=COMMAND_COUNT and gdb.selected_inferior().pid:\n'
            ' try:signal=int(gdb.parse_and_eval("$_siginfo.si_signo"))\n except gdb.error:pass\n'
            'open("dispatch.json","w").write(json.dumps(dict(context=context,command_inputs=command_inputs,outputs=outputs,allocator_states=allocator_states,events=events,pending=sum(map(len,allocation_pending.values())),interfaces=len(interfaces),signal=signal)))\nend\nkill\nquit\n')


def jobs():
    parent=ROOT/'tests/fixtures/shunt_original.json.gz'
    for source in histories():
        if not source['label'].startswith('series/'):continue
        c=copy.deepcopy(source);names=c['names'].copy();prefix=c['creation']
        for name,metal in(('XS1','M2'),('XS2','M3')):
            op=dict(command='COPY',winding=0,name=name,metal=metal);prefix+=command(op,names);update_names(names,op)
        yield dict(label=c['label'],parent=parent,technology=c['technology'],stdin=c['stdin'],prefix=prefix,commands=[[names[0],'XS1'],[names[0],'XS2']])
    wire=copy.deepcopy(next(c for c in histories()if c['label']=='negative-phase'));names=wire['names'].copy();prefix=wire['creation']
    for op in wire['operations'][:2]:prefix+=command(op,names);update_names(names,op)
    yield dict(label='negative-phase',parent=parent,technology=wire['technology'],stdin=wire['stdin'],prefix=prefix,commands=[names.copy()])
    for label in('source-shorter','self'):
        c=copy.deepcopy(next(c for c in histories()if c['label']==label));names=c['names'].copy();prefix=c['creation']
        for op in c['operations'][:-1]:prefix+=command(op,names);update_names(names,op)
        op=c['operations'][-1]
        yield dict(label=label,parent=parent,technology=c['technology'],stdin=c['stdin'],prefix=prefix,commands=[[names[i]for i in[op.get('winding',0),*op['others']]]])
    for label,selected,batch,negative in(('selected-first','XS1',False,False),('selected-later','XS2',False,False),('batch-selected-later','XS2',True,False),('negative-batch',None,True,True)):
        c=copy.deepcopy(next(c for c in histories()if c['label']=='series/wire'));names=c['names'].copy();prefix=c['creation']
        if negative:prefix+='PHASE '+names[0]+' -1\n'
        for name,metal in(('XS1','M2'),('XS2','M3')):
            op=dict(command='COPY',winding=0,name=name,metal=metal);prefix+=command(op,names);update_names(names,op)
        if selected:prefix+='SELECT '+selected+'\n'
        yield dict(label=label,parent=parent,technology=c['technology'],stdin=c['stdin'],prefix=prefix,commands=[[names[0],'XS1','XS2']]if batch else[[names[0],'XS1'],[names[0],'XS2']])


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--reference',type=Path,required=True);parser.add_argument('--library-path',required=True);parser.add_argument('--debug-directory',type=Path,required=True);args=parser.parse_args();original=args.reference/'run/asitic.linux.2.2';cases=[];parents={}
    for path,digest in((original,ORIGINAL_SHA256),(args.reference/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so',LEGACY_SHA256)):
        if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('Unexpected original binary: '+str(path))
    build=setup.arena.BUILD_ID;debug=args.debug_directory/'.build-id'/build[:2]/(build[2:]+'.debug')
    for path in(Path('/lib/i386-linux-gnu/libc.so.6'),debug):
        notes=subprocess.run(['readelf','-n',str(path)],check=True,capture_output=True,text=True).stdout
        if 'Build ID: '+build not in notes:raise ValueError('Unexpected libc/debug build: '+str(path))
    with tempfile.TemporaryDirectory(prefix='pyasitic-shunt-dispatch-')as directory:
        for c in jobs():
            parent=c.pop('parent');parents[parent.name]=hashlib.sha256(parent.read_bytes()).hexdigest();script=c['prefix']+''.join('JOINSHUNT '+' '.join(names)+'\n'for names in c['commands']);gdb_commands=commands(args.debug_directory,len(c['commands']));work=Path(directory)/str(len(cases));work.mkdir()
            for name,value in(('process.tek',c['technology']),('input.asit',script),('answers.txt',c['stdin']),('capture.gdb',gdb_commands)):(work/name).write_text(value)
            env=native_environment(args.library_path);plain=subprocess.run([str(original),'-g','-t','process.tek','-x','input.asit'],cwd=work,env=env,input=c['stdin'],capture_output=True,text=True,start_new_session=True,timeout=120)
            run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=env,capture_output=True,text=True,start_new_session=True,timeout=120)
            if run.returncode or not(work/'dispatch.json').exists()or'Python Exception'in run.stderr:raise RuntimeError(c['label']+run.stdout[-1200:]+run.stderr[-1200:])
            observed=json.loads((work/'dispatch.json').read_text());cases.append(dict(c,script=script,gdb_commands=gdb_commands,plain=dict(returncode=plain.returncode,stdout=plain.stdout,stderr=plain.stderr),stdout=run.stdout,stderr=run.stderr,**observed));print(c['label'],len(observed['outputs']),'command returns',observed['signal'],'plain',plain.returncode,flush=True)
    fixture=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,libc_sha256=hashlib.sha256(Path('/lib/i386-linux-gnu/libc.so.6').read_bytes()).hexdigest(),parents=parents,observer=OBSERVER,environment_overrides=native_environment(args.library_path),reference='Nineteen selected normal command episodes: all twelve creators with two consecutive shunt joins, a negative-phase wire, unequal source, self-join, selected first/later source, selected multi-source and negative-phase multi-source commands. Initial first-dispatch scene/whole heap/allocator are component inputs. Every later argument address, selected pointer, raw live descriptor/primary/secondary record, allocation/free and allocator state is an assertion only. Both joins use one continuing source heap; no per-call snapshot resets. Plain full outcomes remain separate. The parent retains the two previously selected source-longer/duplicate native faults. No native instruction, memory, register, allocation, affinity or result is replaced.',cases=cases)
    with gzip.GzipFile(str(ROOT/'tests/fixtures/shunt_dispatch_original.json.gz'),'wb',mtime=0)as output:output.write((json.dumps(fixture,separators=(',',':'))+'\n').encode())


if __name__=='__main__':main()
