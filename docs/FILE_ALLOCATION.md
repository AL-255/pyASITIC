# Native file-stat and buffer-allocation callers

The source now executes `_IO_doallocbuf`, the legacy C++ doallocate/stat
wrappers, `_IO_file_doallocate`, the fstat/fstatat callers and `_IO_setb`
in the continuing simulation Memory. It constructs both the kernel's
256-byte statx record and libc's 108-byte time64 stat record from earlier
named external-file facts. The full continuing comparison improves from
382 to **298 required differences**: 133 before parser entry and 165 at
final abort. Exactly 84 previously differing address/phase pairs resolve;
none are introduced.

## Earlier facts and source operations

At first-driver entry, the capture independently queries statx on
`/proc/<inferior>/fd/0`. Its schema records named fields, including device
numbers, inode, timestamps, block size and mount ID. It never reads the
program's later stat buffers as an input, and does not retain a raw statx
record. Unexpected nonzero reserved bytes reject capture. The earlier
context also supplies the actual VDSO entry prefix and libc's bound malloc
GOT slot. These become complete later assertions: 19 regions, 1,920 bytes.

`file_allocation.py` emits the pinned i386 saved registers, PIC thunk,
foreign-vtable guard, stack canaries, argument stores and returns through
the native caller chain. The syscall result is encoded from the earlier
file facts, with complete defined padding and reserved bytes. Libc's time64
conversion uses the GNU device-number encoding and original field widths.
The buffer size follows the regular-file block-size/BUFSIZ branch.

The malloc call follows its actual `.plt.got` GLOB_DAT pointer. In this
process that pointer names the executable's canonical malloc PLT entry;
the source derives the entry from ELF relocation/symbol metadata and
follows its existing resolved GOT state. It neither replaces that pointer
with a direct libc address nor fabricates another lazy binding.

The existing guest `Heap.malloc` supplies the actual buffer address. The
post-allocation source emits `_IO_setb`'s stores and the complete caller
return. Malloc's own internal register/stack ABI remains unimplemented;
the connected caller uses its returned pointer and preserved registers,
and overwrites volatile ECX/EDX before use. No observed later allocation
pointer or allocator child frame supplies the missing behavior.

## Independent boundaries and continuing histories

The independent capture repeats all 67 unchanged jobs cold and warm.
It records doallocbuf entry, malloc entry, post-malloc entry and doallocbuf
return. One history reaches this stdin allocation; the other 133 explicitly
retain their absence of calls. Both operations compare every captured
memory region, all 17 registers and full XSAVE bytes. Python and Pyodide
each check **333,348 four-byte units, 34 registers and 4,880 FP bytes with
zero differences**. Units include region tails and overlapping owners.

Mutation checks prove that later stat-buffer, register and FP assertions
are not inputs, missing regions fail, earlier inode/time64 facts drive
both stat records, and an earlier malloc return drives the FILE buffer
pointers. The continuing tests compare generated allocation entry and
malloc entry registers against the independent capture. All eight
previous lazy-binding entry register sets remain exact. Missing earlier
malloc-slot memory fails explicitly; later regions cannot supply it.

The full continuing capture independently repeats all 134 histories from
earlier first-driver inputs. Per-call component snapshots never seed it.
All 9,479,168 later heap words, 664 allocator events, 135 freed buffers
(10,580 bytes), 140 console calls, 132 calendar calls and 132 files
(187,415 bytes) match, with zero unknown bytes. The audit checks 216,125
final component words and 432,250 point words across 266 points. Only the
rectangular cold history retains differences. Its complete CPU report is
identical to the compiled browser report.

The remaining stack differences still require malloc's internal ABI,
kernel poll/timeout and read effects, string-copy ISA/FP effects, printf,
parser child frames, interrupted XSAVE and signal/handler continuation.
Other command, numerical, geometry/lifetime and older heap failures remain
unfinished. No target, expected word or gate is omitted or relaxed.

## Capture provenance and validation

Both fresh captures retain 132 next-driver outcomes, one SIGSEGV and one
SIGABRT. The independent component's plain runs retain 131 normal exits,
two SIGABRT and one SIGSEGV. The continuing capture's plain runs retain
128 normal exits, five SIGABRT and one SIGSEGV.
Relative to the parent input fixture, the continuing capture's
square/1/coarse cold and warm change
from normal exit to SIGABRT; pilot-width3/1/coarse cold and warm and
pilot-boundary/1/coarse cold change from SIGABRT to normal exit;
pilot-width3/1/contacts warm changes from normal exit to SIGABRT. All fresh
outcomes remain recorded, without retuning any launch to select an outcome.

The minimal environment guard runs before earlier stack capture. The
observer reads memory, registers, metadata and output without substituting
inferior results, instructions, memory, registers or signals. Complete
observer/commands, binary hashes and parent hashes accompany both fixtures.

| Fixture | Compressed bytes | Compressed SHA256 | Uncompressed SHA256 |
| --- | ---: | --- | --- |
| `file_allocation_original.json.gz` | 836,012 | `47a1e64248ab7831edf0a091363f2c156ff52577665f451aa659015cab906ec1` | `2d76b565fdecf8697608dd7bdb6aaa2438b47031d98a40cfe2394da52970219d` |
| `stat_transition_original.json.gz` | 47,431,122 | `e2f1ba77c99c227b3eb11e4d77668534594d89378cf4c2381839422147bd4da2` | `104cfb2f52cd0fd7f13417567274279c382375c272660942543fbe9097350e67` |

All 138 targeted CPU tests pass, including five new independent component
tests and four integration tests. Those nine also pass in packaged Pyodide
`4c49bd27fbf5f6bc`. Both mandatory new workflow suites preserve strict
comparison: `fileallocation` passes; `stattransition` exits nonzero with
298 differences. The older full compiled input, stdio, loader and command
gates still fail with 382, 556, 618 and 816 differences respectively; the
older 130 main command histories still pass. Reports stay local. The
numerical WASM and production guard are unchanged; this development
checkpoint is not deployed.

```sh
python tools/capture_file_allocation_original.py --debug-directory /path/to/debug/usr/lib/debug --reference /path/to/asitic-re --library-path /path/to/native-libraries
python tools/capture_stat_transition_original.py --debug-directory /path/to/debug/usr/lib/debug --reference /path/to/asitic-re --library-path /path/to/native-libraries
PYTHONPATH=src:tests python -m unittest test_file_allocation_original test_stat_transition_original -v
python tools/build_site.py
node tools/check_file_allocation_original.mjs /path/to/pyodide.mjs /tmp/file-allocation.json
node tools/check_stat_transition_original.mjs /path/to/pyodide.mjs /tmp/stat-transition.json
```
