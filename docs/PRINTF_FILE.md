# Native printf FILE buffer setup and completion

`printf_file.py` implements the pinned i386 FILE-buffer initializer,
buffer switching, flush-to-FILE and count completion. Direct buffers
update the actual FILE put pointer. Staged buffers invoke the modern
vtable's xsputn/overflow callbacks. `output_file.py` follows the buffered
output, stat, allocation, set-buffer and scalar mempcpy source paths.
`malloc_top_storage.py` emits the top-split caller/frame stores while
`Heap.malloc` makes the allocation decision.

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
evidence only; the complete 134-history capture and validation are pending.

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

Tests require every native target, verify provenance and shard coverage,
and deliberately mutate later memory, registers, FP, heap fields and child
registers. Independent earlier-byte mutations change the emitted text;
missing earlier bytes fail instead of using return snapshots. Init can
write an uninitialized buffer, failed mode bypasses FILE access, and signed
count overflow writes EOVERFLOW through the actual earlier errno TLS slot.

Reproduction after the complete capture:

```sh
python tools/capture_printf_file_original.py --reference ~/github/asitic-re \
  --library-path /path/to/i386/libraries --debug-directory /path/to/debug
PYTHONPATH=src:tests python -m unittest test_printf_file_original
python tools/audit_printf_file_original.py --output /tmp/printf-file-cpu.json
python tools/build_site.py
node tools/check_printf_file_original.mjs /path/to/pyodide.mjs /tmp/printf-file-part.json 1 8
```

All eight disjoint browser shards are required. Reports stay local.
Alternate vtables, terminal/unbuffered/error paths, owned-buffer replacement,
large direct output writes, other malloc paths and the printf parser and
numeric formatters remain explicit unfinished work. These independent
component checks do not prove whole-program parity. The earlier continuing
gate retains its 198 required differences; integration remains unfinished.
