"""Read-only native parser callers and every catalog comparison argument."""
import argparse,hashlib,sys
from pathlib import Path
import capture_dispatch_storage_original as parent

ROOT=Path(__file__).resolve().parents[1]
old="context['characters']=dict("
assert parent.OBSERVER.count(old)==1
OBSERVER=parent.OBSERVER.replace(old,"context['regions'].append(dict(address=0x80cbac0,data=mem(0x80cbac0,4).hex()))\n "+old)+r'''
class ParserBoundary(gdb.Breakpoint):
 def __init__(self,pc,kind,caller=None):self.kind=kind;self.caller=caller;super().__init__('*'+hex(pc),internal=True)
 def stop(self):
  if dispatch_current is None or'parse'not in dispatch_current or self.kind in dispatch_current:return False
  if self.caller is not None and u32(reg('esp'))!=self.caller:return False
  dispatch_current[self.kind]=dispatch_state(dispatch_current['entry']);return False
ParserBoundary(0x808769c,'tokenizer',0x8086fd9);ParserBoundary(0x8086fd9,'tokenized')
ParserBoundary(0x805bcc0,'catalog',0x8086ff6);ParserBoundary(0x805bcd6,'comparison_ready')
comparison_pending={}
class ComparisonAfter(gdb.Breakpoint):
 def __init__(self,pc):self.pc=pc;super().__init__('*'+hex(pc),internal=True)
 def stop(self):
  item=comparison_pending.pop(self.pc,None)
  if item is not None:
   if reg('esp')!=item['before']['registers']['esp']-4:raise RuntimeError('Unexpected native comparison argument stack')
   item['after']=dispatch_state(dispatch_current['entry'])
  return False
class ComparisonBefore(gdb.Breakpoint):
 def __init__(self,pc):self.pc=pc;super().__init__('*'+hex(pc),internal=True)
 def stop(self):
  if dispatch_current is None or'catalog'not in dispatch_current:return False
  item=dict(before=dispatch_state(dispatch_current['entry']));dispatch_current.setdefault('comparisons',[]).append(item)
  if self.pc+1 in comparison_pending:raise RuntimeError('Nested comparison argument observation')
  comparison_pending[self.pc+1]=item;return False
for pc in(0x805bcd6,0x805bce9,0x805bcfc,0x805bd0f):ComparisonBefore(pc);ComparisonAfter(pc+1)
'''


def commands(directory):return parent.commands(directory).replace(parent.OBSERVER,OBSERVER)


def jobs():
    for job in parent.jobs():
        job['parent']=ROOT/'tests/fixtures/dispatch_storage_original.json.gz';yield job


def project(fixture):
    """Factor complete owners by pages, checking bytes before dropping them."""
    pages=fixture.setdefault('loader_pages',{});regions=total=0
    for case in fixture['cases']:
        for call in case['dispatch_calls']:
            points=[point for key,point in call.items()if key!='comparisons']
            points +=[point for pair in call.get('comparisons',())for point in pair.values()]
            for point in points:
                for r in point['regions']:
                    raw=bytes.fromhex(r.pop('data'));keys=[]
                    for offset in range(0,len(raw),4096):
                        block=raw[offset:offset+4096];key=hashlib.sha256(block).hexdigest();value=block.hex()
                        if key in pages and pages[key]!=value:raise ValueError('Conflicting parser page')
                        pages[key]=value;keys.append(key)
                    if b''.join(bytes.fromhex(pages[key])for key in keys)!=raw:raise ValueError('Parser region conversion changed bytes')
                    r.update(size=len(raw),sha256=hashlib.sha256(raw).hexdigest(),pages=keys);regions+=1;total+=len(raw)
    fixture['parser_projection']=dict(regions_checked=regions,bytes_checked=total,reference='Every complete ordered region and every byte retained. Only repeated page content is factored by SHA256; no owner, comparison or outcome is removed.')
    return factor_owners(fixture)


def points(call):
    yield from(point for key,point in call.items()if key!='comparisons')
    yield from(point for pair in call.get('comparisons',())for point in pair.values())


def expand_point(fixture,point):
    if 'regions'in point:return point
    base=fixture['parser_region_bases'][point['regions_base']];changes=dict(point['region_changes'])
    if len(changes)!=len(point['region_changes']):raise ValueError('Repeated parser owner override')
    if any(not isinstance(i,int)or not 0<=i<len(base)for i in changes):raise ValueError('Invalid parser owner override')
    return dict(point,regions=[changes.get(i,r)for i,r in enumerate(base)])


def factor_owners(fixture):
    """Share complete owner lists, asserting lossless expansion at every state."""
    import json
    bases=fixture.setdefault('parser_region_bases',{});checked=owners=0
    for case in fixture['cases']:
        for call in case['dispatch_calls']:
            base=call['entry']['regions'];key=hashlib.sha256(json.dumps(base,separators=(',',':')).encode()).hexdigest();bases[key]=base
            layout=[(r['address'],r['size'])for r in base]
            for point in points(call):
                regions=point.pop('regions')
                if[(r['address'],r['size'])for r in regions]!=layout:raise ValueError('Parser region owner layout changed')
                point.update(regions_base=key,region_changes=[(i,r)for i,r in enumerate(regions)if r!=base[i]])
                if expand_point(fixture,point)['regions']!=regions:raise ValueError('Parser owner conversion changed a region')
                checked+=1;owners+=len(regions)
    fixture['parser_owners_projection']=dict(points_checked=checked,owners_checked=owners,reference='Every ordered owner expands identically at every complete state. Shared base records and complete changed records retain all region contents; no region or target is excluded.')
    return fixture


def main():
    import gzip,json
    p=argparse.ArgumentParser(add_help=False);p.add_argument('--debug-directory',type=Path,required=True);p.add_argument('--output',type=Path,default=ROOT/'tests/fixtures/parser_callers_original.json.gz');own,remaining=p.parse_known_args();sys.argv=[sys.argv[0],*remaining]
    parent.transition.plt.lookup.install.signals.lifetime.main(commands=commands(own.debug_directory),fixture_name=str(own.output.resolve()),job_factory=jobs,
        extra_metadata=dict(parser_callers_provenance=dict(observer=OBSERVER,reference='All unchanged 134 histories and original plain/observed outcomes retained. Capture parser entry, tokenizer entry/return, catalog entry, first comparison-ready point, and every executed argument PUSH before/after at all four alias sites. Complete earlier stacks, ELF/locale/TLS, GP/XSAVE and catalog head word are independent operation inputs. All later regions/registers/FP remain assertions; no native instruction, memory, register, returned child value, signal, allocation, CPU affinity or outcome is replaced. No per-call snapshot initializes continuing driver replay.')))
    path=own.output;fixture=project(json.loads(gzip.decompress(path.read_bytes())))
    with gzip.GzipFile(str(path),'wb',mtime=0)as stream:stream.write((json.dumps(fixture,separators=(',',':'))+'\n').encode())


if __name__=='__main__':main()
