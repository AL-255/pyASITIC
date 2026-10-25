# Public printf on the continuing command history

`CommandTransition` now runs the REPL prompt's public `printf` and both
input/output log `fprintf` calls through `PrintfEntryStorage`, the real
vfprintf parent, formatter, FILE callbacks and flush source. All share the
memory and heap produced continuously from the first ASITIC driver entry.
The actual caller instructions build variadic frames and propagate returned
registers into subsequent calls. The prompt comes from live guest memory.
`ConsoleStorage.record` retains console metadata without performing a second
write. Earlier captures keep their existing, independently required paths.

The string-only calls leave the earlier FP state opaque. An explicit
`preserve_fp=True` permits this without manufacturing an XSAVE image. A
floating conversion still fails as soon as it needs missing FP input. The
default public-entry contract and all existing raw FP comparisons remain
unchanged. Their CPU and browser shard-1 reports still agree exactly with
the preceding checkpoint, including its 1,584 required cohort differences
and independent probe's unresolved kernel words.

The failed cold cache open also now produces ENOENT in the shared TLS errno
slot. Its address comes from the earlier TLS self-pointer and libc GOT;
the error follows the earlier current-directory and absent-cache manifest.
No later errno or saved stack local supplies this store.

## Native evidence and complete comparison

The new read-only observer repeats all 67 unchanged jobs, cold and warm.
All 134 requests, scripts, stdin and variants remain. Observed outcomes
are 132 next-driver stops, one SIGSEGV and one SIGABRT. Fresh plain runs
retain their actual 127 normal exits, six SIGABRT and one SIGSEGV outcomes.
No inferior instruction, allocation, memory, GP/FP register, return value,
CPU affinity or native signal is substituted.

Only earlier first-driver ELF read-only sections and named printf GOT/TLS
controls supplement the previous continuation inputs. The 44 stdio owners
contain 254,478 bytes and remain complete later assertions at every point
and final boundary. The observer records three reached public entry/return
GP pairs as assertion targets, never execution inputs. It supplies no
per-call memory or FP snapshot. The archive is 47,554,571 bytes, SHA-256
`803342f9d96fae47fb626c92c1218050e6e113931ab5230c8afeaf4627df8d5a`.

Lossless projection verifies every byte of 18,354 later region records:
103,364,142 bytes. Ordered owners and overlaps remain intact; repeated
contents are factored by SHA-256. Missing earlier tables, altered earlier
prompt text, changed later GP/region targets and corrupted content hashes
are tested independently.

The first full capture exposed an incomplete native assertion: a corrupted
tcache chain could reach a stack node outside the retained heap. Its
archive and failure logs remain local. The observer was extended to retain
eight bytes at every external cache node, then all jobs were captured
again. This complete run has no external cache nodes. Such targets, when
present, are compared against source memory and initialize only a separate
assertion store. A missing native target is an explicit failure; source
bytes never repair it. A negative test changes an external-node assertion
and verifies both detection and unchanged source memory. All older fixture
files and required gates remain unchanged.

The complete eight-shard Pyodide report checks 664 transition events, 135
freed buffers / 10,580 bytes, 9,479,168 heap words, 8,613,612 component words,
266 points / 17,227,224 point words, 140 console calls, 132 calendar calls,
132 output files / 187,415 bytes and 399 stdin positions. Both complete
region byte counters total the 103,364,142 retained bytes. There are no
unknown bytes. All three reached printf calls and all 102 GP assertions
match. Their source Memory and Heap identities are also checked.

The strict new gate still fails on 34 words in the rectangular cold REPL
history: one point word and 33 final component words. The same remaining
polling pointer occurs at both boundaries; fatal/signal-path stores account
for the other 32 words. Every other history matches. Eight independent
tests pass in each final browser shard; the ninth, complete-state gate
fails in the shard containing that case. There are no execution errors.
The previous continuation gate's 198 differences stay required on its
unchanged inputs. No tolerance or expected difference count is accepted.

The eight complete CPU shards subsequently finished during the
[kill/VDSO checkpoint](KILL_STORAGE.md). Their merged report equals the
complete browser report across all 134 cases, counters and differences,
including the 34 required residual words and exact three GP pairs.
Historical negative-test sampling errors and the corrected independent
rerun are recorded there; no strict gate is waived. Reports remain local.
The source package for this comparison is
`5495b4489a2361a6`; the numerical module is unchanged, SHA-256
`c7869e98f4c18b5414dc172d836e7144ab3ebc0de2de0d1f2eec1a4fe1709186`.

The default public-entry FP guard, all original owners, every native
outcome and every earlier numerical/geometry/heap gate remain required.
This checkpoint does not establish complete command execution or simulator
parity. Remaining work includes select64/kernel/fatal continuation and
the broader floating-point, JOIN/UNJOIN and mapping discrepancies. It is
not promoted over the deployed Pages version.

The subsequent [select64 dispatch integration](SELECT_DISPATCH.md) executes
the timeout setup and syscall-helper saves through VDSO entry. It accounts
for both polling-word assertions, leaving 32 final fatal/signal words in
the complete new browser continuation report. The earlier captures and
strict zero-difference gates remain required.

```sh
python tools/capture_printf_transition_original.py --reference ~/github/asitic-re \
  --library-path /path/to/i386/libs --debug-directory /path/to/debug
PYTHONPATH=src:tests python -m unittest test_printf_transition_original
python tools/audit_printf_transition_original.py --shard 1 --shards 8 \
  --output /tmp/printf-transition-cpu-1.json
python tools/build_site.py
node tools/check_printf_transition_original.mjs /path/to/pyodide.mjs \
  /tmp/printf-transition-wasm-1.json 1 8
python tools/merge_printf_transition_reports.py /tmp/printf-transition-wasm-?.json \
  --output /tmp/printf-transition-wasm-all.json
```
