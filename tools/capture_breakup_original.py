"""Unchanged original SPTOWIRE geometry histories across all twelve creators."""
import argparse,copy,gzip,hashlib,json,subprocess,tempfile
from pathlib import Path
from capture_join_original import COMMANDS as BASE,generators
from capture_unjoin_original import command as prior_command,update_names as prior_names
from capture_trailing_via_heap_original import native_environment
from capture_original_symmetric import ORIGINAL_SHA256,LEGACY_SHA256

ROOT=Path(__file__).resolve().parents[1]
COMMANDS=BASE.replace('import gdb,struct,json','import gdb,struct,json,os').replace("  states.append(dict(shapes=shapes,control=reg('fctrl')))","  environment={v.split(b'=',1)[0].decode():v.split(b'=',1)[1].decode()for v in open('/proc/%d/environ'%gdb.selected_inferior().pid,'rb').read().split(b'\\0')if v}\n  assert not set(environment)-{'PATH','HOME','LANG','LC_ALL','LD_LIBRARY_PATH','TERM','INPUTRC','LINES','COLUMNS','PWD','SHLVL','_'}\n  states.append(dict(shapes=shapes,control=reg('fctrl'),environment=environment))")


def jobs():
    joined=json.loads(gzip.decompress((ROOT/'tests/fixtures/join_original.json.gz').read_bytes()))
    bases=[c for c in generators()if '/edges/'not in c['label']]
    for base in bases:
        c=copy.deepcopy(base);state=next(c for c in joined['cases']if c['label']=='series/'+base['label'])['states'][0]
        c['counts']=[len(next(s for s in state['shapes']if s['name']==name)['segments'])for name in c['names']]
        start=len(c['names'])-1;count=c['counts'][0];c['label']='series/'+base['label']
        c['operations']=[dict(command='SPTOWIRE',winding=0),dict(command='MOVEX',winding=start,x=.125),dict(command='PHASE',winding=start,phase=-1),dict(command='COPY',winding=start,name='copied'),dict(command='RENAME',winding=start,name='leaf'),dict(command='SPTOWIRE',winding=start+count)]
        yield c
    for kind in('transformer','balun','transformer3d'):
        c=copy.deepcopy(next(c for c in jobs_base(bases,joined)if c['label']==kind));c['label']='reuse/'+kind
        c['operations']=[dict(command='SPTOWIRE',winding=0),dict(command='MOVEX',winding=0,x=.125),dict(command='COPY',winding=1,name='copied'),dict(command='MOVE',winding=0,x=1,y=2)]
        yield c
    wire=next(c for c in jobs_base(bases,joined)if c['label']=='wire')
    c=copy.deepcopy(wire);c['label']='duplicate-names';c['operations']=[dict(command='COPY',winding=0,name=c['names'][0]+'_0'),dict(command='SPTOWIRE',winding=0),dict(command='MOVEX',winding=0,x=.125)];yield c
    for alias in('DEMOLISH','SP2WIRE','BREAKUP'):
        c=copy.deepcopy(wire);c['label']='alias/'+alias;c['operations']=[dict(command=alias,winding=0)];yield c
    c=copy.deepcopy(wire);c['label']='empty/fault';c['operations']=[dict(command='UNJOIN',winding=0,index=1,name='empty'),dict(command='SPTOWIRE',winding=1)];yield c


def jobs_base(bases,joined):
    for base in bases:
        c=copy.deepcopy(base);state=next(c for c in joined['cases']if c['label']=='series/'+base['label'])['states'][0]
        c['counts']=[len(next(s for s in state['shapes']if s['name']==name)['segments'])for name in c['names']];yield c


def command(op,names):
    if op['command']in('SPTOWIRE','DEMOLISH','SP2WIRE','BREAKUP'):return op['command']+' '+names[op.get('winding',0)]+'\n'
    return prior_command(op,names)


def update_names(names,counts,op):
    index=op.get('winding',0);kind=op['command']
    if kind in('SPTOWIRE','DEMOLISH','SP2WIRE','BREAKUP'):
        name=names.pop(index);count=counts.pop(index);names.extend(name+'_'+str(i)for i in range(count));counts.extend([1]*count)
    else:
        if kind=='COPY':counts.append(counts[index])
        elif kind=='UNJOIN':counts.append(counts[index]-op['index']);counts[index]=op['index']
        prior_names(names,op)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--reference',type=Path,required=True);parser.add_argument('--library-path',required=True);args=parser.parse_args();original=args.reference.resolve()/'run/asitic.linux.2.2';parents={};cases=[]
    for path,digest in((original,ORIGINAL_SHA256),(args.reference/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so',LEGACY_SHA256)):
        if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('Unexpected native binary')
    parents['join_original.json.gz']=hashlib.sha256((ROOT/'tests/fixtures/join_original.json.gz').read_bytes()).hexdigest()
    with tempfile.TemporaryDirectory(prefix='pyasitic-breakup-original-')as directory:
        for c in jobs():
            parent=c['parent']+'.json';parents[parent]=hashlib.sha256((ROOT/'tests/fixtures'/parent).read_bytes()).hexdigest();names=c['names'].copy();counts=c['counts'].copy();script=c['creation']+'WHO\n'
            for op in c['operations']:script+=command(op,names)+'WHO\n';update_names(names,counts,op)
            work=Path(directory)/str(len(cases));work.mkdir()
            for name,value in(('process.tek',c['technology']),('input.asit',script),('answers.txt',c['stdin']),('capture.gdb',COMMANDS)):(work/name).write_text(value)
            environment=native_environment(args.library_path)
            plain=subprocess.run([str(original),'-g','-t','process.tek','-x','input.asit'],cwd=work,env=environment,input=c['stdin'],capture_output=True,text=True,start_new_session=True,timeout=120)
            run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=environment,capture_output=True,text=True,start_new_session=True,timeout=120)
            if run.returncode or not(work/'spatial.json').exists()or'Python Exception'in run.stderr:raise RuntimeError(c['label']+run.stdout[-1800:]+run.stderr[-1200:])
            observed=json.loads((work/'spatial.json').read_text());cases.append(dict(c,script=script,plain=dict(returncode=plain.returncode,stdout=plain.stdout,stderr=plain.stderr),stdout=run.stdout,stderr=run.stderr,**observed));print(c['label'],len(observed['states']),'states; signal',observed['signal'],'plain',plain.returncode,flush=True)
    fixture=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,parents=parents,gdb_commands=COMMANDS,reference='All twelve existing creators, repeated breakup, native aliases, retained materials/origins/phase, copied leaf segments, existing-name collisions, paired descriptor release/reuse and the selected empty-chain fault. Every unchanged script also runs without GDB. WHO-entry snapshots retain every live descriptor, complete defined ribbon coordinates/materials, native header fields and live/stale friend identities. Minimal native environment guards run at each observation; no native numerical instruction, memory, register, allocator, return or outcome is substituted. Secondary segment groups created by JOINSHUNT are outside this cohort.',cases=cases)
    with gzip.GzipFile(str(ROOT/'tests/fixtures/breakup_original.json.gz'),'wb',mtime=0)as stream:stream.write((json.dumps(fixture,separators=(',',':'))+'\n').encode())


if __name__=='__main__':main()
