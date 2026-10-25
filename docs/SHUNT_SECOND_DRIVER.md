# Consecutive branch analyses on one source heap

All 28 selected branch histories now continue beyond
[port-file setup](SHUNT_COMMAND_TRANSITION.md), through the second complete
Pi2/CALCTRANS driver, node solve and return. The first numerical solve,
intervening parser and second solve share the same source `Heap`, `Memory`,
console, scene/string storage and cache tables. Every unchanged script and
original outcome remains in the comparison. All 28 original plain executions
exit normally; both observed driver returns report success.

## Actual state reuse

The second commands request the same frequency as the first successful solve.
`potential_cache.cpp::load_potential_cache` returns immediately when the
enabled, clean cache already has that frequency. The source continuation uses
the existing table pointers and contents, with no cache-file open, FFT-table
regeneration or second-entry memory initialization. Its 532 pre-CAP allocations
are the original contact groups and contacts. Prepared records and dielectric
coefficients still receive the normal CAP stores on this memory-cache path.

The first source CAP completion supplies the current cache frequency and
external-file state. Cold-run file bytes come from the source writer stream at
that point, before subsequent numerical writes. Warm files remain their
earlier explicit external inputs. At second entry, all cache-table contents and
file sizes/digests are assertions. Every cache table is checked again at second
CAP scope. A test changes a live source table after the first solve and requires
the second capacitance matrix to change; regenerating fresh tables would fail
that test.

The continuing geometry replay clones/copies/joins the existing guest scene
and uses the live legacy string pool and allocator. It does not construct a
new heap from the second observed driver snapshot. The earlier typed geometry
request, technology, mesh and ABI remain component inputs to numerical
preparation; this is not a complete command-language/startup implementation.
The current continuation explicitly rejects a changed sweep frequency, whose
cache-file selection/update path still needs integration.

## Caller frames and retained flag bytes

Contact temporary indices depend on the driver's entry ESP. The second entry
comes from source port-call prologues, rather than the later native stack
observation. `NativePortStack.driver_entry` follows dispatcher `0x805bd40`,
ground export `0x8087770` / wrapper `0x8052b60`, or transformer export
`0x8087ad0`. It accounts for the ground path's pending `fflush` argument,
alignment, saved registers and actual argument widths. Existing contact-frame
arithmetic then supplies all 338 builder temporary indices.

The first full browser comparison matched every numerical/heap/console target
but retained one argument-byte failure in each of the 22 Pi2 histories. The
native short flag push leaves two higher stack bytes untouched. Three separate
read-only hardware-watch histories identify the earlier writer: pinned i386
glibc `fflush` calls virtual `_IO_SYNC` at libc offset `0x75bcf`, leaving return
address `libc_base + 0x75bd2` in that slot. The wrapper's `PUSHW 0` changes only
its low half.

The source now derives that slot from the export and libc prologues, stores the
actual CALL return address using the earlier libc base, and performs the short
push. There is no captured-padding lookup. Synthetic cases vary the libc base,
including address wraparound. Changing the source binding must fail the later
argument-byte comparison while preserving the numerical results.

The second Pi2 call suppresses model printing; CALCTRANS still prints its
narrowband report. The source honors those native call paths while retaining
one console object and all prior output history.

## Exact comparison scope

The new read-only observer continues the same inferior after the first driver
and outer script transition. A separate debugger observer namespace keeps the
two histories distinct; it neither restarts nor resets the inferior. Every
second-entry snapshot is a later assertion target.

| Second solve observation | Checked |
| --- | ---: |
| Geometry events / allocation addresses | 918 / 654 |
| Geometry / string bytes | 133,240 / 18,032 |
| Contact-prelude allocations | 532 |
| Reused cache-table observations | 2,520 / 84,554,880 bytes |
| Cache files after first source completion | 28 / 42,313,168 bytes |
| Numerical events / allocations | 1,950 / 542 |
| Released numerical work arrays | 476 / 193,592 bytes |
| CAP / inductive node-input binary64 words | 6,288 / 6,288 |
| Via stores | 14 |
| Node/cleanup events / allocations | 392 / 168 |
| Complete released node/cleanup arrays | 224 / 162,336 bytes |
| Computed / guest-global port binary64 words | 448 / 448 |
| Second console calls | 304 |
| Unknown early-heap / numerical-heap / node-heap / port bytes | 0 / 0 / 0 / 0 |

Second-entry/contact/scope checks cover 84 complete heaps / 21,719,040 words;
numerical boundaries add 38 / 9,428,992; node/release/return checks add 84 /
21,870,592. This is **206 second-stage heap observations / 53,018,624 words**.
The second-entry observations repeat the preceding transition's endpoint.
Counting that program boundary once, the full two-solve replay checks **384
distinct complete output-heap boundaries / 98,592,768 32-bit words**. All first
driver/command checks remain required. The original 28 driver-entry heaps are
earlier inputs; this is not a whole-address-space comparison.

The complete portable CPU and final packaged WebAssembly reports agree exactly
for all 28 two-solve histories and every coverage counter, with zero differences.

Seven CPU/browser tests preserve provenance and all original outcomes; exact
cold/warm, ground and coupled continuations; identical memory in both node
solves; changed later entry/cache/file/heap/port/console observations; actual
source-table reuse; hardware-watch and variable-base stack provenance; and
failure on a wrong earlier libc binding. Changed later assertions cannot
repair the source heap, memory or allocation state. The required `shunt-second`
Pages suite runs these tests and every complete two-solve history. All older
strict gates remain required.

The seven new tests pass on CPU and packaged WebAssembly. All 28 earlier CPU
command/node/geometry tests pass, and the previous complete 28-case branch
command browser report is unchanged exactly. The older 134-case browser gate
also reproduces its parent report exactly: 130 main histories match, while the
four extended histories retain 816 strict differences in the cold rectangular
fault case. No older failing case or word is waived.

The [port-output continuation](SHUNT_PORT_TAIL.md) now carries these 28 source
histories through the following S record, fclose and export return on the same
stream/memory/heap. It adds 168 full output-heap boundaries and compares the
complete generated files. The subsequent EOF/quit path remains unfinished.

## Remaining work and reproduction

Earlier startup/scene/heap/ABI/stack and typed geometry inputs remain explicit.
Full startup, caller/FP state, changed-frequency cache paths, other port formats,
later commands, six typed-API raw phase failures,
FCOS/logarithm discrepancies and remaining trailing-via aliases are unfinished.
Other static globals and unobserved register/stack state are not established
by these heap checks. This development branch is not deployed and does not
establish whole-program parity.

`shunt_second_driver_original.json.gz`: 28,423,243 bytes, SHA-256
`014bc2a27f72688049630159e3491d97c0f4a76403981dff12e1e4ca6c7c089d`.
`port_driver_writers_original.json`: 106,347 bytes, SHA-256
`4d034d54b4a11145b4c003c8fc288ea160601beff7e407a0bc99239ebfdfd675`.
The capture retains scripts, plain outcomes, minimal environments,
binary/debug-library provenance, complete heap pages and released arrays.
No inferior instruction, register, memory store, numerical value, allocation
result, return or affinity is replaced. Fixtures remain outside the runtime
source archive.

Source package: `5ec64a066f365270`; numerical WASM SHA-256 remains
`c7869e98f4c18b5414dc172d836e7144ab3ebc0de2de0d1f2eec1a4fe1709186`.

```sh
python tools/capture_shunt_second_driver_original.py --reference ~/github/asitic-re \
  --library-path /path/to/i386/libs --debug-directory /path/to/libc/debug
python tools/capture_port_driver_writers_original.py --reference ~/github/asitic-re \
  --library-path /path/to/i386/libs --debug-directory /path/to/libc/debug
PYTHONPATH=src:tests python -m unittest test_shunt_second_driver_original -v
python tools/audit_shunt_second_driver_original.py --output /tmp/shunt-second-cpu.json
python tools/build_site.py
node tools/check_shunt_second_driver_original.mjs /path/to/pyodide.mjs /tmp/shunt-second-wasm.json
```
