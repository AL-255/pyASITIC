# Branch driver return to the next analysis entry

The development replay continues all fourteen unchanged branch scripts, cold
and warm, from their first driver return through direct-script parsing and
port-file setup to the next analysis entry. The same heap, `Memory`, console,
scene, strings and script FILE continue from the
[node/driver replay](SHUNT_NODE_HISTORY.md). No later snapshot initializes a
second execution arena. The endpoint is the next driver entry, before its
numerical solve.

All 28 plain native runs exit normally. The observer reaches 22 Pi2 and six
CALCTRANS entries. Explicit ground, repeated branches, unequal branches,
coupled windings and both eddy paths remain in the comparison. Older faulting
cohorts and their nonzero startup/FP/math/phase gates are still required.

## Ground argument behavior

`command_runtime.cpp` parses a type-8 argument by finding the scene shape,
storing its pointer and calling `reset_geometry_mesh_counts`. That helper in
`geometry.cpp` stores `-1` into width/thickness counts along the primary chain;
it does not traverse secondary branches. `GeometryStorage.reset_mesh_counts`
now performs these stores in the existing guest memory, and the continuing
command parser binds that callback.

`port_dispatch.cpp` takes an optional reference from argument eight of 2PORT
and 2PORTTRANS. The continuing Python dispatch previously always passed the
first winding as reference. It now forwards the parsed optional pointer,
preserving the native first-winding default when that argument is omitted.
The explicit-ground native request requires different device and reference
addresses at the next Pi2 entry.

The first whole WebAssembly comparison retained 870 differences across the
two explicit-ground histories; the other 26 already matched. After the source
fix, all 28 match. These scripts already reset the ground during their first
PI2, making the second reset idempotent. A separate test changes the incoming
counts before outer parsing: the real reset restores the native state, while
suppressing it causes complete-heap failures. Synthetic primary/secondary
records also prove the exact write extent and ordinary type-0 behavior.

## Independent evidence and strict checks

The read-only observer retains the first-driver input stack, script/stdin FILE
records, locale tables, port settings and timezone file as earlier inputs.
Every subsequent observation is a comparison target: allocations/frees,
released usable bytes, parser workspace, settings, complete mapped heaps,
next-driver arguments, console calls, calendar calls and generated files.
The timestamp derives from the source filename-copy stack pushes and the
earlier timezone file, as in the existing command continuation.

| Added transition observation | Checked |
| --- | ---: |
| Allocation/free events | 140 |
| Complete released buffers | 28 / 784 bytes |
| Parse/header boundaries | 56 |
| Parse/header workspace and settings words | 64,120 |
| Complete additional output heaps | 28 |
| Additional heap words | 7,239,680 |
| Final workspace and settings words | 32,060 |
| Generated port files | 28 / 39,384 bytes |
| Calendar calls / added console calls | 28 / 40 |
| Unknown bytes | 0 |

All preceding node/driver comparisons remain mandatory. Together the continuing
driver, node and command replay checks **206 complete output heaps /
52,813,824 32-bit words**, including freed storage, allocator headers and
padding. The 28 earlier driver-entry heaps are inputs. This is not a complete
address-space comparison.

The complete CPU and final packaged WebAssembly reports agree exactly across
all 28 cases and every counter above, with zero differences.

Seven tests cover every original job/outcome and parent digest, complete heap
capture, explicit/default/coupled references, identical source memory,
primary-only mesh reset, changed ground lookup, suppressed reset, and later
file/calendar/argument/workspace/heap mutations. Mutating later observations
must fail without changing the source memory or allocator state. The required
`shunt-command` Pages suite runs these tests and every full continuation in
packaged Python/WebAssembly, alongside all earlier gates. The CPU suite also
discovers the new tests without any exclusion.

The seven new tests pass on CPU and packaged WebAssembly. Fourteen earlier
CPU command/geometry tests and nine earlier browser command tests also pass.
The full older browser command audit retains all 134 cases: the 130 main
histories match, while the four extended histories retain 816 strict parser
workspace/settings differences in the cold rectangular fault case. All four
extended reports match the unmodified parent runtime exactly; this checkpoint
neither introduces nor waives those existing failures.

## Limits and reproduction

Earlier driver-entry scene/heap/strings, ABI, files, cache bindings and stack
remain explicit component inputs. Complete startup, the full caller/FP state,
the second numerical analysis, further commands/cleanup, the six typed-API raw
phase-word failures, FCOS/logarithm discrepancies and remaining trailing-via
aliases are unfinished. This development branch is not deployed and does not
establish whole-program parity.

`shunt_command_transition_original.json.gz` is 16,607,883 bytes, SHA-256
`ba68ca6de8fbe254d2766c0c89a52245ffab49e5c02ad3e7a82ba1254e94c1d2`.
It retains the original scripts, native outcomes, minimal environment,
observer, binary/debug-library provenance and lossless storage pages. No
inferior instruction, register, allocation result, memory store, return,
numerical value or affinity is replaced. Fixtures remain outside the runtime
source package.

Source package: `5cd78f39b371c8f4`; numerical WASM SHA-256 remains
`c7869e98f4c18b5414dc172d836e7144ab3ebc0de2de0d1f2eec1a4fe1709186`.

```sh
python tools/capture_shunt_command_transition_original.py --reference ~/github/asitic-re \
  --library-path /path/to/i386/libs --debug-directory /path/to/libc/debug
PYTHONPATH=src:tests python -m unittest test_shunt_command_transition_original -v
python tools/audit_shunt_command_transition_original.py --output /tmp/shunt-command-cpu.json
python tools/build_site.py
node tools/check_shunt_command_transition_original.mjs /path/to/pyodide.mjs /tmp/shunt-command-wasm.json
```
