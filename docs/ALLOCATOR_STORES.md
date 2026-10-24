# Native allocator pointer stores

The shared-memory replay now generates glibc 2.39's fastbin links, ordinary
bin links and large-bin size-ring stores. These are source operations at
their current guest addresses. They do not refresh headers or copy any later
observed allocator state into execution memory.

The motivating read-only hardware watchpoint followed a word that later
became a header's unused `prev_size`. Its actual last native writer was
`_int_malloc`, `malloc/malloc.c:4413`, clearing `remainder->bk_nextsize` during
a split. The other field, `fd_nextsize`, is cleared alongside it. The same
large-unsorted-chunk rule occurs in all three split branches, ordinary free
and fastbin consolidation. The i386 small/large boundary is 1008 bytes;
fields are at chunk offsets 16 and 20. Clearing every new header's previous
size would hide the missing history and is not the native operation.

Some remaining headers instead contained an earlier large-bin pointer to the
chunk itself. Native insertion into an empty large bin sets both size-ring
links to that chunk; inserting another size or removing a representative
reroutes the relevant links. Equal-sized chunks enter second position and
do not acquire representative links. The port now emits those operations,
including representative transfer to a same-sized successor, together with
the ordinary forward/back links for insertion, removal, splitting and free.
Bin-head addresses derive from the earlier arena address and the verified
i386 `malloc_state.bins` offset. Initial arena bytes are caller inputs loaded
at driver entry, alongside the initial heap; there is no later arena reset.

Fastbin forward links use `following_chunk ^ (address_of_fd >> 12)`. Their
targets are chunk headers, unlike tcache's user-pointer links. A null link is
still encoded. Allocation leaves that stored word alone unless another
source operation overwrites it. The native fastbin-head double-free check is
also retained.

Placement and size-ring representatives still use the logical allocator
metadata. Source store generation does not establish arbitrary byte-corruption
validation/readback for all bin/header decisions, or complete process startup.
Other arena fields remain modeled as logical state; writing the links is not
a claim that every arena-global byte has its producer.

## Independent comparisons

All existing captured histories are retained. The new tests compare native
encoded fastbin words, all regular bin links and size-ring fields, and arena
heads after a source-generated allocation/free sequence. Negative controls
disable the clear/fastbin producers and require the native mismatch to reappear.
Requests, addresses and frees are never supplied from later expected payloads.

Across the complete driver corpus:

| Source stores included | Main heap-word differences | Main physical-header comparisons that differ |
| --- | ---: | ---: |
| Previous checkpoint | 14,236 | 44 |
| Large remainder/free clears | 13,867 | 16 |
| Also encoded fastbin links | 10,971 | 16 |
| Also ordinary bin links and size rings | 6,363 | 0 |

The four additional small histories retain 98 heap-word differences and zero
header differences. All 134 histories still match every observed numerical
output, pre-free buffer, cache table, allocation identity, raw tcache word
and native via store/fault. No unknown heap bytes or via targets remain.
The older independent cache corpus and complete 130-case numerical-history
gate also continue to pass unchanged.

All **6,461 remaining differing words** in these captures lie in the two
traced stdout/log buffers and contain text or NUL bytes. Hardware watchpoints
identify glibc `__vfprintf_internal` / `__printf` / `__fprintf` as their writers.
They remain in the complete-heap comparison: the required `driverhist` gate
still exits nonzero. Matching allocator and numerical bytes does not authorize
excluding those buffers or deploying this development branch.

The subsequent [console-storage replay](CONSOLE_STORAGE.md) generates those
message writes from source templates and earlier stream inputs, and compares
all 134 independently recaptured histories with zero full-heap differences.
The older 6,461-word failure remains required for these captures, whose
earlier stream bindings are missing. No old output or selected failure was
deleted to produce the newer result.

```sh
PYTHONPATH=src:tests python -m unittest test_driver_history_original test_heap_original test_mapping_heap_original test_shared_heap_original test_geometry_storage_original test_cache_storage_original test_libio_storage_original -v
python tools/build_site.py
node tools/check_driver_history_original.mjs /path/to/pyodide.mjs /tmp/driver-audit.json /tmp/driver-extra-audit.json
node tools/check_storage_history_original.mjs /path/to/pyodide.mjs /tmp/history-audit.json
node tools/check_cache_storage_original.mjs /path/to/pyodide.mjs /tmp/cache-audit.json /tmp/cache-extra-audit.json
```
