"""Capture complete original Pi2/2PORT inner-opening geometry histories."""
import argparse,hashlib,json,os,re,subprocess,tempfile
from pathlib import Path
from capture_pi_sessions import COMMANDS
from capture_original_symmetric import ORIGINAL_SHA256,LEGACY_SHA256
ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--reference',type=Path,required=True);parser.add_argument('--library-path',required=True);args=parser.parse_args()
    ref=args.reference.resolve();original=ref/'run/asitic.linux.2.2';legacy=ref/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so'
    for path,want in[(original,ORIGINAL_SHA256),(legacy,LEGACY_SHA256)]:
        if hashlib.sha256(path.read_bytes()).hexdigest()!=want:raise ValueError('Unexpected original checksum')
    parent=ROOT/'tests/fixtures/inner_dimensions_original.json';f=json.loads(parent.read_text());technology=f['technology']
    for key,value in [('chipx',256),('chipy',256),('fftx',128),('ffty',128)]:technology=re.sub(rf'(?im)^(\s*{key}\s*=\s*)[\d.]+',rf'\g<1>{value}',technology)
    labels=['keyword/square/1.75/True/17/-1','interactive/square/1.75/True','keyword/multimetal/1.75/True/17/-1','interactive/multimetal/1.75/True'];records=[]
    with tempfile.TemporaryDirectory(prefix='pyasitic-original-inner-models-')as d:
        for i,label in enumerate(labels):
            c=next(c for c in f['cases']if c['label']==label);p=dict(c['parameters'],x=64,y=64);frequency=[.1234567,2.34567891,1.23456789,1.987654321][i];eddy=i in(1,3)
            creation=c['script'].replace(':XORG=12.345:YORG=23.456',':XORG=64:YORG=64');answers=c['stdin'].replace('12.3456789 23.456789','64 64')
            text=format(frequency,'.17g');script=f'CELL 1000 1000 1000\nCCELL 1000 1000\nEDDY {"ON"if eddy else"OFF"}\n'+creation+f'PI2 A {text}\n2PORT A {text} {text} 1 S RECT SLOW s.out\n'
            work=Path(d)/str(i);work.mkdir()
            for name,value in [('process.tek',technology),('input.asit',script),('answers.txt',answers),('capture.gdb',COMMANDS)]:(work/name).write_text(value)
            run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=args.library_path),capture_output=True,text=True,start_new_session=True,timeout=120)
            if run.returncode or not(work/'raw.json').exists():raise RuntimeError(f'Original inner model {i} failed: '+run.stdout[-1800:]+run.stderr[-1000:])
            raw=json.loads((work/'raw.json').read_text());assert raw['control_before']==raw['control_after']==0x37f
            request=dict(action='pi2',kind=c['kind'],parameters=p,native_keyword=c.get('native_keyword',False),native_interactive=c.get('native_interactive',False),technology=technology,frequency_ghz=frequency,eddy=eddy,mesh={key:1000 for key in ['length_cell','width_cell','thickness_cell','capacitance_length_cell','capacitance_width_cell']})
            records.append(dict(request=request,parent_label=label,script=script,stdin=answers,stdout=run.stdout,**raw));print(f'Original inner electrical {i}: {label}',flush=True)
    out=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,parent_sha256=hashlib.sha256(parent.read_bytes()).hexdigest(),gdb_commands=COMMANDS,reference='Intact original inner-opening square/MMSQUARE keyword and interactive creation, followed by complete Pi2/2PORT commands. Exact original Y/model/S stores and retained resonance return are observed at actual entries/returns; no numerical or runtime code replaced.',cases=records)
    (ROOT/'tests/fixtures/inner_sessions_original.json').write_text(json.dumps(out,separators=(',',':'),allow_nan=False)+'\n')


if __name__=='__main__':main()
