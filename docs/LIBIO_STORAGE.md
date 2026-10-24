# Complete freed storage before CAP

`libio_storage.py` adds the missing i386 glibc FILE construction/closure and
raw cache-header copies. Combined with the earlier
[FFT and stream-buffer producers](PRELUDE_STORAGE.md), the replay now matches
every freed buffer in all 130 original selected histories.

`audit_libio_storage_original.py` starts at the earlier geometry driver,
executes clone/COPY/JOIN, then uses the same heap and guest memory for contact
preparation and the complete cache prelude. It does not initialize from a
captured contacts-entry or CAP-entry byte snapshot. The initial process heap,
ABI and external cache headers remain explicit earlier-state component inputs.
Production trailing-via execution is still guarded.

## FILE and header stores

FILE initialization follows glibc 2.39's [`iofopen.c`](https://github.com/bminor/glibc/blob/glibc-2.39/libio/iofopen.c)
and [`genops.c`](https://github.com/bminor/glibc/blob/glibc-2.39/libio/genops.c).
The failed-open branch unlinks the stream without changing its saved chain.
The successful narrow-byte path follows orientation and close stores from
[`fileops.c`](https://github.com/bminor/glibc/blob/glibc-2.39/libio/fileops.c)
and [`iofclose.c`](https://github.com/bminor/glibc/blob/glibc-2.39/libio/iofclose.c).
The unused FILE/wide-data fields and padding retain their incoming bytes.
Source and LGPL attribution are shipped with the module and existing license.

The captured ABI is a 148-byte FILE, 152-byte FILE-plus, 12-byte lock and
140-byte wide-data object: a 304-byte allocation. `_mode` is the four-byte
orientation at offset 104; it is distinct from the eight-byte `_offset` field
at 76. A failed open leaves orientation zero; successful byte IO changes it
to minus one. Field names/sizes come from earlier matching debug types.

Raw technology headers are **input-file bytes**. The cache may have been
written by another process, whose unused fields and name padding differ from
the current process. The observer reads initial files before cloning, retaining
all header bytes required by the initial technology record counts and the
whole-file size/SHA-256 manifest. Header copies consume those explicit inputs;
they do not serialize current technology objects or read later freed arrays.

## Correct loader binding

The legacy libstdc++ DSO and modern libc both export `_IO_list_all`. Unqualified
GDB lookup, including a source-file-qualified experiment, selected the legacy
copy. Libc's FILE implementation uses its own hidden binding instead.

The final observer reads the actual loaded libc's ELF dynamic symbol offsets
and its independently observed mapping base, then reads that libc global at
driver entry. Jump-table addresses use the same module-specific resolution.
No observed final FILE chain is used to choose or repair an input pointer.
The unqualified value is retained separately to expose the ambiguity.

Both earlier experiments remain in full:
`libio_binding_ambiguous_original.json.gz` has 130 cases and
`libio_binding_pilot_original.json.gz` has two. Replaying the full earlier
ambiguous inputs fails at **exactly all 195 FILE chain words**. The new WASM
check requires that rejection; it never repairs the wrong explicit input from
the expected output.

## Genuine allocator footer stores

Three inherited FILE words in the coupled histories initially differed. They
were stale chunk-footer words left by the earlier geometry free/coalesce
sequence, inside storage later reused as a FILE's unused wide short buffer.

`Heap.observe_header_stores` now traces the actual head/footer stores performed
by split, coalesce, in-use marking, top allocation/extension and trim branches.
It does not refresh all headers from a logical snapshot. Headers inside merged
chunks retain earlier writes, and only source operations that actually store
a word update it. The observer shares memory with cache stores, remains opt-in,
and does not yet make header allocation decisions corruption-aware. The later
[allocator pointer-store port](ALLOCATOR_STORES.md) adds bin/fastbin and
size-ring stores to the same memory.

## Exact results and strict remaining failure

All **130 original histories** now match:

- **7,732 prelude allocation/free events and 6,302 allocation addresses**,
  after the source geometry setup, with no allocator reset.
- **195 complete FILE records and 130 raw header arrays**.
- **975 FFT workspaces and 130 stream buffers**.
- **All 1,430 pre-free buffers / 4,667,260 bytes**, with zero byte differences
  and no unknown bytes.
- The logical allocator state at CAP entry.

The final capture's full SHA-256 is
`f8920049ebb22018c160e7a6fb340e31371b1b4734208135319e0c4eff994909`.
All earlier fixtures remain unchanged. Its actual plain outcomes are 126 normal
exits, two SIGABRT exits and two SIGSEGV exits; no history is excluded by outcome.

Four added 8×8/16×8 native histories also match **all 44 pre-free buffers /
32,248 bytes**, including six FILE records and four header arrays, in portable
Python and WebAssembly. The rectangular cold case still fails the **strict
final heap-state comparison**: native cache-table writes corrupt a chunk header
and stop the original heap walk early. The generated numerical buffers match,
but cache-table byte writes into their actual aliased guest allocations have
not yet been replayed. The strict audit keeps this difference and exits nonzero.
Tests preserve the native damaged walk and subsequent plain SIGABRT; they do
not redefine it as complete heap parity.

The mandatory `libio` WASM suite runs the entire 130-case positive comparison,
all four additional strict cases and the full ambiguous-binding rejection.
It remains nonzero on that rectangular heap-state case. Every prior gate is
still required; nothing is skipped to make this branch deployable.

The subsequent [cache storage replay](CACHE_STORAGE.md) captures the missing
earlier cache allocations and complete external file bodies in new native
runs. It reproduces the actual rectangular overflow and damaged physical
walk; all 134 new histories match. The earlier fixture and its strict logical
audit above remain intact and nonzero. The new result does not repair that
older run with inputs observed in another process.

```sh
PYTHONPATH=src python tools/capture_libio_storage_original.py --debug-directory /tmp/debug/usr/lib/debug --reference /path/to/asitic-re --library-path /path/to/native-libraries --full-output /tmp/libio-storage-full.json.gz
PYTHONPATH=src python tools/capture_libio_storage_extended_original.py --debug-directory /tmp/debug/usr/lib/debug --reference /path/to/asitic-re --library-path /path/to/native-libraries
PYTHONPATH=src:tests python -m unittest test_libio_storage_original -v
python tools/build_site.py
node tools/check_libio_storage_original.mjs /path/to/pyodide.mjs /tmp/libio-audit.json /tmp/libio-extra-audit.json /tmp/binding-audit.json
```

Remaining integration includes source startup cache-table allocations,
corruption-aware allocator reads and production integration of the continuous
driver replay. Earlier
scene/process startup, contact stack-state words, secondary segment groups,
later command cleanup and the known logarithm/cosine and JOIN/UNJOIN numerical
discrepancies also remain unfinished. This checkpoint is not whole-program parity.
