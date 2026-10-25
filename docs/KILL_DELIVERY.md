# Whole kill-to-handler execution

`kill_delivery.py` composes the original glibc kill wrapper, recognized VDSO
prefix, compatibility syscall state and complete legacy signal delivery on
one Memory and actual earlier XSAVE image. Execution starts once at resolved
kill entry. Produced VDSO, syscall, interrupted and handler boundaries are
observed without resetting memory, GP or FP from a captured inner state.
The observer's return value cannot supply a result.

The supported operation is an unblocked caught signal to the caller's own
process group. Other targets, deferred/default signals and additional ABI
modes remain explicit unsupported paths. No host syscall or signal executes.

## Compatibility syscall and frame behavior

The [Linux compatibility entry](https://github.com/torvalds/linux/blob/v7.0/arch/x86/entry/entry_64_compat.S)
preserves the signal argument supplied by the VDSO. The
[fast syscall path](https://github.com/torvalds/linux/blob/v7.0/arch/x86/entry/syscall_32.c)
restores EBP from the saved user stack and selects the VDSO landing pad.
The source models the successful self-group kill, orig_eax and interrupted
PC from the earlier arguments/instruction bytes; no recorded kernel return
supplies those values.

The existing [signal-frame serializer](SIGNAL_FRAMES.md) then builds the
frame, legacy x87 save, aligned extended state, mask and initialized handler
FP state. It follows the [Linux legacy i386 signal interface](https://github.com/torvalds/linux/blob/v7.0/arch/x86/kernel/signal_32.c).
The actual earlier XSAVE image is mandatory. Missing or truncated FP input
cannot be replaced by the interrupted or handler snapshots.

## Unchanged native cohort

The read-only capture repeats all 67 original jobs cold and warm, preserving
all 134 requests, scripts, stdin, variants and native terminal outcomes.
It records actual GP/XSAVE, independent legacy FP, the prior installed
action/mask, process-group facts, complete stack/VDSO and TLS controls at
resolved kill entry. CPU layout and initial PKRU come from the independent
CPUID/RDPKRU probe executed before the jobs. Debug-trap thread state follows
the same unchanged kill PLT observation protocol as the earlier signal
capture. No inferior instruction, allocation, register, memory, syscall
return, signal or CPU affinity is substituted.

The later VDSO, syscall, interrupted and handler states retain every byte of
all three owned regions, including their reserved areas. Every GP value,
XSAVE byte, independent legacy FP byte and signal mask remains required.
Only the earlier kill entry initializes the composed operation. The older
independent pre-signal/handler observations are retained too.

Observed runs retain 129 normal exits, four SIGSEGV and one SIGABRT. Fresh
plain runs retain 127 normal exits, six SIGABRT and one SIGSEGV. Four cases
fault before kill and remain explicitly present with no delivery input;
this component does not claim to predict those earlier application faults.
There is no filtering or retry for preferred outcomes.

The 5,493,481-byte archive has SHA-256
`86fa420510e2417be02bb445d9c312d667bb29f3f0b31dadb615a1561165c6d6`.
Complete regions are losslessly factored by SHA-256, without removing an
owner or target. All parent fixture hashes remain mandatory.

Complete CPU Python and packaged Pyodide reports are identical:

| Required comparison | Count |
| --- | ---: |
| Histories / reached kill calls | 134 / 130 |
| Produced inner boundaries | 520 |
| Whole owned-memory four-byte units | 19,173,440 |
| GP values | 8,840 |
| XSAVE bytes | 1,268,800 |
| Independent legacy FP bytes | 70,200 |
| Signal masks | 520 |
| Differences | 0 |

All nine new tests pass in both runtimes. They alter later intermediate
memory/GP/FP/mask/legacy targets and verify that the produced handler remains
unchanged. Earlier FP mutations reach the saved frame while the handler's
FP state is initialized independently. Earlier EBP, action and mask mutations
reach their proper output fields. Missing earlier code/FP, blocked signals,
other process targets and ignored actions fail explicitly. The alternate
recognized SYSENTER ABI also has a controlled earlier-input test. All 26
combined CPU delivery/kill/signal-frame tests pass. The older standalone
signal-frame capture, tests and audit remain unchanged and required.

## Continuing-driver scope

This component starts at kill with actual earlier FP state. It does not
replace the continuing driver's missing FP propagation with that snapshot.
The current driver result remains unchanged at 28 required final words;
its affected complete CPU report is identical to the preceding checkpoint.
Every older gate remains required, and the continuation assertion stays
zero. Reports remain local.

The new whole-stack evidence corrects the previous diagnosis: four remaining
non-FP words are parser caller-frame stores already present at kill entry,
not handler stores. They remain identical at VDSO, syscall, interrupted and
handler entry. The other 24 words change during extended FP-state saving.
Continuing parser frames and actual earlier FP state must be produced before
this complete delivery operation can be connected. Handler body, process
cleanup and the broader numerical/geometry/JOIN/mapping discrepancies also
remain unfinished; this is not whole-program parity.

The source package is `179a7a0c82ac330b`. Numerical WASM remains unchanged at
SHA-256 `c7869e98f4c18b5414dc172d836e7144ab3ebc0de2de0d1f2eec1a4fe1709186`.
This branch is not promoted over the deployed Pages version.

```sh
python tools/capture_kill_delivery_original.py --reference ~/github/asitic-re \
  --library-path /path/to/i386/libs
PYTHONPATH=src:tests python -m unittest test_kill_delivery_original
python tools/audit_kill_delivery_original.py --output /tmp/delivery-cpu.json
python tools/build_site.py
node tools/check_kill_delivery_original.mjs /path/to/pyodide.mjs /tmp/delivery-wasm.json
```
