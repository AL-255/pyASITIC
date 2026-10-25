"""Real printf on the continuing source, with only earlier table/control inputs."""
import argparse,gzip,hashlib,json,sys
from pathlib import Path
import capture_flush_transition_original as parent
import capture_printf_format_original as formatter
from capture_poll_storage_original import integer_cpu
from capture_getline_bytes_original import integer_cpu as byte_cpu

ROOT=Path(__file__).resolve().parents[1]
ELF='format_section_cache={}\ndef format_elf_data'+formatter.EXTRA.split('def format_elf_data',1)[1].split('def format_inputs',1)[0]
OBSERVER=parent.OBSERVER+'\n'+ELF+r'''
printf_transition_calls=[]
class PrintfTransitionReturn(gdb.Breakpoint):
 def __init__(self,pc,item):self.item=item;super().__init__('*'+hex(pc),internal=True)
 def stop(self):
  if 'after'in self.item or reg('esp')!=self.item['before']['esp']+4:return False
  self.item['after']=registers();self.enabled=False;return False
class PrintfTransitionCall(gdb.Breakpoint):
 def __init__(self,pc,kind):self.kind=kind;super().__init__('*'+hex(pc),internal=True)
 def stop(self):
  if not transition_active:return False
  pc=u32(reg('esp'))
  if pc not in(0x804c012,0x804be86,0x804bea3):return False
  item=dict(kind=self.kind,before=registers());printf_transition_calls.append(item);PrintfTransitionReturn(pc,item);return False
_printf_transition_snapshot=allocator_snapshot
def allocator_snapshot(label):
 _printf_transition_snapshot(label)
 state=allocator_states[-1];state['cache_node_targets']=[]
 for p in sorted(set(p for chain in state['tcache']for p in chain)):
  if any(r['address']<=p and p+8<=r['address']+len(r['data'])//2 for r in state['memory_regions']):continue
  state['cache_node_targets'].append(dict(address=p,data=mem(p,8).hex()))
 if label=='driver_entry':
  environment();ctx=transition_inputs['loader_context'];stdio=transition_inputs['stdio_context'];stdio['printf_abi']=True;elf=[]
  def include(p,n):
   if any(r['address']==p and r['size']==n for r in stdio['regions']):return
   ctx['regions'].append(dict(address=p,data=mem(p,n).hex()));stdio['regions'].append(dict(address=p,size=n))
  for item in ctx['maps']:
   if item['address']!=ctx['main_map']and not item['name'].endswith(('/libc.so.6','/libstdc++-libc6.1-1.so.2')):continue
   path=item['name']or'/proc/%d/exe'%gdb.selected_inferior().pid;data=format_elf_data(path,u32(item['address']))
   data=dict(data,sections=[s for s in data['sections']if s['name']in('.rodata','.data.rel.ro')]);elf.append(data)
   for section in data['sections']:include(section['address'],section['size'])
  base=u32(next(x['address']for x in ctx['maps']if x['name'].endswith('/libc.so.6')));got=base+0x22fe34
  for offset in (0xa0,0xb8,0x16c,0x19ec,0x19f8,0x1a04):include(got+offset,4)
  include(u32(got+0xb8),4);include((u32(ctx['tls_base'])+u32(got+0xa0))&0xffffffff,4)
  stdio['printf_elf']=elf
  PrintfTransitionCall(base+0x57db0,'printf');PrintfTransitionCall(base+0x57670,'fprintf')
'''


def commands(directory,observer=OBSERVER):
    return parent.inputs.stdio.loader.transition.commands(directory,observer).replace('result=dict(transition_inputs=', 'result=dict(printf_transition_calls=printf_transition_calls,transition_inputs=')


def jobs(label=None):
    for job in parent.jobs():
        if label is not None and job['label']!=label:continue
        job['parent']=ROOT/'tests/fixtures/flush_transition_original.json.gz';yield job


def project_regions(fixture):
    """Factor every complete later region, verifying bytes before discarding it."""
    from audit_loader_lookup_original import data
    blobs=fixture.setdefault('loader_regions',{});checked=total=0
    for case in fixture['cases']:
        for point in case['transition_points']+case['transition_states']:
            for r in point.get('regions',point.get('component_regions',[])):
                if 'data'not in r:continue
                before=dict(r);raw=bytes.fromhex(r.pop('data'));key=hashlib.sha256(raw).hexdigest();encoded=raw.hex()
                if key in blobs and blobs[key]!=encoded:raise ValueError('Conflicting continuing region content')
                blobs[key]=encoded;r.update(size=len(raw),sha256=key)
                if dict(address=r['address'],data=data(fixture,r).hex())!=before:raise ValueError('Continuing region conversion changed a native target')
                checked+=1;total+=len(raw)
    fixture['printf_transition_projection']=dict(regions_checked=checked,bytes_checked=total,reference='Every complete later region expands identically before its dense bytes are discarded. All ordered owners and every byte remain assertions; only SHA256 content repetition is factored.')
    return fixture


def main():
    p=argparse.ArgumentParser(add_help=False);p.add_argument('--cc',default='cc');p.add_argument('--output',type=Path,default=ROOT/'tests/fixtures/printf_transition_original.json.gz');p.add_argument('--pilot-label');own,remaining=p.parse_known_args();sys.argv=[sys.argv[0],*remaining];cpu=integer_cpu(own.cc);byte=byte_cpu(own.cc);target=own.output.resolve()
    if own.pilot_label and target==ROOT/'tests/fixtures/printf_transition_original.json.gz':raise ValueError('A pilot requires its own explicit output path')
    parent.inputs.stdio.loader.transition.node.console.driver.main(fixture_name=str(target),parent_name='flush_transition_original.json.gz',job_factory=lambda:jobs(own.pilot_label),observer=OBSERVER,command_builder=commands,
        state_fields=('allocator_states','post_states','transition_states'),buffer_fields=('post_buffers','transition_buffers'),
        extra_metadata=dict(integer_cpu=cpu,byte_cpu=byte,printf_transition_provenance=dict(observer=OBSERVER,parent_sha256=hashlib.sha256((ROOT/'tests/fixtures/flush_transition_original.json.gz').read_bytes()).hexdigest(),pilot_label=own.pilot_label,reference='All unchanged jobs cold/warm. Only earlier first-driver read-only ELF tables and named printf GOT/TLS controls supplement previous inputs. Every new owned region remains a complete later assertion. REPL printf frames, public entries, formatter/FILE helpers and flush operate on the same produced heap/memory; no per-call snapshot or later native target initializes continuation. String-only calls preserve opaque FP state without inventing bytes; floating instructions still require actual FP input. No original request, owner, target, outcome, instruction, memory, register, CPU affinity, allocation, result or signal is replaced.')))
    f=json.loads(gzip.decompress(target.read_bytes()));blobs={}
    for case in f['cases']:
        stdio=case['transition_inputs']['stdio_context'];stdio['sar31_af']=cpu['sar31_af'];stdio['input_abi']['shr1_af']=byte['shr1_af']
        for r in case['transition_inputs']['loader_context']['regions']:
            raw=bytes.fromhex(r.pop('data'));key=hashlib.sha256(raw).hexdigest();blobs[key]=raw.hex();r.update(size=len(raw),sha256=key)
    f['loader_regions']=blobs
    project_regions(f)
    with gzip.GzipFile(str(target),'wb',mtime=0)as stream:stream.write((json.dumps(f,separators=(',',':'))+'\n').encode())


if __name__=='__main__':main()
