# Native kill wrapper and VDSO caller saves

`kill_storage.py` implements the pinned i386 glibc `kill` wrapper through
the earlier TLS sysinfo pointer, followed by the VDSO register saves up to
its actual syscall instruction. It follows the original i386 syscall ABI
under LGPL-2.1-or-later. Both functions write guest memory and return the
produced registers. They execute no host syscall or signal.

The wrapper copies the inherited EBX into EDX, loads the actual pid and
signal arguments, selects syscall 37 and pushes its original return PC.
The VDSO prefix then saves ECX, EDX and EBP in native order. Earlier code
bytes select the recognized `MOV EBP,ECX` or `MOV EBP,ESP` prefix. Flags
and FP state are untouched. An unknown earlier ABI fails before those
stack stores; no later code or GP target chooses the branch.

## Read-only native evidence

All 67 existing jobs run cold and warm, retaining all 134 requests,
scripts, stdin, variants and native outcomes. Observed outcomes remain
132 next-driver stops, one SIGSEGV and one SIGABRT. Fresh plain runs retain
their actual 128 normal exits, five SIGABRT and one SIGSEGV outcomes. No
outcome is retried, selected or replaced.

The earlier dispatch context now owns the 16 immutable bytes at its live
sysinfo pointer. That owner remains a complete assertion at every later
boundary. The capture retains all existing entry/history/parser/kill
states and adds VDSO entry and the syscall instruction before execution.
Every old/new owner, overlap, GP value and XSAVE byte remains required.
Later snapshots never initialize the continuing command replay.

The 1,168,847-byte archive has SHA-256
`874d547bbe1861bccedc60573c1611c94d19dce13111a42bba14eb1d9d010769`.
The older dispatcher capture and default audit are unchanged and required.

Complete CPU Python and packaged Pyodide reports agree exactly: five
operations, 833,045 four-byte comparison units, 85 GP values and 12,200 FP
bytes, with zero differences. The other 133 histories explicitly retain
their absence of dispatch and actual terminal outcomes.

Tests also run both new source operations on one Memory without loading
the captured inner state, asserting every final owned byte and produced
GP value. Changed earlier arguments/registers and the alternate recognized
VDSO prefix exercise live operand propagation. Changed later memory/GP/FP,
missing earlier VDSO bytes and unsupported earlier code fail independently.
All eight tests pass in CPU Python and Pyodide. Forty-five combined CPU
kill/dispatcher/select/stdio/input/read/getline/flush tests pass. The older
dispatcher browser tests and complete default audit also pass.

## Continuing execution and remaining scope

`CommandTransition` now supplies the actual produced quit-binding registers
to the wrapper. Contexts declaring the earlier read/VDSO ABI additionally
execute the recognized prefix. Earlier fixtures without those declared
code inputs retain their missing child effects as required comparisons.
There is no lookup of expected words or per-call input snapshot. Tests
verify the same source Memory, actual register handoff and all three
reached GP boundaries against the independent capture.

The CALL return PC and three VDSO saves account for four previously missing
final words. The complete eight-shard browser continuation report keeps
all 134 histories and 103,364,142 later region bytes, with no unknown bytes.
Its differences decrease from 32 to 28, all final component words in the
rectangular cold signal/cleanup path. All intermediate points and the
other 133 histories match. The changed history's complete CPU report equals
the browser report. All three printf calls / 102 GP assertions still match.
The strict gate remains zero: one browser shard fails that gate, and seven
pass all nine tests, with no execution errors.

The earlier full CPU printf-continuation cohort also finished during this
checkpoint. Its complete merged report equals the corresponding earlier
browser report across every case, counter and difference, including all
34 required residual words on source package `5495b4489a2361a6`. The first
four CPU suites had loaded an obsolete negative-test sample; their full
comparison reports are intact, and the corrected independent tests are
rerun separately. This is not a claim that those historical test processes
exited successfully. No full CPU cohort equality for the newer kill source
is inferred from the changed case alone. All reports remain local.

The new source package is `739e0082a8b28772`; every packaged Python and
technology byte matches the current sources. Numerical WASM is unchanged
at SHA-256 `c7869e98f4c18b5414dc172d836e7144ab3ebc0de2de0d1f2eec1a4fe1709186`,
and its packaged source rebuilds it byte for byte.

The remaining words lie in saved signal FP state and handler frames.
The independent complete signal-frame component remains required;
connecting it needs the actual continuing FP and interrupted CPU state.
This checkpoint does not manufacture FP bytes or execute signal delivery,
kernel return, the complete handler or final process cleanup. Those paths
and every broader arithmetic, geometry, JOIN/UNJOIN and mapping gate remain
unfinished. This branch is not promoted over the deployed Pages version.

```sh
python tools/capture_kill_storage_original.py --reference ~/github/asitic-re \
  --library-path /path/to/i386/libs --debug-directory /path/to/debug
PYTHONPATH=src:tests python -m unittest test_kill_storage_original
python tools/audit_kill_storage_original.py --output /tmp/kill-cpu.json
python tools/build_site.py
node tools/check_kill_storage_original.mjs /path/to/pyodide.mjs /tmp/kill-wasm.json
```
