"""Read-only helper traces for the four differing complete-command pairs."""
import argparse,hashlib,json,os,re,subprocess,tempfile
from pathlib import Path
from capture_original_symmetric import ORIGINAL_SHA256,LEGACY_SHA256
ROOT=Path(__file__).resolve().parents[1]
COMMANDS=r'''
set pagination off
set confirm off
set environment TERM dumb
set environment INPUTRC /dev/null
break *0x8061110
run -g -t process.tek -x input.asit < answers.txt
python
import gdb,struct,json
target=TARGET;ordinal=0
def mem(a,n):return bytes(gdb.selected_inferior().read_memory(a,n))
def reg(k):return int(gdb.parse_and_eval('$'+k))&0xffffffff
def u32(a):return struct.unpack('<I',mem(a,4))[0]
def raw(i=0):return bytes(gdb.parse_and_eval('$st'+str(i)).bytes).hex()
entry=gdb.breakpoints()[0]
while ordinal<target:
 gdb.execute('continue',to_string=True);assert reg('pc')==0x8061110;ordinal+=1
esp=reg('esp');finish=u32(esp);out=u32(esp+12);entry.enabled=False
result=dict(input_bits=mem(u32(esp+4),64).hex()+mem(u32(esp+8),64).hex(),ordinal=ordinal,events=[],control_before=reg('fctrl'))
entries={0x8062ebc:'canonical',0x8062230:'parallel',0x8064308:'self',0x8063ca0:'separation',0x80b3c94:'crosslog',0x8061b84:'planar',0x80613bc:'spatial'}
for a in entries:gdb.Breakpoint('*'+hex(a),internal=True)
gdb.Breakpoint('*'+hex(finish),temporary=True,internal=True)
for a in(0x806433f,0x8064341,0x806434f):gdb.Breakpoint('*'+hex(a),internal=True)
pending={};stack=[]
math_points=MATHPOINTS
for address in math_points:gdb.Breakpoint('*'+hex(address),internal=True)
gdb.execute('continue',to_string=True)
while reg('pc')!=finish:
 pc=reg('pc');esp=reg('esp')
 if pc in entries:
  kind=entries[pc];ret=u32(esp);item=dict(kind=kind,control_before=reg('fctrl'))
  if kind in('canonical','parallel','planar','spatial'):
   a,b=u32(esp+4),u32(esp+8);item.update(first_bits=mem(a,64).hex(),second_bits=mem(b,64).hex());data=(a,b)if kind=='canonical'else(u32(esp+12),)
   if kind=='parallel':item['separation_bits']=mem(esp+16,8).hex()
  else:
   count=6 if kind=='separation'else 2;item['input_bits']=mem(esp+4,8*count).hex();data=()
  assert ret not in pending
  pending[ret]=(len(result['events']),data);stack.append(len(result['events']));result['events'].append(item);gdb.Breakpoint('*'+hex(ret),temporary=True,internal=True)
 elif pc in pending:
  index,data=pending.pop(pc);assert stack.pop()==index;item=result['events'][index];item['control_after']=reg('fctrl')
  if item['kind']=='canonical':item.update(first_output_bits=mem(data[0],64).hex(),second_output_bits=mem(data[1],64).hex(),status=reg('eax'))
  elif item['kind']in('parallel','planar','spatial'):item.update(output_bits=mem(data[0],8).hex(),status=reg('eax')if item['kind']=='parallel'else None)
  else:item['extended_bits']=raw()
 else:
  assert stack;item=result['events'][stack[-1]]
  if pc in math_points:
   for op,when in math_points[pc]:
    if when=='before':item.setdefault('math',[]).append(dict(operation=op,address=hex(pc),input_words=[raw(0)]+([raw(1)]if op in('fyl2x','fyl2xp1','fpatan','fscale')else[])))
    else:item['math'][-1]['output_words']=raw()
  if pc in(0x806433f,0x8064341,0x806434f):
   assert item['kind']=='self';key={0x806433f:'log_argument',0x8064341:'log_return',0x806434f:'term'}[pc];item[key]=raw()
 gdb.execute('continue',to_string=True)
assert not pending and not stack
result.update(output_bits=mem(out,8).hex(),control_after=reg('fctrl'))
open('boundaries.json','w').write(json.dumps(result))
end
kill
quit
'''


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--reference',type=Path,required=True);parser.add_argument('--library-path',required=True);args=parser.parse_args();ref=args.reference.resolve();original=ref/'run/asitic.linux.2.2'
    for path,want in[(original,ORIGINAL_SHA256),(ref/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so',LEGACY_SHA256)]:
        if hashlib.sha256(path.read_bytes()).hexdigest()!=want:raise ValueError('Unexpected original checksum')
    parent=ROOT/'tests/fixtures/conductor_metrics_original.json';f=json.loads(parent.read_text());cases=[]
    disassembly=subprocess.check_output(['objdump','-d',str(original)],text=True);points={}
    for match in re.finditer(r'^\s*([0-9a-f]+):\s+[0-9a-f ]+\s+(fyl2xp?1?|fpatan|fcos|f2xm1|fscale|frndint)\b',disassembly,re.M):
        address=int(match[1],16)
        if any(lo<=address<hi for lo,hi in[(0x8061b84,0x8062230),(0x8063ca0,0x8064357),(0x80b3c94,0x80b3d7d)]):
            points.setdefault(address,[]).append((match[2],'before'));points.setdefault(address+2,[]).append((match[2],'after'))
    with tempfile.TemporaryDirectory(prefix='pyasitic-mutual-boundaries-')as d:
        for index,pair in[(22,772),(46,79),(52,370),(54,805)]:
            c=f['cases'][index];target=c['inductance'][0]['pairs'][pair];work=Path(d)/str(index);work.mkdir()
            script=c['script'].split('\nQ ',1)[0]+'\n'
            for name,value in [('process.tek',c['technology']),('input.asit',script),('answers.txt',c['stdin']),('capture.gdb',COMMANDS.replace('TARGET',str(pair)).replace('MATHPOINTS',repr(points))) ]:(work/name).write_text(value)
            run=subprocess.run(['gdb','-q','-batch','-x','capture.gdb',str(original)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=args.library_path),capture_output=True,text=True,start_new_session=True,timeout=120)
            if run.returncode or not(work/'boundaries.json').exists():raise RuntimeError(f'Original pair trace {index}/{pair}: '+run.stdout[-2000:]+run.stderr[-1500:])
            observed=json.loads((work/'boundaries.json').read_text());assert observed['output_bits']==target['value_bits'];assert observed['control_before']==observed['control_after']==0x37f
            cases.append(dict(parent_case=index,parent_pair=pair,label=c['label'],script=script,stdin=c['stdin'],stdout=run.stdout,**observed));print(f'Original pair trace {index}/{pair}: {len(observed["events"])} helper calls',flush=True)
    result=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,parent_sha256=hashlib.sha256(parent.read_bytes()).hexdigest(),reference='Data-only static entry/instruction and actual-return observations of the original complete INDUCTANCE commands at all four differing mutual pairs. No numerical code, inputs, descriptors, allocator or runtime imports changed. Observation stops after the selected pair returns, then terminates the inferior; this does not claim native termination.',gdb_commands=COMMANDS,math_instruction_points={hex(a):p for a,p in points.items()},cases=cases)
    (ROOT/'tests/fixtures/mutual_command_traces_original.json').write_text(json.dumps(result,separators=(',',':'),allow_nan=False)+'\n')


if __name__=='__main__':main()
