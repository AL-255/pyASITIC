# Native polling caller and timeval adapter

`poll_storage.py` implements two missing source operations before stdin input:
the ASITIC polling helper through the resolved libc `select` entry, and libc's
32-bit timeval adapter through `select64` entry. Both operate on guest Memory.
They execute no host poll, file operation, syscall or native code image.

The subsequent [REPL caller integration](STDIO_TRANSITION.md) connects these
operations using earlier first-driver stream and CPU state. The independent
per-call snapshots below remain assertions only, never continuation seeds.

The native helper (`0x804bdc4`, `repl_stdin_has_input` in the C++ reference)
reserves its original frame, saves EBP/EDI/EBX, clears the complete 128-byte
fd_set and sets descriptor zero. It initializes timeval `{0,100}`, pushes all
five arguments and the native return PC, and invokes the existing ELF/PLT
resolver for `select`. All destinations derive from earlier relocation/GOT
state. Stack padding and the unused frame word retain earlier bytes.

The pinned Ubuntu i386 glibc 2.39 wrapper at libc + `0x121390` saves four
registers and the earlier TLS canary. It retains its temporary microsecond
word, sign-extends both timeval members into the original 16-byte temporary,
pushes the arguments and return PC, then reaches `select64` at + `0x120f90`.
Its null-timeout tail-call branch is explicitly unsupported. The wrapper's
source is glibc `select.c`, LGPL-2.1-or-later; the license accompanies the site.

## Earlier CPU behavior

The last `SAR EBP,31` determines the defined flags, but AF is architecturally
undefined. The first complete comparison found every memory word and other
register exact, with only this AF bit differing. Rather than taking the bit
from the later select result, the capture tool runs a separate freestanding
i386 CPU probe **before any ASITIC jobs**. It executes SAR on positive,
negative and bit-30-set operands, each with earlier AF clear and set. The
six complete observations and probe source are retained as earlier CPU
metadata. A profile with input-dependent AF is explicitly unsupported.

`select64_entry` requires this CPU AF profile as an input; no default is
inferred from its expected output. All defined flags still derive from the
source operand and earlier control flags. Tests check the independent probe's
defined flags and both earlier AF values, and show that changing the earlier
profile changes only the resulting AF comparison. On the reference host the
probe returns AF set for all six cases.

## Independent native evidence

The read-only capture repeats all 67 existing jobs cold and warm, retaining
all 134 histories, actual terminal outcomes and plain-run results. It observes
poll entry, resolved `select` entry and `select64` entry. Only the existing
rectangular cold history reaches polling before the next driver or native
terminal outcome; the other 133 histories remain explicit. GDB observes 132
next-driver outcomes, one SIGSEGV and one SIGABRT. Plain runs observe 129
normal exits, one SIGSEGV and four SIGABRT outcomes. Relative to the parent,
the cold width-3 coarse and contact pilots change from normal exit to SIGABRT;
the cold boundary coarse pilot changes from SIGABRT to normal exit, and its
warm peer from SIGSEGV to SIGABRT. These fresh native outcomes are retained;
no result was selected or retuned to reproduce the parent's terminal counts.

Each independent operation initializes its own **earlier** full stack, ELF,
TLS, registers and XSAVE. Its complete later regions, registers and XSAVE
are assertions. Regions and overlaps are retained; there is no address
exemption or output-word selection. Later-memory/register/FP mutations and
region omissions fail the comparison. Earlier saved-register, padding,
timeval, canary and CPU-profile mutations exercise the source operations.

The capture uses the shared minimal native environment and guards it before
reading the stack. All original instructions, results, allocations, signal
delivery and kernel decisions execute unchanged. No inferior registers or
memory are replaced. Parent fixture hashes, original/libc image hashes,
complete commands and observer source are retained.

The new mandatory `pollstore` browser suite supplements every older gate.
Reports remain local.

All seven new CPU tests and all seven packaged Pyodide tests pass. The complete
CPU and Pyodide audit reports are byte-identical: two operations, 333,210
four-byte comparison units (including short tails and overlapping regions),
34 registers, 4,880 FP-state bytes and zero differences. The source package
version is `5055da6c6f8a7d7f`. Workflow syntax, complete disjoint Python test
discovery, JavaScript syntax and patch validation pass. The numerical WASM
binary is unchanged. The dispatcher checkpoint's 112 affected tests and
continuing reports remain separate evidence; the unconnected polling code
does not alter those continuing paths.

The fixture is 723,752 bytes, SHA256
`a7ac445c2d07ddecf9d831422f30fecc50ab1b4d1cd7a68818df1fbb1b98df77`;
uncompressed SHA256
`699b33fe9e88d8873fe41ee0900e9dde742dd0dbc1f7b5d2ed4d3e3a24463058`.

## Continuing work

At this checkpoint these were independent components. The subsequent
[stdio integration](STDIO_TRANSITION.md) supplies the earlier stream state
and connects their source operations without loading any per-call snapshot.
The subsequent [select64 dispatch source](SELECT_DISPATCH.md) implements
timeout normalization, the EINVAL return and syscall-helper stores through
VDSO entry, including independent null/time64/overflow inputs. The rest of
the `select64` body, kernel fd readiness and timeout copyback, stdin/libio,
`strcat`, parser child ABI and signal/handler continuation remain unfinished.
The loader-only comparison retains 618 required differences; the subsequent
expanded comparison has 556. The older fixture still has 816. All arithmetic, JOIN/UNJOIN, heap/mapping and
other analysis gates remain required. This checkpoint changes no deployed
page or production guard.

```sh
python tools/capture_poll_storage_original.py --debug-directory /path/to/debug/usr/lib/debug --reference /path/to/asitic-re --library-path /path/to/native-libraries
PYTHONPATH=src:tests python -m unittest test_poll_storage_original -v
python tools/audit_poll_storage_original.py --output /tmp/poll-cpu.json
python tools/build_site.py
node tools/check_poll_storage_original.mjs /path/to/pyodide.mjs /tmp/poll-wasm.json
```
