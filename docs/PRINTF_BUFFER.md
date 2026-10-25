# Native printf buffer writer

`printf_buffer.py` follows the pinned i386 `__printf_buffer_write` and its
scalar memcpy child. It copies the actual earlier source bytes into the
declared output buffer, advances its put pointer, updates the caller's
source argument where the original does, and emits the original saved
registers, PIC thunk word, arguments, return PCs and epilogue flags.
Pointer addition uses 32-bit wrapping arithmetic. Failed buffers and
zero-length writes preserve their original early-return behavior.

The source uses the existing `GetlineBytes.memcpy`, with the independent
earlier SHR AF profile. Every generated memcpy entry and return retains
all 17 registers as assertions. No native return register, later stack
word or expected formatted string supplies execution. This is the buffer
writer component; printf parsing, numeric formatting and its remaining
parent frames still need implementation and integration. Buffer exhaustion
explicitly requires its flush-mode source. No captured call in this
cohort reaches that path.

## Complete capture

All 67 unchanged jobs repeat cold and warm, retaining 134 histories.
Observation starts after the first driver returns and ends at the next
driver or native fault. Every buffer-write entry and first matching caller
return retains full owned stack/ELF/TLS/heap/buffer regions, source byte
ranges, all registers and XSAVE. Static libc output buffers are included
even when outside the heap. Nested memcpy/flush entry and return register
sets are also captured. No inferior instruction, register, allocation,
memory, result or signal is replaced. Minimal environment guards precede
all observations; independent integer CPU probes precede all jobs.

The capture contains **28,143 buffer writes, 56,286 complete boundary
snapshots and 24,306 memcpy children**. One history retains its absence
of calls. GDB outcomes are 132 next-driver stops, one SIGSEGV and one
SIGABRT. Plain runs retain 127 normal outcomes, six SIGABRTs and one
SIGSEGV. Every actual outcome remains recorded.

CPU Python and Pyodide now match **all 28,143 captured calls**, with identical
complete reports and zero native comparison differences. The audit checks
6,723,271,384 four-byte units, 478,431 return registers, 68,668,920 FP bytes
and all 826,404 entry/return registers of the 24,306 memcpy children. Units
include overlapping owners and partial-word tails. Each of the 134 histories
occurs exactly once in the merged eight-shard browser report; every counter
and per-case result agrees with the unsharded CPU report.

The 196-case focused CPU run passed its full source audit and every other
test except a stale provenance check that expected context fields inline.
That check now verifies the factored context hashes and original fields,
and passes targeted reruns in CPU Python and Pyodide. Its recorded initial
error was not converted into an accepted result. The first two complete
browser jobs were rerun with the corrected test and retain identical native
reports. All eight complete browser jobs now pass all 15 component and
storage tests. No numerical source, target byte or tolerance changed.

This establishes full-cohort parity for the buffer writer. Printf parsing,
formatting, parent frames and whole-program completion remain unfinished.
The earlier continuing gate retains its 198 required differences.

## Storage and reproduction

The [lossless storage format](PRINTF_FIXTURES.md) verifies all snapshot
fields and ordered owner references against their dense representation,
then separately verifies every original page byte and ordered page list.
There are 134,617 unique region records, 166,195 unique pages, 133 contexts,
1,865 FP records and two ordered-region templates. Complete target order
and bytes remain required. The current capture's dense archive SHA-256 is:

```text
268c8cf84ce027d587b4391af12a00fac59ee68a64a22d70b496648707d25028
```

The compact archive is 174,431,134 bytes, stored as six byte-identical
parts under a checksummed manifest. Its JSON is 352,610,814 bytes. Parts
are fragments of one gzip stream; load the manifest rather than opening
each part as a separate gzip file. The archive SHA-256 is:

```text
16d280fb69d7fe291fdd732378f4351eb105d3013c3e2dfee10f0b2a875431d6
```

Future captures compact each complete native state while collecting it,
verify the page conversion, and update the archive parts and manifest
automatically. This capture used the earlier dense producer; its
GDB observer is byte-identical to the updated capture tool. No native
recapture or altered observation was used to change the storage format.

```sh
PYTHONPATH=src:tests python -m unittest test_printf_buffer_original test_printf_fixture
python tools/audit_printf_buffer_original.py --output /tmp/printf.json
python tools/build_site.py
node tools/check_printf_buffer_original.mjs /path/to/pyodide.mjs /tmp/printf-part.json 1 8
```

The workflow requires all eight disjoint browser shards. Their case
indices partition every history exactly once, and each shard fails for
any differing target. Local verification merges every result and counter
and compares the complete aggregate with CPU Python. Reports stay local.
