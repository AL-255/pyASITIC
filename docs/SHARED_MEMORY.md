# Shared numerical bytes and native cache behavior

The development port now has sparse guest byte memory, complex matrix views
that can alias the same bytes, the original via load/store sequence, and
byte-backed tcache control, links and keys. This extends
[mapped allocation placement](MMAP_PLACEMENT.md). It is **not connected to
production electrical solves**, and the trailing-via guard remains enabled.

`Memory` distinguishes unmapped addresses from mapped but unknown bytes. It
does not silently zero unknown native data. `ComplexView` uses the original
column-major address calculation, including addresses beyond the declared
matrix. `stamp_memory` performs the real load/store before the imaginary
load/store; a second-component fault leaves the preceding real store intact.
Inactive vias do not read their destination.
Released mappings discard their stored bytes; new anonymous mappings and
newly granted brk pages are explicitly zero-initialized, following OS behavior.

`Heap.attach_cache_memory` makes tcache operations read and modify those same
guest bytes. Safe-linked next pointers, counts, heads and keys follow native
allocation/free order. A stamp can change a cached chunk's next pointer, and
subsequent cache operations preserve that change. Damaged chains are observed
as damaged; they are not repaired from a logical-list copy. Other arena metadata
still uses the existing logical placement model. Arbitrary bin/header corruption
and complete byte-level allocator behavior are not claimed as implemented.

## Original observations and byte provenance

`capture_shared_memory_original.py` records raw heap regions and the native
tcache key using the existing read-only GDB observers. The fixture retains all
65 selected input configurations in cold and warm states, complete plain-run
outcomes, 12,877 allocation/free events and all 389 boundary snapshots. The
parent mapping and earlier fixtures remain unchanged.

The full raw capture is approximately 47 MB compressed. The checked-in fixture
is a deterministic, approximately 5.6 MB projection containing every observed
heap chunk header and first eight user bytes, the complete tcache controls,
the CAP and reduced-inductance output arrays at numerical boundaries, and
each via target intersected with mapped heap memory. Full heap-region hashes,
the full compressed-capture hash, the projection rule and the actual GDB
commands are retained. Bytes outside the projection remain unknown. No
selected case, native failure or damaged-chain observation is removed.

The recorded original plain runs have 123 normal exits, five SIGABRT exits and
two SIGSEGV exits. The observed first-node fault is the cold
`square/64/contacts` case. This independent capture has four damaged tcache
observations: cold `square/1/filaments`, warm `pilot-width3/1/filaments`, and
both `pilot-boundary/1/filaments` cache modes. Three chains end at `0x8100`;
the warm boundary pilot ends at `0x811b`. Previous captures have different
damaged-chain counts and outcomes; those observations remain intact.

## Component comparison

The comparator first predicts allocation placement from the source storage
plan and initial allocator snapshot. At via entry it initializes shared bytes
from that boundary's captured input state and attaches the cache backer. This
is an explicit **component-test precondition**, not runtime fixture lookup or
a claim that preceding numerical/heap contents have already been derived.
No after-store or node-output value initializes the simulated memory.

For the numerical check, CAP is then regenerated from current Python geometry,
contact generation, process data and numerical algorithms. Every input CAP
word is compared with the native pre-stamp CAP array. Via records and indices
are derived from the segment chain and process data; target addresses come
from predicted allocation placement. The via formula modifies the shared
bytes. The ported symmetric inverse reinverts the captured pre-via reduced
impedance matrix, then the remaining source allocation/free plan executes.

Packaged Pyodide with compiled kernels matches all selected observations:

- 3,117 allocation addresses and 12,877 allocation/free events.
- 131 completed via stores and the one original unmapped load fault.
- 259 cache boundaries and 39,524 raw cache words, including all four damaged
  chains and their exact final pointer bytes.
- 127,140 regenerated pre-stamp CAP words.
- 118,948 CAP and 118,948 inductive words at the 129 completed node entries.

There are **zero differences** in this component audit. CAP aliases are a
result of shared address calculations, not a fixed row correction. Both
previously failing split-balun configurations are included. Separate tests
cover unknown memory, aliases, inactive vias and partial-store fault order.

This does not establish end-to-end model parity. The pre-via inductive matrix
and otherwise unknown heap bytes remain native inputs to this experiment.
Production integration needs derived process history and preceding numerical
stores, full byte-backed arena metadata, repeated simulations and cleanup,
and resolution of the other known numerical-instruction discrepancies.

## Required checks

The new mandatory `shared` WASM suite runs five fixture/memory tests plus the
full regenerated-CAP and reinversion audit. The older `heap`, `mappings`, JOIN
and UNJOIN numerical gates remain required and unchanged. Their missing-input
or numerical failures are not waived by this component result.

```sh
python tools/capture_shared_memory_original.py --debug-directory /tmp/debug/usr/lib/debug --reference /path/to/asitic-re --library-path /path/to/native-libraries --full-output /tmp/shared-full.json.gz
PYTHONPATH=src:tests python -m unittest test_shared_heap_original -v
python tools/audit_shared_heap_original.py --output /tmp/shared-differences.json
python tools/build_site.py
node tools/check_shared_heap_original.mjs /path/to/pyodide.mjs /tmp/shared-full-audit.json
```

The default CPython audit uses native pre-stamp matrix inputs. The packaged
check additionally regenerates CAP and runs the inverse for all cases.
