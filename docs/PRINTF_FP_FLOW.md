# Original floating formatter ABI

`printf_fp_flow.py` binds binary64 floating conversion to the original
formatter's stack, scratch limbs, registers, buffer helpers and produced
x87 state. Its fixed source program includes the argument-copy paths,
decimal core and wrapper, multiprecision helpers, grouping helpers,
scalar buffer paths, alloca cutoff and PC thunks. It executes algorithm
instructions in Python. It never executes a native binary at runtime or
loads recorded output, later memory or return registers to obtain a result.

`lift_printf_fp_original.py` is an offline source-generation step. It
requires the pinned libc SHA-256
`e936bd40e5479b27721efeade1b502623436a8be2bd8bd0f0ccf8c4f7229a0d0`.
The generated program retains all 5,316 instructions and their bytes,
addresses and operands across the declared ranges. Its 221,305 bytes have
SHA-256 `dc3f3d4a61156e5bc4b9e7ac13ac88ab13ce7e396672fd7ff02f50e6c6fc195c`.
The [independent public-entry probe](PRINTF_ENTRY.md) added the two
instructions of the MPN PC-add thunk, without changing an older instruction.
It also verifies the call-to-next-instruction PC idiom used by the unrolled
subtractor on extreme exponents.
The glibc-derived source is LGPL-2.1-or-later, with the bundled license.
The runtime reads guest operands from actual earlier memory, including
the original ELF tables. Unknown bytes still fail.

The [decimal component](PRINTF_FLOAT_DIGITS.md) independently checks the
same multiprecision conversion algorithm's digits. The fixed flow also
retains the scratch stores and helper-call ABI that a final-string
implementation would omit. It uses the
[x87 state component](X87_FORMAT_STATE.md) for loads, stores, classification
and comparison. `PrintfFormat.xstate` is produced by those instructions;
the complete audit compares it with every original FP byte. Non-floating
calls preserve their incoming FP image through the same interface.

The reference CPU's undefined integer flags are separately measured by
`capture_printf_integer_flags_native.py`. Its static i386 program declares
all 16,528 operands and incoming flag words before execution. It varies
boundaries, seeded random values, shift counts and incoming flags for
MUL/IMUL, DIV/IDIV, BSR/TZCNT and single/double shifts. All 82,640 resulting
register/flag values match in CPU Python and Pyodide. Five regression
tests require all requests, source provenance and complete instruction
extents, and detect modified native flags. These are instruction-behavior
inputs for the pinned AMD reference, not corrections fitted to ASITIC
output. The compressed fixture is 464,414 bytes, SHA-256
`8a64b2f4f7da4f207480fdc019534876a082b6b06983a6e1d6c1e33a84af30ae`.

Integration exposed a real caller-stack omission: after the initial
literal write, `ADD ESP,16` at `0x605b8` restores the conversion frame.
Width/precision readers had incidentally hidden its absence in previous
component paths. The source now performs that original adjustment even
for a bare `%lf` field. All earlier independent integer-format tests
remain required and pass.

The first integrated finite call also exposed an uncaptured earlier
ctype TLS pointer. No later snapshot or assumed C-locale pointer fills
that word. The corrected native capture records the complete static TLS
extent declared by `_rtld_global_ro._dl_tls_static_size` and the pinned
`struct pthread` size. This follows glibc's
[TLS allocation layout](https://github.com/bminor/glibc/blob/glibc-2.39/elf/dl-tls.c).
The existing full pthread owner remains alongside the complete static
TLS owner, including both copies of overlapping kernel rseq words.

The earlier archive is retained locally at
`/tmp/pyasitic-printf-format-before-static-tls`, unchanged at SHA-256
`edc7724655ee6279ee2f224b41f351ed5c0d23cd0fb321734173447e74b41278`.
The new 56,824,093-byte archive has SHA-256
`3229e7382362788a7f958b89e50f22ee8ce9ec0f72c6a3570b2dac91021b5693`.
Every one of the 134 requests, scripts, stdin streams, variants and
observed terminal outcomes is unchanged. Each history retains its exact
formatter/helper count: 4,105 calls and 104,036 helpers in total, one
history without calls, 132 normal runs, one SIGSEGV and one SIGABRT.
The lossless codec checks 12,315 states and 54,708 pages. Neither the
inferior, its CPU affinity nor its allocations/results are substituted.

The complete CPU and browser audits now execute every call, adding all 1,976 formerly
unfinished floating formatters. It compares 1,374,813,338 four-byte units,
69,785 final registers, 10,016,200 FP bytes and 3,537,224 registers at all
104,036 helper boundaries. Final registers, FP, helpers and non-kernel
memory match. Its 4,048 required differences are entirely the two rseq
CPU words, including overlapping owners (2,024 occurrences each at TCB
offsets `0x4a0`/`0x4a4`). The entry audit executes all 4,105 prefixes and
retains 868 differences in those same words. Both gates still fail.

All eight CPU and all eight browser shards finish with identical complete
reports: every case, counter and difference agrees. Each runs eleven
tests; ten pass, and the combined native comparison retains its two
required failing subtests. All shards exit nonzero. Initial logs from a
new regression's case-selection error are retained locally under
`/tmp/pyasitic-printf-fp-initial-test-selection`; corrected final runs retain
the same complete native reports. Reports are not uploaded.

The verified package is `ba1bb18a1356eb05`; the numerical module remains
unchanged at SHA-256
`c7869e98f4c18b5414dc172d836e7144ab3ebc0de2de0d1f2eec1a4fe1709186`.
The source
does not filter a conversion, native outcome, owner or kernel word.
The [whole vfprintf parent](VFPRINTF_WHOLE.md) now uses this formatter
on the same live source state. Integration into continuing replay
remains unfinished, as do unimplemented extended/hexadecimal,
unmasked-fault, registered/wide/localized and allocation/error branches
beyond the original captured paths. The broader 198-difference
continuing gate remains required. Component success does not establish
complete simulator parity.

```sh
python tools/lift_printf_fp_original.py --verify
PYTHONPATH=src:tests python -m unittest test_printf_integer_flags_native
python tools/capture_printf_format_original.py --reference ~/github/asitic-re \
  --library-path /path/to/i386/libs --debug-directory /path/to/debug
PYTHONPATH=src:tests python -m unittest test_printf_format_original
python tools/build_site.py
node tools/check_printf_format_original.mjs /path/to/pyodide.mjs /tmp/part.json 1 8
python tools/merge_printf_format_reports.py /tmp/part-*.json --output /tmp/all.json
```
