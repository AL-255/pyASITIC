# Continuous branch driver memory

The development replay now carries one source heap and memory from combined
driver entry through secondary geometry cloning/COPY/JOIN, contact preparation,
cache file IO and FFT generation, CAP, LMAT, eddy correction, via stores and
first node entry for all 28 selected branch histories. It does not reset memory
at contacts, cache completion, CAP, LMAT or via entry.

These are the fourteen independently specified requests from
[branch filament storage](SHUNT_FILAMENT_STORAGE.md), each with cold and warm
native cache files. Every original request and plain outcome remains present.
The capture reads complete mapped heap regions at all five available boundary
kinds, together with cache files/bindings, bounded released buffers, console
calls, contact records, filament tables and independently observed builder
frames. Nothing in the original process is replaced or patched.

## Contact index provenance

The earlier independent contact component correctly kept the incoming temporary
index unknown. Complete CAP-entry heap checks exposed those unknown words even
though later contact numbering made the numerical results exact.

In the original i386 instructions, the apparent uninitialized word has a source:

| Operation | Frame / store |
| --- | --- |
| Prepare contacts, `0x8053580` | Establish frame pointer `P` |
| Call prepare group, `0x80536c8`, with 16 argument bytes | Its prologue saves `P` at `P-40` |
| Return, then call builder, `0x8053a1c`, with 8 argument bytes | Builder frame becomes `P-32` |
| Builder temporary at frame `-60`, copied by `0x80561e0` | Its `+52` index aliases `P-40`, containing `P` |

The builder leaves that temporary word unwritten before copying all 60 bytes
into each contact. The source `contact_stack.py` derives `P` from the earlier
driver-entry ESP and the actual Pi2/CALCTRANS caller prologues and argument
cleanup. CALCTRANS explicitly cleans its two discretizer arguments at
`0x80512a8`. No later observed frame address or contact word supplies the value.
All **338 original builder entries / 1,352 stack words** and all prepared
contact index words match. Older components without the earlier ESP still keep
the word unknown; their requirements are unchanged.

Changing the earlier ESP changes the actual CAP-entry contact words. Numbering
later overwrites them, preserving the numerical node matrices. Changing only a
later expected builder or heap word causes a strict failure without changing
source memory, addresses or allocation behavior.

## Native integration diagnostics and progress

The complete heap comparison exposed four eddy runs whose numerical values
already matched but whose stdout buffers differed. `green_integration.cpp`
prints QUADPACK diagnostics through direct `printf`, independently of the
program's console logger. They neither add console-emitter calls nor write
the log/recording streams. The next progress dot flushes stdout.

`green_diagnostics.py` ports those source literals and dispatches DQAGIE/DQAWFE
statuses and per-cycle errors in their original order. Binary64 `%lg` fields
use the existing pinned glibc digit algorithm. Message text and format values
come from source integration inputs/results, never captured text.

When storage history is requested, impedance preparation retains each source
Green integration result and its frequency/separation/height/width arguments.
The individual Green numerical kernels remain available in Pyodide. Ordinary
web solves retain the existing batched compiled eddy path; this observation
path does not change their result or add a diagnostic replay to normal requests.

Segment-folded diagnostics precede the dot after the first small inverse.
Packed square diagnostics precede the dot after its real workspace is freed.
Eddy-only analyses also suppress the no-correction cleanup dot. The original
console call positions, direct-output buffer bytes and numerical arrays now
match together. Suppressing the source Green output must fail full-heap parity.

The source CAP headline is emitted before the contacts-entry heap assertion,
matching the native call order. The new comparison observes contacts and CAP
entry in addition to the existing via/node boundaries; it does not discard
unknown words or restrict comparisons to allocated owners.

## Exact comparison coverage

Python and packaged Pyodide independently require zero differences:

| Observation | Checked |
| --- | ---: |
| Source geometry allocation/free events / allocation addresses | 918 / 654 |
| Defined geometry / string bytes | 133,240 / 18,032 |
| Pre-CAP allocation/free events / allocation addresses | 1,148 / 840 |
| Released pre-CAP buffers | 308 / 636,616 bytes |
| Complete cache tables | 1,260 / 42,277,440 bytes |
| Numerical allocation/free events / allocation addresses | 1,950 / 542 |
| Captured released numerical arrays | 476 / 193,592 bytes |
| Via stores / unknown targets | 14 / 0 |
| CAP / inductive first-node binary64 words | 6,288 / 6,288 |
| Original console calls and exact positions | 754 |
| Complete contacts/CAP-entry heaps | 56 / 14,409,728 32-bit words |
| Complete via/node-entry heaps | 38 / 9,363,456 32-bit words |
| Unknown bytes in checked heaps | 0 |

All **94 complete output heap boundaries / 23,773,184 words** are required;
the 28 driver-entry heaps are earlier inputs. This includes padding, freed
storage, allocator metadata and logging buffers. No word or owner is exempt.
The 16,384-byte bound applies only to the separate pre-free array observer;
each mapped `[heap]` boundary is compared in full. Mmap storage outside the
heap retains the existing cache/matrix coverage and is not claimed as a
complete address-space comparison.

Seven tests check every capture/provenance input, complete small cold/warm and
eddy histories, all builder frames, changed earlier ESP, omitted direct printf
and altered later heap/frame words. The required `shunt-driver` Pages suite
runs these and the complete 28-case report. All earlier required gates remain.

## Limits and reproduction

Driver-entry heap/scene/legacy strings, preexisting cache bindings/files,
console controls/ABI and entry ESP remain earlier component inputs. The replay
does not yet derive complete process startup, the whole caller stack/FP state,
outer command cleanup or subsequent analyses on one process heap. The typed
webpage API's six raw phase-word differences, FCOS/logarithm discrepancies,
trailing-via aliases and continuing-process gates remain required. This branch
is not deployed and this result is not whole-program parity.

The later [node/driver continuation](SHUNT_NODE_HISTORY.md) carries this same
source state through node work arrays, global port stores, model reporting,
matrix destruction and first driver return for every one of these 28 cases.
It adds 84 complete output heaps without replacing any earlier comparison.
The [following command continuation](SHUNT_COMMAND_TRANSITION.md) adds another
28 full heaps through direct-script parsing and next analysis entry. Complete
startup/FP state and the following numerical solve remain unfinished.

The archive `shunt_driver_history_original.json.gz` is 14,207,922 bytes,
SHA-256 `6f2be97328dadcfefed4466c09c6137629e67e1966267b89b35ae9f4d21266b4`.
It retains every plain outcome, original/debug-library digest, minimal launch
environment, original command and full capture script. Earlier no-console and
no-stack exploratory captures remain local audit evidence; no run was selected
out of the final cohort. Reference observations are excluded from the runtime.

Source package: `09cdc450ddf68e1f`; numerical WASM SHA-256 remains
`c7869e98f4c18b5414dc172d836e7144ab3ebc0de2de0d1f2eec1a4fe1709186`.

```sh
python tools/capture_shunt_driver_history_original.py --reference ~/github/asitic-re \
  --library-path /path/to/i386/libs --debug-directory /path/to/libc/debug
PYTHONPATH=src:tests python -m unittest test_shunt_driver_history_original -v
python tools/audit_shunt_driver_history_original.py --output /tmp/shunt-driver-cpu.json
python tools/build_site.py
node tools/check_shunt_driver_history_original.mjs /path/to/pyodide.mjs /tmp/shunt-driver-wasm.json
```
