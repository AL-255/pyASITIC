"""Capture complete unchanged-original SPIRAL Pi2 and 2PORT electrical stores."""
import argparse,hashlib,json,os
from pathlib import Path
import re,subprocess,tempfile
from capture_pi_sessions import COMMANDS
from capture_original_symmetric import ORIGINAL_SHA256,LEGACY_SHA256
from capture_polygon_inputs_original import keyword

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--reference',type=Path,required=True);parser.add_argument('--library-path',required=True)
    args=parser.parse_args();reference=args.reference.resolve();original=reference/'run/asitic.linux.2.2'
    for path,want in((original,ORIGINAL_SHA256),(reference/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so',LEGACY_SHA256)):
        if hashlib.sha256(path.read_bytes()).hexdigest()!=want:raise ValueError(f'Unexpected oracle checksum: {path}')
    parent=ROOT/'tests/fixtures/polygon_inputs_original.json';technology=json.loads(parent.read_text())['technology']
    for key,value in(('chipx',128),('chipy',128),('fftx',64),('ffty',64)):
        technology=re.sub(rf'(?im)^(\s*{key}\s*=\s*)[\d.]+',rf'\g<1>{value}',technology)
    jobs=[(3,1.3333333,17,.1234567,False,True),(7,1.7142857,-35.5,2.34567891,False,True),(16,1.25,179.9,1,True,True),(32,1.5,0,1.23456789,False,True),(3,1.3333333333333333,0,.1234567,False,False),(7,1.7142857142857142,0,1.23456789,False,False)]
    records=[]
    with tempfile.TemporaryDirectory(prefix='pyasitic-original-polygon-sessions-')as directory:
        for i,(sides,turns,angle,frequency,eddy,native)in enumerate(jobs):
            p=dict(name='A',metal='M4',radius=25.125,sides=sides,width=3.25,spacing=2.125,turns=turns,angle=angle,phase=-1,x=30,y=30)
            if native:creation=keyword(p);answers='quit\n'
            else:
                p.update(radius=25.123456789,width=3.14159265358979,spacing=2.71828182845905,phase=1)
                creation='SPIRAL\n';answers=f'A\n{sides}\n25.123456789\n3.14159265358979\n2.71828182845905\n{turns:.17g}\nM4\n30 30\nquit\n'
            text=format(frequency,'.17g');script='CELL 1000 1000 1000\nCCELL 1000 1000\n'+f'EDDY {"ON"if eddy else"OFF"}\n'+creation+f'PI2 A {text}\n2PORT A {text} {text} 1 S RECT SLOW s.out\n'
            work=Path(directory)/str(i);work.mkdir()
            for name,value in(('process.tek',technology),('input.asit',script),('answers.txt',answers),('capture.gdb',COMMANDS)):(work/name).write_text(value)
            run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=args.library_path),capture_output=True,text=True,start_new_session=True,timeout=120)
            if run.returncode or not(work/'raw.json').exists():raise RuntimeError(f'Original polygon session failed {i}: {run.stdout[-1600:]} {run.stderr[-1000:]}')
            raw=json.loads((work/'raw.json').read_text())
            if raw['control_before']!=0x37f or raw['control_after']!=0x37f:raise RuntimeError('Unexpected original control word')
            request=dict(action='pi2',kind='polygon',native_keyword=native,parameters=p,technology=technology,frequency_ghz=frequency,eddy=eddy,mesh={key:1000 for key in('length_cell','width_cell','thickness_cell','capacitance_length_cell','capacitance_width_cell')})
            records.append(dict(request=request,script=script,stdin=answers,**raw));print(f'Original polygon electrical session {i}: {sides} sides, keyword {native}, eddy {eddy}',flush=True)
    output=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,parent_sha256=hashlib.sha256(parent.read_bytes()).hexdigest(),gdb_commands=COMMANDS,
                reference='Unchanged original polygon keyword/interactive creation followed by complete Pi2 and 2PORT SLOW sessions. Data-only model/S/resonance observers preserve every original Y/model/S store and retained resonance return.',cases=records)
    (ROOT/'tests/fixtures/polygon_sessions_original.json').write_text(json.dumps(output,separators=(',',':'),allow_nan=False)+'\n')


if __name__=='__main__':main()
