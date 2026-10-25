# Native printf FILE buffer setup and completion

`printf_file.py` implements the pinned i386 FILE-buffer initializer,
buffer switching, flush-to-FILE and count completion. Direct buffers
update the actual FILE put pointer. Staged buffers invoke the modern
vtable's xsputn/overflow callbacks. `output_file.py` follows the buffered
output, stat, allocation, set-buffer and scalar mempcpy source paths.
`malloc_top_storage.py` emits large-allocation caller/frame stores,
including unsorted exact fits, same-bin and higher-bin splits, fastbin
consolidation and top splits. `Heap.malloc` makes the allocation decision.
Its source binmap marking and clearing now update the shared arena bytes.

External descriptor facts precede execution. The libc stat converter
builds both statx and time64 stat records from those named facts, without
host I/O or later native buffers. The existing stdin allocation path
keeps its descriptor-zero default; output supplies an explicit earlier
descriptor. Malloc follows the canonical executable PLT binding from ELF
metadata and continuing GOT bytes. No native child return register,
allocated address, expected text or later stack image supplies execution.

The corrected two-history prototype matches all 120 setup/completion
calls, including both first staged writes and buffer allocations. The
comparison covers 28,392,224 four-byte units, 2,040 return registers,
292,800 FP bytes and 6,664 entry/return registers of 196 captured children,
plus heap state and physical headers. CPU Python and Pyodide reports
agree exactly. Nine prototype source/mutation checks pass in Pyodide;
17 existing stat, malloc and storage checks pass in CPU Python, and the
earlier complete stat/malloc suites pass in Pyodide. This is prototype
evidence only; complete-cohort validation is described separately below.

The draft child observer initially placed its doallocbuf breakpoint
inside setb. Symbol inspection caught this; the observer was corrected
to libc+0x85440, the draft full capture was terminated, and the prototype
and complete cohort were captured again with the corrected observer.
The earlier root observations were not patched or treated as complete
child coverage.

The full capture retains all 67 unchanged jobs cold and warm, starting
after the first driver return and stopping at the next driver or fault.
Every observed init/done call records full earlier stack/ELF/TLS/heap,
arena, FILE, output buffer, lock, vtable and control regions; later owners,
registers, XSAVE and allocator state remain assertions. The named nested
helpers retain all 17 entry and return registers. The shared lossless
snapshot codec checks every field and page conversion, then stores one
gzip stream in checksummed parts. No inferior instruction, register,
memory, result, allocation or signal is replaced. Minimal environment
guards precede capture.

The complete capture contains **7,946 calls**: 3,973 initializers and 3,973
completions. It retains 12,975 captured helper calls, including 132 actual
allocations. One history has no calls. GDB outcomes are 132 next-driver
stops, one SIGSEGV and one SIGABRT. Plain runs retain 130 normal outcomes,
three SIGABRTs and one SIGSEGV. None of those outcomes is changed or omitted.

The first complete eight-shard browser run retained 59 failures for fitting
free-bin allocation paths. Those paths have now been implemented. A separate
diagnostic checks every one of the 132 allocation calls, including all heap,
memory, register, FP and captured-child targets, with zero differences.
The complete CPU rerun and all eight browser shards pass all 11 tests.
The browser indices partition all 134 histories exactly once. Both match
all 7,946 calls, 1,902,446,488 four-byte units, 135,082 return registers,
19,388,240 FP bytes and 441,150 captured helper entry/return registers,
with zero differences. Units include overlapping owners and partial-word
tails. The complete unsharded CPU report equals the merged browser report
in every counter and per-case result. Diagnostic allocation selection did
not replace either full gate. The earlier failed reports remain local;
no target, tolerance, cohort or required assertion was changed to pass.

Already-corrupted cache chains are re-observed from produced guest bytes.
The audit derives all physical chunk, bin-link, fastbin and tcache errors,
including the actual unmapped address, and compares the entire ordered error
list. Native errors are neither dropped nor treated as permission to pass.
Tests independently alter those error targets and require failure.

The compact archive is 47,707,132 bytes in two checksummed parts:

```text
50810f69485e6883b76aba0cb4420c86378ecd61e0c519081daa5a75b2615047
```

Lossless conversion verifies all 15,892 complete snapshots and all 52,795
unique page payloads. The archive has 46,563 region records, 925 factored
contexts and 928 FP images. Earlier ELF metadata records the pinned libc
SHA-256 `e936bd40e5479b27721efeade1b502623436a8be2bd8bd0f0ccf8c4f7229a0d0`;
its detached symbols match build ID `9596d2907557f8966ee5796efe796849ce95de88`.

Twenty-nine allocator, shared-memory, mapping, stat and storage regression
checks pass in CPU Python. The complete 134-history continuing Pyodide
report remains identical to the earlier report, including all 198 unresolved
differences. Shared binmap stores introduce no new target differences there.

Tests require every native target, verify provenance and shard coverage,
and deliberately mutate later memory, registers, FP, heap fields and child
registers. Independent earlier-byte mutations change the emitted text;
missing earlier bytes fail instead of using return snapshots. Init can
write an uninitialized buffer, failed mode bypasses FILE access, and signed
count overflow writes EOVERFLOW through the actual earlier errno TLS slot.

Reproduction:

```sh
python tools/capture_printf_file_original.py --reference ~/github/asitic-re \
  --library-path /path/to/i386/libraries --debug-directory /path/to/debug
PYTHONPATH=src:tests python -m unittest test_printf_file_original
python tools/audit_printf_file_original.py --output /tmp/printf-file-cpu.json
python tools/build_site.py
node tools/check_printf_file_original.mjs /path/to/pyodide.mjs /tmp/printf-file-part.json 1 8
```

The verified source package is `0e764e1a906deba9`. The unchanged compiled
numerical module SHA-256 is
`c7869e98f4c18b5414dc172d836e7144ab3ebc0de2de0d1f2eec1a4fe1709186`.
All eight disjoint browser shards are required. Reports stay local.
Alternate vtables, terminal/unbuffered/error paths, owned-buffer replacement,
large direct output writes, small/tcache/system malloc ABI and the printf parser and
numeric formatters remain explicit unfinished work. These independent
component checks do not prove whole-program parity. The earlier continuing
gate retains its 198 required differences; integration remains unfinished.
