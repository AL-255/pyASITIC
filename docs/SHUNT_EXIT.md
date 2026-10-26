# Exit lists and loader dependency traversal

The continuing source now executes libc's exit-list traversal, decodes the
registered loader callback, sorts the actual loader namespace and enters the
first object's ELF finalizer. All fourteen unchanged scripts, cold and warm,
reach this point on their existing memory and allocator. The source stops at
the unimplemented main ELF finalizer body `0x080b4784`. No observed finalizer
free list, callback order, returned state or exit status supplies execution.
This development branch is not deployed and does not establish full fidelity.

## Source and earlier inputs

`exit_storage.py` follows glibc 2.39
[exit.c](https://github.com/bminor/glibc/blob/glibc-2.39/stdlib/exit.c),
[dl-fini.c](https://github.com/bminor/glibc/blob/glibc-2.39/elf/dl-fini.c),
[dl-sort-maps.c](https://github.com/bminor/glibc/blob/glibc-2.39/elf/dl-sort-maps.c)
and [dl-call_fini.c](https://github.com/bminor/glibc/blob/glibc-2.39/elf/dl-call_fini.c).
It reads the live exit-list head/index/flavor/function/argument fields and
guest TLS pointer guard. It decrements the index, clears a C++ callback's
flavor, releases the list lock before calling it and checks the registration
counter when it returns. The actual captured TLS-destructor lists are empty;
nonempty and contended/concurrent paths remain explicit unfinished branches.

The loader path follows the namespace's actual `l_next` chain, increments
open counts, assigns indexes, sorts dependency/relocation edges, releases its
recursive lock, clears `l_init_called` when entering an object and traverses
its ELF finalizer array in reverse before `DT_FINI`. It implements both
source sorting algorithms. The captured read-only enum is **1 = DFS**;
the tunable's numeric values are a separate interface. Only the DFS cohort
has native end-to-end ordering evidence here.

A new read-only capture supplies genuine first-driver exit lists, TLS slots,
loader globals, all twenty namespace link maps (including the vDSO), raw
dependency lists and ELF dynamic/finalizer-array records. Layouts come from
the matching debug types. These raw regions supplement the earlier loader
input regions; descriptive callback/order metadata is not consulted by the
runtime. The source computes the native order of all **19 initialized
objects / 532 positions** across the unchanged 28 histories. These are order
comparisons, not claims that the later destructor bodies have executed.

## Complete targets and strict failures

The capture retains every parent solve/command/file/stdin/malloc/cleanup
target and every unchanged original outcome. All 28 observed and plain runs
exit normally. It adds **1,484 native calls / 2,940 phases**: public exit,
registered callback, loader entry, nineteen object calls and thirty-one ELF
finalizer calls per history. Every phase retains the complete stack, mapped
heap, arena, stream-list head, all earlier stdio owners and all earlier exit
owners, plus seventeen registers, XSAVE, allocator state and event count.
All **467,460 ordered regions / 4,243,637,580 captured bytes** are expanded
and hash-checked; missing source phases remain failures.

The independent component starts once at the actual earlier exit-entry
boundary. It matches the non-stack memory and allocator state through the
first finalizer entry: **40,416,016 words / 112 output boundaries**, with
zero unknown bytes. Its strict report retains **10,052 failures**: 7,000
stack words, 112 missing GP boundaries, 112 missing FP boundaries, 2,800
unexecuted phases and 28 missing destructor bodies. The initial component
entry is an input, never an output assertion or full-history seed.

The full continuing audit additionally checks exit entry itself:

| New continuing assertion | Checked |
| --- | ---: |
| Calls entered / memory and heap boundaries | 140 / 140 |
| Complete word units | 50,520,020 |
| Declared C argument words | 112 |
| Computed initialized-object order positions | 532 |
| Unknown compared bytes | 0 |

The full report remains nonzero at **664,133 failures**. It preserves all
previous 531,744 failures and adds the new complete exit states. The exit
word differences include stack execution and a newly exposed live loader
relocation counter; no region or field is exempted. Register/FP continuations,
the later callbacks, final stdio cleanup and actual process exit also remain
required. Matching order does not repair any of these missing executions.
The complete CPU and packaged WebAssembly reports agree field for field,
including every individual failure and coverage counter. Of the 129,309 new
exit-word failures, 129,169 are stack words and 140 are relocation-counter
words; the latter remain ordinary failures at all five reached boundaries.

`trace_shunt_exit_lookups_original.py` diagnoses that counter using read-only
symbol lookup breakpoints and the exact original launch files. In the
square/coarse warm history, six first-solve bindings and the final `exit`
binding are absent from the source path. The eight reached source bindings
for the continuing REPL are real executions of the existing lookup/fixup
implementation. The trace's later counter values never initialize runtime
memory, and no per-case increment is substituted for the missing calls.

Nine regression tests check provenance and every complete region, all
independent exit boundaries, same-memory full continuation, lossless heap
factoring, changed later-target independence, descriptor-metadata
independence, a changed actual dependency edge, changed live callback
dispatch, missing earlier bytes, the vDSO and the live sorting enum. Tests
for detecting unfinished behavior are separate from the still-failing full
fidelity gate.
All 63 targeted portable regression tests and all nine new WebAssembly tests
pass. CI discovers all nine new tests. Every one of the eight earlier
printf/parser shard reports is unchanged, including shard five's 24 saved-FP
failures. The prior 28-history port report is unchanged at zero differences.
The older 130+4 command reports retain all parent fields (zero and 816
differences), and the complete earlier cleanup report remains identical at
531,744 strict failures. Its eight regression tests also pass in WebAssembly.

## Lossless fixture transport

Repeated heap dictionaries use a content-addressed bank: all 2,940 native
dictionaries expand with every field preserved (56 unique bodies). Each
expansion owns independent mutable containers, preventing changed later
assertions from modifying earlier component inputs through aliases. Two
complete byte banks live in separate gzip files to keep every file below
GitHub's size limit. `exit_fixture.read_fixture` checks their compressed
SHA-256, entry count and byte count; individual page and region hashes remain
required. No byte, owner, phase or outcome is removed by this factoring.

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `shunt_exit_original.json.gz` | 90,959,803 | `e4470114c4a741600bdb2899af04b9851e3b63d0ecfd5c5a27d31ed76a56d1b0` |
| `shunt_exit_driver_heap_pages_original.json.gz` | 12,956,933 | `7253c3c1bafb8f3b4678f0639df6a981f9a2ada8aa21bee97337a6b26aba6bc5` |
| `shunt_exit_loader_regions_original.json.gz` | 2,333,409 | `3ece17d3e4c9f4c8df0417810cad36c297048d3cf83ef8c87062619401102672` |

Source package `0dc410344088329b` contains all 196 current runtime source
files and no fixtures, checked byte for byte against the working tree.
The downloadable numerical source archive still rebuilds WASM SHA-256
`c7869e98f4c18b5414dc172d836e7144ab3ebc0de2de0d1f2eec1a4fe1709186`
exactly. Earlier fixtures without the newly captured exit inputs retain
their explicit missing-input boundary; later exit snapshots never fill it.

```sh
python tools/capture_shunt_exit_original.py --reference ~/github/asitic-re \
  --library-path /path/to/i386/libs --debug-directory /path/to/libc/debug
PYTHONPATH=src:tests python -m unittest test_shunt_exit_original -v
python tools/audit_shunt_exit_original.py --isolated --output /tmp/exit-isolated.json
python tools/audit_shunt_exit_original.py --output /tmp/exit-full-cpu.json
python tools/build_site.py
node tools/check_shunt_exit_original.mjs /path/to/pyodide.mjs /tmp/exit-full-wasm.json
python tools/trace_shunt_exit_lookups_original.py --reference ~/github/asitic-re \
  --debug-directory /path/to/libc/debug --output /tmp/exit-lookups.json
```
