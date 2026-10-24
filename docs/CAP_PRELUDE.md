# Contact and cache history before CAP

The allocator model now predicts the contact construction and cache-I/O
allocations preceding the previous CAP matrix boundary. The same predicted
heap and contact owners then continue through the
[regenerated matrix and shared-memory comparison](PRE_VIA_PARITY.md). The
experiment no longer needs to initialize allocator state or contact addresses
at that later boundary.

The subsequent [contact-storage comparison](CONTACT_STORAGE.md) now generates
the initialized group/contact bytes at those predicted addresses and their
later matrix numbering stores, checking all 130 histories at both stages.

This remains development work. Allocator state **before contact preparation**,
preexisting geometry/cache-table objects and otherwise unknown heap bytes at
via entry are still captured test preconditions. The production trailing-via
guard remains enabled; no runtime numerical result is read from a fixture.

## Source-derived plan

`capacitance_prelude_storage` follows `contacts.cpp`, `potential_cache.cpp` and
the allocated FFT path in `potential_tables.cpp`. It allocates one 136-byte
group per conductor and its 60-byte contacts. Contact names follow the final
linked-list order, so allocation traverses those contact identities in reverse.
Counts come independently from current Python geometry and contact generation.

The cache paths differ:

- A valid disk cache allocates a reader, substrate/metal header arrays and a
  stdio buffer, then releases them in native order.
- A missing cache first allocates and releases the failed reader, allocates
  and releases a `32*FFT_X` scratch array for each metal pair, then opens,
  buffers and closes the writer.
- A current in-memory cache adds no cache-I/O or FFT allocations.
- Disabled disk caching regenerates FFT tables without reader/writer objects.

The i386 glibc 2.39 stream effects follow the primary sources
[iofopen.c](https://github.com/bminor/glibc/blob/glibc-2.39/libio/iofopen.c) and
[filedoalloc.c](https://github.com/bminor/glibc/blob/glibc-2.39/libio/filedoalloc.c).
The observed ABI has a 152-byte `_IO_FILE_plus`, a 12-byte lock and 140-byte
wide-data object, giving a 304-byte reader/writer allocation. Buffer size is
the smaller positive filesystem block size and the 8192-byte stdio default.
ABI dimensions and filesystem block size are explicit observer inputs; no
geometry-specific allocation/address correction is used.

## Original observations

`capture_cap_prelude_original.py` begins at the intact original contact-builder
entry. It observes actual libc malloc/free calls, along with the enclosing
ASITIC scalar/array interfaces. Thus stdio allocations are included rather
than silently omitted from the original program's allocator history. The
observer calls no inferior function and changes no numerical/allocator result.

The separate allocation fixture retains all 65 selected input configurations
in cold and warm states. Its **7,732 events, 6,302 allocation addresses and
4,872 retained contact/group object identities** match the source plan exactly.
The complete predicted allocator state matches at the former CAP boundary.
Its plain outcomes are 124 normal exits, five SIGABRT exits and one SIGSEGV exit.

`capture_cap_prelude_shared_original.py` independently combines this earlier
boundary with projected byte observations. Its 130 cases and 519 snapshots
preserve all original outcomes, including the cold `square/64/contacts` first
node-load fault. Full raw heaps are reproducible and identified by hashes; the
checked-in projection keeps the same byte-selection rule as the preceding
shared-memory fixture. Older fixtures remain unchanged.

From this earlier boundary, the packaged-Pyodide comparison reproduces:

- **20,609 allocation/free events and 9,419 allocation addresses**, including
  every constructed contact owner and its later free.
- 127,140 regenerated CAP input words and 127,140 regenerated inductive input
  words, with no native matrix used as a calculation input.
- 131 completed via stores, the native unmapped load fault and 39,524 raw cache
  words.
- All 132 via indices and parameter records generated from Python geometry,
  using the same segment traversal as the production solver. Captured segment
  words are comparison expectations rather than stamp inputs. The complete
  live via-index array is also regenerated, matching all 132 original words.
- 118,948 CAP and 118,948 inductive words at the 129 completed node entries.
- All three damaged tcache chains observed in this independent capture.

There are zero differences, and the heap is not reset or resynchronized at
CAP matrix entry. This capture's complete plain runs have 128 normal exits,
one SIGABRT exit and one SIGSEGV exit. The changed outcomes/damaged-chain count
are retained observations of undefined native memory behavior; they do not
replace earlier captures or establish deterministic faults across runs.

## Additional cache paths

Four separate wire observations capture the **second** native CAP invocation.
With `TECHIO ON`, the already-current in-memory cache adds no allocations after
the contacts. With `TECHIO OFF`, each solve regenerates tables without disk I/O.
All 68 events and 38 allocation addresses match, including both inherited
disk-seed modes. The observers record the selected visit and actual native
cache-enabled/frequency fields, so these are not merely first-call predictions.
All four complete original runs exit normally.

## Scope and checks

The plan covers successful contact construction, valid/missing disk caches,
current memory caches and disabled disk I/O in the observed ABI. Invalid or
truncated cache headers, failed allocations/I/O and earlier geometry, process
startup and cache-table allocations remain unfinished. Numeric table contents,
full byte-backed arena metadata and repeated complete-command cleanup still
need integration before production can use the path. Other known numerical
instruction and JOIN/UNJOIN discrepancies also remain open.

A separate mandatory `prelude` WASM suite runs the four provenance/history
tests and the full regenerated-matrix comparison. Every older storage, shared,
inductive, heap/mapping and JOIN/UNJOIN gate remains required.

```sh
python tools/capture_cap_prelude_original.py --debug-directory /tmp/debug/usr/lib/debug --reference /path/to/asitic-re --library-path /path/to/native-libraries
python tools/capture_cap_prelude_shared_original.py --debug-directory /tmp/debug/usr/lib/debug --reference /path/to/asitic-re --library-path /path/to/native-libraries --full-output /tmp/prelude-full.json.gz
python tools/capture_cap_prelude_modes_original.py --debug-directory /tmp/debug/usr/lib/debug --reference /path/to/asitic-re --library-path /path/to/native-libraries
PYTHONPATH=src:tests python -m unittest test_cap_prelude_original -v
python tools/build_site.py
node tools/check_cap_prelude_original.mjs /path/to/pyodide.mjs /tmp/prelude-audit.json
```
