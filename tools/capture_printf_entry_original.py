"""All public printf entry calls, with real parent/formatter/helper assertions."""
import argparse,sys
from pathlib import Path
import capture_vfprintf_whole_original as parent
from capture_getline_bytes_original import integer_cpu
from printf_archive import read_fixture,split_archive

ROOT=Path(__file__).resolve().parents[1]


def replace_once(source,old,new):
    if source.count(old)!=1:raise ValueError('Public printf observer anchor differs')
    return source.replace(old,new)


OBSERVER=replace_once(parent.OBSERVER,
    "s=reg('esp');file=u32(s+4);buffer=file;format=u32(s+8)",
    "s=reg('esp');entry_base=u32(next(x['address']for x in ctx['maps']if x['name'].endswith('/libc.so.6')))\n file=u32(u32(entry_base+0x22fe34+0xb8))if kind=='printf'else u32(s+4);buffer=file;format=u32(s+4 if kind=='printf'else s+8);ctx['entry_kind']=kind")
OBSERVER=replace_once(OBSERVER,"s=reg('esp');fmt=u32(s+8);raw=", "s=reg('esp');fmt=u32(s+4 if ctx.get('entry_kind')=='printf'else s+8);raw=")
OBSERVER=replace_once(OBSERVER,"FileEntry(base+0x62110,'vfprintf');FormatterEntry(base+0x60530)",
    "FileEntry(base+0x57db0,'printf');FileEntry(base+0x57670,'fprintf');FileEntry(base+0x5e680,'vfprintf_public');FileChild(base+0x62110,'vfprintf');FormatterEntry(base+0x60530)")


def commands(directory):return parent.commands(directory).replace(parent.OBSERVER,OBSERVER)


def jobs():
    for job in parent.jobs():
        job['parent']=ROOT/'tests/fixtures/vfprintf_whole_original.manifest.json';yield job


def main():
    p=argparse.ArgumentParser(add_help=False);p.add_argument('--debug-directory',type=Path,required=True);p.add_argument('--cc',default='cc');p.add_argument('--output',type=Path,default=ROOT/'tests/fixtures/printf_entry_original.json.gz');own,remaining=p.parse_known_args();sys.argv=[sys.argv[0],*remaining];projection=parent.parent.Projection();archive=own.output.resolve()
    if not archive.name.endswith('.json.gz'):raise ValueError('Public printf output must end with .json.gz')
    parent.lifetime.main(commands=commands(own.debug_directory),fixture_name=str(archive),job_factory=jobs,case_transform=projection.case,finalize_metadata=projection.metadata,
        extra_metadata=dict(integer_cpu=integer_cpu(own.cc),printf_entry_provenance=dict(observer=OBSERVER,reference='All67 unchanged jobs cold/warm. Earlier public printf/fprintf/vfprintf entry owns full live stack/heap/FILE/arena/control/ELF/static TLS and actual FP inputs before its argument/frame stores. Internal vfprintf and all original formatter/FILE helpers retain entry/return registers. Produced formatter boundaries and public return remain complete owned-state assertions. No later call snapshot initializes execution; no native instructions, memory, registers, CPU affinity, allocations, results or signals are substituted. Minimal environments and independent CPU flag observations precede capture.')))
    fixture=read_fixture(archive);histories=len(fixture['cases']);parents=fixture['parents'];del fixture
    split_archive(archive,archive.with_name(archive.name.removesuffix('.json.gz')+'.manifest.json'),histories=histories,parents=parents);archive.unlink()


if __name__=='__main__':main()
