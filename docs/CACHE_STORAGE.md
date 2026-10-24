# Cache-table writes in shared guest memory

`cache_storage.py` reproduces cache generation and successful cache reads at
their actual guest allocations. The same memory is used by the geometry,
contact, allocator-header, FILE, FFT workspace and stream-buffer producers.
This adds the cache stores needed before joining the earlier driver-entry
history to the later [numerical history](STORAGE_HISTORY.md).

This is development work. Earlier cache allocations, pointer tables, complete
initial contents, raw technology records and external cache files are explicit
caller inputs. Source process-startup allocation and the complete subsequent
numerical history are not yet integrated. Production trailing-via guards and
all existing parity gates remain enabled.

## Actual addressing and operation order

The native generator fills XY rows with an **nx+1** stride, but the transform
reads an **ny+1** stride. Declared XY allocations contain only
`(nx+1)*(ny+1)` complex values. For rectangular inputs, generation can overwrite
neighboring guest objects and heap metadata. Extending an isolated Python
array or clipping to the declared allocation loses those stores.

The existing retained-precision spectral implementation now exposes its
samples before transformation. Python and WebAssembly reuse the same sample
operations and inputs as ordinary production generation. The shared writer
stores each actual row without zeroing untouched padding, allocates scratch
only after the fill, transforms through the original view and frees scratch
before generating/reflection/FFT of the axis tables. Disjoint scratch uses
the existing batched FFT; the aliasing path performs literal shared copies.
The selected native histories cover square and nx>ny layouts; ny>nx scratch
overflow and arbitrary unmapped-fault prefixes still require independent
native observations.

Cold stream writes serialize current shared tables, with the original raw
technology records as earlier inputs. Warm reads copy actual earlier file
bytes into those allocations. Successful reads take the caller's opened
path, not a match on header frequency: native paths round GHz to two decimals,
and the native header validator does not compare frequency. Path construction,
invalid headers, short/failed IO and arbitrary FILE corruption remain outside
this successful-stream component. Trailing file bytes can be read into the
buffer without inventing another fread call.

## Independent observations and strict comparisons

The new read-only GDB observer retains all previously selected inputs:
**130 original histories plus four 8×8/16×8 histories**, cold and warm.
At driver entry it observes all cache pointer arrays, every byte of each
preexisting table, the raw technology records and complete external files.
This includes mmap-backed tables outside the ordinary `[heap]` mapping.
Verified all-zero initial tables use a lossless zero representation; complete
external files use SHA-256 page deduplication. Neither representation chooses
runtime stores. No inferior instruction, allocator result or function return
is substituted.

At CAP entry the observer independently hashes every complete declared table.
The audit derives each actual address from the current guest pointer table,
checks its owner and size, and then hashes generated memory. It also compares
every observed pre-free buffer and the complete physical heap-header walk,
including unused previous-size words and the original walk's stopping error.
Allocator caches, bins, parameters and mapping checks remain required. The
logical allocation ledger is retained separately; native overwrites do not
repair it or suppress the observed physical corruption.

Packaged WebAssembly matches all selected histories with zero differences:

| Capture | Histories | Complete tables / bytes | Pre-free buffers / bytes |
| --- | ---: | ---: | ---: |
| Original inputs | 130 | 5,850 / 535,173,600 | 1,430 / 4,667,260 |
| Additional small inputs | 4 | 180 / 150,720 | 44 / 32,248 |

The 130-case replay also checks all **7,732 prelude events and 6,302 allocation
addresses** after source geometry setup, without an allocator reset. Portable
Python checks all four small cases, including the exact damaged rectangular
walk and its retained plain SIGABRT outcome. All native outcomes are kept:
the new main capture has 124 normal exits, four SIGABRT and two SIGSEGV exits;
the additional capture has three normal exits and one SIGABRT.

Full unprojected capture SHA-256 values:

- Main: `dd4ff786d82fcecbf4f97889d108153393a13584fd4c226eff2e52679e936176`
- Additional: `2019dafcea0592141e1e6acd702c80e3cb4523b093b7e22548d44d520cf51fa8`

The new mandatory `cachestore` suite runs all 134 comparisons and the portable
tests in WebAssembly. Negative controls require detection of clipped writes,
changed earlier external bytes, changed expected owners/digests and changed
physical header words/errors. Clipping happens to leave every final declared
table unchanged in the rectangular history, but fails both physical-walk
comparisons. This prevents table-only checks from hiding the overflow.

The older `libio` suite deliberately remains unchanged in scope and nonzero:
its earlier fixture lacks cache allocations/file bodies, and its logical
heap ledger cannot reproduce that rectangular physical walk. It has not been
reclassified as a passing negative test or supplied inputs from a different
native run. All earlier JOIN/UNJOIN, logarithm and strict heap gates remain
required too. This checkpoint does not make the branch deployable.

```sh
PYTHONPATH=src python tools/capture_cache_storage_original.py --debug-directory /tmp/debug/usr/lib/debug --reference /path/to/asitic-re --library-path /path/to/native-libraries --full-output /tmp/cache-storage-full.json.gz
PYTHONPATH=src python tools/capture_cache_storage_extended_original.py --debug-directory /tmp/debug/usr/lib/debug --reference /path/to/asitic-re --library-path /path/to/native-libraries
PYTHONPATH=src:tests python -m unittest test_cache_storage_original -v
python tools/build_site.py
node tools/check_cache_storage_original.mjs /path/to/pyodide.mjs /tmp/cache-audit.json /tmp/cache-extra-audit.json
```

Remaining work includes source cache/process startup, bin/fastbin byte stores,
allocator decisions reading potentially corrupted shared headers, continuous
integration with CAP/LMAT numerical memory, secondary geometry groups and
later command cleanup. Known arithmetic and JOIN/UNJOIN discrepancies remain
unfinished; these component results do not establish whole-program parity.
