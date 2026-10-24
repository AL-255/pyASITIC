"""Capture complete unchanged-original square Pi2 electrical stores."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from capture_pi_sessions import COMMANDS
from capture_original_symmetric import ORIGINAL_SHA256,LEGACY_SHA256

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',type=Path,required=True);parser.add_argument('--library-path',required=True)
    args=parser.parse_args();reference=args.reference.resolve()
    original=reference/'run/asitic.linux.2.2';legacy=reference/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so'
    for path,want in((original,ORIGINAL_SHA256),(legacy,LEGACY_SHA256)):
        if hashlib.sha256(path.read_bytes()).hexdigest()!=want:raise ValueError(f'Unexpected oracle checksum: {path}')
    parent=ROOT/'tests/fixtures/square_original.json';technology=json.loads(parent.read_text())['technology']
    for key,value in(('chipx',128),('chipy',128),('fftx',64),('ffty',64)):
        technology=re.sub(rf'(?im)^(\s*{key}\s*=\s*)[\d.]+',rf'\g<1>{value}',technology)
    jobs=[(.5,17,1,'M3',.1234567,False,True),(1.25,-35.5,-1,'M3',2.34567891,False,True),(1.75,0,1,'-1',1,True,True),(1.75,0,1,'M3',1.23456789,False,False)]
    records=[]
    with tempfile.TemporaryDirectory(prefix='pyasitic-original-square-sessions-')as directory:
        for i,(turns,angle,phase,exit_metal,frequency,eddy,keyword)in enumerate(jobs):
            p=dict(name='A',metal='M4',exit_metal=exit_metal,length=80.125,height=70.375,width=3.25,spacing=2.125,turns=turns,angle=angle,phase=phase,x=30,y=30)
            if keyword:
                creation='SQUARE NAME=A:METAL=M4:EXIT='+exit_metal+':'+':'.join(f'{key}={p[name]:.17g}'for key,name in(('LEN','length'),('WID','height'),('W','width'),('S','spacing'),('N','turns'),('ORIENT','angle'),('PHASE','phase'),('XORG','x'),('YORG','y')))+'\n';answers='quit\n'
            else:
                p.update(length=80.123456789,height=70.987654321,width=3.14159265358979,spacing=2.71828182845905)
                creation='SQUARE\n';answers='A\n80.123456789 70.987654321\n3.14159265358979\n2.71828182845905\n1.75\nM4\ny\nM3\n30 30\nquit\n'
            text=format(frequency,'.17g');script='CELL 1000 1000 1000\nCCELL 1000 1000\n'+f'EDDY {"ON"if eddy else"OFF"}\n'+creation+f'PI2 A {text}\n2PORT A {text} {text} 1 S RECT SLOW s.out\n'
            work=Path(directory)/str(i);work.mkdir()
            for name,value in(('process.tek',technology),('input.asit',script),('answers.txt',answers),('capture.gdb',COMMANDS)):(work/name).write_text(value)
            run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=args.library_path),capture_output=True,text=True,start_new_session=True,timeout=120)
            if run.returncode or not(work/'raw.json').exists():raise RuntimeError(f'Original square session failed {i}: {run.stdout[-1600:]} {run.stderr[-1000:]}')
            raw=json.loads((work/'raw.json').read_text())
            if raw['control_before']!=0x37f or raw['control_after']!=0x37f:raise RuntimeError('Unexpected original control word')
            request=dict(action='pi2',kind='square',native_keyword=keyword,parameters=p,technology=technology,frequency_ghz=frequency,eddy=eddy,mesh={key:1000 for key in('length_cell','width_cell','thickness_cell','capacitance_length_cell','capacitance_width_cell')})
            records.append(dict(request=request,script=script,stdin=answers,**raw));print(f'Original square electrical session {i}: keyword {keyword}, eddy {eddy}',flush=True)
        # Preserve the earlier out-of-chip history as an explicit invalid
        # native case, rather than discarding its failure to obtain a model.
        bad=records[1];script=bad['script'];assert ':XORG=30:YORG=30'in script
        script=script.replace(':XORG=30:YORG=30',':XORG=10:YORG=20');work=Path(directory)/'invalid';work.mkdir()
        (work/'process.tek').write_text(technology);(work/'input.asit').write_text(script)
        run=subprocess.run([str(original),'-g','-t','process.tek','-x','input.asit'],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=args.library_path,TERM='dumb',INPUTRC='/dev/null'),input='quit\n',capture_output=True,text=True,start_new_session=True,timeout=120)
        if 'Error:  Coordinate out of range.'not in run.stdout or'Error:  Could not generate capacitance matrix.'not in run.stdout:raise RuntimeError('Original invalid square did not retain its coordinate diagnostic')
        request=dict(bad['request'],parameters=dict(bad['request']['parameters'],x=10,y=20))
        invalid=[dict(request=request,script=script,stdin='quit\n',returncode=run.returncode,stdout=run.stdout,stderr=run.stderr)]
    output=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,parent_sha256=hashlib.sha256(parent.read_bytes()).hexdigest(),gdb_commands=COMMANDS,
                reference='Unchanged original square keyword/interactive creation followed by complete Pi2 and 2PORT sessions. Data-only model/S/resonance entry and return observers preserve every original Y/model/S store and retained resonance return. One out-of-chip session retains its original failure transcript.',cases=records,invalid_cases=invalid)
    (ROOT/'tests/fixtures/square_sessions_original.json').write_text(json.dumps(output,separators=(',',':'),allow_nan=False)+'\n')


if __name__=='__main__':main()
