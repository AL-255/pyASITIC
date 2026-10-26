# Continuing stdin, QUIT and cache release

This checkpoint precedes the [shared malloc continuation](SHUNT_MALLOC.md),
which now carries the remaining ten histories through QUIT and cache release.
The counts and explicit failures below describe this earlier checkpoint;
the follow-up retains these targets and adds complete malloc endpoints.

The development replay now resumes the same script, heap, memory and console
through native signal installation, prompt output, stdin flush/read, logging,
normalization, QUIT parsing and cache release for all 18 buffered-input
histories. All fourteen original scripts remain in the cold/warm capture and
full audit. The other ten histories still stop at unimplemented malloc ABI
branches when their first stdin buffer is needed. Log/process cleanup and
complete CPU/stack execution remain unfinished requirements.

## Earlier inputs and shared execution

The new read-only capture supplements the original first-driver entry with
genuine loader/link-map/ELF/GOT/TLS metadata, standard/log FILEs and vtables,
named regular-file stat/statx facts and descriptor position. Independent i386
SAR/SHR probes supply the same undefined-flag profiles used by the existing
stdio translation. Later printf and IO snapshots are assertion targets only;
the continuing execution never loads them.

All 28 unchanged plain and observed original histories exit normally. The
entire previous first solve, outer command, second solve and port output still
match on the new capture, including the newly owned stdio regions at command
boundaries. No inferior instruction, byte, register, allocation, result,
return, signal or affinity is replaced.

`CommandTransition` now separates script-close ABI preparation from the shared
REPL continuation. `ScriptEOFStorage` invokes that continuation after its
actual script stream returns. Contexts with genuine earlier TLS also use the
shared narrow close in the older generic EOF path. Older contexts without
thread inputs retain their partial final-field path and existing strict
targets; no later lock owner supplies the missing earlier input.

Interactive creators have already consumed answers from stdin when simulation
begins. Their descriptor can be at EOF while `quit` remains unread in the
buffer. Native `fflush(stdin)` seeks back over those bytes, invalidates the
cached offset, and makes the subsequent fgets refill that existing buffer.
The source now performs this sequence using virtual descriptor positions.
It never seeks a host file or borrows an observed return count/position.

`SeekStorage` follows the pinned `_IO_file_seek` / `llseek` frames and VDSO
saves. `FlushStorage` includes the legacy four-register seek wrapper;
`StdinStorage` accepts an exhausted existing buffer as well as a first read.
Regular-file readiness produces the original poll wrapper's boolean and
volatile registers. The shared VDSO prefix supplies its actual saves before
kernel entry. Elapsed timeout copyback and other kernel stack effects remain
explicitly incomplete.

The balun cache arrays also revealed a missing earlier input: their mmap chunk
headers and allocation padding were outside the declared table contents.
The capture now reads all 60 complete preexisting cache mappings at first
driver entry, includes their actual allocator records, and observes their
live headers at every later allocator boundary. They are absent from those
later targets after native unmapping. Source cache cleanup frees these actual
continuing mappings; it never initializes padding from a later free snapshot.

## Exact results and remaining failures

The portable and compiled isolated seek/sync component comparison checks all
120 native calls: **4,059,600 full stack/FILE words, 2,040 registers and 120
descriptor positions**, with zero differences. Component tests have their own
earlier call inputs; these inputs are never used by the full replay.

The full continuing replay additionally compares:

| Continuing target | Checked |
| --- | ---: |
| Allocator events / complete freed allocations | 920 / 920 |
| Complete freed usable bytes | 31,902,992 |
| Complete output heap boundaries / words | 186 / 47,818,752 |
| Independent FILE/buffer/list/workspace/stdio bytes | 48,981,612 |
| Interactive parser registers | 180 |
| Public printf/fprintf calls / registers | 64 / 2,176 |
| Stdin IO calls / complete phase registers | 166 / 5,304 |
| Descriptor positions | 312 |
| Complete output files / bytes | 28 / 45,252 |
| Unknown compared bytes, including IO stacks | 0 |

All compared heap/component/free/file bytes, public-call and parser registers,
IO registers and descriptor positions match. The IO call stacks are checked
in their entirety and **still fail**. The full audit retains **263,984
failures**:

| Unfinished assertion | Failures |
| --- | ---: |
| Complete IO stack words | 263,598 |
| Earlier EOF/close register execution | 168 |
| Later parser/exit boundaries | 38 |
| Unexecuted IO calls | 38 |
| Runtime paths: eight unsorted-fit, two consolidation, eighteen cleanup | 28 |
| Remaining event counts | 28 |
| Remaining freed-allocation counts | 28 |
| Process exit execution | 28 |
| Incomplete fgets/underflow return phases | 20 |
| Remaining public printf calls | 10 |

This is a broader audit than the preceding EOF checkpoint: it now observes
every complete native stdin fflush/sync/seek/read stack, rather than merely
reporting those calls as missing. It exposes inherited numerical/libc caller
stack effects and unfinished kernel/cleanup execution. No differing stack
word, owner, input history, outcome or tolerance is waived. Both strict
full-audit commands below exit nonzero while these requirements remain.
The complete portable CPU and final packaged Pyodide reports agree exactly,
including every difference and coverage counter.

Five new regression tests check complete native provenance, source-driven
descriptor positions, all isolated seek targets, continuing QUIT/cache events
and independence from changed later IO words/registers. Passing those tests
does not make the full shutdown audit pass. The prior 134 command reports,
port fixture, EOF tests and more integrated printf/parser/FP comparisons
remain separate required checks. Other phase, math, startup and model-format
gaps remain active; this branch is not deployed.
The older 130+4 command reports remain unchanged (zero and 816 differences).
All eight more integrated printf/parser shards also match fresh reports from
the unmodified parent commit, including its 24 strict saved-FP differences.
The previous 28-history port audit stays at zero differences, and the five
prior EOF regression tests pass. The five new tests pass in portable Python
and the packaged compiled runtime. CI discovery includes them all.

`shunt_repl_original.json.gz`: 41,564,133 bytes, SHA-256
`8bd046333127277e8ce79ab46c70ea2c4de9c1b987cfa290dcbc2343bcad3d1c`.
The fixture is excluded from the browser runtime. Source package:
`2b04d3901f91aba2`, with all 194 runtime source files verified against the
working sources; numerical WASM remains
`c7869e98f4c18b5414dc172d836e7144ab3ebc0de2de0d1f2eec1a4fe1709186`.

```sh
python tools/capture_shunt_repl_original.py --reference ~/github/asitic-re \
  --library-path /path/to/i386/libs --debug-directory /path/to/libc/debug
PYTHONPATH=src:tests python -m unittest test_shunt_repl_original -v
python tools/audit_seek_storage_original.py --output /tmp/seek-cpu.json
python tools/audit_shunt_repl_original.py --output /tmp/shunt-repl-cpu.json
python tools/build_site.py
node tools/check_shunt_repl_original.mjs /path/to/pyodide.mjs /tmp/shunt-repl-wasm.json
```
