"""Capture intact-original MMSQUARE construction after all copy/reflect/join stores."""
import argparse,hashlib,json,math,os,subprocess,tempfile
from pathlib import Path
from capture_square_original import COMMANDS as SQUARE_COMMANDS
from capture_original_symmetric import ORIGINAL_SHA256,LEGACY_SHA256
ROOT=Path(__file__).resolve().parents[1]
COMMANDS=SQUARE_COMMANDS.replace('break *0x8056670','break *0x805af5c').replace('mode=i32(esp+8);','').replace('mode=mode,','').replace('square.json','multimetal.json')


def base_jobs():
    for turns in(.25,.5,.75,1,1.25,1.5,1.75,2,2.75):
        for top,bottom in [('M5','M3'),('M4','M1'),('M2','M1')]:
            for angle in(0,17,-35.5):
                for phase in(1,-1):
                    p=dict(name='A',length=120.125,height=100.375,width=3.25,spacing=2.125,turns=turns,metal=top,bottom_metal=bottom,angle=angle,phase=phase,x=12.345,y=23.456)
                    script=f'MMSQUARE NAME=A:LEN=120.125:WID=100.375:W=3.25:S=2.125:N={turns}:METAL={top}:EXIT={bottom}:ORIENT={angle}:PHASE={phase}:XORG=12.345:YORG=23.456\n'
                    yield dict(label=f'keyword/{turns}/{top}/{bottom}/{angle}/{phase}',script=script,stdin='quit\n',parameters=p,native_keyword=True)
    for turns in [1.74999999,1.7499999,1.75000001]:
        for origin in [False,True]:
            p=dict(name='A',length=120.125,width=3.25,spacing=2.125,turns=turns)
            script=f'MMSQUARE NAME=A:LEN=120.125:W=3.25:S=2.125:N={turns:.17g}'
            if origin:p.update(x=12.345,y=23.456);script+=':XORG=12.345:YORG=23.456'
            yield dict(label=f'defaults/{turns}/{origin}',script=script+'\n',stdin='quit\n',parameters=p,native_keyword=True)
    for turns in [.25,.5,.75,1,1.75,2.75]:
        p=dict(name='A',length=120.123456789,height=100.987654321,width=3.14159265358979,spacing=2.71828182845905,turns=turns,metal='M5',bottom_metal='M1',angle=0,phase=1,x=12.3456789,y=23.456789)
        actual=max(1,turns);p['turns']=actual
        responses=f'{turns}\n'+('1\n'if turns<1 else'')
        answers=f'A\n120.123456789 100.987654321\n3.14159265358979\n2.71828182845905\n{responses}M5\nM1\n12.3456789 23.456789\nquit\n'
        yield dict(label=f'interactive/{turns}',script='MMSQUARE\n',stdin=answers,parameters=p,native_keyword=False)


def jobs():
    yield from base_jobs()
    for i,(angle,phase,turns)in enumerate([(0,0,1.25),(17,-.5,1.25),(-360,-2,1.25),(360,1,1.25),(0,1,10.5),(0,2.9,1.25)]):
        p=dict(name='A',length=120.125,height=100.375,width=3.25,spacing=2.125,turns=turns,metal='M5',bottom_metal='M1',angle=angle,phase=phase,x=12.345,y=23.456)
        script=f'MMSQUARE NAME=A:LEN=120.125:WID=100.375:W=3.25:S=2.125:N={turns}:METAL=M5:EXIT=M1:ORIENT={angle}:PHASE={phase}:XORG=12.345:YORG=23.456\n'
        yield dict(label=f'keyword-corner/{i}',script=script,stdin='quit\n',parameters=p,native_keyword=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',type=Path,required=True);parser.add_argument('--library-path',required=True)
    args=parser.parse_args();reference=args.reference.resolve()
    original=reference/'run/asitic.linux.2.2';legacy=reference/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so'
    for path,want in((original,ORIGINAL_SHA256),(legacy,LEGACY_SHA256)):
        if hashlib.sha256(path.read_bytes()).hexdigest()!=want:raise ValueError(f'Unexpected oracle checksum: {path}')
    technology=(reference/'run/tek/CMOS.tek').read_text();records=[]
    with tempfile.TemporaryDirectory(prefix='pyasitic-original-multimetal-')as directory:
        for i,c in enumerate(jobs()):
            work=Path(directory)/str(i);work.mkdir()
            for name,text in(('process.tek',technology),('input.asit',c['script']),('answers.txt',c['stdin']),('capture.gdb',COMMANDS)):(work/name).write_text(text)
            run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=args.library_path),capture_output=True,text=True,start_new_session=True,timeout=120)
            if run.returncode or not(work/'multimetal.json').exists():raise RuntimeError(f'Original multi-metal capture failed {i}: {run.stdout[-1800:]} {run.stderr[-1000:]}')
            item=json.loads((work/'multimetal.json').read_text())
            if item['control_before']!=0x37f or item['control_after']!=0x37f:raise RuntimeError('Unexpected original control word')
            if c['label'].startswith('interactive/'):
                item['stdout']=run.stdout
                if float(c['label'].split('/')[-1])<1 and 'Need at least 1.000000 truns.'not in run.stdout:raise RuntimeError('Missing original fractional-turn rejection')
            item.update(c);records.append(item);print(f'Original multi-metal {i}: {len(item["segments"])} segments / {c["label"]}',flush=True)
    output=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,technology=technology,
                reference='Actual original multi-metal creator 0x0805af5c entry and return, unchanged numerical instructions. Every XYZ store, scalar width, conductor thickness, metal and explicit via count captured after rotation and native linked/direction reversal; output origin and exact incoming parsed config retained. Native uninitialized conductor mesh counts and via thickness excluded.',gdb_commands=COMMANDS,cases=records)
    (ROOT/'tests/fixtures/multimetal_original.json').write_text(json.dumps(output,separators=(',',':'),allow_nan=False)+'\n')


if __name__=='__main__':main()
