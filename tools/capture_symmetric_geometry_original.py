"""Capture unchanged original symmetric creators at their entry/return stores."""
import argparse,hashlib,json,math,os,subprocess,tempfile
from pathlib import Path
from capture_square_original import COMMANDS as SQUARE_COMMANDS
from capture_original_symmetric import ORIGINAL_SHA256,LEGACY_SHA256
ROOT=Path(__file__).resolve().parents[1]
COMMANDS=SQUARE_COMMANDS.replace('break *0x8056670','break *ENTRY').replace('mode=i32(esp+8);','').replace('config=dict(length=',"config=dict(sides=i32(args+0x64),radius=f64(args+0x80),length=").replace('mode=mode,','').replace('square.json','symmetric.json')


def base_jobs():
    for kind,command,dimension,entry in [('symmetric_square','SYMSQ','LEN',0x8059854),('symmetric_polygon','SYMPOLY','RAD',0x805a45c)]:
        for sides in ([4]if kind=='symmetric_square'else[4,6,16,32]):
            for turns in (1,2,3):
                for primary,secondary in [('M1','M2'),('M4','M3')]:
                    for angle,phase in [(0,1),(17,-1),(-35.5,1)]:
                        p=dict(name='A',width=3.25,spacing=2.125,inner_gap=15.375,turns=turns,metal=primary,secondary_metal=secondary,angle=angle,phase=phase,x=12.345,y=23.456)
                        p['length'if dimension=='LEN'else'radius']=120.125 if dimension=='LEN'else 60.125
                        if dimension=='RAD':p['sides']=sides
                        script=f'{command} NAME=A:{dimension}={p["length"if dimension=="LEN"else"radius"]}:ILEN={p["inner_gap"]}:W={p["width"]}:S={p["spacing"]}:N={turns}:METAL={primary}:METAL2={secondary}:ORIENT={angle}:PHASE={phase}:XORG={p["x"]}:YORG={p["y"]}'
                        if dimension=='RAD':script+=f':SIDES={sides}'
                        yield dict(kind=kind,entry=entry,label=f'keyword/{kind}/{sides}/{turns}/{primary}/{angle}/{phase}',script=script+'\n',stdin='quit\n',parameters=p,native_keyword=True)
        for turns in [1.99999999,1.9999999,2.00000001]:
            p=dict(name='A',width=3.25,spacing=2.125,turns=turns)
            p['length'if dimension=='LEN'else'radius']=120.125 if dimension=='LEN'else 60.125
            yield dict(kind=kind,entry=entry,label=f'defaults/{kind}/{turns}',script=f'{command} NAME=A:{dimension}={p["length"if dimension=="LEN"else"radius"]}:W=3.25:S=2.125:N={turns:.17g}\n',stdin='quit\n',parameters=p,native_keyword=True)
        # The original interactive prompts retain full binary64 dimensions.
        for turns in [1,2,3]:
            p=dict(name='A',width=3.14159265358979,spacing=2.71828182845905,inner_gap=15.123456789,turns=turns,metal='M4',secondary_metal='M3',angle=0,phase=0,x=12.3456789,y=23.456789)
            p['length'if dimension=='LEN'else'radius']=120.123456789 if dimension=='LEN'else 60.123456789
            if dimension=='RAD':p['sides']=6
            answers=f'A\n{p["length"if dimension=="LEN"else"radius"]}\n{p["width"]}\nM4\nM3\n{p["spacing"]}\n{p["inner_gap"]}\n'+('6\n'if dimension=='RAD'else'')+f'{turns}\n{p["x"]} {p["y"]}\nquit\n'
            yield dict(kind=kind,entry=entry,label=f'interactive/{kind}/{turns}',script=command+'\n',stdin=answers,parameters=p,native_keyword=False)


def jobs():
    yield from base_jobs()
    for kind,command,dimension,entry in [('symmetric_square','SYMSQ','LEN',0x8059854),('symmetric_polygon','SYMPOLY','RAD',0x805a45c)]:
        corners=[dict(angle=360,phase=0),dict(angle=-360,phase=-.5),dict(angle=1e-9,phase=-2),dict(sides=7.9),dict(turns=11 if dimension=='LEN'else 9),dict(secondary_metal='M1')]
        for i,override in enumerate(corners):
            p=dict(name='A',width=3.25,spacing=2.125,inner_gap=15.375,turns=2,metal='M1',secondary_metal='M2',angle=0,phase=1,x=12.345,y=23.456)
            p['length'if dimension=='LEN'else'radius']=120.125 if dimension=='LEN'else 60.125
            if dimension=='RAD':p['sides']=6
            p.update(override)
            script=f'{command} NAME=A:{dimension}={p["length"if dimension=="LEN"else"radius"]}:ILEN={p["inner_gap"]}:W={p["width"]}:S={p["spacing"]}:N={p["turns"]}:METAL={p["metal"]}:METAL2={p["secondary_metal"]}:ORIENT={p["angle"]}:PHASE={p["phase"]}:XORG={p["x"]}:YORG={p["y"]}'
            if dimension=='RAD':script+=f':SIDES={p["sides"]}'
            yield dict(kind=kind,entry=entry,label=f'keyword-corner/{kind}/{i}',script=script+'\n',stdin='quit\n',parameters=p,native_keyword=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',type=Path,required=True);parser.add_argument('--library-path',required=True)
    args=parser.parse_args();reference=args.reference.resolve()
    original=reference/'run/asitic.linux.2.2';legacy=reference/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so'
    for path,want in((original,ORIGINAL_SHA256),(legacy,LEGACY_SHA256)):
        if hashlib.sha256(path.read_bytes()).hexdigest()!=want:raise ValueError(f'Unexpected oracle checksum: {path}')
    technology=(reference/'run/tek/CMOS.tek').read_text();records=[]
    with tempfile.TemporaryDirectory(prefix='pyasitic-original-symmetric-geometry-')as directory:
        for i,c in enumerate(jobs()):
            work=Path(directory)/str(i);work.mkdir()
            for name,text in(('process.tek',technology),('input.asit',c['script']),('answers.txt',c['stdin']),('capture.gdb',COMMANDS.replace('ENTRY',hex(c['entry'])))):(work/name).write_text(text)
            run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=args.library_path),capture_output=True,text=True,start_new_session=True,timeout=120)
            if run.returncode or not(work/'symmetric.json').exists():raise RuntimeError(f'Original symmetric capture failed {i}: {run.stdout[-1800:]} {run.stderr[-1000:]}')
            item=json.loads((work/'symmetric.json').read_text())
            if item['control_before']!=0x37f or item['control_after']!=0x37f:raise RuntimeError('Unexpected original control word')
            item.update(c);records.append(item);print(f'Original symmetric {i}: {len(item["segments"])} segments / {c["label"]}',flush=True)
    output=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,technology=technology,
                reference='Actual original symmetric square 0x08059854 / polygon 0x0805a45c creators entry and return, unchanged numerical instructions. Every XYZ store, scalar width, conductor thickness, metal and explicit via count captured after rotation and native linked/direction reversal; output origin and exact incoming parsed config retained. Native uninitialized conductor mesh counts and via thickness excluded.',gdb_commands=COMMANDS,cases=records)
    (ROOT/'tests/fixtures/symmetric_geometry_original.json').write_text(json.dumps(output,separators=(',',':'),allow_nan=False)+'\n')


if __name__=='__main__':main()
