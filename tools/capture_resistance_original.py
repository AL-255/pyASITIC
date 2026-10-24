"""Capture unchanged original RESIS/RESISHF inputs and retained returns."""
import argparse,hashlib,json,os
from pathlib import Path
import subprocess,tempfile
from capture_original_symmetric import ORIGINAL_SHA256,LEGACY_SHA256

ROOT=Path(__file__).resolve().parents[1]
PARENTS=('analysis','square_sessions_original','ring_sessions_original','polygon_sessions_original','gf180_network')
COMMANDS=r'''
set pagination off
set confirm off
set environment TERM dumb
set environment INPUTRC /dev/null
python
import gdb,struct,json
entries={0x804eedc:'dc',0x804d70c:'hf'}
for address in entries:gdb.Breakpoint('*'+hex(address),internal=True)
end
run -g -t process.tek -x input.asit < answers.txt
python
def memory(a,n):return bytes(gdb.selected_inferior().read_memory(a,n))
def u32(a):return struct.unpack('<I',memory(a,4))[0]
def i32(a):return struct.unpack('<i',memory(a,4))[0]
def f64(a):return struct.unpack('<d',memory(a,8))[0]
def segments(shape):
 out=[];a=u32(shape+0xa8);count=i32(0x80d8904);metals=u32(0x80d8910);vias=u32(0x80d8914)
 while a:
  assert len(out)<20000
  metal=i32(a+0xdc);r=dict(endpoints=list(struct.unpack('<6d',memory(a,48))),width=f64(a+0xcc),metal=metal,via=metal>=count)
  if metal<count:r.update(thickness=f64(metals+236*metal+0xb0),resistance=f64(metals+236*metal+0xb8))
  else:r.update(resistance=f64(vias+240*(metal-count)+0xc0),nx=i32(a+0xe0),ny=i32(a+0xe4))
  out.append(r);a=u32(a+0xec)
 return out
before=int(gdb.parse_and_eval('$fctrl'));events=[];pending={};inputs=None
while len(events)<8:
 pc=int(gdb.parse_and_eval('$pc'))
 if pc in entries:
  esp=int(gdb.parse_and_eval('$esp'));ret=u32(esp);shape=u32(esp+4);actual=segments(shape)
  if inputs is None:inputs=actual
  else:assert actual==inputs
  event=dict(operation=entries[pc])
  if event['operation']=='hf':event['frequency_hz']=f64(esp+8)
  assert ret not in pending;pending[ret]=event;gdb.Breakpoint('*'+hex(ret),temporary=True,internal=True)
 else:
  event=pending.pop(pc);event['extended_bits']=bytes(gdb.parse_and_eval('$st0').bytes).hex();events.append(event)
 if len(events)<8:gdb.execute('continue',to_string=True)
assert not pending
open('resistance.json','w').write(json.dumps(dict(inputs=inputs,events=events,control_before=before,control_after=int(gdb.parse_and_eval('$fctrl')))))
end
kill
quit
'''


def jobs(technology):
    for parent in PARENTS:
        for i,c in enumerate(json.loads((ROOT/f'tests/fixtures/{parent}.json').read_text())['cases']):
            request=c.get('request',c);kind=request['kind'];p=dict(request['parameters'])
            stop='BSAVE'if parent=='analysis'else'PI2'if parent.endswith('sessions_original')else'PI2'
            script=c['script'].split(stop,1)[0]
            if parent=='gf180_network':script=c['script'].split('PI2',1)[0]
            native=(kind in('square','ring','polygon','wire')and parent=='analysis')or(kind=='wire'and parent=='gf180_network')
            if parent=='analysis':
                p.setdefault('name','A')
                if kind=='wire':
                    fields=dict(part.split('=',1)for part in next(line for line in script.splitlines()if line.startswith('WIRE ')).split(' ',1)[1].split(':'))
                    for source,key in(('XORG','x'),('YORG','y')):
                        if source in fields:p.setdefault(key,float(fields[source]))
            if parent=='analysis'and kind=='square':
                # The typed parent fixture omitted explicit EXIT=-1 because
                # it was formerly that API's default. Keyword mode has a
                # different default, so preserve the actual script argument.
                p=dict(p);p.setdefault('exit_metal','-1')
            public=dict(kind=kind,parameters=p,technology=request.get('technology',technology),native_keyword=native or request.get('native_keyword',False))
            yield dict(label=f'{parent}/{i}',technology=request.get('technology',technology),creation=script,stdin=c.get('stdin','quit\n'),public=public)
    for i,width in enumerate((.5,1,2.5,20,100,.1)):
        metal='M'+str(i+1 if i<5 else 5);p=dict(name='A',length=80,width=width,metal=metal,x=10,y=20)
        script=f'WIRE NAME=A:LEN=80:WID={width:.17g}:METAL={metal}:XORG=10:YORG=20\n'
        yield dict(label=f'wire/{metal}/{width}',technology=technology,creation=script,stdin='quit\n',public=dict(kind='wire',parameters=p,technology=technology,native_keyword=True))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--reference',type=Path,required=True);parser.add_argument('--library-path',required=True)
    args=parser.parse_args();reference=args.reference.resolve();original=reference/'run/asitic.linux.2.2'
    for path,want in((original,ORIGINAL_SHA256),(reference/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so',LEGACY_SHA256)):
        if hashlib.sha256(path.read_bytes()).hexdigest()!=want:raise ValueError(f'Unexpected oracle checksum: {path}')
    technology=(reference/'run/tek/CMOS.tek').read_text();records=[]
    frequencies=(.001,.1234567,1,10,100,1000,1000000)
    with tempfile.TemporaryDirectory(prefix='pyasitic-original-resistance-')as directory:
        for i,c in enumerate(jobs(technology)):
            script=c['creation']+'RESIS A\n'+''.join(f'RESISHF A {f:.17g}\n'for f in frequencies)
            work=Path(directory)/str(i);work.mkdir()
            for name,value in(('process.tek',c['technology']),('input.asit',script),('answers.txt',c['stdin']),('capture.gdb',COMMANDS)):(work/name).write_text(value)
            run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=args.library_path),capture_output=True,text=True,start_new_session=True,timeout=120)
            if run.returncode or not(work/'resistance.json').exists():raise RuntimeError(f'Original resistance capture failed {i}/{c["label"]}: {run.stdout[-2000:]} {run.stderr[-1000:]}')
            item=json.loads((work/'resistance.json').read_text())
            if item['control_before']!=0x37f or item['control_after']!=0x37f:raise RuntimeError('Unexpected original control word')
            item.update(c,script=script,frequency_ghz=frequencies);records.append(item);print(f'Original resistance {i}: {len(item["inputs"])} segments / {c["label"]}',flush=True)
    output=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,parents={name:hashlib.sha256((ROOT/f'tests/fixtures/{name}.json').read_bytes()).hexdigest()for name in PARENTS},gdb_commands=COMMANDS,
                reference='Unchanged original CLI RESIS (0x0804eedc) and RESISHF (0x0804d70c) entry/actual-return observers. Every consumed endpoint, width, sheet/via resistance, conductor thickness and defined via count is captured, with actual parsed Hz and raw ST0 return. No function replacements or numerical input overrides. Public requests also record existing creator modes; unported creator inputs remain an independent parity audit.',cases=records)
    (ROOT/'tests/fixtures/resistance_original.json').write_text(json.dumps(output,separators=(',',':'),allow_nan=False)+'\n')


if __name__=='__main__':main()
