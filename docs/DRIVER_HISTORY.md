# Continuous memory from driver entry to node input

The development replay now carries the **same heap and guest memory** from
driver entry through geometry cloning/JOIN, contact preparation, cache IO,
CAP, LMAT, via stores and the first node-equation input. It does not replace
memory with a CAP-entry snapshot. All 134 selected native histories remain
required, including the four wire histories that skip the via stage.

This is still a component of the original-program port. Driver-entry heap
state, scene/legacy string storage, ABI details, preexisting cache bindings
and external files remain explicit earlier inputs. Process startup is not
derived, production trailing-via guards remain enabled, and this development
branch is not deployable while strict parity checks fail.

## Source memory and ownership

`StorageHistory` accepts an existing memory object only when it is already
bound to the same heap/cache key. It rejects replacement initial regions,
another memory object or another key. Continuing the constructor performs
no memory stores: it neither reinitializes allocator controls nor rewrites
prepared contacts or geometry. The earlier geometry producer exports the
actual cloned descriptor/segment addresses used for later cleanup. Later
observed via owners and words are comparisons, not address inputs.

The CAP producer runs after allocation and zeroing of its full matrix. Its
table provider reads the actual cache pointers and shared table bytes.
`ComplexArray` indexes with native signed pointer arithmetic; its iteration
extent is a transport size, not a bound that clips native reads. This matters
for rectangular grids, whose contact accesses can read beyond declared XY
allocations into neighboring objects. Padded isolated arrays produced a
different CAP result in both 16×8 wire histories. Live shared reads reproduce
their native results; an isolated-table negative control must fail.

Contact matrix stores follow native row order through the shared view.
Batching is used only when cache/pointer storage is disjoint from the output;
rectangular reads use the literal path. The disjoint transport copies raw
binary64 bytes instead of performing a guest-memory lookup per complex value.
The ordinary production solver path remains unchanged.

Before cache IO/generation, CAP stores its calculated layer coefficients at
the destination observed independently at driver entry. The original loads
that pointer from `0x80d8ac8` and stores four words per coefficient in
`0x8052e61..0x8052e75`. The values use the existing retained-precision
coefficient algorithm, never later heap bytes.

The no-via, eddy-disabled admittance branch reduces directly to Y and skips
the two small symmetric inverse wrappers. The full filament matrix's lower
triangle remains constructor zero: native impedance assembly writes only
the upper triangle and its first inverse does not mirror. The older memory
producer incorrectly copied the Python symmetric input into that lower
triangle. Complete freed-matrix observations exposed that error; the source
store now leaves zeros there.

## New independent native observations

`capture_driver_history_original.py` adds read-only observations to the
earlier cache/geometry observer. At the recorded driver-entry, contacts,
CAP-matrix, via-entry and node-entry boundaries it reads the
**complete mapped `[heap]` regions** and the current tcache key. It also reads
every numerical array immediately before original delete[] when the original
allocation request is at most 16,384 bytes, retaining the existing workspace
observer's explicit bound. Larger mmap-backed numerical arrays are not fully
observed by that bounded delete[] check; mapped cache tables have their
separate complete input/output observations.

There are 649 boundary observations and 2,735 bounded pre-free numerical
arrays in the 130 main histories, plus 16 boundaries and 56 arrays in the
four added histories. Complete heap/file pages are losslessly deduplicated
as each case finishes. No byte range is removed from a captured heap, and no
inferior instruction, function return, allocation result or store is changed.
The plain process and observed process start with byte-identical files.
All outcomes are retained: the main capture has 123 normal exits, six SIGABRT
and one SIGSEGV; the additional capture has three normal exits and one SIGABRT.

Full capture SHA-256 values:

- Main: `0fe5f912ea7fa76d155207f77b488f1ac652f42abf79ee3e82c334ce0d251495`
- Additional: `941670d80476e97ef5e7214b39b9b9244112520bda4ae2a0863a739831eca0a7`

Every projected initial/final heap, earlier input file, numerical workspace,
cache binding and boundary heap reconstructs losslessly. Reference fixtures
are excluded from the runtime and downloadable source archives.

## Strict checks and remaining work

The new required `driverhist` suite runs all 134 histories and the portable
provenance/continuation/negative-control tests in packaged WebAssembly. It
compares every captured bounded pre-free numerical array and complete mapped
heap at each via/node boundary, in addition to cache tables, matrix outputs,
allocation identities, allocator state and raw tcache words. Unknown bytes
remain failures. Changing later via owners, keys or words does not repair the
source state; continuing a memory object must perform no seed stores.

The full-heap comparison is deliberately still strict and nonzero. Progress
on numerical outputs and workspace storage does not establish byte parity
for unrelated logging buffers, allocator metadata or later cleanup. No range
is excluded or marked acceptable to make the gate green. The older complete
numerical-history comparison still passes, and every previous gate—including
the older incomplete-context libio failure—remains required.

Final packaged results across all 134 histories:

| Observation | Checked | Differences |
| --- | ---: | ---: |
| Complete cache tables | 6,030 / 535,324,320 bytes | 0 |
| Pre-CAP freed buffers | 1,474 / 4,699,508 bytes | 0 |
| Bounded numerical pre-free arrays | 2,791 / 1,816,160 bytes | 0 |
| Numerical allocation/free events | 13,013 | 0 |
| Via stores / native mapping faults | 131 / 1 | 0 |
| CAP / inductance binary64 components at node input | 118,956 / 118,956 | 0 |
| Complete later heaps | 263 boundaries / 19,456,000 32-bit words | 6,461 words |

There are no unknown heap bytes or unknown via targets. All observed raw
tcache words and pre-via matrix words also match. The 130-case main audit
now returns 6,363 heap-word differences; the four extra cases return 98.
[Native allocator pointer stores](ALLOCATOR_STORES.md) resolve all previously
differing physical headers, including unused `prev_size` fields, without
refreshing them from observations. The remaining words are all in the two
traced stdout/log buffers. Both strict commands still exit nonzero; these
discrepancies are not accepted outputs.

The later [console-storage experiment](CONSOLE_STORAGE.md) independently
recaptures every one of these 134 histories with earlier stream bindings and
separate native console-call observations. Source-generated console stores
then resolve every full-heap difference in that stronger experiment, with no
buffer exclusions or later-byte refreshes. These older fixtures and their
unaugmented required gate are retained, including all missing-context failures
and the distinct plain-process outcomes documented there.

```sh
PYTHONPATH=src python tools/capture_driver_history_original.py --debug-directory /tmp/debug/usr/lib/debug --reference /path/to/asitic-re --library-path /path/to/native-libraries --full-output /tmp/driver-history-full.json.gz
PYTHONPATH=src python tools/capture_driver_history_extended_original.py --debug-directory /tmp/debug/usr/lib/debug --reference /path/to/asitic-re --library-path /path/to/native-libraries --full-output /tmp/driver-history-extra-full.json.gz
PYTHONPATH=src:tests python -m unittest test_driver_history_original -v
python tools/build_site.py
node tools/check_driver_history_original.mjs /path/to/pyodide.mjs /tmp/driver-audit.json /tmp/driver-extra-audit.json
```

Remaining work includes the stores identified by the strict heap comparison,
source process/scene/cache startup, all other analysis/eddy branches and
secondary geometry groups, larger numerical-buffer observations, complete
command cleanup after node input and the known logarithm/cosine and
JOIN/UNJOIN arithmetic discrepancies. These are not whole-program parity
results and do not authorize deployment.
