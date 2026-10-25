# Native stdin and newline append

This records the 382-difference stdin checkpoint. The subsequent
[file-allocation integration](FILE_ALLOCATION.md) implements the stat syscall
record and allocation callers and reduces the continuing gate to 298
differences. The original fixture and its strict comparisons remain required.

The continuing source now executes the narrow fgets/getline/uflow caller
stores, legacy C++ stream wrappers, foreign-vtable acceptance fast path and
the short newline append in the same simulation Memory. All **eight** lazy
resolver entry register sets match independent native captures, covering all
17 registers each. The full continuing comparison improves from 556 to
**382 required differences**: 175 before parser entry and 207 at final abort.

The comparison is also broader: it checks the complete 1,024-byte main input
buffer, immutable string literals and additional libc globals at every later
point and final boundary. Every newly added region matches in the cold CPU
case, including the input buffer's retained tail. Per-call native snapshots
remain assertions only; they never initialize the continuing simulation.

## Earlier inputs

`capture_input_transition_original.py` repeats all 67 existing jobs cold and
warm, preserving all 134 histories, outcomes, scripts and input files. At the
earlier **first-driver entry**, it supplements the preceding stdio context
with libc's weak stdin ABI binding, encoded foreign-vtable acceptance pointer,
the corresponding main ABI flag, immutable program string data and the main
input-buffer view derived from the earlier parent frame. The loader/TLS
context already supplies the pointer and stack guards. All of those memory
owners become later assertions too: 17 regions totaling 1,884 bytes.

The earlier regular stdin descriptor also supplies its actual stat metadata.
The source allocation uses the stat block size and BUFSIZ rule rather than a
fixed 4,096-byte request. An input mutation to an 8,192-byte block size changes
both the generated allocation and the read binding's size argument. The full
native stat structure, its syscall writes and allocator child frame remain
unimplemented; no later observed stat structure or returned pointer supplies
those missing words.

## Source operations

`stdin_storage.py` implements the pinned i386 caller layouts and source state
changes around `fgets`, `_IO_getline`, `_IO_getline_info`, `__uflow`,
`_IO_default_uflow` and `_IO_file_underflow`. The foreign-vtable fast path
demangles the **earlier** acceptance pointer with the earlier TLS pointer
guard and verifies that it names `_IO_vtable_check`. It emits that function's
saved EBX, PC-thunk return, stack canary and return flags. Other namespace and
compatibility paths stop explicitly.

The legacy `streambuf::uflow`, `filebuf::underflow` and `filebuf::sys_read`
wrappers emit their original frames, saved EBX, PIC thunk, argument pushes
and return PCs. Their imports resolve through the existing source ELF/PLT
implementation. The GOT comes from ELF metadata and the callbacks from the
earlier stream vtable, with the legacy image hash and implementations checked.
There is no native execution, instruction decoding or observed target lookup
inside the Python model.

The existing `InputStream` byte algorithm performs the actual external-file
read into its source-allocated guest buffer. Optional ABI hooks interleave
the native caller/underflow/read-binding stores with allocation and refill.
The successful getline return emits its memchr/memcpy caller arguments and
releases the stream lock. The native child ISA effects and syscall/allocator
frames remain separate unfinished work.

The stdio caller then binds `strcat` using the source IFUNC selector. The
currently connected libc implementation is its first-16-byte destination
probe followed by the two-byte newline/NUL copy. That short path uses no XMM
register. The caller's immutable newline comes from the earlier program
literal, and the function preserves the rest of the destination and saved
registers. Longer destination scans require their SIMD-state implementation
and stop explicitly. Logging, normalization and dispatch keep their existing
source algorithms and ABI stores.

All eight generated resolver entries are compared to the independent native
PLT fixture in their original order: `signal`, `select`, `_IO_default_uflow`,
`_IO_file_underflow`, `_IO_file_read`, `strcat`, `add_history`, `kill`. No
entry, register or target is selected away. The preceding four-entry stdio
test remains required for its older inputs as well.

## Required differences

Relative to the 556-difference stdio checkpoint, 176 address/phase mismatches
resolve and two new ones appear. One genuine earlier source write at
workspace + 2672 survives in Python at both later checkpoints, while native
later execution overwrites it with zero. It remains a required failure.
No word is selectively zeroed, exempted or supplied from expected output.

Kernel polling/timeout effects, full stat and allocator child frames, read
syscall/VDSO effects, memchr/memcpy ISA and FP state, printf and parser child
frames, interrupted XSAVE and signal/handler continuation remain unfinished.
Other command/analysis/lifetime paths, arithmetic, JOIN/UNJOIN and older
heap/mapping failures remain required. The three older continuation fixtures
retain their 556, 618 and 816 failures. The mandatory `inputtransition` suite
supplements every older gate and exits nonzero while any target differs.
Diagnostic reports stay local. No deployment or production guard changes.

## Native provenance

The fresh GDB runs retain 132 next-driver outcomes, one SIGSEGV and one
SIGABRT. Plain runs retain 128 normal exits, five SIGABRT and one SIGSEGV.
Relative to the parent, square/1/coarse warm changes from SIGABRT to normal
exit; pilot-width3/1/coarse warm from normal exit to SIGABRT; both contact
width-3 pilots from SIGABRT to normal exit; and pilot-boundary/1/coarse warm
from normal exit to SIGABRT. No launch or target is retuned to change these
fresh native outcomes.

The minimal environment is checked before reading the earlier stack. The
observer only reads memory, registers, procfs file metadata and native
outputs. No inferior memory, instruction, register, allocation, kernel
result or signal outcome is substituted. Complete commands, observer source,
binary hashes and parent hashes accompany the fixture.

The fixture is 47,373,753 bytes, compressed SHA256
`5b322f9d0f34271bac115b6e092bb624d3ef57992b7f4fa112228cfc2859281f`,
uncompressed SHA256
`0c592dc22ffbb020ee29efdebfb2b462bf4be0280c9892823b67e908748975d4`.

## Verification

The 124 regression CPU tests and five new CPU tests pass. All five new tests
also pass in packaged Pyodide, version `7a0a81d1164b0a53`. The complete cold
CPU report is identical to its compiled browser report. The new full browser
audit retains all 134 histories: only the rectangular cold history differs.
All 9,479,168 later heap words, 664 allocator events, 135 freed buffers,
140 console calls and 132 output files match, with zero unknown bytes.
The expanded check compares 214,928 final component words and 429,856 point
words, including every byte of the added main input buffer.

All three older full compiled continuation comparisons were rerun on the
same final package. They retain 556, 618 and 816 differences respectively;
all 130 older main histories still pass. All four strict checks exit nonzero.
Workflow syntax, complete disjoint Python discovery, JavaScript syntax and
patch validation pass. The numerical WASM is unchanged. These changes are
not deployed and retain the production trailing-via guard.

```sh
python tools/capture_input_transition_original.py --debug-directory /path/to/debug/usr/lib/debug --reference /path/to/asitic-re --library-path /path/to/native-libraries
PYTHONPATH=src:tests python -m unittest test_input_transition_original -v
python tools/build_site.py
node tools/check_input_transition_original.mjs /path/to/pyodide.mjs /tmp/input-wasm.json
node tools/check_stdio_transition_original.mjs /path/to/pyodide.mjs /tmp/stdio-wasm.json
node tools/check_loader_transition_original.mjs /path/to/pyodide.mjs /tmp/loader-wasm.json
node tools/check_command_transition_original.mjs /path/to/pyodide.mjs /tmp/older-main.json /tmp/older-extra.json
```
