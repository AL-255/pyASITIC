# Native flush, sync and write ABI

`flush_storage.py` implements the pinned successful, single-threaded i386
`fflush` chain on the same guest Memory as the heap, loader and stdin model.
The independent native audit matches all **414 calls**. The continuing
comparison improves from **284 to 198 required memory differences**:
86 address/phase differences resolve and none are introduced. Exact whole
program fidelity remains unfinished; no differing target is waived.

## Source execution

The source follows libc `fflush`, accepted foreign-vtable validation, the
legacy `filebuf::sync` wrapper, `_IO_file_sync`, `_IO_do_write`, internal
`new_do_write`, the legacy `sys_write` wrapper, `_IO_file_write`, libc
`__write` and the i386 VDSO frame. Modern file vtables use their direct
callbacks. Import resolution uses the existing source ELF loader. Shared
legacy wrappers and vtable guards now live in `libio_abi.py`; stdin uses
those same routines.

Saved registers, call arguments, return PCs, canaries, FILE pointers,
recursive lock depths, file-offset cache changes and epilogue flags follow
the pinned instructions. Narrow output uses its existing pending prefix,
including bytes written before the first driver. Successful source writes
emit descriptor, buffer address, count and all bytes to a virtual sink.
There are no host descriptor writes or host syscalls. No captured returned
count, register, later stack word or later FILE byte supplies execution.

The continuing prompt and input/output logs defer their flush. Output-log
formatting occurs after the input-log flush, preserving the native order.
Four REPL flushes now execute the complete child source. The selected
history writes a 10-byte prompt, flushes stdin without a write, writes the
184-byte earlier input-log header plus six appended bytes, then writes the
15-byte output-log line. Resetting the pending pointer before the source
flush would incorrectly drop that earlier header.

The outer printf/poll entry algorithms remain unfinished. Tests require
the 13 known callee-saved/stack/segment entry fields, the actual FILE
argument, all 17 return registers, every write field and byte, and all
eight existing PLT binding entry register sets. They do not claim the
incoming printf/poll EAX/ECX/EDX/flags are already exact. Independent tests
change those three unused volatile inputs and prove the flush's complete
memory, output registers and writes remain identical.

Partial/error writes, read-side seeks, wide streams, contended/multithreaded
locks, flush-all traversal, noncancellable writes, column adjustment and
other library implementations remain separate work and fail explicitly.
The supported write chunks are positive full writes of at most 4096 bytes.
These restrictions are not exceptions in the complete native audit: all
414 captured calls execute and every captured target remains required.

## Complete native captures

Both captures retain all 67 unchanged jobs, cold and warm, for 134 histories.
The independent observer starts after the first driver returns, captures
every flush entry and its first matching caller return, and stops at the
next driver or fault. It retains complete stack/ELF/TLS/heap/FILE/lock/vtable
regions, all registers, XSAVE, and each write's actual operands, bytes and
return. One history retains its absence of calls. No inferior instruction,
memory, register, allocation, syscall result or signal is substituted.
Minimal-environment guards precede every capture.

The audit checks **98,167,038 four-byte units, 7,038 registers, 1,010,160 FP
bytes, 413 writes and 198,537 written bytes**, with zero differences.
Units include overlapping owners and partial-word tails. The scalar source
preserves complete FP/XSAVE bytes. Lossless manifests retain 2,228,130
before/after owners containing 785,021,664 bytes, including repeated owners.
There are 4,712 unique records and 7,257 content-addressed chunks containing
18,339,965 unique bytes. Full owner order, addresses, sizes and content hashes
remain checked; deduplication removes no assertion.

The continuing fixture starts at the earlier first-driver boundary and
never imports per-call component snapshots. It adds the input/output log
global bindings, complete FILEs, locks and vtables to the existing owners:
33 owners, 2,362 bytes total. Every owner remains a complete assertion at
both parse points and the final boundary. Independent CPU probes still
precede all jobs. All existing heaps, events, freed buffers, files,
descriptor offsets, signals and terminal outcomes remain required.

The full compiled Pyodide continuation checks 9,479,168 heap words,
230,755 final component words, 461,510 point words, 664 events, 135 freed
buffers, 132 files and 399 descriptor positions, with no unknown bytes.
Only `prelude/fft/16/8/cold` differs: 83 point words and 115 final component
words. Its complete CPU and Pyodide reports agree. The 181 focused Python
tests and all eleven new component/integration tests in Pyodide pass.

The independent and continuing captures ran at different times. The
continuing write test therefore obtains every expected write byte from
its own complete native later heap, after source execution has finished.
The independent capture supplies descriptor/address/count/return assertions
and full return registers. Timestamped log headers are neither normalized
nor ignored, and later expected bytes never initialize the source.

Both GDB captures retain 132 next-driver outcomes, one SIGSEGV and one
SIGABRT. Independent plain runs retain 127 normal outcomes, six SIGABRTs
and one SIGSEGV; continuing plain runs retain 126 normal outcomes, seven
SIGABRTs and one SIGSEGV. Relative to the earlier getline capture, plain
`square/1/coarse/cold` and `pilot-boundary/1/coarse/cold` change from SIGABRT
to normal, and `pilot-width3/1/contacts/cold` changes from normal to SIGABRT.
These actual outcomes stay recorded; no history is removed or repaired.

## Reproduction and provenance

```sh
PYTHONPATH=src:tests python -m unittest test_flush_storage_original test_flush_transition_original
python tools/audit_flush_storage_original.py --output /tmp/flush.json
python tools/build_site.py
node tools/check_flush_storage_original.mjs /path/to/pyodide.mjs /tmp/flush-wasm.json
node tools/check_flush_transition_original.mjs /path/to/pyodide.mjs /tmp/flush-transition.json
```

The independent audit must return zero. The continuing audit must still
fail while its 198 differences remain. The workflow adds both as required
suites; failures do not become accepted baselines. Reports stay local.

| Fixture | Compressed bytes | SHA-256 |
| --- | ---: | --- |
| `flush_storage_original.json.gz` | 8,995,865 | `9f6c79ec0bb47980761069b527172d19f7b6b0d8def61d246783aa2a70bf46ac` |
| `flush_transition_original.json.gz` | 47,564,240 | `b9dcbb46b7c2695dd8ad35f3a2d5245cc384642b01181fe1b47e1136aee35bc2` |

Decompressed SHA-256 values respectively:

```text
09106fc3baca4b9750e2d02a94c726e65ff66b692993624d1a04b7e1a1d9ab95
4c362c686670eafee3017900c7b11689f82e4e04c1c8120962c4be83a8d6f428
```

The original binary, legacy DSO and libc/loader identities remain pinned
by the capture metadata and existing parent manifests. The numerical WASM
binary is unchanged. Remaining printf, parser, kernel/poll, FP and signal
continuations still prevent exact whole-program completion and publication
of this development branch.
