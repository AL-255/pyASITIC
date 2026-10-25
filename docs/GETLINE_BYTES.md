# Scalar getline search and copy

The subsequent [flush checkpoint](FLUSH_STORAGE.md) connects complete
fflush/sync/write source and reduces the new continuing fixture to 198
required differences. This getline fixture and its strict 284-difference
gate remain required unchanged.

`getline_bytes.py` implements the pinned i386 internal memchr and memcpy
called directly by `_IO_getline_info`. These routines are scalar, using
byte/word loads, arithmetic and REP MOVS; they do not execute SIMD or x87
operations. The independent comparison matches **all 268 captured calls**,
including script input and the stdin line, against complete native regions,
all registers and XSAVE state.

## Source algorithms

Memchr follows the original alignment prefix, 16-byte batches, bounded
four-byte probes, zero-byte detection and final byte tail. It retains the
actual intermediate ECX/EDX values and original register saves. The final
tail counter uses 32-bit wrapping arithmetic; it never probes an extra word
merely because Python integers are wider. Tests explicitly make the bytes
after the last valid word unknown.

Memcpy follows the actual source/destination alignment branch, initial
byte/word copies, forward DWORD copies and final byte tail. It emits the
original saved-EDI stack word where that branch pushes it. Source/destination
overlap follows those actual forward instruction widths rather than a
temporary whole-range copy. Caller-preserved registers, volatile return
registers and flags follow the original instruction sequence.

The undefined AF bit after SHR comes from an independent 32-bit instruction
probe run **before all native jobs**. Twenty-four observations cover twelve
operands with both earlier AF states, checking the result and every defined
arithmetic flag. This capture reports constant AF=16; the source also
supports a constant zero or a measured preserved-AF profile. Unknown
behavior stops explicitly. No later native function-return flags select
the profile or correct the Python output.

## Continuing stdin caller

For the supported first narrow stdin line, `InputStream` interleaves the
first uflow character with the actual buffered search and copy. It does not
write future copied characters before executing those callers. Argument
stores, saved locals and all entry registers derive from the earlier FILE,
buffer, source read result, parent frames and remaining count. Memchr's
incoming ECX follows the original underflow's cached file offset; memcpy's
registers follow the delimiter extraction branch. Both calls operate in
the same Memory as the existing heap and read model.

All 17 entry and return registers of both generated calls match the
independent stdin capture, and all eight previous PLT binding register sets
remain exact. Missing earlier CPU behavior fails explicitly. Additional
refill/undelimited getline callers, other library implementations and the
remaining FP/kernel continuation are still unfinished.

The complete continuing comparison retains **284 required differences**,
with 126 point-word differences and 158 final-word differences. The same
address/phase pairs remain: later native operations overwrite the source
caller words and still require their own implementation. No mismatching
word is exempted, zeroed or loaded from expected later state.

## Complete independent captures and lossless storage

All 67 unchanged jobs are repeated cold and warm. Across 134 histories,
133 reach at least one operation; one retains its absence of calls.
There are 134 memchr calls and 134 memcpy calls. The observer records each
call's first matching return at its actual caller ESP, preventing a later
call at the same return PC from overwriting the earlier assertion. Full
regions, all 17 registers and XSAVE remain targets at every boundary.

The comparison checks **63,688,292 four-byte units, 4,556 registers and
653,920 FP bytes with zero differences** in CPU Python and Pyodide. Units
include overlapping owners and partial-word tails. Complete FP bytes stay
unchanged, as required by these scalar instruction paths.

The capture contains 1,435,944 before/after region owners and 509,302,656
bytes counting repeated owners. Lossless manifests retain their exact order,
addresses, sizes and full content hashes: 3,501 unique records reference
5,544 content-addressed chunks containing 12,625,545 unique bytes. Every
expanded owner record and every reconstructed byte was checked against
the complete original capture before conversion. Manifest and chunk hashes
are checked on read. No target is omitted by deduplication.

The independent audit also coalesces only the exact union of earlier mapping
owners, preserving every gap and unknown byte. This avoids repeatedly
sorting thousands of overlapping ELF owners on each guest access. Region
comparisons still require every original owner separately. Tests verify gap
faults, manifest integrity and later-target independence.

The continuing capture uses earlier first-driver state plus the independent
CPU profile. It imports no per-call search/copy snapshots. All 26 memory
owners (1,942 bytes), descriptor positions, heaps, allocator events, freed
buffers, console/calendar calls, files and terminal outcomes remain required.

## Validation

All **170 targeted CPU tests pass**, including seven component tests and
four continuing integration tests. Those eleven also pass in packaged
Pyodide, version `cee7072bb5018fcf`. The full independent CPU and Pyodide
reports are identical, including every per-history counter. Manifest-index
validation is additionally checked after adding explicit rejection of
negative indices.

The fresh full compiled comparison retains every history. Only the
rectangular cold history differs, and its complete CPU report is identical
to Pyodide's report. All 399 descriptor positions, 9,479,168 later heap words,
664 allocator events, 135 freed buffers (10,580 bytes), 140 console calls,
132 calendar calls and 132 files (187,415 bytes) match with zero unknown
bytes. All 26 region owners remain checked, totaling 216,790 final component
words and 433,580 point words across 266 points, plus partial-word tails.

All seven older full compiled gates were rerun on the same package. Their
read, malloc, stat, input, stdio, loader and extra-command histories retain
284, 284, 298, 382, 556, 618 and 816 differences respectively; the older
130 main command histories still pass. The new and seven older strict
continuing checks all exit nonzero. Workflow syntax, complete disjoint test
discovery, language syntax and patch validation pass. The mandatory new
workflow suites are `getlinebytes` and `getlinetransition`.

## Provenance

Both fresh GDB captures retain 132 next-driver outcomes, one SIGSEGV and one
SIGABRT. The component's plain runs retain 130 normal exits, three SIGABRT
and one SIGSEGV; its pilot-width3/1/contacts cold and warm histories change
from SIGABRT to normal exit relative to the parent read fixture.

The continuing plain runs retain 125 normal exits, eight SIGABRT and one
SIGSEGV. Relative to the parent, square/1/coarse cold and warm,
pilot-width3/1/coarse warm and pilot-boundary/1/coarse warm change from normal
exit to SIGABRT; pilot-width3/1/contacts cold changes from SIGABRT to normal
exit. All outcomes remain recorded without selecting or retuning launches.

The minimal environment guard precedes capture. Observer/commands, binary
hashes and parent hashes accompany both fixtures. No inferior instruction,
memory, register, allocation, result or signal is substituted. Reports stay
local. The numerical WASM and production guard are unchanged; this
development checkpoint is not deployed.

| Fixture | Compressed bytes | Compressed SHA256 | Uncompressed SHA256 |
| --- | ---: | --- | --- |
| `getline_bytes_original.json.gz` | 6,609,918 | `e2ad3c69615bfcffd64df9c9135d9b4292e0d1fe300d36666953be6664f980e6` | `02fb6b8f774101e8a2b2c322d99471b96e64b998eb0b3f613e3095cf57ea8798` |
| `getline_transition_original.json.gz` | 47,501,074 | `5a9bc5b2511b6131d04f233f3d33020e62b973e5598d9a160a6dc4ab39247dd2` | `c4bd8ac2b79ed466753231686d81e91cbb26295c16d53556309ae5580a05462b` |

```sh
python tools/capture_getline_bytes_original.py --debug-directory /path/to/debug/usr/lib/debug --reference /path/to/asitic-re --library-path /path/to/native-libraries
python tools/capture_getline_transition_original.py --debug-directory /path/to/debug/usr/lib/debug --reference /path/to/asitic-re --library-path /path/to/native-libraries
PYTHONPATH=src:tests python -m unittest test_getline_bytes_original test_getline_transition_original -v
python tools/build_site.py
node tools/check_getline_bytes_original.mjs /path/to/pyodide.mjs /tmp/getline-bytes.json
node tools/check_getline_transition_original.mjs /path/to/pyodide.mjs /tmp/getline-continuing.json
```
