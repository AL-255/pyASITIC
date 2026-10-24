"""Capture complete original Pi2/2PORT histories of signed/default gaps."""
import argparse,hashlib,json,os,re,subprocess,tempfile
from pathlib import Path
from capture_pi_sessions import COMMANDS
from capture_original_symmetric import ORIGINAL_SHA256,LEGACY_SHA256
from capture_contact_geometry_original import COMMANDS as CONTACT_COMMANDS
ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--reference',type=Path,required=True);parser.add_argument('--library-path',required=True);args=parser.parse_args()
    ref=args.reference.resolve();original=ref/'run/asitic.linux.2.2';legacy=ref/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so'
    for path,want in[(original,ORIGINAL_SHA256),(legacy,LEGACY_SHA256)]:
        if hashlib.sha256(path.read_bytes()).hexdigest()!=want:raise ValueError('Unexpected original checksum')
    parent=ROOT/'tests/fixtures/transition_original.json';f=json.loads(parent.read_text());technology=f['technology']
    for key,value in [('chipx',256),('chipy',256),('fftx',128),('ffty',128)]:technology=re.sub(rf'(?im)^(\s*{key}\s*=\s*)[\d.]+',rf'\g<1>{value}',technology)
    records=[]
    with tempfile.TemporaryDirectory(prefix='pyasitic-original-transition-models-')as d:
        for i,(kind,command,dimension)in enumerate([('symmetric_square','SYMSQ','LEN=80'),('symmetric_polygon','SYMPOLY','RAD=40:SIDES=6')]):
            for j,(spacing,gap)in enumerate([(0,None),(1,0),(1,-.1)]):
                index=3*i+j;frequency=[.1234567,2.34567891,1.23456789,1.987654321,2.12345678,1][index];eddy=index in(1,4)
                p=dict(name='A',width=3,spacing=spacing,turns=1,metal='M4',secondary_metal='M3',x=64,y=64)
                p['length'if i==0 else'radius']=80 if i==0 else 40
                if i:p['sides']=6
                if gap is not None:p['inner_gap']=gap
                creation=f'{command} NAME=A:{dimension}:W=3:S={spacing}:N=1:METAL=M4:METAL2=M3:XORG=64:YORG=64'
                if gap is not None:creation+=f':ILEN={gap}'
                text=format(frequency,'.17g');script=f'CELL 1000 1000 1000\nCCELL 1000 1000\nEDDY {"ON"if eddy else"OFF"}\n'+creation+f'\nPI2 A {text}\n2PORT A {text} {text} 1 S RECT SLOW s.out\n'
                work=Path(d)/str(index);work.mkdir()
                for name,value in [('process.tek',technology),('input.asit',script),('answers.txt','quit\n'),('capture.gdb',COMMANDS)]:(work/name).write_text(value)
                run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=args.library_path),capture_output=True,text=True,start_new_session=True,timeout=120)
                if run.returncode or not(work/'raw.json').exists():raise RuntimeError(f'Original transition model {index} failed: '+run.stdout[-2000:]+run.stderr[-1200:])
                raw=json.loads((work/'raw.json').read_text());assert raw['control_before']==raw['control_after']==0x37f
                request=dict(action='pi2',kind=kind,parameters=p,native_keyword=True,technology=technology,frequency_ghz=frequency,eddy=eddy,mesh={key:1000 for key in ['length_cell','width_cell','thickness_cell','capacitance_length_cell','capacitance_width_cell']})
                (work/'contact.gdb').write_text(CONTACT_COMMANDS)
                contact=subprocess.run(['gdb','-q','-batch','-x','contact.gdb',str(original)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=args.library_path),capture_output=True,text=True,start_new_session=True,timeout=120)
                if contact.returncode or not(work/'contacts.json').exists():raise RuntimeError('Original transition contacts failed: '+contact.stdout[-1600:]+contact.stderr[-1000:])
                plain_script=script.replace('\nPI2 A ', '\nCIFSAVE A layout.cif 1 1000 POLY\nPI2 A ')
                (work/'plain.asit').write_text(plain_script)
                plain=subprocess.run([str(original),'-g','-t','process.tek','-x','plain.asit'],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=args.library_path,TERM='dumb',INPUTRC='/dev/null'),input='quit\n',capture_output=True,text=True,start_new_session=True,timeout=120)
                if not(work/'layout.cif').exists():raise RuntimeError('Missing original CIF stream: '+plain.stdout[-1200:])
                records.append(dict(request=request,script=script,stdout=run.stdout,plain_script=plain_script,plain_stdout=plain.stdout,plain_returncode=plain.returncode,cif=(work/'layout.cif').read_text(),contact_capture=json.loads((work/'contacts.json').read_text()),**raw));print(f'Original transition electrical {index}: {kind}, gap {gap}, eddy {eddy}',flush=True)
    out=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,parent_sha256=hashlib.sha256(parent.read_bytes()).hexdigest(),gdb_commands=COMMANDS,contact_gdb_commands=CONTACT_COMMANDS,reference='Intact original symmetric square/polygon keyword creation with omitted, explicit zero and negative ILEN, followed by complete Pi2/2PORT histories. Exact original Y/model/S stores and retained resonance returns observed at actual entries/returns. Independent contact observations and plain CLI/CIF transcripts retain nonfinite and degenerate histories; no numerical or runtime code replaced.',cases=records)
    (ROOT/'tests/fixtures/transition_sessions_original.json').write_text(json.dumps(out,separators=(',',':'),allow_nan=False)+'\n')


if __name__=='__main__':main()
