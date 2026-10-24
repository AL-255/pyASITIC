"""Read-only x87 point-rotation traces within an intact spatial command history."""
import argparse,gzip,hashlib,json,os,subprocess,tempfile
from pathlib import Path
from capture_spatial_edits_original import COMMANDS,jobs,command,ROOT
from capture_original_symmetric import ORIGINAL_SHA256,LEGACY_SHA256
POINTS=r'''
points=[];active_point=None
def raw():return bytes(gdb.parse_and_eval('$st0').bytes).hex()
class Point(gdb.Breakpoint):
 def stop(self):
  global active_point
  pc=reg('pc')
  if pc==0x80b4688:
   assert active_point is None;esp=reg('esp');p=u32(esp+4);active_point=dict(pointer=p,input_bits=(mem(p,16)+mem(esp+8,24)).hex(),control=reg('fctrl'))
  elif pc==0x80b46f0:
   active_point['output_bits']=mem(active_point.pop('pointer'),16).hex();points.append(active_point);active_point=None
  else:active_point[{0x80b46ac:'radius',0x80b46c2:'polar',0x80b46cb:'rotated',0x80b46d0:'cosine',0x80b46d6:'x_accumulator',0x80b46dd:'sine',0x80b46e1:'y_accumulator'}[pc]]=raw()
  return False
for a in(0x80b4688,0x80b46ac,0x80b46c2,0x80b46cb,0x80b46d0,0x80b46d6,0x80b46dd,0x80b46e1,0x80b46f0):Point('*'+hex(a),internal=True)
'''

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--reference',type=Path,required=True);p.add_argument('--library-path',required=True);a=p.parse_args();ref=a.reference.resolve();original=ref/'run/asitic.linux.2.2'
 for path,want in((original,ORIGINAL_SHA256),(ref/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so',LEGACY_SHA256)):
  if hashlib.sha256(path.read_bytes()).hexdigest()!=want:raise ValueError('Unexpected original checksum')
 c=next(c for c in jobs()if c['label']=='wire/edges/0.0');script=c['creation']
 for op in c['operations']:script+=command(op,c['names'])
 commands=COMMANDS.replace("end\nrun -g",POINTS+"\nend\nrun -g").replace('dict(states=states,signal=signal)','dict(states=states,signal=signal,points=points,unfinished_point=active_point)')
 with tempfile.TemporaryDirectory(prefix='pyasitic-original-rotation-points-')as directory:
  work=Path(directory)
  for name,value in(('process.tek',c['technology']),('input.asit',script),('answers.txt',c['stdin']),('capture.gdb',commands)):(work/name).write_text(value)
  run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=a.library_path),capture_output=True,text=True,start_new_session=True,timeout=120)
  if run.returncode or not(work/'spatial.json').exists()or'Python Exception'in run.stderr:raise RuntimeError(run.stdout[-2000:]+run.stderr[-1500:])
  result=json.loads((work/'spatial.json').read_text());assert not result['signal']and result['unfinished_point']is None
 result.update(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,gdb_commands=commands,public=c['public'],technology=c['technology'],operations=c['operations'],script=script,stdin=c['stdin'],stdout=run.stdout,stderr=run.stderr,reference='Read-only observations of unchanged original complete WIRE and spatial-edit history. Every point entry/return, FSQRT/FPATAN/FCOS/FSIN return, retained accumulators and input/output stores; no substitutions or caller/register changes.')
 with gzip.GzipFile(str(ROOT/'tests/fixtures/rotation_points_original.json.gz'),'wb',mtime=0)as out:out.write((json.dumps(result,separators=(',',':'),allow_nan=False)+'\n').encode())
 print(len(result['points']),'complete original point rotations')

if __name__=='__main__':main()
