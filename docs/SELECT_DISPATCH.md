# Native select64 setup and syscall-helper entry

`select_storage.py` implements the pinned i386 glibc `__select64` frame,
timeout normalization, time32/time64 dispatch and EINVAL return. It also
executes the syscall helper's argument loads, three register saves and
call through the live TLS sysinfo pointer. This follows glibc 2.39
`select.c` and its i386 syscall ABI, under LGPL-2.1-or-later. The VDSO and
kernel have not executed at the final implemented boundary.

Seconds and microseconds come from guest memory. The source retains the
original signed division, nanosecond conversion, saturation on signed
time64 overflow, and original time32 selection and cast. No alternate
timeout arithmetic or improved overflow behavior replaces the original.
Negative seconds or microseconds produce EINVAL at the earlier TLS errno
binding, restore the actual caller registers and return without a syscall.
Multithread cancellation still fails explicitly pending its source path.

## Complete native evidence

The read-only ASITIC capture repeats all 67 existing jobs cold and warm.
All 134 histories, requests, scripts, stdin, variants and native outcomes
remain. Observed runs have 132 next-driver stops, one SIGSEGV and one
SIGABRT. Fresh plain runs retain their actual 130 normal exits, two
SIGABRT and two SIGSEGV outcomes. No run is selected or retried for a
preferred outcome. The earlier polling fixture is unchanged and required.

The new capture adds complete syscall-helper and VDSO entry states to the
existing poll/select/select64 boundaries. All owners, overlaps, GP and
XSAVE bytes remain assertions. Only the earlier boundary initializes each
independent component; no later state supplies source execution. The
945,021-byte archive has SHA-256
`db00ea3800f12e58224fe0a9a1139351e9485a173666e30f4ac4406019c2462a`.

An independent normal native caller additionally provides 13 declared
requests: null and zero timeouts, fractional seconds, microsecond carry,
time32 overflow, time64 inputs, signed time64 saturation and three invalid
negative inputs. The actual captured entry operands are checked against
every declared request. All 13 dispatches remain, including the three
EINVAL returns; ten calls also reach the syscall helper and VDSO. No kernel
or function return is substituted. The caller uses the same pinned libc,
minimal environment and actual regular-file stdin. Its 296,591-byte archive
has SHA-256
`56c1151eccbff377a88f45f59184a71b4bd761ded6c7ecff5a74d2d3ddf25bb6`.

CPU Python and packaged Pyodide produce identical complete reports:

- ASITIC: four operations, 666,420 four-byte comparison units, 68 GP values,
  9,760 FP bytes and zero differences; the other 133 histories explicitly
  retain their absence of polling and actual outcomes.
- Independent caller: 13 dispatches and ten helper executions, 1,616,739
  four-byte comparison units, 391 GP values, 56,120 FP bytes and zero
  differences.

The independent caller also executes dispatch followed by its helper on
one source Memory without loading the captured inner state. Every produced
inner GP value and complete final owned region is checked. Tests change
later memory/GP/FP targets, remove earlier stack memory and alter live
syscall arguments. All eight tests pass in both runtimes. Nineteen combined
CPU select/poll/flush tests pass; 18 additional earlier stdio/input/read/
getline continuation tests pass. The older polling report and targets stay
required; their capture commands retain their exact original text.

## Continuing execution

`CommandTransition` now passes the actual adapter result through dispatch
and the syscall helper on the existing source memory. No new per-call
snapshot, expected GP value or timing result initializes it. A separate
test verifies the shared Memory identity, produced register handoff and
every reached GP boundary against the independent ASITIC capture.

The missing polling word was the helper's saved EBP at its original
ESP-12. That store now matches at both later assertions. The complete
eight-shard browser continuation report retains all 134 histories and
103,364,142 later region bytes, with no unknown bytes. All three printf
calls / 102 GP assertions still match. The residual differences decrease
from 34 to 32, all final component words in the rectangular cold fatal/
signal path. Every other history and every intermediate point matches.
The changed history's complete CPU report equals the browser report.

The strict gate still requires zero differences. One browser shard fails
that gate; the other seven pass all nine tests, with no execution errors.
This is no whole-program parity claim. The earlier complete CPU printf
cohort is still running separately; its completed warm shards 2, 4, 6 and
8 match their earlier browser reports exactly. No full new CPU cohort
equality is claimed from that partial evidence. Reports remain local.

The source package is `eb6fd51930e20567`. Numerical WASM is unchanged at
SHA-256 `c7869e98f4c18b5414dc172d836e7144ab3ebc0de2de0d1f2eec1a4fe1709186`;
the packaged numerical sources still rebuild it byte for byte. VDSO/kernel
execution, elapsed-time copyback, select/poll returns and fatal/signal
continuation remain unfinished. All other arithmetic, geometry, JOIN/
UNJOIN and heap/mapping gates remain required. This branch is not promoted
over the deployed Pages version.

```sh
python tools/capture_select_dispatch_original.py --reference ~/github/asitic-re \
  --library-path /path/to/i386/libs --debug-directory /path/to/debug
python tools/capture_select_dispatch_probe.py --debug-directory /path/to/debug
PYTHONPATH=src:tests python -m unittest test_select_dispatch_original
python tools/audit_select_dispatch_original.py --output /tmp/select-cpu.json
python tools/build_site.py
node tools/check_select_dispatch_original.mjs /path/to/pyodide.mjs /tmp/select-wasm.json
```
