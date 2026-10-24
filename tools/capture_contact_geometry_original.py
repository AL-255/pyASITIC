"""Observe original contact-builder inputs, native counts and integer bounds."""
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
break *0x8053580
run -g -t process.tek -x input.asit < answers.txt
python
import gdb,struct,json
def memory(a,n):return bytes(gdb.selected_inferior().read_memory(a,n))
def u32(a):return struct.unpack('<I',memory(a,4))[0]
def i32(a):return struct.unpack('<i',memory(a,4))[0]
def f64(a):return struct.unpack('<d',memory(a,8))[0]
def segment(a):return dict(points=[list(struct.unpack('<3d',memory(a+k,24)))for k in(0,24,0x44,0x5c,0x88,0xa0)],width=f64(a+0xcc),primary_width=f64(a+0x30),metal=i32(a+0xdc),nx=i32(a+0xe0),ny=i32(a+0xe4))
esp=int(gdb.parse_and_eval('$esp'));finish=u32(esp);shapes=[u32(esp+4),u32(esp+8)]
origins={}
for shape in shapes:
 origin=[f64(shape+0x54),f64(shape+0x5c)];s=u32(shape+0xa8)
 while s:
  origins[s]=origin;extra=u32(s+0xe8)
  while extra:origins[extra]=origin;extra=u32(extra+0xe8)
  s=u32(s+0xec)
options=dict(nx=i32(0x80ce990),ny=i32(0x80ce994),width=f64(0x80ce980),height=f64(0x80ce988),length_step=f64(0x80ce598),width_step=f64(0x80ce5a0),metal_count=i32(0x80d8904))
before=int(gdb.parse_and_eval('$fctrl'));records=[];pending={};build=0x8053a1c
gdb.Breakpoint('*'+hex(build),internal=True);gdb.Breakpoint('*'+hex(finish),temporary=True,internal=True)
gdb.execute('continue',to_string=True)
while int(gdb.parse_and_eval('$pc'))!=finish:
 pc=int(gdb.parse_and_eval('$pc'))
 if pc==build:
  esp=int(gdb.parse_and_eval('$esp'));ret=u32(esp);group=u32(esp+4);s=u32(esp+8);old=u32(group+128)
  assert s in origins and ret not in pending
  item=dict(segment=segment(s),origin=origins[s],counts=[i32(group+112),i32(group+116)],translated=[f64(group+k)for k in(80,88,96,104)])
  pending[ret]=(group,old,item);gdb.Breakpoint('*'+hex(ret),temporary=True,internal=True)
 else:
  assert pc in pending,(hex(pc),pending)
  group,old,item=pending.pop(pc);contact=u32(group+128);contacts=[]
  while contact!=old:
   assert contact and len(contacts)<1024
   contacts.append(dict(bounds_bits=memory(contact,32).hex(),indices=list(struct.unpack('<5i',memory(contact+32,20)))))
   contact=u32(contact+56)
  item['contacts']=contacts;records.append(item)
 gdb.execute('continue',to_string=True)
assert not pending
result=dict(options=options,records=records,success=bool(int(gdb.parse_and_eval('$eax'))&255),control_before=before,control_after=int(gdb.parse_and_eval('$fctrl')))
open('contacts.json','w').write(json.dumps(result))
end
kill
quit
'''


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',type=Path,required=True);parser.add_argument('--library-path',required=True)
    args=parser.parse_args();reference=args.reference.resolve()
    original=reference/'run/asitic.linux.2.2';legacy=reference/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so'
    for path,want in((original,ORIGINAL_SHA256),(legacy,LEGACY_SHA256)):
        if hashlib.sha256(path.read_bytes()).hexdigest()!=want:raise ValueError(f'Unexpected oracle checksum: {path}')
    parents={};jobs=[]
    for name in('pi_sessions_original','ring_sessions_original','square_sessions_original'):
        path=ROOT/f'tests/fixtures/{name}.json';fixture=json.loads(path.read_text());parents[name]=hashlib.sha256(path.read_bytes()).hexdigest()
        for i,c in enumerate(fixture['cases']):jobs.append((name,i,c))
    for index,y in enumerate((20,20.125)):
        c=dict(request=dict(technology=(reference/'run/tek/CMOS.tek').read_text()),script='CELL 1000 1000 1000\nCCELL 1000 1000\nWIRE\nPI2 A 1\n',stdin=f'A\n40\n.01\nM5\n1\n10 {y}\n0\nquit\n')
        jobs.append(('interactive_thin_wire',index,c))
    records=[]
    with tempfile.TemporaryDirectory(prefix='pyasitic-original-contact-geometry-')as directory:
        for i,(parent,index,c)in enumerate(jobs):
            work=Path(directory)/str(i);work.mkdir()
            for name,value in(('process.tek',c['request']['technology']),('input.asit',c['script']),('answers.txt',c.get('stdin','quit\n')),('capture.gdb',COMMANDS)):(work/name).write_text(value)
            run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=args.library_path),capture_output=True,text=True,start_new_session=True,timeout=120)
            if run.returncode or not(work/'contacts.json').exists():raise RuntimeError(f'Original contact capture failed {parent}/{index}: {run.stdout[-1600:]} {run.stderr[-1000:]}')
            item=json.loads((work/'contacts.json').read_text())
            if item['control_before']!=0x37f or item['control_after']!=0x37f:raise RuntimeError('Unexpected original control word')
            item.update(parent=parent,index=index);records.append(item);print(f'Original contact setup {parent}/{index}: {len(item["records"])} builders',flush=True)
    output=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,parents=parents,gdb_commands=COMMANDS,
                reference='Unchanged original prepare_potential_contacts 0x08053580 and build_potential_contacts 0x08053a1c. Data-only entry/return observers capture actual options, every incoming segment/origin, prepared group counts, translated endpoints, physical contact bounds and consumed integer/metal records. Incoming contact.index history and linked addresses are excluded.',cases=records)
    (ROOT/'tests/fixtures/contact_geometry_original.json').write_text(json.dumps(output,separators=(',',':'),allow_nan=False)+'\n')


if __name__=='__main__':main()
