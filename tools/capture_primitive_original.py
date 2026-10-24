"""Capture intact-original CAP plate joins and VIA construction/input stores."""
import argparse,hashlib,json,math,os,subprocess,tempfile
from pathlib import Path
from capture_square_original import COMMANDS as SQUARE_COMMANDS
from capture_original_symmetric import ORIGINAL_SHA256,LEGACY_SHA256
ROOT=Path(__file__).resolve().parents[1]
COMMANDS=SQUARE_COMMANDS.replace('break *0x8056670','break *ENTRY').replace('mode=i32(esp+8);','').replace('mode=mode,','').replace('square.json','primitive.json')
COMMANDS=COMMANDS.replace('result=dict(config=config,',"result=dict(origin_bits=memory(head+0x54,16).hex(),config=config,")
COMMANDS=COMMANDS.replace('config=dict(length=',"config=dict(nx=i32(args+0x64),ny=i32(args+0x6c),length=")
JOIN="""gdb.breakpoints()[0].enabled=False
gdb.Breakpoint('*0x8078890',temporary=True,internal=True)
gdb.execute('continue',to_string=True)
esp=int(gdb.parse_and_eval('$esp'));ret=u32(esp)
"""


def jobs():
    for length,width in [(80.125,3.25),(10.125,.1),(40.375,10.125)]:
        for first,second in [('M5','M4'),('M4','M1'),('M1','M5'),('M3','M3')]:
            for angle in [0,17,-35.5,360]:
                p=dict(name='A',length=length,width=width,metal=first,bottom_metal=second,angle=angle,x=12.345,y=23.456)
                script=f'CAPACITOR NAME=A:LEN={length}:WID={width}:METAL1={first}:METAL2={second}:ORIENT={angle}:XORG=12.345:YORG=23.456\n'
                yield dict(kind='capacitor',label=f'keyword/cap/{length}/{width}/{first}/{second}/{angle}',parameters=p,native_keyword=True,entry=0x8057998,script=script,stdin='quit\n')
    for dimensions in [dict(length=10.125),dict(width=10.125),dict(length=10.125,width=3.25)]:
        p=dict(name='A',**dimensions)
        script='CAPACITOR NAME=A:'+':'.join(('LEN'if k=='length'else'WID')+'='+str(v)for k,v in dimensions.items())+'\n'
        yield dict(kind='capacitor',label='defaults/cap/'+','.join(dimensions),parameters=p,native_keyword=True,entry=0x8057998,script=script,stdin='quit\n')
    for angle in [0,37,-35.5,360]:
        p=dict(name='A',length=80.123456789,width=3.14159265358979,metal='M5',bottom_metal='M3',x=12.3456789,y=23.456789,angle=angle)
        answers=f'A\n80.123456789\n3.14159265358979\nM5\nM3\n12.3456789 23.456789\n{angle}\nquit\n'
        yield dict(kind='capacitor',label=f'interactive/cap/{angle}',parameters=p,native_interactive=True,native_keyword=False,entry=0x8057998,script='CAPACITOR\n',stdin=answers)
    for via in ['VIA1','VIA4']:
        for nx,ny in [(1,1),(2,3),(7,5),(2.9,3.9),(0,2),(-1,2)]:
            for phase in [1,-1,0,'-0',-.5]:
                p=dict(name='A',via=via,nx=nx,ny=ny,phase=phase,x=12.345,y=23.456)
                script=f'VIA NAME=A:VIA={via}:NX={nx}:NY={ny}:PHASE={phase}:XORG=12.345:YORG=23.456\n'
                yield dict(kind='via',label=f'keyword/via/{via}/{nx}/{ny}/{phase}',parameters=p,native_keyword=True,entry=0x8057b78,script=script,stdin='quit\n')
    for phase in [None,1,'-0']:
        p=dict(name='A',via='VIA1',nx=3)
        if phase is not None:p['phase']=phase
        script='VIA NAME=A:VIA=VIA1:NX=3'+(''if phase is None else':PHASE='+str(phase))+'\n'
        yield dict(kind='via',label=f'defaults/via/{phase}',parameters=p,native_keyword=True,entry=0x8057b78,script=script,stdin='quit\n')
    for phase in [-1,1]:
        p=dict(name='A',via='VIA4',nx=2,ny=3,phase=phase,x=12.3456789,y=23.456789)
        answers=f'A\nVIA4\n2\n3\n{phase}\n12.3456789 23.456789\nquit\n'
        yield dict(kind='via',label=f'interactive/via/{phase}',parameters=p,native_interactive=True,native_keyword=False,entry=0x8057b78,script='VIA\n',stdin=answers)
    # The preceding interactive WIRE leaves a full-binary64 width in the native descriptor.
    p=dict(name='A',via='VIA1',nx=2,native_previous_width=3.14159265358979)
    answers='B\n40\n3.14159265358979\nM5\n1\n20 20\n0\nquit\n'
    yield dict(kind='via',label='history/via/interactive-wire-width',parameters=p,native_keyword=True,entry=0x8057b78,script='WIRE\nVIA NAME=A:VIA=VIA1:NX=2\n',stdin=answers)

    for via in ['VIA1','VIA2','VIA3','VIA4']:
        for nx,ny in [(1,1),(2.9,3.9),(7,5)]:
            for phase in [-1,1]:
                p=dict(name='A',via=via,nx=nx,ny=ny,phase=phase,x=12.3456789,y=23.456789)
                answers=f'A\n{via}\n{nx}\n{ny}\n{phase}\n12.3456789 23.456789\nquit\n'
                yield dict(kind='via',label=f'interactive/via/{via}/{nx}/{ny}/{phase}',parameters=p,native_interactive=True,native_keyword=False,entry=0x8057b78,script='VIA\n',stdin=answers)
    p=dict(name='A',via='VIA1',nx=2,ny=3,phase=1,x=12.3456789,y=23.456789)
    yield dict(kind='via',label='interactive/via/retry-count-and-phase',parameters=p,native_interactive=True,native_keyword=False,entry=0x8057b78,script='VIA\n',stdin='A\nVIA1\n0\n2\n-1\n3\n0\n1\n12.3456789 23.456789\nquit\n')

    p=dict(name='A',via='VIA1',nx=2,ny=3,phase=1,x=-0.,y=0.)
    yield dict(kind='via',label='interactive/via/signed-zero-origin',parameters=p,native_interactive=True,native_keyword=False,entry=0x8057b78,script='VIA\n',stdin='A\nVIA1\n2\n3\n1\n-0 0\nquit\n')

    p=dict(name='A',length=40,width=5,metal='M2',bottom_metal='M1',phase='ignored')
    yield dict(kind='capacitor',label='keyword/cap/ignored-phase',parameters=p,native_keyword=True,entry=0x8057998,script='CAPACITOR NAME=A:LEN=40:WID=5:METAL1=M2:METAL2=M1:PHASE=ignored\n',stdin='quit\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',type=Path,required=True);parser.add_argument('--library-path',required=True)
    args=parser.parse_args();reference=args.reference.resolve()
    original=reference/'run/asitic.linux.2.2';legacy=reference/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so'
    for path,want in((original,ORIGINAL_SHA256),(legacy,LEGACY_SHA256)):
        if hashlib.sha256(path.read_bytes()).hexdigest()!=want:raise ValueError(f'Unexpected oracle checksum: {path}')
    technology=(reference/'run/tek/CMOS.tek').read_text();records=[];rejections=[];invalid=[]
    with tempfile.TemporaryDirectory(prefix='pyasitic-original-primitives-')as directory:
        for i,c in enumerate(jobs()):
            work=Path(directory)/str(i);work.mkdir()
            if c['kind']=='via'and c.get('native_keyword'):
                for name,text in [('process.tek',technology),('input.asit',c['script'])]:(work/name).write_text(text)
                run=subprocess.run([str(original),'-g','-t','process.tek','-x','input.asit'],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=args.library_path,TERM='dumb',INPUTRC='/dev/null'),input=c['stdin'],capture_output=True,text=True,start_new_session=True,timeout=120)
                if 'Error:  Unknown argument type.'not in run.stdout:raise RuntimeError('Original VIA keyword rejection changed')
                rejections.append(dict(c,returncode=run.returncode,stdout=run.stdout,stderr=run.stderr));print(f'Original VIA keyword rejection {i}',flush=True);continue
            commands=COMMANDS.replace('ENTRY',hex(c['entry']))
            if c['kind']=='capacitor':commands=commands.replace("gdb.Breakpoint('*'+hex(ret),temporary=True,internal=True)",JOIN+"gdb.Breakpoint('*'+hex(ret),temporary=True,internal=True)")
            for name,text in(('process.tek',technology),('input.asit',c['script']),('answers.txt',c['stdin']),('capture.gdb',commands)):(work/name).write_text(text)
            run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=args.library_path),capture_output=True,text=True,start_new_session=True,timeout=120)
            if run.returncode or not(work/'primitive.json').exists():raise RuntimeError(f'Original primitive capture failed {i}: {run.stdout[-1800:]} {run.stderr[-1000:]}')
            item=json.loads((work/'primitive.json').read_text())
            if item['control_before']!=0x37f or item['control_after']!=0x37f:raise RuntimeError('Unexpected original control word')
            if 'retry-'in c['label']:item['stdout']=run.stdout
            item.update(c);records.append(item);print(f'Original primitive {i}: {len(item["segments"])} segments / {c["label"]}',flush=True)
        for label,p,script in [('missing-dimensions',dict(name='A'),'CAPACITOR NAME=A'),('snapped-zero-length',dict(name='A',length=.01,width=3.25),'CAPACITOR NAME=A:LEN=.01:WID=3.25')]:
            work=Path(directory)/label;work.mkdir();(work/'process.tek').write_text(technology);(work/'input.asit').write_text(script+'\n')
            run=subprocess.run([str(original),'-g','-t','process.tek','-x','input.asit'],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=args.library_path,TERM='dumb',INPUTRC='/dev/null'),input='quit\n',capture_output=True,text=True,start_new_session=True,timeout=120)
            expected='Missing Argument'if label=='missing-dimensions'else'Plate dimensions too small'
            if expected not in run.stdout:raise RuntimeError('Original capacitor validation changed: '+run.stdout[-900:])
            invalid.append(dict(label=label,parameters=p,script=script+'\n',stdin='quit\n',returncode=run.returncode,stdout=run.stdout,stderr=run.stderr))
    output=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,technology=technology,
                reference='Actual original capacitor wire entry 0x08057998 through join 0x08078890 return and VIA 0x08057b78 entry/return, unchanged numerical instructions. Every XYZ store, scalar width, conductor thickness, metal and explicit via count captured after rotation and native linked/direction reversal; output origin and exact incoming parsed config retained. Native uninitialized conductor mesh counts and via thickness excluded.',gdb_commands=COMMANDS,capacitor_join_commands=JOIN,cases=records,keyword_rejections=rejections,invalid_capacitors=invalid)
    (ROOT/'tests/fixtures/primitive_original.json').write_text(json.dumps(output,separators=(',',':'),allow_nan=False)+'\n')


if __name__=='__main__':main()
