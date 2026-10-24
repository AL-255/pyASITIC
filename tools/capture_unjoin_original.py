"""Unchanged original UNJOIN histories, boundary indices and empty-chain faults."""
import argparse,copy,gzip,hashlib,json,os,subprocess,tempfile
from pathlib import Path
from capture_join_original import COMMANDS,generators,command as prior_command,update_names as prior_names
from capture_original_symmetric import ORIGINAL_SHA256,LEGACY_SHA256
ROOT=Path(__file__).resolve().parents[1]


def jobs():
    prior=json.loads(gzip.decompress((ROOT/'tests/fixtures/join_original.json.gz').read_bytes()))
    bases=[c for c in generators()if '/edges/'not in c['label']]
    counts={c['label'].removeprefix('series/'):len(next(s for s in c['states'][0]['shapes']if s['name']==c['names'][0])['segments'])for c in prior['cases']if c['label'].startswith('series/')}
    for base in bases:
        c=copy.deepcopy(base);n=len(c['names']);count=counts[base['label']];c['label']='series/'+base['label']
        if count==1:
            ops=[dict(command='UNJOIN',winding=0,index=0,name='c',expect_rejection=True),dict(command='UNJOIN',winding=0,index=1,name='c')]
        else:
            ops=[dict(command='UNJOIN',winding=0,index=0,name='c'),dict(command='MOVE',winding=n,x=.125,y=-.25),dict(command='PHASE',winding=n,phase=-1),dict(command='FLIP',winding=n),dict(command='COPY',winding=n,name='d'),dict(command='JOIN',winding=0,others=[n,n+1]),dict(command='UNJOIN',winding=0,index=-1,name='e'),dict(command='FLIPH',winding=n)]
        c['operations']=ops;yield c
    for kind in('square','wire'):
        base=next(c for c in bases if c['label']==kind);count=counts[kind]
        for index in sorted({-count-1,-count,-count+1,-2,-1,0,1,count-1,count,count+1}):
            c=copy.deepcopy(base);c['label']=f'index/{kind}/{index}'
            rejected=abs(index)>count or(index==0 and count<2)
            c['operations']=[dict(command='UNJOIN',winding=0,index=index,name='c',**({'expect_rejection':True}if rejected else{}))];yield c
    base=next(c for c in bases if c['label']=='square')
    c=copy.deepcopy(base);c['label']='name-collisions';c['operations']=[dict(command='COPY',winding=0,name='c'),dict(command='UNJOIN',winding=0,index=0,name='a',expect_rejection=True),dict(command='UNJOIN',winding=0,index=999,name='c',expect_rejection=True),dict(command='UNJOIN',winding=0,index=0,name='c',expect_rejection=True),dict(command='UNJOIN',winding=1,index=1,name='d')];yield c
    # Keep every selected empty-chain follow-up, including native faults.
    base=next(c for c in bases if c['label']=='wire')
    for label,op in[
        ('unjoin',dict(command='UNJOIN',winding=1,index=0,name='d')),
        ('copy',dict(command='COPY',winding=1,name='d')),
        ('erase',dict(command='ERASE',windings=[1])),
        ('flip',dict(command='FLIP',winding=1)),
        ('join',dict(command='JOIN',winding=0,others=[1])),
        ('move',dict(command='MOVE',winding=1,x=.125,y=-.25)),
        ('rotate',dict(command='ROTATE',winding=1,angle=17.123456789)),
        ('fliph',dict(command='FLIPH',winding=1)),
        ('flipv',dict(command='FLIPV',winding=1)),
        ('phase',dict(command='PHASE',winding=1,phase=-1)),
        ('rename',dict(command='RENAME',winding=1,name='d')),
        ('befriend',dict(command='BEFRIEND',winding=1,other=0)),
        ('only-empty',dict(command='ERASE',windings=[0])),
        ('unjoin-name-collision',dict(command='UNJOIN',winding=1,index=0,name='a',expect_rejection=True)),
        ('copy-same-name',dict(command='COPY',winding=1,name='c',expect_rejection=True)),
    ]:
        c=copy.deepcopy(base);c['label']='empty/'+label;c['operations']=[dict(command='UNJOIN',winding=0,index=1,name='c'),op];yield c
    # Split descriptors allocate a header but transfer the existing segment
    # chain. Reuse and subsequent stale friend writes exercise that distinction.
    base=next(c for c in bases if c['label']=='transformer')
    c=copy.deepcopy(base);c['label']='reuse/transformer';c['operations']=[dict(command='JOIN',winding=0,others=[1]),dict(command='UNJOIN',winding=0,index=1,name='c'),dict(command='MOVE',winding=0,x=.125,y=-.25),dict(command='COPY',winding=1,name='d'),dict(command='MOVE',winding=0,x=1,y=2)];yield c


def command(op,names):
    if op['command']=='UNJOIN':return f"UNJOIN {names[op.get('winding',0)]} {op['index']} {op['name']}\n"
    if op['command']=='ERASE':return 'ERASE '+' '.join(names[i]for i in op['windings'])+'\n'
    return prior_command(op,names)


def update_names(names,op):
    if op.get('expect_rejection',False):return
    if op['command']=='UNJOIN':names.append(op['name'].upper())
    elif op['command']=='ERASE':names[:]=[name for i,name in enumerate(names)if i not in op['windings']]
    else:prior_names(names,op)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--reference',type=Path,required=True);p.add_argument('--library-path',required=True);a=p.parse_args();original=a.reference/'run/asitic.linux.2.2'
    for path,digest in((original,ORIGINAL_SHA256),(a.reference/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so',LEGACY_SHA256)):
        assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
    cases=[];parents={'join_original.json.gz':hashlib.sha256((ROOT/'tests/fixtures/join_original.json.gz').read_bytes()).hexdigest()}
    with tempfile.TemporaryDirectory(prefix='pyasitic-original-unjoin-')as directory:
        for c in jobs():
            parent=c['parent']+'.json';parents[parent]=hashlib.sha256((ROOT/'tests/fixtures'/parent).read_bytes()).hexdigest();names=c['names'].copy();script=c['creation']+'WHO\n'
            for op in c['operations']:script+=command(op,names)+'WHO\n';update_names(names,op)
            work=Path(directory)/str(len(cases));work.mkdir()
            for name,value in(('process.tek',c['technology']),('input.asit',script),('answers.txt',c['stdin']),('capture.gdb',COMMANDS)):(work/name).write_text(value)
            env=dict(os.environ,LD_LIBRARY_PATH=a.library_path)
            with (work/'answers.txt').open()as stdin:
                plain=subprocess.run([str(original),'-g','-t','process.tek','-x','input.asit'],cwd=work,env=env,stdin=stdin,capture_output=True,text=True,start_new_session=True,timeout=120)
            r=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=env,capture_output=True,text=True,start_new_session=True,timeout=120)
            if r.returncode or not(work/'spatial.json').exists()or'Python Exception'in r.stderr:raise RuntimeError(c['label']+r.stdout[-1500:]+r.stderr[-1000:])
            observed=json.loads((work/'spatial.json').read_text());cases.append(dict(c,script=script,stdout=r.stdout,stderr=r.stderr,plain=dict(returncode=plain.returncode,stdout=plain.stdout,stderr=plain.stderr),**observed))
            print(c['label'],len(observed['states']),'states; signal',observed['signal'],'plain',plain.returncode,flush=True)
    result=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,parents=parents,gdb_commands=COMMANDS,reference='Unchanged original UNJOIN commands with read-only WHO-entry snapshots, all twelve generators, default and signed index boundaries, name-collision precedence, transferred segment chains, header reuse and all selected empty-chain follow-ups including faults. Each script also has a separate unobserved original execution; all outcomes are retained.',cases=cases)
    with gzip.GzipFile(str(ROOT/'tests/fixtures/unjoin_original.json.gz'),'wb',mtime=0)as stream:stream.write((json.dumps(result,separators=(',',':'),allow_nan=False)+'\n').encode())


if __name__=='__main__':main()
