# Secondary groups in shared-memory geometry

`geometry_storage.py` now executes secondary-group allocation, copying,
subdivision, joining and removal in the caller's guest memory and allocator.
It also executes consecutive JOINSHUNT dispatches, including their native
selected-winding update and deleted-source-pointer phase fallthrough.
This extends the [earlier geometry storage component](GEOMETRY_STORAGE.md);
it does not seed production calculations from captured final geometry.

## Native stores and ordering

The reference paths are `geometry.cpp`, `composite_geometry.cpp`,
`geometry_edit.cpp` and `geometry_dispatch.cpp` under `recomp_cpp/src/`.
Primary NEXT at `0xec` and secondary group NEXT at `0xe8` remain separate.
The implementation preserves the original operations:

- Prepending copies a raw 240-byte primary record, then copies and prepends
  each original secondary record. Child NEXT points to the preceding primary
  at allocation time. Reversing the primary chain does not change child NEXT.
- Longitudinal subdivision chooses the maximum retained length over a parent
  and its children, spills it to binary64, and uses one common ceiling count.
  Each edge still uses its own direction and length. Unsplit copies retain
  raw bytes; typed split copies retain their floating-copy/NaN behavior and
  clear links before inserting the new records.
- COPY and JOIN reverse secondary lists through native prepend order.
  Translated source records include every secondary record. Removal frees
  children before their primary and the descriptor after its segment chain.
- JOINSHUNT reverses both primary lists, translates and copies source primary
  records into the corresponding target groups, removes the source, then
  reverses the target. Existing source children are removed with their source,
  following the native raw-copy/link overwrite behavior.

Descriptor and segment bytes share the allocator's cache/link/header stores.
Caller-owned initial records can be released through that same allocator;
the allocator still validates their actual physical headers and free state.
No secondary owner is excluded from comparison.

## Clone/COPY/JOIN through CAP preparation

Fourteen unchanged native scripts run in separate cold and warm cache states,
giving 28 observations. The original twelve JOINSHUNT model sessions remain
present: wire, square and balun, coarse/refined cells, repeated branches,
explicit ground, eddy correction and three coupled requests. Two additional
square histories attach a longer source segment to a shorter target segment.
They exercise a child-governed split count and asymmetric CAP/inductive cells
that select typed one-part copying. All 28 plain runs exit normally.

The read-only observer captures whole initial heap, allocator, source scene
and string pool at the first analysis-driver entry. Later geometry records,
allocation/free calls, pool contents and allocator states are independent
assertions. Source clone/COPY/JOIN executes first; its same allocator then
continues through CAP contact/cache preparation without a contacts-entry
reset. Contact-count reconstruction includes all branches, the explicit
reference and native coupled copy stages.

Portable Python and packaged Pyodide have identical complete reports:

| Check | Exact coverage |
| --- | ---: |
| Geometry allocation/free events | 918 |
| Allocation addresses | 654 |
| Complete descriptor/primary/secondary bytes | 133,240 |
| String-pool/global bytes | 18,032 |
| Following CAP-preparation events | 1,148 |
| Following allocation addresses | 840 |

The longer-child case has a roughly 69 µm parent and 78 µm branch with a
35 µm inductive cell: the original makes three pieces for both, where the
parent alone would require two. All six resulting primary records and their
children match. The original 24 observations retain their separate totals:
890 events, 626 addresses, 123,096 geometry bytes and 15,456 string bytes.
Additional cases do not replace any earlier assertion.

## Consecutive JOINSHUNT commands and exact phase words

A separate 19-episode cohort starts at the first JOINSHUNT dispatch, with
the source scene, whole heap and allocator as earlier component inputs.
All twelve creators run two consecutive joins. Additional episodes cover
negative phase, unequal source length, self-join, a selected first/later
source, a selected multi-source command and a negative multi-source command.
All nineteen plain scripts exit normally. The existing parent archive still
retains the longer-source and duplicate-source SIGSEGV cases; this component
does not claim their partial faulting-memory histories are verified.

Commands are supplied as public names. The source resolves each name from
its own continuing descriptor list and heap. Later native parsed addresses
are comparisons only. Neither the allocator nor byte memory is reinitialized
between commands. At every return, checks require exact head/selection
identities, all raw live descriptors and records, both link orders, allocation
events and the physical allocator header walk.

All 33 returns match in Python and packaged Pyodide:

| Check | Exact coverage |
| --- | ---: |
| Allocation/free events | 494 |
| Allocation addresses | 229 |
| Complete live geometry bytes | 187,084 |
| Raw phase words | 53 |
| Physical allocator boundaries | 33 |

Command 421's fallthrough reads argument one's raw source descriptor pointer
after deleting that source. The source replay obtains that pointer from its
earlier scene, reverses endpoints when the sign changes, and stores the actual
pointer value. The negative multi-source case verifies that it stores the
first source's address. No recovered phase/address constant is substituted.

Mutation checks change a later parser pointer, secondary-record word or phase
expectation. Each produces a required failure while the generated continuing
heap remains unchanged. Six new tests pass on CPU and packaged Pyodide. Nine
existing CPU geometry/prelude tests also pass, and the prior 140-observation
geometry suite still matches every byte/address in WebAssembly. The required
`shunt-storage` Pages job runs the new tests and complete reports.

## Evidence and remaining integration

| Archive | Bytes | SHA-256 |
| --- | ---: | --- |
| `shunt_geometry_storage_original.json.gz` | 626,167 | `365d16f40f10739650a37593fc515f64ca9addcd0a7297f2fc93ef29e6196ea4` |
| `shunt_dispatch_original.json.gz` | 311,921 | `e6d3c6a48ff58fe232974d91c6992d7b487527c7805430ba22d8bd72e341367f` |

The archives retain original scripts/plain outcomes, observer commands,
minimal environments, parent hashes and binary/library digests. They are not
packaged into the simulator. Initial heap/scene construction remains a caller
input to these components. No native numerical instruction, register, memory,
allocation, affinity or returned result is replaced.

The typed webpage API still uses a geometry-only arena without complete
startup/prompt memory. Its four capacitor phase-word and two JOINSHUNT
source-address differences remain in the strict zero-difference gate.
This shared-memory result does not waive them. [Filament-array storage](SHUNT_FILAMENT_STORAGE.md)
now covers branch table bytes and complete lifetimes/cleanup across all 28
runs, including native reused contact headers. All 28 numerical histories now
match every captured bounded released buffer and complete first-node matrix,
including eddy correction and via stamps. Complete heap-byte equality and earlier
contact/cache history through the complete numerical driver remain required. Known
FCOS/logarithm, trailing-via aliases and continuing-process failures remain
required; this development branch is undeployed.

Source package: `54b403a4fef7caed`; numerical WASM remains SHA-256
`c7869e98f4c18b5414dc172d836e7144ab3ebc0de2de0d1f2eec1a4fe1709186`.

```sh
python tools/capture_shunt_geometry_storage_original.py --reference ~/github/asitic-re \
  --library-path /path/to/i386/libs --debug-directory /path/to/libc/debug
python tools/capture_shunt_dispatch_original.py --reference ~/github/asitic-re \
  --library-path /path/to/i386/libs --debug-directory /path/to/libc/debug
PYTHONPATH=src:tests python -m unittest test_shunt_geometry_storage_original -v
python tools/audit_geometry_setup_original.py --fixture tests/fixtures/shunt_geometry_storage_original.json.gz
python tools/audit_shunt_dispatch_original.py
python tools/build_site.py
node tools/check_shunt_geometry_storage_original.mjs /path/to/pyodide.mjs /tmp/setup.json /tmp/dispatch.json
```
