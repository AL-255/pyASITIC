# Native vfprintf caller around its formatter

`vfprintf_storage.py` follows the pinned i386 glibc 2.39
`__vfprintf_internal` caller. It implements the narrow, unlocked path's
orientation checks, frame saves, PIC word, variadic/mode arguments, canary,
FILE-buffer initialization, formatter call site, count completion and
epilogue. It calls the existing `PrintfFile` source on the same Memory and
Heap, including its actual large-allocation paths.

`call(registers, formatter)` connects those source phases to an explicit
formatter callback. Without that implementation it raises. It does not
render with Python percent formatting, load a recorded return state, or
fill missing bytes from a fixture. The parser and numeric formatter remain
required work at libc+0x60530. Locked/cancellation, incompatible-stream,
wide-stream and argument/error branches also remain explicit boundaries.

## Independent component boundary

The caller audit separately checks entry through formatter entry, and
formatter return through caller return. Each phase initializes from its
own earlier native boundary only. The formatter return is a standalone
suffix-component input, never a continuing-replay seed or an implementation
of formatting. No whole-parent execution claim follows from those phase
checks. The reports explicitly retain `formatter_calls_pending` and
`formatter_children_pending` for every observed call and middle helper.

All formatter states and nested helper registers remain in the native
corpus. Exact child-index boundaries recorded by the observer partition
prefix, formatter and suffix helpers without guessing from function names.
Missing formatter returns and invalid boundaries fail. The earlier
continuing gate and all its unresolved differences remain required.

The corrected two-history prototype has 60 parent calls and 120 caller
phases, matching 28,393,852 four-byte units, 2,040 output registers, 292,800
FP bytes and 10,744 entry/return registers of 316 captured caller helpers.
CPU and Pyodide reports agree exactly; nine prototype source/negative tests
pass in each runtime. The 60 formatter calls and 466 middle helpers remain
pending. Complete-cohort verification is described below.

## Native capture and tests

All 67 unchanged jobs repeat cold and warm. Observation starts after the
first driver returns and stops at the next driver or native fault. Every
vfprintf entry, formatter entry/return and parent return retains full owned
stack, ELF, TLS, heap, arena, FILE, lock, vtable and control regions, actual
format bytes through NUL, registers, XSAVE and allocator/error state. Named
nested FILE helpers retain all 17 entry/return registers. Independent
external descriptor facts precede execution. No inferior instruction,
register, memory, allocation, result or signal is replaced. Guarded minimal
environments precede each observation.

The shared snapshot converter verifies every field, ordered owner list and
page byte before factoring it. Nested formatter states pass through the
same lossless converter without changing their ownership or discarding
any state. Archive manifests validate every part and the entire gzip stream.

The complete capture retains 134 histories and 3,973 parent/formatter calls,
including one no-call history. Named helper observations contain 20,921
caller helpers and 30,267 middle formatter helpers; all middle targets stay
recorded and pending. GDB outcomes retain 132 next-driver stops, one SIGSEGV
and one SIGABRT. Plain runs retain 130 normal outcomes, one SIGSEGV and three
SIGABRTs. No outcome is changed or omitted.

Lossless conversion verifies all 15,892 complete states and all 42,378 page
payloads. There are 36,147 region records, 917 factored contexts and 928 FP
images. The 46,399,324-byte gzip archive is stored as two checksummed parts:

```text
54c0415c44ffd9cf37c78a825c326f433782d90fa920a74eff69dcd163a2d327
```

The full unsharded CPU audit and all eight browser caller-phase shards
pass all 11 tests. Browser shards partition all 134 histories exactly once.
Both runtimes match all 7,946 caller phases,
1,902,553,920 four-byte units, 135,082 output registers, 19,388,240 FP
bytes and 711,314 entry/return registers of 20,921 caller helpers, with
zero differences. Overlapping owners and partial-word tails stay included.
The 3,973 formatter calls and 30,267 middle helpers remain required work.
The complete CPU report equals the merged browser report in every counter
and per-case result. These are caller-phase results; formatting itself is
not executed by this audit or treated as completed.
The complete previous FILE-helper CPU regression passes all 11 tests and
retains an identical full report for all 7,946 calls. Its shared comparison
logic now accepts an explicit source-storage factory; the default algorithm,
inputs and native assertions are unchanged.

Tests alter later memory, registers, FP bytes, heap fields and helper
registers and require differences. Earlier variadic pointers and mode
flags determine the generated formatter arguments. Missing earlier
controls fail; an altered suffix canary fails. A test-only callback writes
one byte through the same guest buffer and verifies count/callee-save
propagation; it is not used by production or native comparisons.

```sh
python tools/capture_vfprintf_original.py --reference ~/github/asitic-re \
  --library-path /path/to/i386/libraries --debug-directory /path/to/debug
PYTHONPATH=src:tests python -m unittest test_vfprintf_original
python tools/audit_vfprintf_original.py --output /tmp/vfprintf-cpu.json
python tools/build_site.py
node tools/check_vfprintf_original.mjs /path/to/pyodide.mjs /tmp/vfprintf-part.json 1 8
```

All eight disjoint browser shards are required. Reports stay local.
The verified source package is `82393d56d37332a0`; the compiled numerical
module remains unchanged at SHA-256
`c7869e98f4c18b5414dc172d836e7144ab3ebc0de2de0d1f2eec1a4fe1709186`.
This component does not establish complete formatting, continuing-call
integration or whole-program parity. The broader gate still retains its
198 unresolved differences.
The separate [formatter component](PRINTF_FORMAT.md) now implements
literal/narrow-string paths and retains complete nonzero formatter gates;
it does not change this caller audit into whole-parent execution.
