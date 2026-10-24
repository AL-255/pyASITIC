"""Capture complete unchanged-original WIRE Pi2/2PORT SLOW sessions."""
import argparse,hashlib,json,os
from pathlib import Path
import math,re,struct,subprocess,tempfile
from capture_original_symmetric import ORIGINAL_SHA256,LEGACY_SHA256
from capture_pi_sessions import COMMANDS
from capture_wire_original import keyword
from capture_contact_geometry_original import COMMANDS as CONTACT_COMMANDS

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--reference',type=Path,required=True);parser.add_argument('--library-path',required=True)
    args=parser.parse_args();reference=args.reference.resolve();original=reference/'run/asitic.linux.2.2'
    for path,want in((original,ORIGINAL_SHA256),(reference/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so',LEGACY_SHA256)):
        if hashlib.sha256(path.read_bytes()).hexdigest()!=want:raise ValueError(f'Unexpected oracle checksum: {path}')
    parent=ROOT/'tests/fixtures/wire_original.json';technology=json.loads(parent.read_text())['technology']
    for key,value in(('chipx',128),('chipy',128),('fftx',64),('ffty',64)):
        technology=re.sub(rf'(?im)^(\s*{key}\s*=\s*)[\d.]+',rf'\g<1>{value}',technology)
    jobs=[(40.125,3.25,'M4',37,1,.1234567,False,True),(50.125,10.125,'M5',-35.5,-1,2.34567891,False,True),(40,.1,'M5',17,1,1,False,True),(40,5,'M4',0,-1,1,True,True),(40.123456789,3.14159265358979,'M4',37,1,1.23456789,False,False),(40.123456789,3.14159265358979,'M4',-35.5,-1,2.34567891,True,False),(40.123456789,.01,'M5',0,1,.1234567,False,False),(10.125,.1,'M5',17,1,1,False,True)]
    records=[];undefined=[]
    with tempfile.TemporaryDirectory(prefix='pyasitic-original-wire-sessions-')as directory:
        for i,(length,width,metal,angle,phase,frequency,eddy,native)in enumerate(jobs):
            p=dict(name='A',length=length,width=width,metal=metal,angle=angle,phase=phase,x=30,y=30)
            case_technology=technology
            if i==6:p.update(x=10,y=20)
            if i==7:
                p.update(x=4,y=4.2)
                for key,value in(('chipx',32),('chipy',32),('fftx',128),('ffty',128)):
                    case_technology=re.sub(rf'(?im)^(\s*{key}\s*=\s*)[\d.]+',rf'\g<1>{value}',case_technology)
            if native:creation=keyword(p);answers='quit\n'
            else:
                creation='WIRE\n';answers=f'A\n{length:.17g}\n{width:.17g}\n{metal}\n{phase}\n{p["x"]} {p["y"]}\n{angle:.17g}\nquit\n'
            text=format(frequency,'.17g');script='CELL 1000 1000 1000\nCCELL 1000 1000\n'+f'EDDY {"ON"if eddy else"OFF"}\n'+creation+f'PI2 A {text}\n2PORT A {text} {text} 1 S RECT SLOW s.out\n'
            work=Path(directory)/str(i);work.mkdir()
            for name,value in(('process.tek',case_technology),('input.asit',script),('answers.txt',answers),('capture.gdb',COMMANDS)):(work/name).write_text(value)
            run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=args.library_path),capture_output=True,text=True,start_new_session=True,timeout=120)
            if run.returncode or not(work/'raw.json').exists():raise RuntimeError(f'Original wire session failed {i}: {run.stdout[-1800:]} {run.stderr[-1000:]}')
            raw=json.loads((work/'raw.json').read_text())
            if raw['control_before']!=0x37f or raw['control_after']!=0x37f:raise RuntimeError('Unexpected original control word')
            request=dict(action='pi2',kind='wire',native_keyword=native,native_interactive=not native,parameters=p,technology=case_technology,frequency_ghz=frequency,eddy=eddy,mesh={key:1000 for key in('length_cell','width_cell','thickness_cell','capacitance_length_cell','capacitance_width_cell')})
            item=dict(index=i,request=request,script=script,stdin=answers,**raw)
            if all(math.isfinite(struct.unpack('<d',bytes.fromhex(v))[0])for v in raw['model']['Y']):records.append(item)
            else:
                transcript=subprocess.run([str(original),'-g','-t','process.tek','-x','input.asit'],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=args.library_path,TERM='dumb',INPUTRC='/dev/null'),input=answers,capture_output=True,text=True,start_new_session=True,timeout=120)
                if'nan'not in transcript.stdout.lower():raise RuntimeError('Original nonfinite model transcript missing')
                (work/'capture-contact.gdb').write_text(CONTACT_COMMANDS)
                contact=subprocess.run(['gdb','-q','-batch','-x','capture-contact.gdb',str(original)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=args.library_path),capture_output=True,text=True,start_new_session=True,timeout=120)
                if contact.returncode or not(work/'contacts.json').exists():raise RuntimeError('Original undefined wire contact capture failed')
                item.update(stdout=transcript.stdout,stderr=transcript.stderr,returncode=transcript.returncode,contact_capture=json.loads((work/'contacts.json').read_text()))
                undefined.append(item)
            print(f'Original wire electrical session {i}: keyword {native}, angle {angle}, eddy {eddy}',flush=True)
    output=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,parent_sha256=hashlib.sha256(parent.read_bytes()).hexdigest(),gdb_commands=COMMANDS,contact_gdb_commands=CONTACT_COMMANDS,
                reference='Unchanged original keyword/interactive WIRE creation followed by Pi2 and 2PORT SLOW. Data-only entry/return observers capture all Y/model/S stores and retained resonance. Interactive angle values retain the actual native raw-radian prompt behavior. Both original nonfinite histories retain all raw outputs, direct CLI transcripts and independently captured contact bounds; one has zero contact area, while the finer-grid case has nonzero contact area.',cases=records,undefined_cases=undefined)
    (ROOT/'tests/fixtures/wire_sessions_original.json').write_text(json.dumps(output,separators=(',',':'),allow_nan=False)+'\n')


if __name__=='__main__':main()
