# Continuing S output and port-file close

The development replay now carries all 28 selected cold/warm branch histories
past [both numerical solves](SHUNT_SECOND_DRIVER.md), through the S record,
`fclose`, and port-export return. The same heap, `Memory`, console and actual
`OutputStream` continue from parser/header setup. No stream, heap or numerical
snapshot is reconstructed at the second driver return.

Every unchanged script and native outcome remains present. All 28 original
plain runs exit normally, and every observed export returns without a signal.
The endpoint is the dispatcher instruction after the port-export call, before
the following script EOF/interactive/quit processing.

## Live Y values, native S values and exact decimal fields

`PortOutputStorage` reads the four actual guest Y globals written by the second
node solve. It uses the existing retained-precision translation of
`two_port_output.cpp::convert_two_port_scattering`, including the original
first-diagonal formula. It publishes the four S globals at the fixed ET_EXEC
destinations used by the original conversion/record instructions. The record
order is frequency, S11, S21, S12, S22, with real/imaginary binary64 fields.

Frequency scaling preserves the original multiplication by the binary64
`1e-9` constant and its explicit store. Every original `fprintf` format and all
72 argument bytes per record are checked, before comparing text. Fields use
the existing glibc MPN decimal conversion in `printf_float_digits.py`, with
`%-20.15e`; host float/string formatting and captured text supply no digits.
The current continuing output path explicitly supports the selected S/RECT
records; other parameter/polar formats remain unfinished integration work.

The source writes through the exact buffered stream that generated the earlier
header. The buffer retains its old tail bytes. Closing unlinks the FILE, holds
its lock while flushing the pending row and freeing the buffer, resets the
narrow FILE fields, releases the lock, and frees the FILE using the continuing
allocator. The final external-file bytes include
the source-generated header and record together.

## Transient fclose locking

The first complete comparison already matched every S value, `fprintf`
argument, generated file and released buffer, but retained four assertions per
history. Two lock fields differed at the buffer-free boundary, observed both
in the complete heap and in the independent FILE region.

Pinned i386 glibc `fclose` holds the FILE lock while `close_it` flushes and
releases the buffer. It releases that lock before the FILE itself is freed.
The source now performs those transitions using `THREAD_SELF` from an actual
earlier TLS header. The read-only capture obtains that header at the original
first-driver entry, using `PTRACE_GET_THREAD_AREA`; the later observed lock
owner is never an input. Existing S globals at that same earlier boundary are
also explicit inputs, pending complete process-startup integration.

Uncontended and recursive ownership follow the original lock/count/owner
fields. Contended or multithreaded waits stay explicit unsupported paths.
Tests vary ownership/counts and list placement, require the held lock during
buffer release and its release before FILE destruction, and reject contention.

The buffer and FILE free-call return addresses come from the pinned libc
instructions at offsets `0x85434` and `0x758a6`, respectively. The observation
retains their complete usable bytes, including allocator padding/footer bytes.

## Exact comparison scope

The read-only observer continues the same inferior after its second driver
return. It records complete heaps and independent FILE/buffer/list-head/S
regions at record entry, record return, close entry, buffer free, FILE free and
export return. No inferior value, instruction, register, store, allocation,
return, outcome or affinity is replaced.

| Added output/close observation | Checked |
| --- | ---: |
| Ordered free events | 56 |
| Complete freed usable buffers | 56 / 123,872 bytes |
| Complete heap boundaries | 168 |
| Heap 32-bit words | 43,462,656 |
| Independent FILE/buffer/list-head/S bytes | 750,624 |
| `fprintf` calls / raw binary64 argument bytes | 28 / 2,016 |
| Complete output files | 28 / 45,252 bytes |
| Unknown bytes | 0 |

All preceding first-driver, parser, second-driver, cache, model and console
checks remain mandatory. Counting the duplicated second-entry observation
once, the full replay now checks **552 distinct complete output-heap boundaries
/ 142,055,424 32-bit words**. The original 28 first-driver heaps and earlier
ABI/TLS/stream/scene inputs remain inputs. This is not a whole-address-space or
complete CPU-state comparison.

The full portable CPU and final packaged WebAssembly reports agree exactly
across all 28 histories and every coverage counter, with zero differences.

Seven new CPU/browser tests preserve provenance, all scripts/outcomes and
complete captures; compare cold/warm, grounded and coupled files; require the
same source stream/memory/heap/console; change later file/format-argument/S/heap/
freed-buffer assertions without changing source state; change live Y and require
different S arguments/globals/files; exercise close locks and list placement;
and require a missing unlink to fail even when all file bytes match. The
required `shunt-port-tail` Pages suite runs those tests and every full history.
All older strict gates remain required.

The seven new tests pass on CPU and packaged WebAssembly. Twenty-three earlier
CPU second-driver/command tests pass. The previous complete 28-case two-solve
browser report is unchanged exactly, as are the older 134 command histories:
130 main cases match, and the four extended histories retain the same 816
strict differences in the cold rectangular fault case. No old failure is waived.

## Remaining work and reproduction

The following EOF/interactive/quit continuation, changed-frequency driver/cache
paths, other port parameter formats, full startup/caller/FP state and typed
geometry-to-process integration remain unfinished. The six typed-API raw phase
failures, FCOS/logarithm discrepancies, remaining trailing-via aliases and older
faulting/gap cohorts remain required gates. No tolerance or owner/range
exemption is introduced. This development branch is not deployed and does not
establish whole-program parity.

`shunt_port_tail_original.json.gz`: 31,148,174 bytes, SHA-256
`2aeb863715ed06c381d0f817de225038ac37057b3fda1f8538907b0702017c32`.
It retains original scripts, plain outcomes, minimal environment,
binary/debug-library provenance, complete heap pages, full free buffers,
format/argument records and complete files. Fixtures remain outside the runtime
source archive.

Source package: `cae81998e3fc63a2`; numerical WASM SHA-256 remains
`c7869e98f4c18b5414dc172d836e7144ab3ebc0de2de0d1f2eec1a4fe1709186`.

```sh
python tools/capture_shunt_port_tail_original.py --reference ~/github/asitic-re \
  --library-path /path/to/i386/libs --debug-directory /path/to/libc/debug
PYTHONPATH=src:tests python -m unittest test_shunt_port_tail_original -v
python tools/audit_shunt_port_tail_original.py --output /tmp/shunt-port-tail-cpu.json
python tools/build_site.py
node tools/check_shunt_port_tail_original.mjs /path/to/pyodide.mjs /tmp/shunt-port-tail-wasm.json
```
