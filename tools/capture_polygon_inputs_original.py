"""Capture unchanged original SPIRAL input boundaries and complete XYZ stores."""
import argparse,hashlib,json,math,os
from pathlib import Path
import subprocess,tempfile
from capture_original_symmetric import ORIGINAL_SHA256,LEGACY_SHA256
from capture_square_original import COMMANDS as SQUARE_COMMANDS

ROOT=Path(__file__).resolve().parents[1]
COMMANDS=SQUARE_COMMANDS.replace('0x8056670','0x8057248').replace("length=f64(args+0x70),height=f64(args+0x78),", "radius=f64(args+0x80),sides=i32(args+0x64),").replace("'square.json'","'polygon.json'").replace('exit_metal=i32(args+0x6c),','').replace('mode=i32(esp+8);','').replace(',mode=mode','')


def keyword(p):
    names={'radius':'RAD','sides':'SIDES','width':'W','spacing':'S','turns':'N','metal':'METAL','angle':'ORIENT','phase':'PHASE','x':'XORG','y':'YORG'}
    return 'SPIRAL NAME=A:'+':'.join(names[k]+'='+format(v,'.17g')if isinstance(v,(float,int))else names[k]+'='+v for k,v in p.items()if k in names)+'\n'


def jobs():
    for sides in(3,4,5,7,8,12,16,32):
        for angle in(0,17,-35.5,179.9,360):
            p=dict(name='A',radius=120.125,sides=sides,width=3.25,spacing=2.125,turns=2.375,metal='M4',angle=angle,phase=-1 if angle in(17,-35.5)else 1,x=12.345,y=23.456)
            yield dict(label=f'keyword/{sides}/{angle}/{p["phase"]}',parameters=p,native_keyword=True,script=keyword(p),stdin='quit\n')
        p=dict(p,angle=17,phase=1)
        yield dict(label=f'keyword/{sides}/17/1',parameters=p,native_keyword=True,script=keyword(p),stdin='quit\n')
    for sides in(3,7,16):
        edge=2+1/sides
        for turns in(math.nextafter(edge,0.),edge-1e-8,edge-1e-6,math.nextafter(edge,math.inf),edge+1e-8,edge+1e-6):
            p=dict(name='A',radius=120.125,sides=sides,width=3.25,spacing=2.125,turns=turns,metal='M4',angle=17,phase=1,x=12.345,y=23.456)
            yield dict(label=f'keyword/turn-boundary/{sides}/{turns:.17g}',parameters=p,native_keyword=True,script=keyword(p),stdin='quit\n')
    for sides,radius,turns in((3,25.125,2.3333333333333335),(7,40.125,6.5714283),(7,40.125,6.7142855),(16,25.125,4.625)):
        p=dict(name='A',radius=radius,sides=sides,width=3.25,spacing=2.125,turns=turns,metal='M4',angle=17,phase=1,x=12.345,y=23.456)
        yield dict(label=f'keyword/maximum/{sides}/{turns:.17g}',parameters=p,native_keyword=True,script=keyword(p),stdin='quit\n')
    for missing in(('sides','metal','angle','phase','x','y'),('angle','x'),('y',)):
        p=dict(name='A',radius=120.125,sides=7,width=3.25,spacing=2.125,turns=2.375,metal='M4',angle=17,phase=-1,x=12.345,y=23.456)
        for k in missing:del p[k]
        yield dict(label='keyword/defaults/'+','.join(missing),parameters=p,native_keyword=True,script=keyword(p),stdin='quit\n')
    for sides,turns in((3,1.3333333333333333),(7,1.7142857142857142),(16,2.375),(32,2.96875)):
        p=dict(name='A',radius=120.123456789,sides=sides,width=3.14159265358979,spacing=2.71828182845905,turns=turns,metal='M4',angle=0,phase=1,x=12.3456789,y=23.456789)
        answers=f'A\n{sides}\n120.123456789\n3.14159265358979\n2.71828182845905\n{turns:.17g}\nM4\n12.3456789 23.456789\nquit\n'
        yield dict(label=f'interactive/{sides}/{turns:.17g}',parameters=p,native_keyword=False,script='SPIRAL\n',stdin=answers)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--reference',type=Path,required=True);parser.add_argument('--library-path',required=True)
    args=parser.parse_args();reference=args.reference.resolve();original=reference/'run/asitic.linux.2.2'
    for path,want in((original,ORIGINAL_SHA256),(reference/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so',LEGACY_SHA256)):
        if hashlib.sha256(path.read_bytes()).hexdigest()!=want:raise ValueError(f'Unexpected oracle checksum: {path}')
    technology=(reference/'run/tek/CMOS.tek').read_text();records=[]
    with tempfile.TemporaryDirectory(prefix='pyasitic-original-polygon-inputs-')as directory:
        for i,c in enumerate(jobs()):
            work=Path(directory)/str(i);work.mkdir()
            for name,value in(('process.tek',technology),('input.asit',c['script']),('answers.txt',c['stdin']),('capture.gdb',COMMANDS)):(work/name).write_text(value)
            run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=args.library_path),capture_output=True,text=True,start_new_session=True,timeout=120)
            if run.returncode or not(work/'polygon.json').exists():raise RuntimeError(f'Original polygon capture failed {i}: {run.stdout[-1800:]} {run.stderr[-1000:]}')
            item=json.loads((work/'polygon.json').read_text())
            if item['control_before']!=0x37f or item['control_after']!=0x37f:raise RuntimeError('Unexpected original control word')
            item.update(c);records.append(item);print(f'Original polygon {i}: {len(item["segments"])} segments / {c["label"]}',flush=True)
    invalid=[]
    with tempfile.TemporaryDirectory(prefix='pyasitic-original-polygon-invalid-')as directory:
        for i,(radius,turns,message)in enumerate(((10.125,2,'cannot support more'),(257,1,'exceed chip dimension'),(40.125,6.714285714285714,'cannot support more'))):
            p=dict(name='A',radius=radius,sides=7,width=3.25,spacing=2.125,turns=turns,metal='M4')
            work=Path(directory)/str(i);work.mkdir();script=keyword(p)
            (work/'process.tek').write_text(technology);(work/'input.asit').write_text(script)
            run=subprocess.run([str(original),'-g','-t','process.tek','-x','input.asit'],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=args.library_path,TERM='dumb',INPUTRC='/dev/null'),input='quit\n',capture_output=True,text=True,start_new_session=True,timeout=120)
            if message not in run.stdout:raise RuntimeError('Original polygon did not retain expected invalid input diagnostic')
            invalid.append(dict(parameters=p,script=script,stdin='quit\n',returncode=run.returncode,stdout=run.stdout,stderr=run.stderr))
    output=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,technology=technology,gdb_commands=COMMANDS,
                reference='Unchanged original SPIRAL creator 0x08057248 entry and actual return, with data-only observers. Actual parsed config, output origin, every XYZ store, scalar width and conductor thickness/metal are captured. Native uninitialized mesh counts are excluded. Invalid keyword histories retain direct original transcripts.',cases=records,invalid_cases=invalid)
    (ROOT/'tests/fixtures/polygon_inputs_original.json').write_text(json.dumps(output,separators=(',',':'),allow_nan=False)+'\n')


if __name__=='__main__':main()
