"""Unchanged JOINSHUNT histories with complete primary/secondary link records."""
import argparse,copy,gzip,hashlib,json,subprocess,tempfile
from pathlib import Path
from capture_spatial_edits_original import jobs as generators
from capture_unjoin_original import command as previous_command,update_names as previous_names
from capture_trailing_via_heap_original import native_environment
from capture_original_symmetric import ORIGINAL_SHA256,LEGACY_SHA256

ROOT=Path(__file__).resolve().parents[1]
COMMANDS=r'''
set pagination off
set confirm off
set environment TERM dumb
set environment INPUTRC /dev/null
handle SIGQUIT nostop noprint pass
python
import gdb,struct,json,os
states=[]
def mem(a,n):return bytes(gdb.selected_inferior().read_memory(a,n))
def reg(k):return int(gdb.parse_and_eval('$'+k))&0xffffffff
def u32(a):return struct.unpack('<I',mem(a,4))[0]
def i32(a):return struct.unpack('<i',mem(a,4))[0]
def text(a):return mem(a,80).split(b'\0',1)[0].decode('latin1')
def record(a):
 metal=i32(a+0xdc);metals=i32(0x80d8904)
 r=dict(address=a,next_address=u32(a+0xec),group_address=u32(a+0xe8),raw=mem(a,240).hex(),coordinates_bits=b''.join(mem(a+o,24)for o in(0,24,0x44,0x5c,0x88,0xa0)).hex(),width_bits=mem(a+0xcc,8).hex(),metal=metal)
 if metal<metals:r.update(thickness_bits=mem(a+0xd4,8).hex(),primary_width_bits=mem(a+0x30,8).hex(),primary_thickness_bits=mem(a+0x38,8).hex())
 else:r.update(nx=i32(a+0xe0),ny=i32(a+0xe4))
 return r
def shape(a):
 out=dict(address=a,name=text(a),origin_bits=mem(a+0x54,16).hex(),native_kind=i32(a+0x50),native_n=i32(a+0x64),turns_bits=mem(a+0x98,8).hex(),attributes=i32(a+0xac),partner_address=u32(a+0xb4),segments=[]);s=u32(a+0xa8);seen=set()
 while s:
  if s in seen or len(seen)>=20000:raise RuntimeError('Cyclic or unbounded native primary chain')
  seen.add(s);r=record(s);r['secondary']=[];child=r['group_address'];children=set()
  while child:
   if child in children or len(children)>=20000:raise RuntimeError('Cyclic or unbounded native secondary chain')
   children.add(child);r['secondary'].append(record(child));child=u32(child+0xe8)
  out['segments'].append(r);s=r['next_address']
 return out
class Observe(gdb.Breakpoint):
 def stop(self):
  if i32(reg('esp')+4)!=224:return False
  environment={v.split(b'=',1)[0].decode():v.split(b'=',1)[1].decode()for v in open('/proc/%d/environ'%gdb.selected_inferior().pid,'rb').read().split(b'\0')if v}
  assert not set(environment)-{'PATH','HOME','LANG','LC_ALL','LD_LIBRARY_PATH','TERM','INPUTRC','LINES','COLUMNS','PWD','SHLVL','_'}
  head=u32(0x80ce558);shapes=[];seen=set()
  while head:
   if head in seen or len(seen)>=20000:raise RuntimeError('Cyclic or unbounded native descriptor chain')
   seen.add(head);shapes.append(shape(head));head=u32(head+0xb0)
  names={s['address']:s['name']for s in shapes}
  for s in shapes:s.update(partner=names.get(s['partner_address']),dangling_partner=bool(s['partner_address']and s['partner_address']not in names))
  states.append(dict(shapes=shapes,control=reg('fctrl'),environment=environment));return False
Observe('*0x805bd40',internal=True)
end
run -g -t process.tek -x input.asit < answers.txt
python
signal=0
if gdb.selected_inferior().pid:signal=int(gdb.parse_and_eval('$_siginfo.si_signo'));gdb.execute('kill',to_string=True)
open('shunt.json','w').write(json.dumps(dict(states=states,signal=signal)))
end
quit
'''


def jobs():
    bases=[c for c in generators()if '/edges/'not in c['label']]
    for base in bases:
        c=copy.deepcopy(base);n=len(c['names']);c['label']='series/'+base['label']
        c['operations']=[dict(command='COPY',winding=0,name='c',metal='M2'),dict(command='JOINSHUNT',winding=0,others=[n]),dict(command='PHASE',winding=0,phase=-1),dict(command='PHASE',winding=0,phase=1),dict(command='COPY',winding=0,name='d'),dict(command='MOVEX',winding=n,x=.125),dict(command='FLIP',winding=n)]
        yield c
    square=next(c for c in bases if c['label']=='square');wire=next(c for c in bases if c['label']=='wire')
    c=copy.deepcopy(square);c['label']='repeated/square';c['operations']=[dict(command='COPY',winding=0,name='c',metal='M2'),dict(command='JOINSHUNT',winding=0,others=[1]),dict(command='COPY',winding=0,name='d',metal='M3'),dict(command='JOINSHUNT',winding=0,others=[1]),dict(command='COPY',winding=0,name='e'),dict(command='ROTATE',winding=1,angle=17.123456789),dict(command='FLIPV',winding=1)];yield c
    for label,ops in[
        ('source-shorter',[dict(command='COPY',winding=0,name='c'),dict(command='UNJOIN',winding=1,index=1,name='tail'),dict(command='JOINSHUNT',winding=0,others=[1])]),
        ('source-longer',[dict(command='COPY',winding=0,name='c'),dict(command='UNJOIN',winding=0,index=1,name='tail'),dict(command='JOINSHUNT',winding=0,others=[1])]),
    ]:
        c=copy.deepcopy(square);c['label']=label;c['operations']=ops;yield c
    for label,ops in[
        ('self',[dict(command='JOINSHUNT',winding=0,others=[0])]),
        ('duplicates',[dict(command='COPY',winding=0,name='c'),dict(command='JOINSHUNT',winding=0,others=[1,1])]),
        ('negative-phase',[dict(command='PHASE',winding=0,phase=-1),dict(command='COPY',winding=0,name='c',metal='M2'),dict(command='JOINSHUNT',winding=0,others=[1]),dict(command='PHASE',winding=0,phase=-1)]),
        ('breakup',[dict(command='COPY',winding=0,name='c',metal='M2'),dict(command='JOINSHUNT',winding=0,others=[1]),dict(command='SPTOWIRE',winding=0)]),
    ]:
        c=copy.deepcopy(wire);c['label']=label;c['operations']=ops;yield c


def command(op,names):
    if op['command']=='JOINSHUNT':return 'JOINSHUNT '+' '.join(names[i]for i in[op.get('winding',0),*op['others']])+'\n'
    if op['command']=='SPTOWIRE':return 'SPTOWIRE '+names[op.get('winding',0)]+'\n'
    return previous_command(op,names)


def update_names(names,op):
    if op['command']=='JOINSHUNT':names[:]=[name for i,name in enumerate(names)if i in[op.get('winding',0)]or i not in op['others']]
    elif op['command']=='SPTOWIRE':names[:]=[names[0]+'_0',names[0]+'_0_0']
    else:previous_names(names,op)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--reference',type=Path,required=True);parser.add_argument('--library-path',required=True);args=parser.parse_args();original=args.reference.resolve()/'run/asitic.linux.2.2';parents={};cases=[]
    for path,digest in((original,ORIGINAL_SHA256),(args.reference/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so',LEGACY_SHA256)):
        if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('Unexpected native binary')
    with tempfile.TemporaryDirectory(prefix='pyasitic-shunt-original-')as directory:
        for c in jobs():
            parent=c['parent']+'.json';parents[parent]=hashlib.sha256((ROOT/'tests/fixtures'/parent).read_bytes()).hexdigest();names=c['names'].copy();script=c['creation']+'WHO\n'
            for op in c['operations']:script+=command(op,names)+'WHO\n';update_names(names,op)
            work=Path(directory)/str(len(cases));work.mkdir()
            for name,value in(('process.tek',c['technology']),('input.asit',script),('answers.txt',c['stdin']),('capture.gdb',COMMANDS)):(work/name).write_text(value)
            env=native_environment(args.library_path);plain=subprocess.run([str(original),'-g','-t','process.tek','-x','input.asit'],cwd=work,env=env,input=c['stdin'],capture_output=True,text=True,start_new_session=True,timeout=120)
            run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=env,capture_output=True,text=True,start_new_session=True,timeout=120)
            if run.returncode or not(work/'shunt.json').exists()or'Python Exception'in run.stderr:raise RuntimeError(c['label']+run.stdout[-1800:]+run.stderr[-1200:])
            observed=json.loads((work/'shunt.json').read_text());cases.append(dict(c,script=script,plain=dict(returncode=plain.returncode,stdout=plain.stdout,stderr=plain.stderr),stdout=run.stdout,stderr=run.stderr,**observed));print(c['label'],len(observed['states']),'states; signal',observed['signal'],'plain',plain.returncode,flush=True)
    fixture=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,parents=parents,gdb_commands=COMMANDS,reference='All twelve existing creators and selected repeated, unequal-chain, self, duplicate, negative-phase and breakup JOINSHUNT histories. Every unchanged script runs plainly and with read-only WHO-entry observers. All ordered primary and secondary records, full raw segment bytes, native next/group pointers, defined geometry/material/header/phase fields and live/stale descriptor links remain present. Minimal environment guards precede observation. No native instruction, numerical input, register, memory, allocation, returned result or outcome is replaced.',cases=cases)
    with gzip.GzipFile(str(ROOT/'tests/fixtures/shunt_original.json.gz'),'wb',mtime=0)as stream:stream.write((json.dumps(fixture,separators=(',',':'))+'\n').encode())


if __name__=='__main__':main()
