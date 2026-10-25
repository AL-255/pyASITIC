"""Whole vfprintf parents with complete earlier formatter inputs and every helper."""
import argparse,sys
from pathlib import Path
import capture_vfprintf_original as parent
import capture_printf_format_original as formatter
import capture_trailing_via_heap_original as lifetime
from capture_getline_bytes_original import integer_cpu
from printf_archive import read_fixture,split_archive

ROOT=Path(__file__).resolve().parents[1]
# Reuse the exact read-only earlier ELF/static-TLS observer from the formatter
# capture. It reads the same format and va_list argument positions at this
# parent entry; it does not initialize from the later formatter boundary.
INPUTS='format_section_cache={}\ndef format_elf_data'+formatter.EXTRA.split('def format_elf_data',1)[1].split('class FormatPoint',1)[0]
EXTRA_CHILDREN="((0x586c0,'init'),(0x58710,'done'),(0xa3cb0,'strchrnul'),(0x58750,'write'),(0x58390,'pad'),(0x58440,'putc'),(0x584b0,'puts'),(0x58230,'flush'),(0x5a990,'fp-l-buffer'),(0x58920,'fp-buffer'),(0xbc470,'strlen-ia32'),(0xa9630,'strlen-sse2-bsf'),(0x19ccc0,'strlen-sse2'),(0xbb390,'strnlen-ia32'),(0x19ea20,'strnlen-sse2'),(0x56dd0,'itoa-word'),(0x56ec0,'itoa'),(0x58570,'switch')"
OBSERVER=parent.OBSERVER.replace("fd=u32(file+56);ctx['file']=file;ctx['profile']=dict(fd=fd,statx=statx_metadata(fd))\n return ctx",
    "fd=u32(file+56);ctx['file']=file;ctx['profile']=dict(fd=fd,statx=statx_metadata(fd))\n format_inputs(ctx);return ctx").replace(
    "((0x586c0,'init'),(0x58710,'done'),(0x58570,'switch')",EXTRA_CHILDREN)+'\n'+INPUTS


def commands(directory):return parent.commands(directory).replace(parent.OBSERVER,OBSERVER)


def jobs():
    for job in parent.jobs():
        job['parent']=ROOT/'tests/fixtures/vfprintf_original.manifest.json';yield job


def main():
    p=argparse.ArgumentParser(add_help=False);p.add_argument('--debug-directory',type=Path,required=True);p.add_argument('--cc',default='cc');p.add_argument('--output',type=Path,default=ROOT/'tests/fixtures/vfprintf_whole_original.json.gz');own,remaining=p.parse_known_args();sys.argv=[sys.argv[0],*remaining];projection=parent.Projection();archive=own.output.resolve()
    if not archive.name.endswith('.json.gz'):raise ValueError('Whole-parent output must end with .json.gz')
    lifetime.main(commands=commands(own.debug_directory),fixture_name=str(archive),job_factory=jobs,case_transform=projection.case,finalize_metadata=projection.metadata,
        extra_metadata=dict(integer_cpu=integer_cpu(own.cc),vfprintf_whole_provenance=dict(observer=OBSERVER,reference='All67 unchanged jobs cold/warm. Complete earlier parent ELF tables, aligned format bytes, full pthread/static TLS, stack/heap/arena/FILE/control/profile inputs are read before vfprintf executes. Formatter entry and return retain full owned states as assertions only; whole-parent execution never initializes from them. Every old caller helper and all added formatter helpers retain entry/return registers. No native instruction, memory, CPU affinity, allocation, result or signal is replaced. Minimal environment guards precede capture.')))
    fixture=read_fixture(archive);histories=len(fixture['cases']);parents=fixture['parents'];del fixture
    split_archive(archive,archive.with_name(archive.name.removesuffix('.json.gz')+'.manifest.json'),histories=histories,parents=parents);archive.unlink()


if __name__=='__main__':main()
