"""Read-only original filament/upper assembly boundary for joined CALCTRANS."""
import argparse,gzip,hashlib,json,os,subprocess,tempfile
from pathlib import Path
from capture_impedance_original import COMMANDS,ORIGINAL_SHA256,LEGACY_SHA256
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--reference',type=Path,required=True);p.add_argument('--library-path',required=True);a=p.parse_args();original=a.reference/'run/asitic.linux.2.2'
 for path,digest in((original,ORIGINAL_SHA256),(a.reference/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so',LEGACY_SHA256)):
  assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
 parent=ROOT/'tests/fixtures/join_sessions_original.json.gz';f=json.loads(gzip.decompress(parent.read_bytes()));c=next(c for c in f['cases']if c['label']=='finite-balun/calctrans')
 with tempfile.TemporaryDirectory(prefix='pyasitic-original-join-assembly-')as directory:
  work=Path(directory)
  for name,value in(('process.tek',c['request']['technology']),('input.asit',c['script']),('answers.txt',c['stdin']),('capture.gdb',COMMANDS)):(work/name).write_text(value)
  r=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=a.library_path),capture_output=True,text=True,start_new_session=True,timeout=120)
  if r.returncode or not(work/'assembly.json').exists()or'Python Exception'in r.stderr:raise RuntimeError(r.stdout[-1800:]+r.stderr[-1000:])
  result=json.loads((work/'assembly.json').read_text())
 out=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,parent_sha256=hashlib.sha256(parent.read_bytes()).hexdigest(),gdb_commands=COMMANDS,reference='Read-only original initial upper impedance assembly and every filament construction from the unchanged finite-balun/calctrans JOIN session. The observer terminates after the actual assembly return, before inversion; the complete native model is captured separately.',cases=[dict(label=c['label'],request=c['request'],stdout=r.stdout,stderr=r.stderr,**result)])
 with gzip.GzipFile(str(ROOT/'tests/fixtures/join_assembly_original.json.gz'),'wb',mtime=0)as stream:stream.write((json.dumps(out,separators=(',',':'))+'\n').encode())
 print(result['n'],'original joined filaments captured.')
if __name__=='__main__':main()
