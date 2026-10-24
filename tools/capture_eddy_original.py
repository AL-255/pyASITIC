"""Capture real original eddy stamps, retained Green returns and libm imports."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from capture_original_symmetric import ORIGINAL_SHA256,LEGACY_SHA256

ROOT=Path(__file__).resolve().parents[1]
COMMANDS=r'''
set pagination off
set confirm off
set environment TERM dumb
set environment INPUTRC /dev/null
python
import gdb,struct,json,base64,zlib
entries={0x80949dc:'green',0x8092f30:'fold',0x8092cd0:'square',0x804a604:'cos',0x804ae24:'sin'}
end=0x8089cb0
for address in [*entries,end]:gdb.Breakpoint('*'+hex(address),internal=True)
end
run -g -t process.tek -x input.asit < answers.txt
python
green=[];trig=[];stamps=[];pending={};active_green=None;active_green_item=None;stop_after_stamp=False
def memory(address,size):return bytes(gdb.selected_inferior().read_memory(address,size))
def u32(address):return struct.unpack('<I',memory(address,4))[0]
def i32(address):return struct.unpack('<i',memory(address,4))[0]
def f64(address):return struct.unpack('<d',memory(address,8))[0]
control_before=int(gdb.parse_and_eval('$fctrl'))
while int(gdb.parse_and_eval('$pc'))!=end:
 address=int(gdb.parse_and_eval('$pc'))
 if address in entries:
  kind=entries[address];esp=int(gdb.parse_and_eval('$esp'));pc=u32(esp)
  if kind=='kernel':
   assert active_green_item is not None
   active_green_item['points'].append(memory(u32(esp+4),8));gdb.execute('continue',to_string=True);continue
  item=dict(kind=kind)
  if kind=='green':
   item['input_bits']=memory(esp+4,32).hex();active_green=len(green);item['trig_start']=len(trig);item['points']=[];active_green_item=item
   kernel=u32(0x80ceb7c)
   if kernel not in entries:entries[kernel]='kernel';gdb.Breakpoint('*'+hex(kernel),internal=True)
  elif kind in ('cos','sin'):
   item['argument_bits']=memory(esp+4,8).hex();item['green_index']=active_green
  else:
   shape,descriptor=u32(esp+4),u32(esp+8);data=u32(descriptor);rows=i32(descriptor+12);columns=i32(descriptor+16);stride=i32(descriptor+20)
   assert rows==columns and 1<=rows<=256 and stride>=rows
   def matrix_bytes():return b''.join(memory(data+j*stride*16,rows*16) for j in range(rows))
   item.update(rows=rows,before_bits=matrix_bytes().hex(),green_start=len(green),data=data,stride=stride)
   segments=[];segment=u32(shape+0xa8)
   while segment:
    assert len(segments)<2048
    segments.append(dict(wire_bits=memory(segment,56).hex(),metal=i32(segment+0xdc)));segment=u32(segment+0xec)
   item['segments']=segments
   item['config']=[1,len(segments),rows,i32(0x80d8904),1,int(kind=='square'),f64(esp+12),f64(0x80ce568),
                   f64(shape+0x70),f64(shape+0x88),f64(shape+0x90),f64(shape+0x98),0.,0.,0.,0.,*([0.]*8)]
   if kind=='square':item['config'][12]=f64(u32(0x80d891c)+8*i32(shape+0x68))
  assert pc not in pending
  pending[pc]=item;gdb.Breakpoint('*'+hex(pc),temporary=True,internal=True)
 else:
  assert address in pending,(hex(address),pending)
  item=pending.pop(address);kind=item['kind']
  if kind=='green':
   item['extended_bits']=bytes(gdb.parse_and_eval('$st0').bytes).hex();item['trig_count']=len(trig)-item['trig_start']
   points=item.pop('points');item['observations']=len(points);item['points_zlib_base64']=base64.b64encode(zlib.compress(b''.join(points),9)).decode()
   green.append(item);active_green=None;active_green_item=None
  elif kind in ('cos','sin'):
   item['extended_bits']=bytes(gdb.parse_and_eval('$st0').bytes).hex();trig.append(item)
  else:
   data,stride,rows=item.pop('data'),item.pop('stride'),item['rows']
   item['after_bits']=b''.join(memory(data+j*stride*16,rows*16) for j in range(rows)).hex();item['green_count']=len(green)-item['green_start'];stamps.append(item)
   if stop_after_stamp:break
 gdb.execute('continue',to_string=True)
assert not pending
result=dict(green=green,trig=trig,stamps=stamps,control_before=control_before,control_after=int(gdb.parse_and_eval('$fctrl')),
            libm_paths=sorted({o.filename for o in gdb.objfiles() if '/libm.' in o.filename or '/libm-' in o.filename}))
open('trace.json','w').write(json.dumps(result))
end
kill
quit
'''


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference",type=Path,required=True)
    parser.add_argument("--library-path",help="i386 runtime search path for original CLI")
    args=parser.parse_args();reference=args.reference.resolve()
    original=reference/"run/asitic.linux.2.2";legacy=reference/"run/libs/libstdc++-2-libc6.1-1-2.9.0.so"
    for path,expected in ((original,ORIGINAL_SHA256),(legacy,LEGACY_SHA256)):
        if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise ValueError(f"Unexpected oracle checksum: {path}")
    parent=ROOT/"tests/fixtures/transformer_network.json";cases=json.loads(parent.read_text())["cases"];records=[]
    eddy_parent=ROOT/"tests/fixtures/eddy.json";eddy_cases=json.loads(eddy_parent.read_text())["cases"]
    jobs=[("coupled",i,False,cases[i]) for i in (5,8,11)]
    jobs.extend(("lmat",i,fine,c) for i,c in enumerate(eddy_cases) if c["process"]=="CMOS" for fine in (False,True))
    with tempfile.TemporaryDirectory(prefix="pyasitic-original-eddy-") as directory:
        for label,(source,index,fine,case) in enumerate(jobs):
            work=Path(directory)/str(label);work.mkdir();script=case["script"]
            if fine:
                script=script.replace("CELL 1000 1000 1000","CELL 50 3 .5",1).replace("CCELL 1000 1000","CCELL 50 1000",1).replace("LMAT A 1 ","LMAT A 2 ",1)
            for name,text in (("process.tek",case["technology"]),("input.asit",script),("answers.txt",case.get("stdin","quit\n"))):(work/name).write_text(text)
            commands=COMMANDS.replace("stop_after_stamp=False","stop_after_stamp=True") if source=="lmat" else COMMANDS
            (work/"capture.gdb").write_text(commands)
            env=dict(os.environ,LD_LIBRARY_PATH=args.library_path or str(reference/"run/libs"))
            run=subprocess.run(["gdb","-q","-batch","-x","capture.gdb",str(original)],cwd=work,env=env,capture_output=True,text=True,start_new_session=True,timeout=120)
            if run.returncode or not (work/"trace.json").exists():raise RuntimeError(f"Original eddy capture failed {index}: {run.stdout[-1600:]} {run.stderr[-1000:]}")
            record=json.loads((work/"trace.json").read_text());record.update(session_index=index,source=source,fine=fine)
            if record["control_before"]!=record["control_after"] or record["control_before"]&0xf00!=0x300:raise RuntimeError("Unexpected x87 control word")
            record["libm_sha256"]={str(Path(p).resolve()):hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in record.pop("libm_paths") if Path(p).is_file()}
            records.append(record);print(source,index,'fine' if fine else 'coarse',len(record["green"]),"Green calls,",len(record["trig"]),"imported trig returns,",len(record["stamps"]),"complete matrix stamps",flush=True)
    coverage={key:sum(len(r[key]) for r in records) for key in ("green","trig","stamps")}
    result=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,parent_fixture_sha256=hashlib.sha256(parent.read_bytes()).hexdigest(),eddy_fixture_sha256=hashlib.sha256(eddy_parent.read_bytes()).hexdigest(),coverage=coverage,
                reference="Actual original CLI sessions stopped at the first model extraction entry (coupled) or first eddy stamp return (LMAT). Fine LMAT probes start with the fixture's fine mesh and 2 GHz. GDB entry/return breakpoints observe unmodified Green, libm and eddy matrix instructions. No numerical or runtime functions are replaced. Retained words come directly from ST0 at each actual return address; finish/unwind inference is not used.",
                gdb_commands=COMMANDS,cases=records)
    (ROOT/"tests/fixtures/eddy_original.json").write_text(json.dumps(result,separators=(",",":"),allow_nan=False)+"\n")


if __name__=="__main__":main()
