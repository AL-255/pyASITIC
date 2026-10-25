# Continuing history and quit dispatch

`dispatch_storage.py` now executes the original history, normalization and
quit caller stores in the existing simulation Memory. The complete continuing
comparison improves from 658 to 618 differing words: 293 before parser entry
and 325 at the final abort. These are still required failures. The older
fixtures without loader context remain separately required with 816 differences.

The subsequent [REPL/stdio integration](STDIO_TRANSITION.md) connects source
polling from earlier full standard-stream state and reduces the expanded
continuing audit to 556 required differences. The 618-difference comparison
documented here remains an independent older gate.

## Source behavior

Main's retained input arguments and dispatch call derive from its earlier
frame and preserved registers. The input caller's comparison with `QUIT`
determines the remaining scan count; its initialized delay supplies EAX/EDX.
The logical-test flags derive from the earlier caller control flags. The
controlled scripts contain no delay-setting command. Acquisition cancellation
and other delay/exception paths remain unfinished.

The dispatcher reserves the original fixed records, saves its parent registers,
scans the input byte string, and calls the `add_history` ELF import. The linked
reference history shim is exactly a RET, verified against its image SHA256
`91bfdf1bce9990520d44fc1d66d7a0dbb0a14c5a096acaab1cfae93ec333d90f`.
Other history implementations stop explicitly. The existing source PLT/lookup
code computes the binding and stack stores. No observed native target supplies
the result.

`Characters.normalize` retains its existing byte algorithm. An optional ABI
observer now emits its caller's saved-register and local-word stores, source
pointer, character classification, quote/content state and trailing-character
test. It preserves partial-byte fields and padding. The instrumented return
path currently supports flags `0x8e`; other return-register paths need their
locale-pointer state. Ordinary callers without ABI observation keep their
existing behavior.

After normalization, source arguments and return words form the actual parser
entry. The existing parser still computes tokens and the command identity.
For its no-argument quit return, the command catalog determines the retained
92-byte row offset. The original caller comparison, kill arguments and ELF
binding then produce the resolved `kill` target entry. Remaining parser child
frames and the subsequent syscall, signal delivery and handler frames are not
silently replaced by observed data.

The continuing integration checks every generated register against independent
native observations at dispatch entry and at all three now-connected bindings:
`signal`, `add_history` and `kill`. Registers derive from earlier source state.
No per-call native snapshot is loaded into that replay.

## Independent unchanged-original boundaries

The new read-only capture retains every unchanged original job in cold and
warm cache states: 134 histories. It observes dispatch entry, history return,
pre-parser entry, parser return and resolved kill target entry. The three
independent operations are:

1. Dispatch entry through history return and caller argument adjustment.
2. History return through normalization and parser entry.
3. Parser return through the quit caller and resolved kill target entry.

The parser body is outside these three independent operations; it remains
covered by the separate continuing comparison. Each operation begins with
its earlier full stack/registers/FP state and ELF/locale/TLS metadata, and its
entire later regions/registers/FP bytes are assertions. These component inputs
are never used to initialize continuing process state.

| Compared observation | Count | Differences |
| --- | ---: | ---: |
| Actual dispatch histories | 1 | 0 |
| Complete independent operations | 3 | 0 |
| Four-byte region units, including short tails and overlaps | 499,815 | 0 |
| General/segment registers | 51 | 0 |
| Preserved FP/SIMD bytes | 7,320 | 0 |

The other 133 histories have no dispatch in the observed interval and remain
explicit, including the earlier square/64/contacts cold SIGSEGV. The dispatch
history is the rectangular cold case, which still reaches its native SIGABRT.
GDB records 132 next-driver stops, one SIGSEGV and one SIGABRT. Plain processes
record 130 normal exits, two SIGSEGV and two SIGABRT.

Relative to the earlier loader-transition capture, plain square/1/coarse warm,
pilot-width3/1/coarse cold and pilot-width3/1/contacts warm change from SIGABRT
to normal. Pilot-boundary/1/coarse cold changes from SIGSEGV to SIGABRT and
warm changes from SIGABRT to SIGSEGV. All fresh and previous outcomes remain
in the evidence. No native run is replaced to obtain a preferred outcome.

Minimal launcher environments and environment-name guards precede stack
capture. The unchanged original runs in its own process group. The observer
does not replace inferior instructions, operands, registers, allocation
results or returned values.

## Continuing comparison and open producers

On the same earlier inputs and native expectations, 62 previously differing
addresses now match and 22 newly visible final-boundary differences remain.
The pre-parser boundary improves by 43 words with no newly differing address.
The final boundary resolves 19 addresses and exposes 22 later overwrites that
are not yet executed by the source replay. Those source writes are retained;
they are not cleared merely because the later native boundary contains zeros.
The independent complete caller comparisons above establish the earlier writes.

The 618 remaining differences and the older 816-difference gate remain nonzero
and mandatory. No expected-difference allowance, mask, tolerance adjustment or
target selection turns them into passes. Later command/kernel/caller effects
must produce the missing overwrites in the same Memory.

Polling/select, the stdin/libio call chain, `strcat` and the surrounding REPL
frames remain unconnected. The legacy static stream lock/vtable state needs
its earlier inputs; copying later poll or stdin registers would bypass that
work. Full loader startup and earlier binding lifetimes, parser child ABI,
interrupted FP state and kernel/handler continuation, later commands/exit,
other analysis branches, older missing-context gates and known arithmetic/
JOIN/UNJOIN differences also remain unfinished. The production trailing-via
guard and current deployment are unchanged.

The seven new tests additionally check earlier-input mutations, saved words,
retained padding, later-output independence, every original job and boundary,
minimal environments, native outcomes and the source-generated dispatch entry.
The existing integration test now compares all three connected PLT entries.
The mandatory `dispatchstore` suite supplements all older gates. Diagnostic
reports remain local.

All 112 affected CPU tests pass. The seven new tests and complete independent
audit also pass in packaged Pyodide, version `7636fc9661e173ac`; its report
is byte-identical to the CPU report. Both full compiled continuing audits
were rerun. All 130 main histories and three additional histories pass, while
the rectangular cold history retains the 293 + 325 differences above. All
9,479,168 later heap words, 664 allocator events, 135 pre-free buffers, 140
console calls and 132 output files still match, with zero unknown bytes.
The older four-case comparison retains its 816 required differences. Both
continuing checks still exit nonzero. Workflow syntax, complete disjoint
Python test discovery and patch validation pass. The numerical WebAssembly
binary is unchanged.

The fixture is 946,191 bytes, compressed SHA256
`bb2e0e7b061eb52ff6d365ac34a3d496e63947f939cab5ab0cefdeadf8512fef`,
uncompressed SHA256
`75d0c87e6ff70aefedba4dcfe03d917a6fae570d328532f8a83c9e1e6f44f852`.

```sh
python tools/capture_dispatch_storage_original.py --debug-directory /path/to/debug/usr/lib/debug --reference /path/to/asitic-re --library-path /path/to/native-libraries
PYTHONPATH=src:tests python -m unittest test_dispatch_storage_original test_loader_transition_original -v
python tools/audit_dispatch_storage_original.py --output /tmp/dispatch-audit.json
python tools/build_site.py
node tools/check_dispatch_storage_original.mjs /path/to/pyodide.mjs /tmp/dispatch-wasm.json
node tools/check_loader_transition_original.mjs /path/to/pyodide.mjs /tmp/continuing-wasm.json
node tools/check_command_transition_original.mjs /path/to/pyodide.mjs /tmp/older-main.json /tmp/older-extra.json
```
