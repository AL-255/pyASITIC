"""Allocator observations including independently read Linux layout inputs."""
import hashlib
import capture_allocator_original as arena

OBSERVER=arena.OBSERVER+r'''
import os,re
_arena_snapshot=allocator_snapshot
def allocator_snapshot(label):
 _arena_snapshot(label)
 state=allocator_states[-1];pid=gdb.selected_inferior().pid
 personality=int(open('/proc/%d/personality'%pid).read().strip(),16)
 limits=open('/proc/%d/limits'%pid).read();stack=next(line.split()[3]for line in limits.splitlines()if line.startswith('Max stack size'))
 guard=re.search(r'(?:^|\s)stack_guard_gap=(\d+)(?:\s|$)',open('/proc/cmdline').read())
 state['mapping_policy']=dict(personality=personality,stack_limit=None if stack=='unlimited'else int(stack),stack_guard_gap_pages=int(guard[1])if guard else 256,guard_gap_source='boot-command-line'if guard else'kernel-default',legacy_va_layout=int(open('/proc/sys/vm/legacy_va_layout').read()),mmap_min_addr=int(open('/proc/sys/vm/mmap_min_addr').read()),page_size=os.sysconf('SC_PAGE_SIZE'),kernel_release=os.uname().release,transparent_hugepage=open('/sys/kernel/mm/transparent_hugepage/enabled').read().strip())
 live={}
 for event in events:
  if event['kind']=='allocate':live[event['address']]=event['request']
  elif event['kind']=='free':live.pop(event['address'],None)
 mapped=[]
 for address,request in live.items():
  previous,word=struct.unpack('<II',mem(address-8,8))
  if word&2:mapped.append(dict(address=address-8,prev_size=previous,size_word=word,request=request))
 state['mapped_chunks']=sorted(mapped,key=lambda c:c['address'])
'''


if __name__=='__main__':
    parent=arena.lifetime.ROOT/'tests/fixtures/allocator_state_original.json.gz'
    arena.main(observer=OBSERVER,fixture_name='allocator_mappings_original.json.gz',extra_metadata=dict(mapping_parent_sha256=hashlib.sha256(parent.read_bytes()).hexdigest()))
