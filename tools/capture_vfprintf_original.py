"""Original vfprintf caller, formatter boundaries, and nested FILE helpers."""
import argparse,sys
from pathlib import Path
import capture_printf_file_original as parent
import capture_printf_buffer_original as buffer
import capture_trailing_via_heap_original as lifetime
from printf_archive import read_fixture,split_archive

ROOT=Path(__file__).resolve().parents[1]
OBSERVER=parent.OBSERVER.replace(
 "s=reg('esp');buffer=u32(s+4);file=u32(s+8)if kind=='init'else u32(buffer+24)",
 "s=reg('esp');file=u32(s+4);buffer=file;format=u32(s+8)").replace(
 "(got+0x1a30,4),(got+0x1c4,4)",
 "(got+0x11c,4),(got+0x15c,4),(got+0x1a30,4),(got+0x1c4,4)").replace(
 "ctx['regions']+=[dict(address=p,data=mem(p,n).hex())for p,n in controls if p and n]",
 "ctx['regions']+=[dict(address=p,data=mem(p,n).hex())for p,n in controls if p and n]\n if format:ctx['regions'].append(dict(address=format,data=(format_bytes(format)+b'\\0').hex()))").replace(
 "for off,kind in ((0x586c0,'init'),(0x58710,'done')):FileEntry(base+off,kind)",
 "FileEntry(base+0x62110,'vfprintf');FormatterEntry(base+0x60530)").replace(
 "((0x58570,'switch')", "((0x586c0,'init'),(0x58710,'done'),(0x58570,'switch')")
OBSERVER+=r'''
def format_bytes(p):return gdb.Value(p).cast(gdb.lookup_type('char').pointer()).string(encoding='latin1').encode('latin1')
class FormatterReturn(gdb.Breakpoint):
 def __init__(self,pc,item):self.item=item;super().__init__('*'+hex(pc),internal=True)
 def stop(self):
  if 'after'in self.item['formatter']or reg('esp')!=self.item['formatter']['before']['registers']['esp']+4:return False
  self.item['formatter']['after']=file_state(self.item['before']);self.item['formatter']['children_end']=len(self.item['children']);self.enabled=False;return False
class FormatterEntry(gdb.Breakpoint):
 def __init__(self,pc):super().__init__('*'+hex(pc),internal=True)
 def stop(self):
  if file_current is None:return False
  if 'formatter'in file_current:raise RuntimeError('Repeated/nested formatter needs its explicit observer')
  file_current['formatter']=dict(before=file_state(file_current['before']),children_start=len(file_current['children']));FormatterReturn(u32(reg('esp')),file_current);return False
'''


def commands(directory):return parent.commands(directory).replace(parent.OBSERVER,OBSERVER)


def jobs():
    for job in parent.jobs():
        job['parent']=ROOT/'tests/fixtures/printf_file_original.manifest.json';yield job


class Projection(buffer.PrintfProjection):
    def case(self,case):
        # The existing codec verifies every complete state before factoring.
        # Temporarily expose nested formatter states to that same converter;
        # restore their original ownership/order without dropping any field.
        calls=case['printf_calls'];count=len(calls)
        calls.extend(call['formatter']for call in list(calls)if 'formatter'in call)
        try:super().case(case)
        finally:del calls[count:]
        return case


def main():
    p=argparse.ArgumentParser(add_help=False);p.add_argument('--debug-directory',type=Path,required=True);own,remaining=p.parse_known_args();sys.argv=[sys.argv[0],*remaining];projection=Projection()
    lifetime.main(commands=commands(own.debug_directory),fixture_name='vfprintf_original.json.gz',job_factory=jobs,case_transform=projection.case,finalize_metadata=projection.metadata,
        extra_metadata=dict(vfprintf_provenance=dict(observer=OBSERVER,reference='All unchanged jobs cold/warm. Every vfprintf entry, actual formatter entry/return, and parent return retains full owned regions, registers, XSAVE and allocator/error state. Parent inputs include FILE/lock/vtable, earlier external descriptor facts and native controls. Captured nested FILE helpers retain entry/return registers. Formatter return snapshots are independent component inputs for suffix auditing only; never continuing-replay seeds or formatting implementations. No native memory, instruction, register, result, allocation or signal is replaced; minimal environments precede capture.')))
    archive=ROOT/'tests/fixtures/vfprintf_original.json.gz';fixture=read_fixture(archive);histories=len(fixture['cases']);parents=fixture['parents'];del fixture
    split_archive(archive,ROOT/'tests/fixtures/vfprintf_original.manifest.json',histories=histories,parents=parents);archive.unlink()


if __name__=='__main__':main()
