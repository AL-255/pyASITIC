# Script EOF and the remaining process-shutdown audit

The development branch now retains the actual `InputStream` created by the
outer command continuation. After both numerical solves and the port export,
`ScriptEOFStorage` resumes that same stream, reads EOF, and closes its FILE on
the same heap, memory, console, list and earlier TLS state. It does not recreate
a stream from a later native FILE snapshot. A subsequent script command is an
explicit unsupported continuation, rather than being discarded as EOF.

The read-only original observer continues further: all fourteen unchanged
scripts, each cold/warm, now run through interactive QUIT, cache/log cleanup,
libc exit processing and the actual process exit. All 28 plain and observed
runs exit with status zero. The capture retains every intervening allocator
event and every complete freed usable allocation, including padding. It never
calls or replaces an inferior function, instruction, register, memory store,
allocation, return, signal, result or affinity.

## Shared narrow close and transient stores

`libio_storage.close_byte_stream` now supplies the port and new script close
paths. It unlinks the live FILE, acquires its lock from earlier `THREAD_SELF`,
flushes output when applicable, frees the buffer, resets narrow FILE fields,
unlocks, and frees the FILE. Recursive ownership/count and uncontended locks
retain the existing port-close behavior; wait paths remain unsupported.

The older generic `_script_eof` path resets the FILE before releasing its
buffer. The new native capture demonstrates why that ordering is insufficient:
at the buffer-free boundary the original FILE still retains its live pointers,
descriptor and held lock. The new continuation follows those stores. Rewiring
the older generic EOF/REPL path, including its earlier loader/stdio/FP inputs,
remains integration work; this change does not declare that path complete.

The source retains all six new EOF/close heap and independent component
boundaries exactly across all 28 histories:

| Implemented EOF/close target | Checked |
| --- | ---: |
| Ordered frees | 56 |
| Complete freed usable allocations | 56 / 123,872 bytes |
| Complete heap boundaries | 168 |
| Heap 32-bit words | 43,462,656 |
| Independent FILE/buffer/list/workspace bytes | 1,489,152 |
| Complete retained output files | 28 / 45,252 bytes |
| Unknown bytes | 0 |

These are memory/allocator/file results. The native register observations at
these boundaries are still missing from the source execution and remain
failures. Five CPU/browser tests check capture integrity, actual stream reuse,
later-target independence and the transient-reset regression. Deliberately
resetting the FILE early fails the intermediate heap/FILE assertions even
though the final heap is unchanged.

## Full shutdown remains a failing requirement

The full native horizon contains **224 complete heap boundaries / 57,950,208
32-bit words**, **1,985,536 independent component bytes**, **2,240 register
values**, **1,606 allocator events**, and **1,596 complete freed allocations /
42,914,688 bytes**. It includes the later interactive parser and `exit` entries,
the prompt call and the actual process outcome. None are initialized into the
source continuation or counted as matched before being executed.

The portable and packaged WebAssembly audit reports agree exactly. Both
report **336 failures**, comprising:

| Unfinished full-shutdown assertion | Failures |
| --- | ---: |
| Native register continuation at the six implemented boundaries | 168 |
| Later interactive-parser/exit boundaries | 56 |
| Remaining event count | 28 |
| Remaining freed-allocation count | 28 |
| Prompt/console continuation | 28 |
| Actual process exit | 28 |

The strict audit commands below intentionally exit nonzero while these
requirements remain. Passing integrity/regression unit tests do not convert
this full audit into a passing gate. No count, target owner, range, outcome or
tolerance is waived. All preceding first/second-driver, cache, model, console
and port checks still pass on the new captures. The prior port fixture also
retains zero differences after the shared close extraction.
The older 134 command histories retain identical complete reports: 130 main
histories have zero differences; the four extra histories still retain their
816 strict workspace/settings differences. These existing failures are not
removed or reclassified by the new EOF checkpoint.

Earlier first-driver descriptor position is now captured explicitly for stdin.
Interactive creation can leave `quit` in an existing buffer; keyword creation
can reach the REPL with no buffer and require a new 4096-byte allocation.
Neither path may substitute a later buffer or descriptor observation.

Next integration must carry the native register/FP state and earlier
loader/stdio bindings through script close, signal installation, prompt,
buffered/unbuffered stdin, QUIT dispatch, cache/log release and libc cleanup.
The existing whole-process phase, FCOS/logarithm and saved-FP gaps also remain
required work. This branch is not deployed and does not establish whole-program
equivalence.

`shunt_shutdown_original.json.gz`: 36,086,282 bytes, SHA-256
`903d9b5100ba3840e79d368161565a05af3c3484ab0385a01e4d01ccda212d0e`.
Binary/debug-library hashes, minimal launch environment, original scripts,
plain outcomes, all prior checkpoints and output files remain in the archive.
The fixture is excluded from the browser runtime archive.

Source package: `16628c7aa6146edf`, with all 193 runtime source files checked
against the working sources and no fixture files. Numerical WASM SHA-256 remains
`c7869e98f4c18b5414dc172d836e7144ab3ebc0de2de0d1f2eec1a4fe1709186`.

```sh
python tools/capture_shunt_shutdown_original.py --reference ~/github/asitic-re \
  --library-path /path/to/i386/libs --debug-directory /path/to/libc/debug
PYTHONPATH=src:tests python -m unittest test_shunt_shutdown_original -v
python tools/audit_shunt_shutdown_original.py --output /tmp/shunt-shutdown-cpu.json
python tools/build_site.py
node tools/check_shunt_shutdown_original.mjs /path/to/pyodide.mjs /tmp/shunt-shutdown-wasm.json
```
