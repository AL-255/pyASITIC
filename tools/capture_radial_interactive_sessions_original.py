"""Complete original interactive radial Pi2/2PORT sessions and independent CIF."""
import argparse,gzip,hashlib,json,os,re,subprocess,tempfile
from pathlib import Path
from capture_original_symmetric import ORIGINAL_SHA256,LEGACY_SHA256
from capture_pi_sessions import COMMANDS
from capture_radial_interactive_original import interactive
ROOT=Path(__file__).resolve().parents[1]


def jobs():
 for i,(kind,sides,turns,width,gap)in enumerate([('ring',7,1,3.14159265358979,41.375),('ring',16,1,3.14159265358979,720.1234567),('ring',4,1,25.123456789,20),('polygon',3,1.3333333333333333,3.14159265358979,0),('polygon',7,1.7142857142857142,3.14159265358979,0),('polygon',16,1.0625,3.14159265358979,0)]):
  yield kind,dict(name='A',radius=25.123456789,sides=sides,turns=turns,width=width,spacing=2.71828182845905,gap=gap,x=40.123456789,y=40.987654321,metal='M4'),[.1234567,1.23456789,2.34567891,1,3.1234567,1.987654321][i],i==1


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--reference',type=Path,required=True);p.add_argument('--library-path',required=True);a=p.parse_args();ref=a.reference.resolve();original=ref/'run/asitic.linux.2.2'
 for path,expected in((original,ORIGINAL_SHA256),(ref/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so',LEGACY_SHA256)):
  if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise ValueError('Unexpected original checksum')
 technology=(ROOT/'src/reasitic/CMOS.tek').read_text()
 for key,value in(('chipx',128),('chipy',128),('fftx',64),('ffty',64)):technology=re.sub(rf'(?im)^(\s*{key}\s*=\s*)[\d.]+',rf'\g<1>{value}',technology)
 records=[]
 with tempfile.TemporaryDirectory(prefix='pyasitic-original-radial-pi-')as d:
  for index,(kind,parameters,frequency,eddy)in enumerate(jobs()):
   work=Path(d)/str(index);work.mkdir();creation='RING\n'if kind=='ring'else'SPIRAL\n';text=format(frequency,'.17g');answers=interactive(kind,parameters)
   script='CELL 1000 1000 1000\nCCELL 1000 1000\n'+f'EDDY {"ON"if eddy else"OFF"}\n'+creation+f'PI2 A {text}\n2PORT A {text} {text} 1 S RECT SLOW s.out\n'
   for name,value in(('process.tek',technology),('input.asit',script),('answers.txt',answers),('capture.gdb',COMMANDS)):(work/name).write_text(value)
   run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=a.library_path),capture_output=True,text=True,start_new_session=True,timeout=120)
   if run.returncode or not(work/'raw.json').exists()or'Python Exception'in run.stderr or'Traceback'in run.stderr:raise RuntimeError(f'{index}/{kind}: '+run.stdout[-2000:]+run.stderr[-1600:])
   raw=json.loads((work/'raw.json').read_text());plain_script=script.replace(creation,creation+'CIFSAVE A layout.cif 1 1000 POLY\n');(work/'plain.asit').write_text(plain_script)
   plain=subprocess.run([str(original),'-g','-t','process.tek','-x','plain.asit'],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=a.library_path,TERM='dumb',INPUTRC='/dev/null'),input=answers,capture_output=True,text=True,start_new_session=True,timeout=120)
   if not(work/'layout.cif').exists():raise RuntimeError('Missing native CIF: '+plain.stdout[-2000:])
   records.append(dict(request=dict(action='pi2',kind=kind,native_interactive=True,native_mesh=True,parameters=parameters,technology=technology,frequency_ghz=frequency,eddy=eddy,mesh={k:1000 for k in('length_cell','width_cell','thickness_cell','capacitance_length_cell','capacitance_width_cell')}),script=script,stdin=answers,stdout=run.stdout,stderr=run.stderr,plain_script=plain_script,plain_stdout=plain.stdout,plain_returncode=plain.returncode,cif=(work/'layout.cif').read_text(),**raw));print(index,kind,'model stores',len(raw['model']['M']),'plain return',plain.returncode,flush=True)
 result=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,gdb_commands=COMMANDS,reference='Unchanged complete original interactive RING/SPIRAL, Pi2 and 2PORT CLI histories. Data-only actual model/scattering/resonance entry/return observations. Native wide ring, periodic gap and fractional turn cases; independent unobserved CLI/CIF transcripts retained. No numerical or runtime replacement.',cases=records)
 with gzip.GzipFile(str(ROOT/'tests/fixtures/radial_interactive_sessions_original.json.gz'),'wb',mtime=0)as f:f.write((json.dumps(result,separators=(',',':'),allow_nan=False)+'\n').encode())

if __name__=='__main__':main()
