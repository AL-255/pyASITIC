"""Capture unchanged original WIRE parsed inputs and all defined XYZ stores."""
import argparse,hashlib,json,math,os
from pathlib import Path
import subprocess,tempfile
from capture_original_symmetric import ORIGINAL_SHA256,LEGACY_SHA256
from capture_square_original import COMMANDS as SQUARE_COMMANDS

ROOT=Path(__file__).resolve().parents[1]
COMMANDS=SQUARE_COMMANDS.replace('0x8056670','0x8057998').replace('height=f64(args+0x78),','').replace('spacing=f64(args+0x90),turns=f64(args+0x98),','').replace('exit_metal=i32(args+0x6c),','').replace('mode=i32(esp+8);','').replace(',mode=mode','').replace("'square.json'","'wire.json'")
COMMANDS=COMMANDS.replace('width_bits=memory(segment+0xcc,8).hex(),metal=metal','width_bits=memory(segment+0xcc,8).hex(),primary_width_bits=memory(segment+0x30,8).hex(),primary_thickness_bits=memory(segment+0x38,8).hex(),metal=metal')


def keyword(p):
    keys={'length':'LEN','width':'WID','metal':'METAL','x':'XORG','y':'YORG','angle':'ORIENT','phase':'PHASE'}
    return 'WIRE NAME=A:'+':'.join(keys[k]+'='+format(v,'.17g')if isinstance(v,(float,int))else keys[k]+'='+v for k,v in p.items()if k in keys)+'\n'


def jobs():
    for width in(.1,3.25,10.125):
        for metal in('M1','M5'):
            for angle in(0,17,37,-35.5,179.9,360):
                for phase in(1,-1):
                    p=dict(name='A',length=80.125,width=width,metal=metal,x=12.345,y=23.456,angle=angle,phase=phase)
                    yield dict(label=f'keyword/{width}/{metal}/{angle}/{phase}',parameters=p,native_keyword=True,script=keyword(p),stdin='quit\n')
    edge=1e-10*180/math.pi
    for angle in(0.,math.nextafter(edge,0.),edge*(1-1e-6),math.nextafter(edge,math.inf),edge*(1+1e-6),-edge):
        p=dict(name='A',length=80.125,width=3.25,metal='M4',x=12.345,y=23.456,angle=angle,phase=1)
        yield dict(label=f'keyword/rotation-threshold/{angle:.17g}',parameters=p,native_keyword=True,script=keyword(p),stdin='quit\n')
    for missing in(('metal','angle','phase','x','y'),('y',),('x',),('x','y')):
        p=dict(name='A',length=80.125,width=3.25,metal='M4',x=12.345,y=23.456,angle=17,phase=-1)
        for key in missing:del p[key]
        yield dict(label='keyword/defaults/'+','.join(missing),parameters=p,native_keyword=True,script=keyword(p),stdin='quit\n')
    for phase in(0,-.5,-2):
        p=dict(name='A',length=80.125,width=3.25,metal='M4',x=12.345,y=23.456,angle=17,phase=phase)
        yield dict(label=f'keyword/phase/{phase}',parameters=p,native_keyword=True,script=keyword(p),stdin='quit\n')
    for width in(.01,3.14159265358979):
        for angle in(0,37,-35.5,360):
            for phase in(1,-1):
                p=dict(name='A',length=80.123456789,width=width,metal='M4',x=12.3456789,y=23.456789,angle=angle,phase=phase)
                answers=f'A\n80.123456789\n{width:.17g}\nM4\n{phase}\n12.3456789 23.456789\n{angle:.17g}\nquit\n'
                yield dict(label=f'interactive/{width}/{angle}/{phase}',parameters=p,native_keyword=False,native_interactive=True,script='WIRE\n',stdin=answers)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--reference',type=Path,required=True);parser.add_argument('--library-path',required=True)
    args=parser.parse_args();reference=args.reference.resolve();original=reference/'run/asitic.linux.2.2'
    for path,want in((original,ORIGINAL_SHA256),(reference/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so',LEGACY_SHA256)):
        if hashlib.sha256(path.read_bytes()).hexdigest()!=want:raise ValueError(f'Unexpected oracle checksum: {path}')
    technology=(reference/'run/tek/CMOS.tek').read_text();records=[]
    with tempfile.TemporaryDirectory(prefix='pyasitic-original-wire-')as directory:
        for i,c in enumerate(jobs()):
            work=Path(directory)/str(i);work.mkdir()
            for name,value in(('process.tek',technology),('input.asit',c['script']),('answers.txt',c['stdin']),('capture.gdb',COMMANDS)):(work/name).write_text(value)
            run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=args.library_path),capture_output=True,text=True,start_new_session=True,timeout=120)
            if run.returncode or not(work/'wire.json').exists():raise RuntimeError(f'Original wire capture failed {i}: {run.stdout[-1800:]} {run.stderr[-1000:]}')
            item=json.loads((work/'wire.json').read_text())
            if item['control_before']!=0x37f or item['control_after']!=0x37f:raise RuntimeError('Unexpected original control word')
            item.update(c);records.append(item);print(f'Original wire {i}: {c["label"]}, parsed angle {item["config"]["angle"]:.17g}',flush=True)
    invalid=[]
    with tempfile.TemporaryDirectory(prefix='pyasitic-original-wire-invalid-')as directory:
        for i,(length,width)in enumerate(((40,.01),(.01,5))):
            p=dict(name='A',length=length,width=width,metal='M4');work=Path(directory)/str(i);work.mkdir();script=keyword(p)
            (work/'process.tek').write_text(technology);(work/'input.asit').write_text(script)
            run=subprocess.run([str(original),'-g','-t','process.tek','-x','input.asit'],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=args.library_path,TERM='dumb',INPUTRC='/dev/null'),input='quit\n',capture_output=True,text=True,start_new_session=True,timeout=120)
            if'Wire dimensions too small'not in run.stdout:raise RuntimeError('Original wire did not preserve its snapped-dimension error')
            invalid.append(dict(parameters=p,script=script,stdin='quit\n',returncode=run.returncode,stdout=run.stdout,stderr=run.stderr))
    output=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,technology=technology,gdb_commands=COMMANDS,
                reference='Unchanged original WIRE creator 0x08057998 entry and actual return with data-only observers. Actual incoming length/width/origin/angle/metal/phase, output origin, all XYZ stores, scalar and primary width/thickness and metal captured. Uninitialized conductor mesh counts excluded. Snapped dimension rejection histories retain original stdout.',cases=records,invalid_cases=invalid)
    (ROOT/'tests/fixtures/wire_original.json').write_text(json.dumps(output,separators=(',',':'),allow_nan=False)+'\n')


if __name__=='__main__':main()
