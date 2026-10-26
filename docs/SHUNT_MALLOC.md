# Continuing stdin allocation through QUIT

This checkpoint precedes [continuing log closure](SHUNT_CLEANUP.md). The same
source now closes the logs and reaches exit entry on this fixture too. The
counts below describe the earlier checkpoint; every native target remains
required in the subsequent audit.

The source replay now handles first-buffer stdin allocation in the ten
previously blocked keyword-created histories. All fourteen unchanged scripts,
cold and warm, now reach QUIT parsing and cache release using the same
continuing heap, memory, FILEs and descriptor positions. Complete stack/FP
execution, log closure and process exit remain unfinished. This development
branch is not deployed.

## Shared source execution

`MallocTopStorage` already implemented large allocation ABI effects for
printf. It now separates entry and return so stdin can share those effects
around its existing single `Heap.malloc` call. The original one-call interface
remains for printf. `MallocStorage` retains its unsorted exact-fit path and
routes other large requests to the shared bin/top/consolidation path.
Allocation addresses, split candidates and free lists come from the source
allocator, never observed native returns.

The heap now publishes changing arena fields and fastbin heads into its
existing guest memory. Binding requires a genuine earlier arena image;
known inconsistent images fail explicitly. Minimal older component inputs
without that image retain their partial ABI rather than receiving fabricated
bytes. Full replay supplies the original first-driver arena before geometry
and follows all its intervening operations. It never reloads an arena or
heap at stdin malloc entry.

The read-only native observer adds every stdin doallocate malloc public
entry/return, with complete stack, heap and arena regions, all 17 registers,
XSAVE and allocator state. It keeps all prior solve, command, file and shutdown
targets and every original script/outcome. No inferior instruction, byte,
register, result, allocation, return, signal or affinity is replaced.

Sixty complete captured malloc regions (25,827,120 bytes) are losslessly
factored into the existing immutable heap page bank. Ordered owners,
original lengths and SHA-256 hashes remain required. Projection checks the
complete original bytes before removing the dense representation; readers
validate both each page and the complete expanded region. This affects fixture
storage only. The browser runtime contains no fixture files.

## Independent and continuing comparisons

The independent whole-function comparison supplies each call's own earlier
entry inputs, then executes the source allocator and ABI. All ten native
calls match: **3,228,390 complete memory words, 170 registers, 24,400 XSAVE
bytes and ten allocator boundaries**, with zero differences. These independent
component inputs are never inputs to the full history.

The full history observes malloc against the live source heap and memory;
there is no snapshot copyback. Both phases of all ten calls are checked:
**6,456,780 memory words, 340 registers and twenty allocator boundaries**.
Heap/arena bytes, physical header walks, allocator fields and registers match.
There are 19,866 differing stack words. In every affected history, the complete
list of differing addresses and actual/original values is identical before
and after malloc: the call preserves these inherited differences. They remain
failures. The earlier complete source FP state is still missing, so twenty
malloc FP boundaries also remain explicit failures rather than borrowing
native entry XSAVE to claim continuing matches.

The full audit now additionally reaches:

| Continuing target | Checked |
| --- | ---: |
| Allocator events / complete freed allocations | 1,410 / 1,400 |
| Complete freed usable bytes | 42,664,592 |
| Complete output heaps / words | 196 / 50,706,432 |
| Independent FILE/buffer/list/workspace/stdio bytes | 51,615,032 |
| Interactive parser registers | 280 |
| Public printf/fprintf calls / registers | 84 / 2,856 |
| Stdin IO calls / phase registers | 176 / 5,984 |
| Descriptor positions | 352 |
| Complete output files / bytes | 28 / 45,252 |
| Unknown compared bytes, including malloc and IO | 0 |

All compared heap/component/freed/file bytes, public-call/parser/IO registers
and descriptor positions match. The strict full report nevertheless contains
**323,552 failures**:

| Unfinished assertion | Failures |
| --- | ---: |
| Complete IO stack words | 303,330 |
| Complete malloc stack words inherited from earlier execution | 19,866 |
| EOF/close register execution | 168 |
| Log/process cleanup runtime | 28 |
| Exit boundaries | 28 |
| Remaining event counts | 28 |
| Remaining freed-allocation counts | 28 |
| Process exit execution | 28 |
| Later IO calls | 28 |
| Continuing malloc FP state | 20 |

The expanded audit exposes more stack differences as the previously stopped
histories advance. No word, owner, history, outcome or tolerance is waived.
Portable CPU and final packaged Pyodide reports agree exactly in every
difference and coverage counter. Full audit commands return nonzero while
these requirements remain.

Eight new regression tests cover complete provenance, every independent
malloc endpoint, actual unbuffered QUIT/cache continuation, later-target
independence, missing controls, inconsistent earlier arena inputs, complete
later allocator fields and changed later FP assertions. The older changed-request test now executes the newly
supported 8,192-byte allocation and checks its actual header instead of
requiring the former unsupported-path exception. All previous native output
targets remain unchanged. All eight new tests pass in portable Python and the
final packaged compiled runtime. CI discovery includes all eight.

The prior 28-history port report remains at zero. The prior 134 command
reports and eight printf/parser shards retain every parent field, including
the 816 older command differences and 24 saved-FP differences. Heap/mapping,
shared-memory, EOF, malloc and malloc-transition regressions remain required.
These checks do not establish whole-program equivalence; earlier phase/math,
startup, other command/model paths and final process cleanup still need work.

`shunt_malloc_original.json.gz`: 41,921,899 bytes, SHA-256
`308591ce8ebb8f3caf5e7bd51471afab967de0fccdaedfa31373aec40c4c152c`.
Source package `8d759fd610287c40` contains all 194 current runtime source files,
verified byte for byte against the working tree. Numerical WASM remains
`c7869e98f4c18b5414dc172d836e7144ab3ebc0de2de0d1f2eec1a4fe1709186`; the downloadable native source archive rebuilds it exactly.

```sh
python tools/capture_shunt_malloc_original.py --reference ~/github/asitic-re \
  --library-path /path/to/i386/libs --debug-directory /path/to/libc/debug
PYTHONPATH=src:tests python -m unittest test_shunt_malloc_original -v
python tools/audit_shunt_malloc_original.py --isolated --output /tmp/malloc-isolated.json
python tools/audit_shunt_malloc_original.py --output /tmp/shunt-malloc-cpu.json
python tools/build_site.py
node tools/check_shunt_malloc_original.mjs /path/to/pyodide.mjs /tmp/shunt-malloc-wasm.json
```
