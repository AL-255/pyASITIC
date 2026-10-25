# REPL callers and earlier standard streams

The source continuation now connects main's acquisition wrapper, the stdio
caller and prompt caller, native polling setup and libc's timeval adapter in
the same simulation Memory. The new full comparison improves from the older
618 mismatches to **556 required mismatches**: 262 before parser entry and
294 at the final abort. It also compares additional complete static stream,
lock, vtable, binding and REPL-control regions at every later boundary.

All generated registers match independent native observations at poll entry,
select64 entry and four lazy-resolver entries (`signal`, `select`,
`add_history`, `kill`). Each comparison covers the complete 17-register set,
including the earlier segment selectors and `orig_eax`. No call snapshots
seed the continuing path.

## Earlier inputs and broader assertions

`capture_stdio_transition_original.py` repeats all 67 existing jobs cold and
warm. It extends the earlier **first-driver entry** context with:

- Complete 152-byte views of stdin, stdout and stderr, their global bindings,
  actual signed-offset vtables and 12-byte locks.
- The REPL script path/control bytes and selected acquisition function.
- The full earlier register set and stdin's regular-file type and position.
- The independent i386 SAR behavior probe, run before all ASITIC jobs.

The continuing source still starts at the same earlier simulation boundary
and retains every prior heap, event, freed buffer, file and command target.
All 12 added regions, totaling 688 bytes, are checked at **every** later
command point and final transition state. Later bytes never initialize the
simulation. Mutation tests alter later lock assertions and remove regions;
the checks fail. Removing the earlier lock bytes produces an explicit unknown
memory error, with no recovery from the later regions. Mutating the earlier
stdout FILE lock pointer changes the generated poll EDX to that pointer.

Some histories have already buffered stdin before the first driver, including
a file position of 51. Those earlier positions and buffers remain explicit;
they are not reset to zero. The connected EOF path currently requires the
observed regular-file stdin at position zero and rejects other acquisitions
or recording modes. The existing native history that reaches this path has
those earlier inputs.

## Source stores

`repl_storage.py` emits the native main/acquisition/stdio/message caller
frames, saved registers, word-sized flags, argument pushes and return PCs.
Unused alignment bytes survive. The prompt's existing source stream emitter
supplies successful output; the fflush return ABI derives its volatile
registers from the earlier stream lock and TLS state, restoring the saved
caller registers. It does not copy native return values.

The successful single-threaded, unlocked, no-input-seek fflush path follows
`iofflush.c` and `fileops.c`: successful sync invalidates `_offset` with
`_IO_pos_BAD`, and lock release supplies EDX and the final depth-test flags.
The first narrow underflow sets stdin's byte orientation through `_IO_fwide`.
These three FILE words were newly exposed by the complete static-stream
checks; their source stores resolve all added static-region mismatches.
Wide-oriented, locked, threaded and unread-input seek paths stop explicitly.
The glibc-derived stores retain the LGPL-2.1-or-later license notice.

The polling caller derives all incoming registers from those earlier frames
and stream fields, executes `poll_select` and `select64_entry`, and retains
their actual source stack stores. The external descriptor is the original
launcher's regular answers file. The kernel and full select64 body are still
unfinished; no observed timeout value or readiness return is injected.
The pre-input flush/fgets, append/log and normalization caller stores follow
the original stdio routine. Logging and byte normalization keep their existing
source algorithms; the normalization ABI emits its real locals and saved
words. Main and dispatch preserve the earlier nonmodified register fields.

## What remains different

Relative to the older loader-context comparison, 64 differing address/phase
pairs resolve and two new pairs appear: one real earlier source-written word
differs at both the pre-parser and final checkpoints. Native later execution
overwrites it with zero; the corresponding later operation is not implemented
yet. The word is at workspace + 2968. It remains a required failure. No word is selectively cleared, exempted,
fitted or supplied from an expected snapshot.

The full printf/libio/sync child stack frames, select64/kernel timeout and
syscall paths, three stdin `_IO_*` bindings and `strcat` binding remain
unfinished. The current source preserves their missing later overwrites as
strict failures. Parser child ABI, interrupted FP/XSAVE and signal/handler
continuation, other commands and analyses, complete startup/lifetimes,
arithmetic, JOIN/UNJOIN and older heap/mapping differences remain required.
The loader-only audit still requires 618 differences and the older audit
still requires 816; neither fixture is replaced. The mandatory
`stdiotransition` suite supplements all earlier suites and exits nonzero
until the full continuing comparison passes. Diagnostic reports stay local.

## Native capture provenance

All 134 histories and actual native outcomes remain. GDB reaches 132 next
drivers, one SIGSEGV and one SIGABRT. Plain runs observe 127 normal exits,
six SIGABRT and one SIGSEGV. Relative to the loader-context parent, the cold
width-3/contact pilot changes from normal exit to SIGABRT, the cold boundary
coarse pilot from SIGSEGV to SIGABRT, and its warm peer from SIGABRT to normal
exit. These fresh outcomes are retained, without target or launch retuning.

The minimal environment is guarded before reading the earlier stack. The
observer only reads native memory, registers, procfs metadata and outputs.
No inferior instruction, register, memory byte, allocation, kernel result or
signal outcome is substituted. Full original commands, observer source,
binary hashes, parent hashes and all original data remain in the fixture.

The fixture is 47,205,879 bytes, compressed SHA256
`8f1b0fb9e7ed1126b6903268d0e49c10defb3664fbe26fa560d354d6dc44fec7`,
uncompressed SHA256
`d7ebdba45a2ab1ca7e081a6fbff2284d9502174a4786f8c09a514b3d3904321f`.

## Verification

All 124 affected CPU tests pass, including the five new integration tests.
The same five tests pass in packaged Pyodide, version `b2236a2cf6630d21`.
The complete rectangular cold CPU report equals its compiled browser report.
The full browser audit retains all 134 histories and reports 556 differences
only in that cold history; the other 133 histories match all their targets.
All 9,479,168 later heap words, 664 allocator events, 135 freed buffers,
140 console calls and 132 output files match, with zero unknown bytes.
The expanded audit checks 175,161 final component words and 350,322 point
words; all added static-region words match.

Both older full compiled comparisons were rerun on the final source package.
The loader-only fixture still reports 618 required mismatches. All 130 older
main histories pass; the four extra histories retain their 816 required
mismatches. All three strict checks exit nonzero. Workflow syntax, complete
disjoint Python test discovery, JavaScript syntax and patch validation pass.
The numerical WASM binary is unchanged. These changes are not deployed and
do not change the production trailing-via guard.

```sh
python tools/capture_stdio_transition_original.py --debug-directory /path/to/debug/usr/lib/debug --reference /path/to/asitic-re --library-path /path/to/native-libraries
PYTHONPATH=src:tests python -m unittest test_stdio_transition_original -v
python tools/build_site.py
node tools/check_stdio_transition_original.mjs /path/to/pyodide.mjs /tmp/stdio-wasm.json
node tools/check_loader_transition_original.mjs /path/to/pyodide.mjs /tmp/loader-only.json
node tools/check_command_transition_original.mjs /path/to/pyodide.mjs /tmp/older-main.json /tmp/older-extra.json
```
