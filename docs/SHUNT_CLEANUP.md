# Continuing log closure to libc exit entry

The subsequent [exit-list/loader work](SHUNT_EXIT.md) now continues beyond
this historical checkpoint when genuine earlier exit metadata is available.
The original cleanup fixture and all of its strict targets remain unchanged.

The source now continues all fourteen original scripts, cold and warm, from
cache release through input-log and output-log closure to the native libc
`exit` entry. It uses the existing heap, FILE list, locks and current control
globals. The same code also advances the previous stdin/malloc fixtures;
there is no fixture-selection or outcome gate. Libc exit handlers, loader
finalizers and complete CPU/stack/FP execution remain unfinished. This
branch is not deployed.

## Reference order and source stores

`console_runtime.cpp` / originals `0x0804be20` and `0x0804c33c` close the input
log before the output log. Recording output/input close afterward when the
live recording byte is set. The source `ProcessCleanup` follows that order
and shares `close_byte_stream` with script and port closure. That helper
unlinks each FILE, acquires its real guest lock, releases its buffer while
locked, clears its narrow areas and descriptor, unlocks it and releases the
FILE allocation. Every free uses the continuing source allocator.

Observers at the free entry now run after the source event has been entered
and before `Heap.free`; they never supply heap, memory or returned values.
The virtual log-close path rejects pending output that still needs its write
implementation, rather than discarding those bytes. Wide-output and complete
caller/free CPU branches remain explicit work.

The read-only native capture retains all previous solve, command, file,
stdin, malloc and shutdown targets and all unchanged original outcomes.
It additionally observes both log fclose entries/returns, their buffer/FILE
free entries and X11 `XFreeThreads` entry/return. Every point retains the
complete stack, heap, arena, stream-list head, relevant FILE and all earlier
stdio owners, plus registers, XSAVE, allocator state and event position.
No differing region or alias is removed from the comparison.

The capture supplies genuine first-driver log/recording controls, X11 global
pointer slots, fini-array bytes and destructor controls. Later close and
finalizer snapshots never initialize the full replay. The final three frees
come from X11 `XFreeThreads` during exit, after the observed libc exit entry;
they are still missing source execution. The earlier X11 metadata is retained
for implementing the actual exit/loader path, rather than replaying those
observed frees as a list of answers.

All 28 plain and observed original histories exit normally. Complete region
content is losslessly factored into the immutable page bank, preserving every
ordered owner, original length and SHA-256. All **15,344 cleanup regions /
399,245,376 captured bytes** are expanded and verified by the regression
checks. Descriptive metadata was corrected to distinguish internal free
entries from public fclose returns; no observed input/output, page or hash
was changed by that correction.

## What matches and what remains required

The independent close comparison uses each call's genuine earlier entry
state and executes the shared source close and allocator. All 56 closes
match their non-stack memory, FILE/list/lock stores and allocator states at
both free entries and return: **59,889,864 complete words / 168 boundaries**
are checked. The full independent report still fails: it retains 6,618
unexecuted stack words, 168 missing register boundaries, 168 missing FP
boundaries and 56 missing X11 finalizer phases. These failures are not waived
by passing the semantic-store regression checks.

The full continuing history now checks:

| Continuing target | Checked |
| --- | ---: |
| Allocator events / complete freed allocations | 1,522 / 1,512 |
| Complete freed usable bytes | 42,912,336 |
| Complete shutdown heaps / words | 224 / 57,950,208 |
| Independent FILE/buffer/list/workspace/stdio bytes | 58,998,016 |
| Parser registers | 280 |
| Public printf/fprintf calls / registers | 84 / 2,856 |
| Stdin IO calls / phase registers | 176 / 5,984 |
| Descriptor positions | 352 |
| Continuing malloc calls / phases / words | 10 / 20 / 6,456,780 |
| Continuing malloc registers / allocator boundaries | 340 / 20 |
| Log fclose calls / phases / words | 56 / 224 / 79,853,152 |
| Additional close allocator boundaries | 224 |
| Complete output files / bytes | 28 / 45,252 |
| Unknown compared bytes, including IO/malloc/close | 0 |

All checked heap, arena, FILE/list/lock and freed-allocation bytes match.
Complete heap owners include contiguous source brk extensions and remain
separate from adjacent executable/BSS mappings. This corrected an audit view
which first omitted the extension and then merged unrelated neighboring
VMAs; the exact owner comparison is retained. Every new close-word mismatch
is in the stack. The additional exit-entry component checks expose 672 stack
words; all remain failures.

The strict full audit retains **531,744 failures**:

| Unfinished assertion | Failures |
| --- | ---: |
| Complete stdin IO stack words | 303,330 |
| Complete log-close stack words | 207,016 |
| Complete malloc stack words | 19,866 |
| Exit-entry workspace stack words | 672 |
| Log-close register / FP boundaries | 224 / 224 |
| Earlier EOF/close and exit-entry register execution | 196 |
| X11 finalizer phases | 56 |
| Libc/loader exit runtime | 28 |
| Remaining allocator-event / freed-allocation counts | 28 / 28 |
| Process exit execution | 28 |
| Later stdin IO calls | 28 |
| Continuing malloc FP state | 20 |

The broader audit checks many previously unexecuted states. Its larger failure
count is not a tolerance change or a passing full-program result. Both full
commands return nonzero while the stack/FP/exit requirements remain.
The complete portable CPU and final packaged Pyodide reports agree exactly,
including every difference and coverage counter.

Eight new regression tests cover native provenance and every complete region,
all independent closes, actual continuous log release, changed later targets,
transient lock/FILE ordering even when final memory agrees, missing earlier
controls, preservation of pending output, and genuine earlier X11 controls.
The prior malloc/REPL regression tests now require reaching exit entry and
preserve its newly exposed 24 stack failures in each tested history. Their
native targets are unchanged. The previous malloc fixture also advances to
224 heap boundaries and still fails strictly. Broader phase/math, startup,
command/model and final process requirements remain active.
All 45 targeted portable regression checks pass, including the eight new
checks; all eight new compiled-runtime checks pass too. CI discovery includes
all eight. The older 130+4 command reports retain every parent field (zero and
816 differences), and every one of the eight printf/parser shards retains the
parent report, including its 24 saved-FP differences. The prior 28-history port
report remains at zero. The previous malloc fixture now reaches all 224 heap
boundaries and reports 324,224 strict failures; its additional 672 exit-entry
stack words remain required. The downloadable native source archive rebuilds
the unchanged numerical WASM byte for byte.

`shunt_cleanup_original.json.gz`: 47,712,672 bytes, SHA-256
`742506203a60080aa25ac03c2e0c5e6ba194467208c346e35ea1a14b15d7b32d`.
Source package `f691155179e12c92` contains all 195 current runtime source files and no
fixtures, verified byte for byte against the working tree. Numerical WASM
remains `c7869e98f4c18b5414dc172d836e7144ab3ebc0de2de0d1f2eec1a4fe1709186`.

```sh
python tools/capture_shunt_cleanup_original.py --reference ~/github/asitic-re \
  --library-path /path/to/i386/libs --debug-directory /path/to/libc/debug
PYTHONPATH=src:tests python -m unittest test_shunt_cleanup_original -v
python tools/audit_shunt_cleanup_original.py --isolated --output /tmp/cleanup-isolated.json
python tools/audit_shunt_cleanup_original.py --output /tmp/shunt-cleanup-cpu.json
python tools/build_site.py
node tools/check_shunt_cleanup_original.mjs /path/to/pyodide.mjs /tmp/shunt-cleanup-wasm.json
```
