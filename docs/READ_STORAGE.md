# Native stdin read ABI and descriptor positions

`read_storage.py` now models the regular-file `_IO_file_read` tail call,
single-threaded libc `__read` frame, i386 VDSO saved registers and successful
read return. The source copies only the returned byte range and advances the
descriptor by its actual source byte count. External contents and the offset
are earlier inputs. No host file, syscall or observed native return result
is used at runtime.

The complete continuing comparison retains **284 required memory
differences**, with the same address/phase pairs as the malloc checkpoint.
Eight still-differing words now contain the source read frame; later library
operations overwrite those words in native execution and still need their
own implementation. No word is selected away or filled from its expected
later value. The new comparison also requires all later descriptor offsets.

## Source execution

The source follows the pinned libc implementation: `_IO_file_read` replaces
its FILE argument with that FILE's descriptor, then tail-calls `__read`.
The wrapper saves EDI/ESI/EBX, reserves its locals, calls through GS:0x10 and
returns through its original epilogue. VDSO entry bytes come from the earlier
loader/TLS context; unsupported entries fail explicitly. All 17 return
registers derive from the actual arguments, source byte count and caller
frame, including final ADD flags. No floating-point operation is introduced.

`InputStream` routes its external-file refill through this component when
the earlier read ABI inputs are present. The same continuing Memory receives
the kernel-style buffer writes and caller stores. The rest of the buffer is
preserved, including retained heap contents. Older ABI inputs retain their
source byte-copy path. The continuing caller tracks the descriptor position
separately from the FILE read pointer, so buffer consumption does not advance
the external descriptor twice.

Cancellation, noncancellable wrappers, error/errno, oversized requests,
nonregular sources and other read paths remain unfinished. The component
is connected only to the supported stdin ABI, and rejects missing earlier
offsets rather than recovering them from a later syscall observation.

## Independent native proof

The component capture repeats all 67 unchanged jobs cold and warm, retaining
all 134 histories and outcomes. One reaches the stdin read; the other 133
explicitly retain their absence of calls. At `_IO_file_read` entry, an
independent open obtains the external file contents and procfs supplies the
actual descriptor position. It never obtains source bytes from the later
program buffer or changes the inferior's descriptor offset. Complete
stack/ELF/TLS/FILE/heap/VDSO regions, all registers, XSAVE and the native
returned descriptor position remain assertions.

CPU Python and Pyodide each compare **201,467 four-byte units, 17 registers,
2,440 FP bytes and the returned descriptor position with zero differences**.
The source reads five bytes. Units include overlapping regions and partial
word tails. All six component tests pass in both runtimes. They mutate later
buffer/register/FP/offset targets, remove a region, alter earlier file
bytes/offset/caller registers, remove earlier VDSO memory and verify EOF
preserves both the buffer and descriptor position.

The continuing capture starts earlier, at first-driver entry. It never
imports component snapshots. The existing 26 memory owners (1,942 bytes)
remain complete later targets, and the observer independently records
descriptor positions at every point and final state. Of the 134 earlier
positions, 130 are zero and four are 51: both cold/warm histories of
`balun/head/pi2` and `balun/head-tail/calctrans`. The model preserves those
actual earlier offsets. Across all 399 later observations, 385 are zero,
12 are 51 and two are five. Every one remains an exact required assertion.

All four integration tests pass in CPU Python and packaged Pyodide. They
compare generated read entry/return registers and offsets with the
independent capture, preserve all eight previous PLT binding register sets,
retain every history/region/offset target and prove that later descriptor
positions cannot supply missing earlier input.

All **159 targeted CPU regression tests pass**. The complete Pyodide audit,
package `e905d93b1da90fac`, retains every history and exactly matches the
rectangular cold CPU report: 126 point-word differences and 158 final-word
differences, with zero unknown bytes. All 399 descriptor positions match,
as do 9,479,168 later heap words, 664 allocator events, 135 freed buffers
(10,580 bytes), 140 console calls, 132 calendar calls and 132 output files
(187,415 bytes). Every one of the 26 region owners remains checked; the
audit counts 216,790 final component words and 433,580 point words across
266 points and also compares every partial-word control-region tail.

All six older full compiled gates were rerun on the same package. They
retain 284, 298, 382, 556, 618 and 816 failures respectively for malloc,
stat, input, stdio, loader and extra-command histories; all 130 older main
command histories still pass. The new and six older strict continuing
checks all exit nonzero. Workflow syntax, complete disjoint Python
discovery, language syntax and patch checks pass.

## Native provenance

Both fresh GDB captures retain 132 next-driver outcomes, one SIGSEGV and one
SIGABRT. Each plain-run capture retains 128 normal exits, five SIGABRT and
one SIGSEGV. Relative to the parent malloc fixture, the component changes
square/1/coarse cold and pilot-boundary/1/coarse warm from normal exit to
SIGABRT; square/1/coarse warm and pilot-boundary/1/coarse cold change from
SIGABRT to normal exit. The continuing capture changes square/1/coarse warm
and pilot-width3/1/coarse warm from SIGABRT to normal exit, and
pilot-width3/1/contacts cold and warm from normal exit to SIGABRT. No launch
or target is retuned to select any of these fresh outcomes.

The minimal environment guard precedes earlier stack capture. Complete
observer/commands, binary hashes and parent hashes accompany both fixtures.
No inferior instruction, memory, register, syscall result, allocation or
signal is substituted. Diagnostic reports stay local.

| Fixture | Compressed bytes | Compressed SHA256 | Uncompressed SHA256 |
| --- | ---: | --- | --- |
| `read_storage_original.json.gz` | 726,186 | `15e6d86e963bbdba8bd4ae6f524f512461cc0420c176dbedf784580e71f2d787` | `93244107956118224aed889cade9308830f6c15759560db8ba1dc26425bde17c` |
| `read_transition_original.json.gz` | 47,491,069 | `79691cf3087342c20269ecad17910071e035b9d0fab91465ddb21225cc63609b` | `6ad0ee18980c2fa55405e4bedf989a88fa229011af81eec91595ea40463bfba3` |

The mandatory `readstore` suite checks every component target; the mandatory
`readtransition` suite fails on every remaining continuing difference.
Kernel poll/timeout effects, later string-copy ISA/FP state, printf/parser
child frames, interrupted XSAVE and signal continuation remain unfinished,
alongside the older numerical, geometry/lifetime and heap gates. The
numerical WASM and production guard are unchanged. This checkpoint is not
deployed.

```sh
python tools/capture_read_storage_original.py --debug-directory /path/to/debug/usr/lib/debug --reference /path/to/asitic-re --library-path /path/to/native-libraries
python tools/capture_read_transition_original.py --debug-directory /path/to/debug/usr/lib/debug --reference /path/to/asitic-re --library-path /path/to/native-libraries
PYTHONPATH=src:tests python -m unittest test_read_storage_original test_read_transition_original -v
python tools/build_site.py
node tools/check_read_storage_original.mjs /path/to/pyodide.mjs /tmp/read-component.json
node tools/check_read_transition_original.mjs /path/to/pyodide.mjs /tmp/read-continuation.json
```
