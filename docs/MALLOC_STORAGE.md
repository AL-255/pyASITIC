# Native malloc ABI in continuing stdin allocation

The stdin buffer allocation now emits the pinned i386 `__libc_malloc` and
`_int_malloc` stack/register effects for the single-threaded unsorted-bin
exact-fit path. The existing `Heap.malloc` still computes the returned
address and performs the allocator's actual data changes. The complete
continuing audit improves from 298 to **284 required differences**, resolving
14 address/phase pairs without introducing any: 126 differing words before
parser entry and 158 at final abort.

## Source behavior and earlier inputs

`malloc_storage.py` validates the earlier malloc initialization, thread,
tcache TLS binding, bin controls, main arena and perturbation state. It
follows the same noncacheable large-request branch and validates the
unsorted candidate's physical header, links, foot and following header.
It writes only the saved registers, CALL/PC-thunk effects and local slots
that the original branch writes. The branch emits no floating-point work.
Return ECX follows the next chunk's size word; EDX and the return flags
follow the libc epilogue. All 17 entry and return registers match the
independent native boundaries.

Stdin's caller passes its existing heap and Memory to the ABI component.
It prepares the native frame before the same source allocation, then
executes the native caller return using the pointer that allocation
actually produced. No later native pointer, stack snapshot or register
result supplies those effects. Other tcache, small-bin, consolidation,
alternate-arena, perturbation and system-allocation paths stop explicitly
until their source ABI is implemented; this is not a complete malloc port.

The continuing capture supplements the earlier first-driver context with
seven actual malloc control/TLS regions totaling 22 bytes. Together with
the preceding inputs, all 26 owners (1,942 bytes) become complete later
assertions. Component snapshots never seed continuing execution. Older
fixtures without these controls keep their original missing-ABI failures.

## Independent complete comparisons

The independent capture repeats all 67 unchanged jobs cold and warm,
retaining all 134 outcomes. One history reaches the stdin allocation;
133 preserve their absence of calls. It captures doallocbuf entry,
malloc entry, post-malloc entry and doallocbuf return, with complete
stack/ELF/TLS/FILE/heap/arena/control regions, registers, XSAVE and native
allocator snapshots. The audit compares all three operations independently:
stat preparation, malloc, then buffer installation and caller return.

In the native malloc-entry state, a corrupted physical chunk walk stops
before a still-reachable free-bin candidate. Independent test initialization
reads bin-owned headers and their following headers from the **same earlier
heap bytes** to construct the logical inventory. It preserves the physical
bytes and observed stopping error, which remain complete later targets.
The continuing simulation instead retains the inventory produced by its
own earlier allocation history; it imports no component allocator state.

Python and Pyodide each compare **605,328 four-byte units, 51 registers,
7,320 FP bytes and three allocator boundaries with zero differences**.
Units include overlapping owners and region tails. Arena images, logical
allocator fields, parameters, tcache counts, mappings and the original
physical-header error all remain required. Missing memory is an explicit
audit failure. Mutation tests change later memory/register/FP/heap targets,
remove a region, alter earlier caller registers/request/control bytes and
inject later allocator-field errors. Every relevant comparison fails as
expected; later state cannot repair earlier missing inputs.

All four continuing integration tests pass in CPU Python and Pyodide.
They compare the generated malloc entry/return and all eight existing PLT
binding register sets with independent native captures, preserve every
history/region/outcome and reject missing earlier controls. The separate
149 distinct targeted CPU checks pass (148 regression checks plus the
additional allocator-field mutation check); the final seven component
checks also pass with all strengthened assertions.

The full packaged Pyodide audit, version `5c32835d9611b69d`, retains every
one of the 134 histories. Only the rectangular cold history differs; its
complete CPU report is identical to the compiled report. All 9,479,168 later
heap words, 664 allocator events, 135 freed buffers (10,580 bytes),
140 console calls, 132 calendar calls and 132 files (187,415 bytes) match,
with zero unknown bytes. Expanded region assertions compare 216,790 final
component words and 433,580 point words over 266 points. Every one-byte
control region is also compared in full. The older stat, input, stdio, loader and
extra-command compiled gates retain 298, 382, 556, 618 and 816 failures
respectively; the older 130 main command histories still pass. All six
strict continuing checks exit nonzero, preserving the unresolved targets.

## Native provenance

Both fresh GDB captures retain 132 next-driver outcomes, one SIGSEGV and
one SIGABRT. The component's plain runs retain 126 normal exits, five
SIGABRT and three SIGSEGV; the continuing capture's plain runs retain
128 normal exits, five SIGABRT and one SIGSEGV. All fresh outcomes are
recorded without selecting launches to match the parent.

Compared with the preceding stat fixture, the component changes
pilot-width3/1/coarse warm from normal exit to SIGSEGV,
pilot-boundary/1/coarse cold from normal exit to SIGABRT, and its warm
history from SIGABRT to SIGSEGV. The continuing capture changes
square/1/coarse cold, pilot-width3/1/contacts warm and
pilot-boundary/1/coarse warm from SIGABRT to normal exit;
pilot-width3/1/coarse cold and warm and pilot-boundary/1/coarse cold
change from normal exit to SIGABRT.

The minimal environment is checked before earlier stack capture. Commands,
observer source, binary hashes and parent hashes accompany the fixtures.
No inferior instruction, register, memory, allocation, syscall result or
signal is replaced. Diagnostic reports remain local.

| Fixture | Compressed bytes | Compressed SHA256 | Uncompressed SHA256 |
| --- | ---: | --- | --- |
| `malloc_storage_original.json.gz` | 967,599 | `55e3fa58037e84e5ddf5f6e6f55abcc7e582985b959e767a8028bf9ecc7570f2` | `72b31024b29e8264ad5d412586cd2742ded4ca1ae129b2268575775035ceac02` |
| `malloc_transition_original.json.gz` | 47,497,932 | `76bdeaa0a62e256ae8e65ea6fcde748e472956e639c125b151454fe029b98c3b` | `a20b8c2ef6fc1fd6bf8375bed9eba203d68f0888c059bb00075364cae60da1a7` |

The new `mallocstore` and `malloctransition` workflow suites are mandatory.
The latter keeps every unresolved difference as a failure. Kernel
poll/timeout/read effects, string-copy ISA/FP, printf/parser child frames,
interrupted XSAVE and signal continuation remain unfinished, alongside
other numerical, geometry/lifetime and older heap gates. The numerical
WASM and production guard are unchanged; this checkpoint is not deployed.

```sh
python tools/capture_malloc_storage_original.py --debug-directory /path/to/debug/usr/lib/debug --reference /path/to/asitic-re --library-path /path/to/native-libraries
python tools/capture_malloc_transition_original.py --debug-directory /path/to/debug/usr/lib/debug --reference /path/to/asitic-re --library-path /path/to/native-libraries
PYTHONPATH=src:tests python -m unittest test_malloc_storage_original test_malloc_transition_original -v
python tools/build_site.py
node tools/check_malloc_storage_original.mjs /path/to/pyodide.mjs /tmp/malloc-component.json
node tools/check_malloc_transition_original.mjs /path/to/pyodide.mjs /tmp/malloc-continuation.json
```
