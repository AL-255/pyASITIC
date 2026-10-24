# Storage lifetimes toward native trailing-via behavior

The subsequent [contact/cache prelude port](CAP_PRELUDE.md) now begins before
contact construction and carries the predicted heap through the numerical
stages. Its separate 130-run comparison checks 20,609 events without resetting
the heap at this document's later CAP boundary. Earlier observations below
remain unchanged.

`allocation_plan.py` now ports the allocation/free sequence from folded CAP
through the first combined-network node solve. It **does not place objects at
physical heap addresses**, permit trailing-via simulations, or resolve the
failing JOIN/UNJOIN models. This is an intermediate part of reproducing the
native memory interaction described in [UNJOIN_PORTING.md](UNJOIN_PORTING.md).
The next-stage [arena placement port](HEAP_PLACEMENT.md) now matches 110
pre-via boundaries from independently captured initial allocator snapshots.
Its strict full audit still fails, and it is not integrated into simulations.

## Source port

The plan follows the reference `potential_solver.cpp`, `solver.cpp`,
`filament_setup.cpp`, and geometry cleanup in `combined_network.cpp` and
`later_analysis.cpp`. It describes successful inverse branches, disabled eddy
correction, and independent segment chains. It covers:

- The full CAP matrix, general-inverse pivots/workspace, reduced/folded CAP
  matrices and output allocation.
- Contact/group deletion and release of temporary CAP matrices.
- Filament context arrays, the full impedance matrix, symmetric-inverse
  workspace, zero-filled temporary and reduced output allocation.
- Via scratch storage, the required reinversion, context cleanup and cloned
  geometry deletion before node solving.

Inputs are contact counts in native group order, conductor count, filament
count, via count and cloned segment count. The calculation contains no native
addresses, geometry-specific cases or returned numerical fixture values. A
physical address allocator must also model allocations preceding this plan;
the current geometry-only arena is not a complete process allocator.

The native trace comparison checks requested byte counts, scalar versus array
allocation interfaces, exact free-object identities, scalar chunk sizes and
the two retained output owners. Reusing an address is tracked as a new object
lifetime, rather than conflating its previous and current owners.

## Independent inputs and observed outcomes

The capture includes 17 square winding sizes from one to 64 conductors, each
with coarse, refined conductor-width and refined contact-width meshes. It also
retains twelve exploratory pilot jobs and both previously failing split-balun
jobs: 65 selected input configurations, each observed with cold and warm disk
caches. Every selected complete run and fault is retained.

The corrected fixture contains **130 observations and 12,877 allocation/free
events**. The source plan matches every observed request and free identity.
There are 129 completed node-input observations and one matching fault prefix:
the cold `square/64/contacts` run faults at the trailing-via load from an
unmapped address. Its missing result is recorded as missing, not replaced with
a zero or a successful return.

The complete unobserved runs in this capture have 125 normal exits, three
SIGABRT exits and two SIGSEGV exits. These are recorded executions, not a claim
that undefined native heap behavior has deterministic outcomes on every host
or invocation. Reaching the first node boundary does not prove that the
subsequent repeated analysis or process cleanup completes.

For each cache mode, 25 trailing writes target the live CAP output and 40 fall
outside that output. A fixed correction to CAP row `n-1`, column zero would
therefore be wrong for most selected inputs. For example, in this capture:

| Input | Trailing target |
| --- | --- |
| One conductor, coarse mesh | CAP |
| One conductor, refined filament mesh | Outside CAP |
| Eight conductors, coarse mesh | Outside CAP |
| Eight conductors, refined filament mesh | CAP |
| Twenty-four conductors, coarse mesh | CAP |
| Twenty-four conductors, refined contact mesh | Outside CAP |

Cold and warm runs happen to agree on CAP-target classification for these
65 configurations, while allocation placement and complete-run outcomes can
differ. For five-conductor refined-contact input, the CAP-minus-inductance
buffer offset is 4,320 bytes cold and 4,416 bytes warm; both targets remain
outside CAP. This does not establish cache independence for other histories.

Current Python geometry, contact generation and filament counts independently
reproduce all dimensions used by the captured plans. Some native filament
systems exceed the browser's 256-filament solver limit; counting and the
storage plan still preserve those inputs. These tests do not raise or bypass
the browser solver limit.

## Cache-state correction and provenance

The first broad experiment executed a cold plain run followed by GDB in the
same directory. The first run created a native disk cache, so its observed run
was warm. That experiment is retained intact in
`trailing_via_heap_mixed_cache_original.json.gz`. It must not be treated as a
same-initial-state comparison between GDB and plain execution.

The corrected harness tests cold and warm states explicitly. Before each GDB
run it restores byte-identical input files and cache files in the same working
directory used by its corresponding plain run. Warm cache bytes come from the
original program's cold run. Initial-file, initial-cache and post-plain-cache
manifests record file sizes and SHA-256 digests. Both processes use the same
TERM and INPUTRC settings. Tests verify cache-generation diagnostics and the
manifests for every pair.

Read-only observers capture array/scalar allocation interfaces, CAP descriptors,
via inputs, target words at entry and at the actual load/store instructions,
and the first node inputs. No numerical instruction, allocator callback or
returned word is replaced. Debugger runs stop at node entry or a native fault;
complete unobserved runs are recorded separately.

## Reproduce

```sh
python tools/capture_trailing_via_heap_original.py --reference /path/to/asitic-re --library-path /path/to/native-libraries
python tools/audit_trailing_via_heap.py --output /tmp/storage-lifetime-differences.json
PYTHONPATH=src:tests python -m unittest test_allocation_plan_original -v
python tools/build_site.py
node tools/check_allocation_plan_original.mjs /path/to/pyodide.mjs
```

The three fixture/plan tests pass in CPython and packaged Pyodide with the
compiled kernels installed. A separate mandatory storage CI job runs them.
The JOIN and UNJOIN numerical checks remain mandatory and failing. Storage
order parity is not physical heap parity or complete simulation parity.
