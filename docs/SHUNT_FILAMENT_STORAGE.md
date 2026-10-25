# Filament tables and cleanup for secondary groups

`filament_storage.py` now generates the original group/physical-segment
layout, pointer tables and filament counts from source geometry. The shared
`StorageHistory` uses that writer. `combined_network_storage` sizes its
arrays for physical records, retains group-sized arrays where the original
does, and releases every child before its parent. Geometry addresses are
derived from the earlier source replay and live group links.

The reference paths are `filament_setup.cpp`, `solver.cpp`, `geometry.cpp`,
`contacts.cpp` and `eddy.cpp` under `recomp_cpp/src/`.

## Correct native dimensions and ordering

The original keeps separate counts for electrical conductor groups and
physical indexed segments. `extra_segments` has one integer per conductor
group. `segments`, `width_counts` and `thickness_counts` have one entry for
each primary/secondary record in a conductor group. The index order is parent
then its group chain. Via indices retain their group positions, including
trailing positions. Children attached to a via primary are omitted from the
conductor index but still released during geometry cleanup.

The source layout reads actual secondary pointers from the same earlier
guest memory. Typed geometry without that memory cannot invent physical
branch addresses. Cleanup identities follow the source chain order rather
than allocation order; native prepend operations reverse that order.

The lifetime plan also retains the selected eddy inverse branches. Folded
eddy correction needs both small-matrix inverse wrappers; packed square
correction additionally allocates its source-derived real matrix. Successful
array allocation/inverse paths are covered. Allocation failures and arbitrary
corrupted-list cleanup remain separate work.

## Native comparisons

The new observer retains every fourteen-session/cold-warm parent from
[secondary geometry storage](SHUNT_STORAGE.md), giving 28 original runs.
It records the actual filament context at the first impedance fill, complete
pointer/count arrays, geometry, prepared/numbered contact records and every
array release after CAP scope and before first node whose original request is at most 16,384 bytes.
Every plain run and native outcome remains present. Later bytes and pointers
are assertions only.

Python and packaged Pyodide both require exact native values:

| Check | Exact coverage |
| --- | ---: |
| Native allocation/free events after CAP scope | 1,950 |
| Allocation addresses | 542 |
| Filament arrays at impedance fill | 122 / 4,736 bytes |
| Same arrays immediately before release | 122 / 4,736 bytes |
| Live geometry at impedance fill | 92,144 bytes |
| Geometry records released in native order | 362 |
| Final logical allocator states | 28 |

The earlier source geometry and CAP preparation use one continuing allocator.
Full native lifetimes include coarse/refined cells, repeated branches,
explicit reference, coupled models, eddy correction and a longer child that
controls its parent's subdivision. No final context dimension chooses an
allocation size, pointer or cleanup owner. Changing a later expected table
word or free pointer produces a required failure without changing the source
tables or allocator execution.

This table/lifetime comparison checks the logical allocator state and chunk
metadata. The separate numerical replay below additionally checks all captured
bounded released arrays and complete first-node matrices. Neither comparison
claims complete final heap-byte equality.

The later [continuous branch driver comparison](SHUNT_DRIVER_HISTORY.md)
connects earlier cache/file/FFT stores and derives the incoming contact word
from driver ESP. It requires all 94 complete contacts/CAP/via/node output heaps
across the same 28 cases, including the eddy diagnostic buffers. The numerical
array checks in this document remain independently required.

## Contact-group header fix

The new record comparison exposed a separate bug in the secondary contact
observer path. Native `prepare_potential_contact_group(..., reuse=true)`
overwrites the shared group header for each child. The final header therefore
contains the last child's coordinates, cell counts and metal. The old observer
reported one header per physical record, although the returned contacts were
already folded per electrical group. `contact_storage.records` consequently
paired later groups with the wrong metadata.

The source now reports the final reused header once per group, while keeping
the native combined contact order. All **1,064** prepared/numbered group and
contact observations match their **61,584 defined bytes**, including explicit
ground and coupled names. The independent component check also requires
**28,096** uninitialized padding/index bytes to stay unknown until the source
defines them. Initial contact index words are overwritten by numbering;
unwritten name padding is preserved by a continuing memory caller. No unknown
value is silently replaced with zero. The numerical contact geometry is shared
with the production CAP solver.

## Actual branch storage hooks through node entry

All 28 branch cases now execute the actual `StorageHistory` hooks through
first node entry. CAP and LMAT buffers and inverse workspaces come from the
source numerical algorithms, and contacts come from the production record
generator. The initial driver heap and source-generated geometry continue
through preparation, numerical arrays, branch tables and geometry cleanup
without a later byte reset.

The history preserves the native order of small inverses, eddy correction and
via stores. `prepare_impedance(include_storage=True)` retains the pre-eddy
impedance alongside the corrected result. Segment-folded correction follows
the first small inverse's cleanup. Packed square correction writes its actual
real matrix in column-major order before release. Eddy-only runs still execute
the final small inverse; the later full-matrix cleanup must preserve that
result. Via stamps execute from the source records, independently of native
observer events, into the same shared memory before the final inverse.

The numerical replay matches **1,950 allocation/free events**, all **476
captured released arrays / 193,592 bytes**, **12,576 CAP/inductive first-node
binary64 words**, all **14 via stores / 56 before-and-after words**, and final
logical allocator state. This includes coarse/refined wire and square cases,
repeated branches, explicit ground, coupled wire/balun windings, eddy folding,
packed square eddy correction and unequal branches. Released-array coverage is
bounded to the capture's 16,384-byte maximum per allocation; larger released
arrays are not asserted by this observer. Both first-node matrices are checked
in full. No final native output initializes or repairs source memory.

Ten tests pass in Python and packaged Pyodide. Mutating a later numerical
workspace or via result produces the required failure without changing source
buffers, addresses or allocator execution. Omitting segment-folded eddy
correction fails the original first-node comparison. Memory attachment also
defers filament reads until the caller requests the plan, preserving the
earlier memory-only continuation contract without reseeding any bytes.
The public mesh preflight independently matches every native branch filament
and conductor-group count across the fourteen distinct requests.
Thirteen existing CPU contact/geometry/storage tests pass too. The prior complete
130-case browser storage-history audit retains zero differences across
12,877 events and all checked numerical/cache/node words, including its
native fault and predicted cache errors. The shunt webpage regression also
passes all 124 geometry histories, GDS/project flows and twelve displayed/
downloaded models; its six raw phase-word assertions remain required failures.
The required `shunt-filaments` Pages job executes the complete new report and mutation
tests. The earlier phase, JOIN/UNJOIN, heap and continuing-process gates are
unchanged; the six typed-API raw phase-word failures still prevent deployment.

The archive `shunt_filament_storage_original.json.gz` is 790,475 bytes,
SHA-256 `afda63afc5d3e7bebd0f0ad5e654207e9a553fab7e418078bee43d8f68a8268a`.
It retains scripts/plain outcomes, observer commands, initial whole heap,
parent hashes, minimal environments and original binary/library digests.
It is not included in the runtime package. No native instruction, numerical
input, register, memory, allocation, affinity or returned result is replaced.

Source package: `ed1c96df0b305682`; numerical WASM remains SHA-256
`c7869e98f4c18b5414dc172d836e7144ab3ebc0de2de0d1f2eec1a4fe1709186`.

```sh
python tools/capture_shunt_filament_storage_original.py --reference ~/github/asitic-re \
  --library-path /path/to/i386/libs --debug-directory /path/to/libc/debug
PYTHONPATH=src:tests python -m unittest test_shunt_filament_storage_original -v
python tools/audit_shunt_filament_storage_original.py --output /tmp/filament-cpu.json
python tools/build_site.py
node tools/check_shunt_filament_storage_original.mjs /path/to/pyodide.mjs /tmp/filament-wasm.json
```
