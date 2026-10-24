"""Actual original helper/instruction returns for joined assembly discrepancies."""
import argparse,gzip,hashlib,json,os,re,subprocess,tempfile
from pathlib import Path
from capture_mutual_command_traces_original import COMMANDS,ORIGINAL_SHA256,LEGACY_SHA256
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--reference',type=Path,required=True);p.add_argument('--library-path',required=True);a=p.parse_args();original=a.reference/'run/asitic.linux.2.2'
 for path,digest in((original,ORIGINAL_SHA256),(a.reference/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so',LEGACY_SHA256)):
  assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
 parent=ROOT/'tests/fixtures/join_assembly_original.json.gz';assembly=json.loads(gzip.decompress(parent.read_bytes()))['cases'][0];models=ROOT/'tests/fixtures/join_sessions_original.json.gz';model=next(c for c in json.loads(gzip.decompress(models.read_bytes()))['cases']if c['label']==assembly['label'])
 math_parent=ROOT/'tests/fixtures/mutual_command_traces_original.json';points=json.loads(math_parent.read_text())['math_instruction_points'];points={int(k,16):v for k,v in points.items()};cases=[]
 disassembly=subprocess.check_output(['objdump','-d',str(original)],text=True)
 for match in re.finditer(r'^\s*([0-9a-f]+):\s+[0-9a-f ]+\s+(fyl2xp?1?|fpatan|fcos|fsin|f2xm1|fscale|frndint)\b',disassembly,re.M):
  address=int(match[1],16)
  if 0x80613bc<=address<0x8061b84:
   points.setdefault(address,[]).append((match[2],'before'));points.setdefault(address+2,[]).append((match[2],'after'))

 with tempfile.TemporaryDirectory(prefix='pyasitic-join-mutual-')as directory:
  for i,j in((12,45),(12,48)):
   ordinal=sum(assembly['n']-1-k for k in range(i))+j-i-1;commands=COMMANDS.replace('TARGET',str(ordinal)).replace('MATHPOINTS',repr(points));work=Path(directory)/str(j);work.mkdir()
   for name,value in(('process.tek',model['request']['technology']),('input.asit',model['script']),('answers.txt',model['stdin']),('capture.gdb',commands)):(work/name).write_text(value)
   r=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=a.library_path),capture_output=True,text=True,start_new_session=True,timeout=120)
   if r.returncode or not(work/'boundaries.json').exists():raise RuntimeError(r.stdout[-1800:]+r.stderr[-1200:])
   observed=json.loads((work/'boundaries.json').read_text());assert observed['input_bits']==assembly['records'][i]['wire_bits']+assembly['records'][j]['wire_bits'];assert observed['control_before']==observed['control_after']==0x37f
   cases.append(dict(first=i,second=j,script=model['script'],stdin=model['stdin'],stdout=r.stdout,stderr=r.stderr,**observed));print(i,j,len(observed['events']),'original helpers captured',flush=True)
 result=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,parents={path.name:hashlib.sha256(path.read_bytes()).hexdigest()for path in(parent,models,math_parent)},gdb_commands=COMMANDS,math_instruction_points={hex(k):v for k,v in points.items()},reference='Unchanged JOIN/CALCTRANS script stopped at two actual upper-assembly mutual calls, with read-only entry, helper-return and instruction-word observers. Observed entry operands match the independently captured original filament records. The inferior is terminated after the selected pair returns, not at native command exit.',cases=cases)
 with gzip.GzipFile(str(ROOT/'tests/fixtures/join_mutual_traces_original.json.gz'),'wb',mtime=0)as stream:stream.write((json.dumps(result,separators=(',',':'))+'\n').encode())
if __name__=='__main__':main()
