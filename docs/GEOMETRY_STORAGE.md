# Geometry storage before contact preparation

`geometry_storage.py` now executes the original combined-network clone and
CALCTRANS clone/COPY/JOIN setup in shared guest memory. It derives allocation
requests, physical descriptor/segment addresses, list reversals, source
translations, field adoption and temporary-object frees from those operations.
No final geometry address or byte is an execution input.

This moves the allocator comparison earlier than
[contact/cache preparation](CAP_PRELUDE.md). The same heap then executes that
prelude through the first CAP matrix boundary. Initial process/scene state is
still explicit component-test input; this is not yet production trailing-via
support or complete original-binary parity.

## Source and original-binary evidence

The reference paths are `geometry.cpp`, `composite_geometry.cpp`,
`combined_network.cpp` and `later_analysis.cpp` in the C++ reconstruction.
The original binary is authoritative where it differs: default COPY names use
the binary's inlined libstdc++ 2.9 `basic_string` and small-object pool, rather
than the reconstruction's temporary character array. `legacy_strings.py`
ports Rep sharing, capacity growth, replacement/destruction, free lists and
successful pool refills from those instructions. Large string allocations
use the same process heap as geometry.

Unsplit segments are raw 240-byte copies. Split segments use the original
typed floating copies and the production longitudinal subdivision arithmetic;
these retain the distinction between raw NaN payloads and FLD/FSTP quieting.
Descriptor constructors initialize only the original fields. Names are copied
through NUL, preserving prior padding. Clone/COPY/JOIN list writes and
temporary frees also retain the original order. All operations share the
heap's generated tcache stores, including key clearing on reuse.

The read-only observer starts at native PI2/CALCTRANS driver entry, before any
cloning. It captures the whole initial mapped `[heap]`, scene records,
allocator metadata and string-pool globals. Initial ranges are independent of
future via targets. At contact entry it separately records complete first and
reference descriptors, every full segment record and the whole string-pool
free-list contents. No inferior function, instruction result or allocation
address is replaced. Each plain/GDB pair starts with identical files; cold
and warm cache states remain separate observations.

## Exact comparisons

All original 65 histories and both cache states are retained, including
faulting plain command exits and the observed later node fault. Across these
130 cases, the source replay matches exactly:

- **2,308 geometry allocation/free events and 2,206 allocation addresses**.
- **983,544 descriptor/segment bytes**, including unwritten name padding.
- **83,720 string-pool/global bytes** at contact entry.
- The allocator's mappings, chunk headers, bins, caches and parameters at
  contact entry, then **7,732 contact/cache events and 6,302 further addresses**
  through CAP matrix entry, without an allocator reset.

An additional ten native observations cover longitudinal subdivision,
different CAP/inductive length cells, a subdivided coupled JOIN and a 63-byte
source name whose generated COPY name needs a 144-byte libc allocation.
They match **442 events, 284 addresses, 33,728 geometry bytes, 7,720 string
bytes**, and the subsequent **654 prelude events / 544 addresses** exactly.
The parent 130 cases are unchanged. Expected output data never repairs the
guest state. A regression removes the later via geometry observations and
still obtains the same predicted geometry owners.

The original fixture's 35,676,160 initial heap bytes are component inputs,
compressed with its independent observations. Raw fixture data is loaded only
by capture/test/audit tools and is never packaged into the simulator.
CPython tests and the mandatory `geometry` WebAssembly suite run both complete
comparisons. Earlier heap, matrix, shared-memory and JOIN/UNJOIN gates remain
required; a passing component does not bypass their known discrepancies.

```sh
PYTHONPATH=src python tools/capture_geometry_setup_original.py --debug-directory /tmp/debug/usr/lib/debug --reference /path/to/asitic-re --library-path /path/to/native-libraries
PYTHONPATH=src python tools/capture_geometry_setup_extended_original.py --debug-directory /tmp/debug/usr/lib/debug --reference /path/to/asitic-re --library-path /path/to/native-libraries
PYTHONPATH=src:tests python -m unittest test_geometry_storage_original -v
python tools/build_site.py
node tools/check_geometry_storage_original.mjs /path/to/pyodide.mjs /tmp/geometry-audit.json /tmp/geometry-extra-audit.json
```

## Remaining integration

The new comparison derives geometry owners earlier, but the existing
[numerical storage history](STORAGE_HISTORY.md) still starts byte memory at
CAP entry. [Pre-CAP storage](PRELUDE_STORAGE.md) now generates the FFT scratch
and stream-buffer bytes. FILE/header records and other intervening stores must
also be generated before those byte histories can be joined without a reset. Earlier
scene/process construction also remains an input. Non-cache arena metadata
still uses logical decisions, rather than arbitrary byte-corruption handling.

Secondary segment groups, rejected via-layer JOINs, allocation failures,
concurrent pool access and COPY name collisions without an explicit caller
random-byte stream are outside this component's current execution scope.
Known logarithm/cosine and JOIN/UNJOIN discrepancies, repeated command cleanup
after node entry and other original analysis branches also remain unfinished.
The development branch remains unsuitable for deployment until all required
whole-program gates pass.
