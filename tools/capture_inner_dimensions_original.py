"""Observe original square/MMSQUARE inner-hole input descriptors and geometry."""
import argparse,hashlib,json,math,os,subprocess,tempfile
from pathlib import Path
from capture_original_symmetric import ORIGINAL_SHA256,LEGACY_SHA256
from capture_square_original import COMMANDS as SQUARE_COMMANDS
from capture_multimetal_original import COMMANDS as MULTIMETAL_COMMANDS
ROOT=Path(__file__).resolve().parents[1]

def commands(kind):
    text=SQUARE_COMMANDS if kind=='square'else MULTIMETAL_COMMANDS
    text=text.replace('control_before=int',"name=lambda a:memory(a,80).split(b'\\0')[0].decode('latin1')\ncontrol_before=int",1)
    text=text.replace('config=dict(length=', 'config=dict(name=name(args),length=')
    text=text.replace('origin=[f64(head+0x54),f64(head+0x5c)],',"name=name(head),origin=[f64(head+0x54),f64(head+0x5c)],origin_bits=memory(head+0x54,16).hex(),")
    return text


def jobs():
    for kind in ['square','multimetal']:
        command='SQUARE'if kind=='square'else'MMSQUARE';exit='M3'if kind=='square'else'M1';metal='M4'if kind=='square'else'M5'
        for turns in [.25,.5,.75,1,1.25,1.5,1.75,2,2.75,1.74999999,1.7499999]:
            for rectangular in [False,True]:
                for angle,phase in [(0,1),(17,-1)]:
                    p=dict(name='A',inner_length=32.125,width=3.25,spacing=2.125,turns=turns,metal=metal,angle=angle,phase=phase,x=12.345,y=23.456)
                    p['exit_metal'if kind=='square'else'bottom_metal']=exit
                    dimensions='ILEN=32.125'
                    if rectangular:p['inner_height']=27.375;dimensions+=':IWID=27.375'
                    script=f'{command} NAME=A:{dimensions}:W=3.25:S=2.125:N={turns:.17g}:METAL={metal}:EXIT={exit}:ORIENT={angle}:PHASE={phase}:XORG=12.345:YORG=23.456\n'
                    yield dict(kind=kind,label=f'keyword/{kind}/{turns}/{rectangular}/{angle}/{phase}',parameters=p,native_keyword=True,script=script,stdin='quit\n')
        for turns in [1,1.25,1.5,1.75,2.75,1.7499999999999998]:
            for rectangular in [False,True]:
                p=dict(name='A',inner_length=32.123456789,width=3.14159265358979,spacing=2.71828182845905,turns=turns,metal=metal,x=12.3456789,y=23.456789)
                p['exit_metal'if kind=='square'else'bottom_metal']=exit
                hole='32.123456789'
                if rectangular:p['inner_height']=27.987654321;hole+=' 27.987654321'
                exit_answers='y\nM3\n'if kind=='square'else'M1\n'
                answers=f'A\n-1\n{hole}\n3.14159265358979\n2.71828182845905\n{turns:.17g}\n{metal}\n{exit_answers}12.3456789 23.456789\nquit\n'
                yield dict(kind=kind,label=f'interactive/{kind}/{turns}/{rectangular}',parameters=p,native_interactive=True,script=command+'\n',stdin=answers)
        # Original LEN takes precedence over ILEN; WID and IWID are independent.
        for height in [False,True]:
            p=dict(name='A',length=90.125,inner_length=32.125,inner_height=27.375,width=3.25,spacing=2.125,turns=1.75,metal=metal)
            p['exit_metal'if kind=='square'else'bottom_metal']=exit
            if height:p['height']=80.375
            script=f'{command} NAME=A:LEN=90.125'+(':WID=80.375'if height else'')+f':ILEN=32.125:IWID=27.375:W=3.25:S=2.125:N=1.75:METAL={metal}:EXIT={exit}\n'
            yield dict(kind=kind,label=f'precedence/{kind}/{height}',parameters=p,native_keyword=True,script=script,stdin='quit\n')
        # Keyword WID does not replace a missing IWID in inner mode.
        p=dict(name='A',inner_length=32.125,height=100.375,width=3.25,spacing=2.125,turns=1.75,metal=metal)
        p['exit_metal'if kind=='square'else'bottom_metal']=exit
        yield dict(kind=kind,label=f'inner-ignores-WID/{kind}',parameters=p,native_keyword=True,script=f'{command} NAME=A:ILEN=32.125:WID=100.375:W=3.25:S=2.125:N=1.75:METAL={metal}:EXIT={exit}\n',stdin='quit\n')
        for phase in [0,-.5,2.9]:
            p=dict(name='A',inner_length=32.125,inner_height=27.375,width=3.25,spacing=2.125,turns=1.75,metal=metal,phase=phase)
            p['exit_metal'if kind=='square'else'bottom_metal']=exit
            script=f'{command} NAME=A:ILEN=32.125:IWID=27.375:W=3.25:S=2.125:N=1.75:METAL={metal}:EXIT={exit}:PHASE={phase}\n'
            yield dict(kind=kind,label=f'keyword-phase/{kind}/{phase}',parameters=p,native_keyword=True,script=script,stdin='quit\n')
        for x,y in [(0,30),(-5,30),(30,0),(30,-5)]:
            p=dict(name='A',inner_length=x,inner_height=y,width=3.25,spacing=2.125,turns=1.75,metal=metal)
            p['exit_metal'if kind=='square'else'bottom_metal']=exit
            script=f'{command} NAME=A:ILEN={x}:IWID={y}:W=3.25:S=2.125:N=1.75:METAL={metal}:EXIT={exit}\n'
            yield dict(kind=kind,label=f'keyword-signed-inner/{kind}/{x}/{y}',parameters=p,native_keyword=True,script=script,stdin='quit\n')
        # The prompt does not reapply outer-dimension turn capacity after expansion.
        p=dict(name='A',inner_length=3.125,width=3,spacing=2.125,turns=1.75,metal=metal)
        p['exit_metal'if kind=='square'else'bottom_metal']=exit
        answers='A\n-1\n3.125\n3\n2.125\n1.75\n'+metal+'\n'+('y\nM3\n'if kind=='square'else'M1\n')+'12.345 23.456\nquit\n'
        p.update(x=12.345,y=23.456)
        yield dict(kind=kind,label=f'interactive-small-hole/{kind}',parameters=p,native_interactive=True,script=command+'\n',stdin=answers)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--reference',type=Path,required=True);parser.add_argument('--library-path',required=True);args=parser.parse_args()
    ref=args.reference.resolve();original=ref/'run/asitic.linux.2.2';legacy=ref/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so'
    for path,want in[(original,ORIGINAL_SHA256),(legacy,LEGACY_SHA256)]:
        if hashlib.sha256(path.read_bytes()).hexdigest()!=want:raise ValueError('Unexpected original checksum')
    technology=(ref/'run/tek/CMOS.tek').read_text();cases=[]
    with tempfile.TemporaryDirectory(prefix='pyasitic-original-inner-')as d:
        for i,c in enumerate(jobs()):
            work=Path(d)/str(i);work.mkdir();gdb=commands(c['kind'])
            for name,value in [('process.tek',technology),('input.asit',c['script']),('answers.txt',c['stdin']),('capture.gdb',gdb)]:(work/name).write_text(value)
            run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=args.library_path),capture_output=True,text=True,start_new_session=True,timeout=120)
            result=work/('square.json'if c['kind']=='square'else'multimetal.json')
            if run.returncode or not result.exists():raise RuntimeError(f'Original inner {i}/{c["label"]} failed: '+run.stdout[-1600:]+run.stderr[-1000:])
            raw=json.loads(result.read_text());assert raw['control_before']==raw['control_after']==0x37f
            cases.append(dict(c,stdout=run.stdout,**raw));print(f'Original inner {i}: {c["label"]}',flush=True)
    out=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,technology=technology,gdb_commands={kind:commands(kind)for kind in ['square','multimetal']},reference='Intact original inner-hole keyword/interactive descriptors and actual constructor-return stores. Full XYZ/origin/width/conductor-thickness/metal/defined-via-count fields, keyword precedence and prompt expansion differences; numerical instructions, input descriptors and allocations unchanged.',cases=cases)
    (ROOT/'tests/fixtures/inner_dimensions_original.json').write_text(json.dumps(out,separators=(',',':'),allow_nan=False)+'\n')


if __name__=='__main__':main()
