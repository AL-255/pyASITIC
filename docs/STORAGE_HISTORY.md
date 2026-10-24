# Continuous numerical memory from the earlier CAP boundary

The development port now replays contact records, complete CAP matrices,
inductive matrices, pivot/work arrays, cache stores and cleanup into **one
guest memory** through the original first node boundary. Via loads no longer
initialize this comparison from a captured via-entry heap. No cache or matrix
bytes are reset at that later boundary.

This combines the separately checked [contact stores](CONTACT_STORAGE.md),
[CAP buffers](CAP_STORAGE.md) and [cache stores](CACHE_STORES.md). The production
trailing-via guard remains enabled. This is a source-history comparison with
explicit earlier-state inputs, not a fixture-backed production simulator.

## Initial state and provenance

Allocation placement starts with the existing contact-entry allocator
snapshot and source-generated contact/cache prelude. Guest byte memory begins
at the subsequent CAP matrix boundary, **before the first CAP matrix allocation**.
Its complete preexisting mapped arena bytes, process tcache key and preexisting
geometry addresses are component-test inputs. Earlier process/scene/cache
history has not yet been derived.

The separate [geometry storage replay](GEOMETRY_STORAGE.md) now derives clone
and coupled JOIN addresses and full records from driver-entry state, then
continues the same allocator through contact/cache preparation.
[Pre-CAP storage](PRELUDE_STORAGE.md) generates FFT scratch and stream-buffer
bytes, and [libio storage](LIBIO_STORAGE.md) adds FILE/header and head/footer
stores. [Shared cache storage](CACHE_STORAGE.md) now reproduces all selected
table stores and the rectangular overflow from explicit earlier cache inputs.
Joining that earlier memory to this numerical replay still requires the
remaining allocator byte history and source process-startup allocations.
The later [continuous driver replay](DRIVER_HISTORY.md) now connects the same
earlier memory through this numerical stage, with live cache reads and no
CAP-entry reset. It adds complete-heap and bounded freed-matrix comparisons;
those stronger checks still expose missing heap stores.

The complete initial bytes matter: name padding left untouched in a contact
group can later become an allocator validation word after reuse. Supplying
only free chunks left two reads unknown; the comparator reported those reads
rather than guessing zero. Missing initial context remains an explicit failure.

`project_initial_storage_memory_original.py` takes all initial mapped arena
regions from the unchanged full native capture. No later via location, node
matrix, via-entry byte or numerical result selects the ranges. The 35,676,160
initial bytes across 130 observations are represented by 860 unique exact
4096-byte pages, deduplicated by SHA-256. The compressed fixture is 909,591
bytes. Tests reconstruct every region and match the earlier native heap
manifests; no bytes are omitted by deduplication.

## Source stores and workspace values

`storage_history.py` follows the existing allocation/free plan and original
constructor/store order at the observed boundaries. It writes complete CAP
buffers before cleanup, preserves their remaining bytes after frees, applies
the source coupled-junction termination store and constructs subsequent
inductive buffers and index/pointer arrays. The full inductive inverse is
retained only when diagnostic storage is requested; ordinary production solves
do not retain that extra matrix reference.

The general inverse's final workspace comes from the same LU factorization:
its copied lower first column and the original workspace-size word. Symmetric
pivots and final factor/inverse work arrays come from the source factorization
and final scratch-column copy, including one/two-entry pivot handling. The
extra factor calls produce storage values for this diagnostic; no recorded
numerical word enters a calculation.

`capture_workspace_storage_original.py` independently observes bounded array
contents immediately before native `delete[]`. It retains every array at most
16 KiB, covering **all** selected pivot and factor/inverse workspaces. Larger
matrices remain covered by the existing complete matrix captures. All 65 input
histories and both cache states remain present, including the later node fault.
This independent observation has 126 normal plain exits, three SIGABRT exits
and one SIGSEGV exit; prior outcomes/fixtures remain unchanged.

All **1,427 pivot/workspace arrays and 499,272 bytes** match the generated
values exactly in the packaged backend. The 2,735 bounded pre-free arrays and
1,815,488 captured bytes remain in the fixture for provenance and later work.
Portable tests independently check the first cold/warm workspace histories.

## Complete selected-history comparison

At via entry the cache reader takes over the **same** generated memory/key.
Vias load and store those bytes, so an out-of-range diagonal can alias a live
CAP cell or freed storage naturally. The same memory then supplies the final
inductive inverse and subsequent frees, without a captured-state reset.

All 130 selected observations match, with no selected fault or damaged chain
removed:

- **12,877 body allocation/free events and 3,117 allocation addresses**. The
  preceding source prelude also still checks all 7,732 events and 6,302 addresses.
- **127,140 CAP input words and 127,140 inductive input words** before stamping.
- **131 completed via stores and the original unmapped load fault**.
- **259 cache boundaries and 39,524 raw cache words**, including all three
  damaged-chain observations in this original capture.
- **118,948 CAP and 118,948 inductive words** at all 129 completed node entries.

There are zero differences and no unknown target values. A regression changes
an observed pre-stamp word: validation fails, while the generated store still
matches the unchanged native post-stamp value. Expected data never repairs the
guest memory.

## Checks and remaining scope

Mandatory `history` and `workspaces` WASM suites add the full comparisons and
provenance/portable tests. Every older heap/mapping, shared, inductive, prelude,
CAP and JOIN/UNJOIN gate remains required and unchanged.

```sh
python tools/project_initial_storage_memory_original.py --full-capture /tmp/prelude-full.json.gz
python tools/capture_workspace_storage_original.py --debug-directory /tmp/debug/usr/lib/debug --reference /path/to/asitic-re --library-path /path/to/native-libraries
PYTHONPATH=src:tests python -m unittest test_storage_history_original test_workspace_storage_original -v
python tools/build_site.py
node tools/check_workspace_storage_original.mjs /path/to/pyodide.mjs /tmp/workspace-audit.json
node tools/check_storage_history_original.mjs /path/to/pyodide.mjs /tmp/history-audit.json
```

The earlier initial heap contents/metadata and geometry addresses are still
captured inputs. Non-cache arena structures still make logical rather than
arbitrary byte-corruption-aware decisions. Scene/process/cache-table startup,
secondary segment groups, other analysis branches, complete repeated-command
execution after node entry and the known logarithm/cosine and JOIN/UNJOIN
discrepancies remain unfinished. These exact selected-history results do not
establish whole-program parity or authorize deployment of this branch.
