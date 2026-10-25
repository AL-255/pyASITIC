# Whole original vfprintf execution

`VfprintfStorage.call` now executes the real `PrintfFormat` between its
caller prefix and suffix on the same Memory, Heap, FILE and child trace.
The default path requires actual earlier CPU flags and XSAVE input. The
formatter's produced registers and FP state continue into count completion
and the parent epilogue. A missing input raises; a captured formatter
return never supplies execution. The optional callback remains a test
interface and is not used by native whole-parent comparisons.

The existing [caller-phase audit](VFPRINTF.md) and its entire original
archive remain unchanged. All eleven phase tests pass against every
7,946 earlier caller phase. Its independent suffix input is deliberately
separate from the new whole-parent path. It does not become a continuation
seed merely because the complete formatter now exists.

The new `vfprintf_whole_original` capture repeats all 67 original jobs,
cold and warm. At parent entry it owns the original stack, heap, arena,
FILE/locks/vtables, descriptor facts, controls, aligned format bytes,
ELF read-only/data/GOT sections and full pthread/static TLS. The exact
earlier ELF/TLS reader is shared with the formatter capture. Minimal
environments and the earlier independent integer-flag probe precede
execution. No inferior code, memory, register, CPU affinity, allocation,
result or signal is substituted.

Every old parent call and the complete helper-kind subsequence from the
older capture are retained. All 134 request/script/stdin/variant records
and their observed outcomes match the old cohort. There are 3,973
parents, 20,921 caller helpers and 98,228 middle formatter helpers: all
119,149 helper entries and returns remain assertions. The original
3,973 formatter-entry/return pairs remain complete owned-state targets.
Observed outcomes are 132 next-driver stops, one SIGSEGV and one SIGABRT.
The new plain runs retain their actual 127 normal, six SIGABRT and one
SIGSEGV outcomes, without retries or filtering. The old plain outcomes
remain in the unchanged older archive.

Lossless conversion checks all 15,892 states and 45,086 pages. The capture
has 38,573 region records, 3,664 contexts and 928 FP images. Its two-part
49,520,421-byte gzip stream has SHA-256
`02330e6799a014065e2bc8ea1d6316406fcf8393e88e120cfd591c5869abaf92`.
Part and complete-stream checksums remain mandatory.

The whole-parent auditor constructs the source engine once at parent
entry. A read-only observer checks the current produced Memory/Heap,
registers and FP image at formatter entry and formatter return. Its
comparison adapter returns already-produced registers on the live source
memory; it never constructs another execution state from a target.
Helper boundaries are checked using the source's actual child counts.
Final parent state and every helper are then compared as well. Native
inner snapshots are assertions throughout this path.

Tests track the single engine initialization, change earlier string data
and require it to reach the whole output/count, reject missing actual FP
and TLS inputs, and mutate inner/final GP, FP, heap and helper targets.
Missing or invalid inner boundaries fail. Both overlapping TLS owners,
their kernel rseq words and all native outcomes stay required. Reports
remain local.

All eight CPU and eight Pyodide shards have finished. Their merged
reports are identical for every case, counter and difference. Every
3,973 parent executes, with 7,946 produced inner-boundary assertions and
119,149 helpers. The final comparisons check 1,327,502,534 four-byte
units, 67,541 registers, 9,694,120 FP bytes and 4,051,066 helper registers.
The inner assertions additionally check 2,655,005,068 four-byte units,
135,082 registers and 19,388,240 FP bytes.

The strict whole-state gate still fails on 8,028 memory-word assertions,
all at pthread offsets `0x4a0` and `0x4a4`: 1,844 occurrences per word at
parent return, 1,700 per word at formatter return and 470 per word at
formatter entry. Both overlapping TLS owners remain checked. These are
the kernel-managed rseq CPU fields; there are no other memory, heap,
register, FP or helper differences. No kernel word is exempted and no
affinity or later-state substitution hides these failures. Each of the
sixteen shards runs seven tests: six pass, and the complete required
state comparison fails. No shard has an execution error.

The verified source package is `9306f25876f0836b`; the numerical module
remains unchanged at SHA-256
`c7869e98f4c18b5414dc172d836e7144ab3ebc0de2de0d1f2eec1a4fe1709186`.
The subsequent [continuing printf integration](PRINTF_TRANSITION.md)
connects this parent through the actual public prompt/log entries, using
the earlier first-driver state. This independent whole-parent gate and
the earlier 198-difference continuation gate remain required.
Whole-program parity remains unfinished.

```sh
python tools/capture_vfprintf_whole_original.py --reference ~/github/asitic-re \
  --library-path /path/to/i386/libs --debug-directory /path/to/debug
PYTHONPATH=src:tests python -m unittest test_vfprintf_whole_original
python tools/audit_vfprintf_whole_original.py --output /tmp/whole-cpu.json
python tools/build_site.py
node tools/check_vfprintf_whole_original.mjs /path/to/pyodide.mjs /tmp/whole-part.json 1 8
python tools/merge_vfprintf_whole_reports.py /tmp/whole-part-*.json --output /tmp/whole-all.json
```
