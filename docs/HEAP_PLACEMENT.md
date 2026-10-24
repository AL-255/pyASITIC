# Native arena placement: development status

The [mapped-allocation extension](MMAP_PLACEMENT.md) now covers all allocation
addresses in a new independent capture of the same 130 input/cache cases.
It retains this earlier fixture and its missing-policy audit failures.

`src/reasitic/heap.py` ports the single-threaded i386 glibc 2.39 arena
algorithms needed after the existing [storage plan](STORAGE_LIFETIMES.md).
It is **not connected to electrical solves**. Neither native snapshots nor
recorded addresses are runtime inputs, and trailing-via models remain guarded.

The port implements request normalization, bounded tcache lists, fastbins,
small bins, ordered large bins and equal-size selection, unsorted-list
processing, last-remainder splitting, forward/backward coalescing, fastbin
consolidation, top allocation, contiguous page-aligned brk growth and trimming.
It follows glibc `malloc/malloc.c`, tag `glibc-2.39`, under LGPL-2.1-or-later:
<https://github.com/bminor/glibc/blob/glibc-2.39/malloc/malloc.c>.
The Python source carries its attribution; the distribution includes the
license in `web/GLIBC-LGPL-2.1.txt`.

## Independent native observation

`capture_allocator_original.py` extends the read-only lifetime observer with
matching detached libc symbols. The binary has build ID
`9596d2907557f8966ee5796efe796849ce95de88`, Ubuntu glibc 2.39-0ubuntu8.9 i386.
The harness checks both ELF build IDs before running and records hashes of
libc, debug symbols, the parent fixture, every input and cache file, and the
complete GDB commands. It calls no inferior function and changes no native
memory, register or allocator callback.

All 65 selected input configurations are preserved in cold and warm cache
states: 130 observations, 12,877 allocation/free events and 389 allocator
snapshots. Each snapshot retains raw arena bytes, chunk headers, ordered bin
lists, decoded safe-linked tcache/fastbin chains, cache counts, malloc
parameters and process maps. Plain/GDB pairs begin with identical files in the
same directory. The original lifetime and earlier mixed-cache fixtures remain
unchanged.

This independent capture has 126 normal plain exits, three SIGABRT exits and
one SIGSEGV exit. These differ from the previous lifetime capture and are
observations of undefined native behavior, not deterministic outcome promises.
The observed first-node fault remains the cold `square/64/contacts` case.
Its two snapshots and fault prefix are retained, along with every other case.

The observer also records damaged chains explicitly. In two warm refined-wire
cases (`square/1/filaments` and `pilot-width3/1/filaments`), the first node
boundary contains a tcache chain ending at unreadable address `0x8100` after
the trailing-via stamp. The snapshot records the error instead of repairing
the chain or discarding the observation.

## Exact comparison and remaining work

The comparator initializes an isolated allocator from each **initial** native
snapshot as a test precondition. Subsequent allocation requests and frees come
from the source-derived storage plan. External contacts and cloned geometry
are identified at the initial boundary; subsequent returned pointers are
predictions, never copied from observed allocations or used to resynchronize
after a mismatch.

The current comparison checks **2,772 allocation addresses and 9,900 lifetime
events**, with zero address/header/free-list differences over those prefixes.
It reaches 110 pre-via and 110 node boundaries, checking 112 via target
addresses. Both previously failing split-balun configurations match physical
placement through node entry in both cache modes. Of the 110 predicted trailing
targets, 48 fall inside CAP and 62 outside it; no fixed CAP-row correction is
used. This is placement evidence, not an electrical-model parity claim.

The full strict audit still **fails with 22 unresolved observations**:

- Twenty require mmap allocation. The port explicitly stops at that boundary;
  it does not invent an address or substitute the captured return value.
- Two have the native damaged tcache chains described above. Modeling
  allocation placement does not yet apply numerical writes to allocator data.

There are 108 observations with complete, undamaged allocator-state matches.
Passing prefix/provenance tests do not waive any of the 22 failures. A separate
mandatory packaged-WASM `heap` CI suite runs the full strict audit and remains
failing. Existing JOIN/UNJOIN numerical gates remain unchanged and required.

Production integration still requires deriving pre-CAP process state from
allocation history, mmap placement/unmapping and dynamic thresholds, applying
actual numerical stores into shared memory, and validating complete repeated
simulations and cleanup. Successful inverse branches and disabled eddy mode
remain the storage plan's current scope. Multi-arena/threaded behavior and
allocator error paths are not claimed as implemented.

## Reproduce

Extract `libc6-dbg_2.39-0ubuntu8.9_i386.deb` into a temporary directory; no
system installation is needed. Then run:

```sh
python tools/capture_allocator_original.py --debug-directory /tmp/debug/usr/lib/debug --reference /path/to/asitic-re --library-path /path/to/native-libraries
PYTHONPATH=src:tests python -m unittest test_heap_original test_allocation_plan_original -v
python tools/audit_allocator_original.py --output /tmp/allocator-differences.json
python tools/build_site.py
node tools/check_heap_original.mjs /path/to/pyodide.mjs
```

Both strict audit commands currently exit 1 for the unresolved observations.
