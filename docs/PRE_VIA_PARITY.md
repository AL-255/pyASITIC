# Regenerated inductive matrices before via stamping

The shared-memory experiment now regenerates **both** matrix inputs from the
Python implementation. The native pre-via inductive matrix is no longer a
calculation input when `--ported-ind` is selected. This extends the earlier
[shared-memory component comparison](SHARED_MEMORY.md), whose captured-state
and production-integration limits still apply.
The later [continuous history](STORAGE_HISTORY.md) combines the same numerical
buffers with preceding stores and cleanup; it no longer initializes from
captured via-entry bytes. This earlier component mode remains required.

`prepare_impedance` is the preparation used by `solve_impedance`: it performs
the existing filament construction, mutual/self assembly, native symmetric
factor/inverse, segment folding, reduced inverse and optional eddy correction.
`solve_impedance` then applies vias and finishes the existing outputs. The
extraction preserves the original calculations and the public solver's default
filament limit, trailing-via guard, diagnostics and matrix exports. There is no
separate approximate inductive calculation in the audit.

The comparison constructs its shape and mesh from the request. Its diagnostic
budget is explicitly 512 filaments, independently of fixture dimensions. It
does not take a matrix, mutual value or correction from recorded outputs.
The generated reduced impedance overwrites the entire native matrix region
before any via load; captured words are used only for comparison.

Via traversal is now shared with production through `vias.segment_records`.
The audit derives the diagonal indices, Z endpoints, via width/resistance and
cell counts from the request's Python geometry and technology. All 132 records
in each 130-run corpus match the original segment observations byte for byte.
Observed segment records serve only as expectations. A changed original Z
word fails validation without changing the generated stamp inputs. The same
source-derived records are required by both the older shared-memory audit and
the [earlier contact/cache comparison](CAP_PRELUDE.md).
Their 132 generated diagonal indices also overwrite the complete live
`ind.via_indices` array at its predicted allocation address before stamping;
every original 32-bit index word matches. Its bytes are no longer native
calculation inputs to this comparison.

## Internal capacity and independent original checks

The selected native inputs include 288- and 384-filament systems. Symmetric,
impedance-assembly and complex-sum buffers now support 512 entries internally.
The WebAssembly module exports its capacity; JavaScript sizes its views and
Python chooses its compiled path using that value. The webpage still checks
and enforces its 256-filament mesh budget.

The larger storage changes no arithmetic, pivot or accumulation loop order.
The compiled file grows from 405,481 to 405,506 bytes; its static linear memory
grows from 28.1875 to 35 MiB. The new SHA-256 is
`c3a0a5e12560a0a83401d6a9f94f1d392de41bb4f52c8285e9f56a4212bddfb5`.
Existing performance measurements referring to the preceding artifact remain
historical measurements, not benchmarks of this build.

`capture_wide_symmetric_original.py` calls the intact original ZSYTF2/ZSYTRI
instructions with the original numerical DSO imports and larger probe backing.
It retains all four selected cases in a separate fixture: 288 dominant, 384
dominant, 384 paired, and 512 paired. Complete upper-triangle input, factor and
inverse digests, every pivot, untouched stride canaries, source, compile flags,
original/DSO hashes and the parent fixture hash are recorded. Both paired cases
exercise two-entry pivots. All seven old/new large-system digests match the
compiled port, and the 44 earlier matrix cases remain unchanged.

## Exact selected-system results

The full packaged-Pyodide comparison regenerates CAP and the pre-via inductive
matrix for all 65 selected input configurations, each in cold and warm native
cache state. All 130 observations match without component tolerances:

- 127,140 regenerated CAP input words and 127,140 regenerated inductive input
  words.
- 3,117 allocation addresses and 12,877 allocation/free events.
- 131 completed via stores and the original unmapped load fault.
- 39,524 raw cache words and all four damaged chains in this capture.
- 118,948 CAP and 118,948 inductive words at the 129 completed node entries.

The audit reports **zero differences**. No selected larger matrix, native
fault, cache mode or damaged-chain case was skipped. A separate portable test
checks all twelve small-system/cache combinations against the native input
words. Existing tests continue to check the public solver, eddy behavior,
assembly, browser mesh recovery and real-worker output/download flows.

## Remaining scope

The original comparison initializes allocator state at CAP matrix entry; the
[subsequent prelude comparison](CAP_PRELUDE.md) moves that boundary back before
contact construction. Those initial states and otherwise unknown heap bytes at
via entry remain captured component-test preconditions. These must be derived from
process/scene allocation history and preceding stores before production can use
the shared-memory path. Most arena structures still have logical rather than
full byte-backed metadata. Complete repeated command execution and cleanup,
the other known numerical-instruction mismatches, and whole-program parity
remain unfinished.

The normal runtime does not read fixtures and still guards unsupported
trailing-via aliases. No JOIN/UNJOIN numerical gate is waived. A new mandatory
`inductive` job runs the full regenerated-input comparison separately from the
existing `shared` job; the older failing audits remain required.

```sh
python tools/capture_wide_symmetric_original.py --reference /path/to/asitic-re
python tools/build_kernels.py --zig /path/to/zig-0.13.0 --verify
python tools/build_site.py
PYTHONPATH=src:tests python -m unittest test_impedance_preparation -v
node tools/check_matrix_kernels.mjs /path/to/pyodide.mjs
node tools/check_pre_via_original.mjs /path/to/pyodide.mjs /tmp/pre-via-audit.json
```
