# Branch node solve and first driver return

The development replay now continues all 28 selected branch driver histories
through the node solve, model report, and first driver return. The source uses
the same heap, `Memory`, cache results, CAP/LMAT arrays and console object that
were produced by the [earlier driver stages](SHUNT_DRIVER_HISTORY.md). There is
no node-entry snapshot reset or second allocation arena.

The fourteen requests include cold/warm wire, square and balun analyses,
repeated branches, explicit ground, coupled windings, both eddy paths and
unequal branches. Every unchanged request and original outcome is retained.
All 28 plain runs exit normally, and all observed node/driver returns report
success. Older faulting native cohorts and their strict gates remain required.

## Actual guest port stores

The earlier node component computed correct port values but retained them only
in a Python object. The original also writes four global complex variables,
which later commands can read from the shared program memory.

`NodeStorage.publish_ports()` now performs those stores after the six node
work arrays have been released and before the node-return boundary. The source
order is `y22`, `y11`, `y21`, `y12`, matching `node_equations.cpp` and the original
instructions at `0x805489d..0x80549fe`. The fixed ET_EXEC destination bindings
come from those instruction operands. Later captured port addresses do not
choose the source destinations.

Both the computed complex values and the actual guest-memory cells are checked
at node return and driver return. Changing a later port address cannot redirect
a store. Suppressing publication fails the memory check even when every computed
port and printed metric remains correct. Other unobserved global/stack/register
state is not claimed to match by these checks.

## Continuing the source computation

Node dimensions come from the source conductor groups, including secondary
branches, rather than the later observed node descriptor. The source allocates
pivots, LU storage and four vectors in native order, folds the live CAP matrix,
factors the network, solves both excitations and writes the final work arrays.
The original column-major/transpose behavior is preserved for asymmetric
admittance matrices.

The first release snapshot includes all final node work values. The source then
releases the six work arrays, publishes the ports, extracts and prints the Pi or
coupled model, and destroys the original CAP/LMAT arrays. The native first driver
return is the endpoint. Complete heap checks retain freed storage, logging
buffers, allocator headers and padding.

The console comparison is deferred while the supplied console object continues
through these later emitters. The final check requires every prefix and model
call, its text and all event positions. Altering either a prefix message or the
final model message must still fail; no console call is exempted.

## Independent native evidence

The new read-only capture extends every driver-parent history past the existing
node-entry stop. It observes every node/cleanup allocation/free, every released
array in full, all port values and the complete mapped heap at node release,
node return and first driver return. The added released-array observations have
no 16,384-byte cutoff: the largest is 18,496 bytes. The earlier numerical-array
observer keeps its separate documented bound.

Python and packaged Pyodide require exact values throughout:

| Added continuation observation | Checked |
| --- | ---: |
| Allocation/free events / allocation addresses | 392 / 168 |
| Complete released arrays | 224 / 162,336 bytes |
| Complete later heap boundaries | 84 |
| Later heap words | 21,800,960 |
| Port binary64 values at both returns | 448 |
| Actual global port-memory binary64 words at both returns | 448 |
| Console calls through the complete model report | 838 |
| Unknown heap / port bytes | 0 / 0 |

The same run also requires all preceding 94 output heap boundaries, 1,260 cache
tables, 338 builder frames, numerical buffers and via stores. Together the
driver/node continuation checks **178 complete output heaps / 45,574,144
32-bit words**, with no range or owner exclusion. The 28 driver-entry heaps
remain earlier inputs. This is not a complete address-space comparison.

Seven new tests verify provenance, original outcomes and complete captures;
cold/warm, eddy, coupled and unequal-branch continuations; identical source
memory and publication order; altered later ports/CAP/workspace/extent/owner
observations; deferred console assertions; missing global stores; a wrong RHS;
and a suppressed model report. Six earlier portable node tests pass with the
stronger guest-port checks. The required `shunt-node` Pages suite executes the
new tests and every complete branch continuation, alongside all older gates.

## Limits and reproduction

Earlier driver-entry heap/scene/strings, cache bindings/files, console ABI and
entry ESP are still explicit inputs. Complete startup, the whole caller stack
and FP state, outer command return, subsequent analyses and the remaining
hardware-math/phase/alias paths are unfinished. The six typed-API raw phase-word
failures remain required; this development branch is not deployed.

The archive `shunt_node_history_original.json.gz` is 15,738,418 bytes,
SHA-256 `a397c6ede8441115decec48bb37b798f993cda3723e0dc9a743c101c76228308`.
It retains the original command files, plain outcomes, minimal environment,
observer script, original/debug-library provenance and lossless heap/buffer
pages. No inferior instruction, numerical value, allocation result, register,
memory store, return or affinity is replaced. Reference fixtures are excluded
from the runtime source archive.

Source package: `09d468f5e231ed6f`; numerical WASM SHA-256 remains
`c7869e98f4c18b5414dc172d836e7144ab3ebc0de2de0d1f2eec1a4fe1709186`.

```sh
python tools/capture_shunt_node_history_original.py --reference ~/github/asitic-re \
  --library-path /path/to/i386/libs --debug-directory /path/to/libc/debug
PYTHONPATH=src:tests python -m unittest test_shunt_node_history_original -v
python tools/audit_shunt_node_history_original.py --output /tmp/shunt-node-cpu.json
python tools/build_site.py
node tools/check_shunt_node_history_original.mjs /path/to/pyodide.mjs /tmp/shunt-node-wasm.json
```
