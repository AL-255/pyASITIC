# UNJOIN development status

UNJOIN/SPLIT/BREAK/CUT is implemented on the composition development branch.
It is not deployed. Geometry comparisons pass, but three selected finite
simulation sessions still fail exact comparisons. Those failures are required
checks, not exclusions or tolerated errors.

## Original command behavior

The port follows `recomp_cpp/src/geometry_edit.cpp` and 44 unchanged-original
histories. Each history is also run without GDB. Read-only WHO-entry observers
retain 178 states and 33,084 binary64 coordinate stores across all twelve
generators, with origins, materials, phase state, descriptor kind, division
count, initialized turn fields, friend links and descriptor reuse.

The public edit is:

```json
{"command":"UNJOIN","winding":0,"index":0,"name":"SECOND"}
```

The native operation transfers existing segment records into a new descriptor;
it does not copy or reallocate the tail segments. The source retains its kind
and friend link. The new winding has native wire kind and no friend. Its local
minimum is added to the source origin using retained arithmetic, then its
coordinates are translated by the retained old-minus-new origin difference.

For a chain of `n` segments:

- `0` uses integer `n/2`, rejecting a single-segment chain.
- A positive index cuts after that many segments.
- A negative index first becomes `index - 1 + n`. The traversal still retains
  at least the first segment, even when this expression is nonpositive.
- Indices outside `[-n,n]` are rejected without changing geometry.
- The source turn field is decremented by the transformed index divided by
  the descriptor division count, using integer division toward zero. The new
  descriptor receives that updated field.
- Existing-name rejection precedes segment and index handling.

RING's uninitialized turn field stays unknown in Python. The port does not
invent its bytes or use captured garbage as a runtime value. Its split
coordinates do not depend on that field. Interactive CAP's opaque positive
phase word is tested for its sign behavior rather than for an invented pointer
value. These qualifications limit raw descriptor parity claims.

## Empty results and faults

Cutting after the last segment successfully creates an empty winding with
the native `1e15` minimum-coordinate sentinel. Captures cover MOVE, ROTATE,
FLIPH, FLIPV, PHASE, RENAME and BEFRIEND on that winding, name rejection before
empty-chain access, and erasing the nonempty source so only the empty winding
remains.

Separate selected follow-ups show original SIGSEGV (`11`, plain return `-11`)
for COPY, ERASE, FLIP, JOIN and another UNJOIN of the empty chain. The Python
API raises explicit diagnostics for these recorded faults. Failed browser
operations leave the editable history unchanged. Empty windings retain project
and GDS export, selection, undo and reset; analyses are disabled. A scene with
only an empty winding exports a valid GDS with zero boundaries.

All captured geometry states pass CPython and real Pyodide/WASM comparisons.
Every scene is checked through GDS export, project save/restore, regeneration,
selection and undo/reset. CPython also reads GDS with independent gdstk.
Chrome checks actual split controls, both wire Pi2 model downloads, GDS/project
downloads, empty selection, fault diagnostics and undo, with desktop/mobile
screenshots. This Chrome check does not certify the unresolved balun models.

## All nine selected model requests

| Session | Original outcome | Current status |
| --- | --- | --- |
| `wire/head/pi2` | Finite | Exact model, Y and S stores |
| `wire/tail/pi2` | Finite | Exact model, Y and S stores |
| `square/head/pi2` | Finite | Exact model, Y and S stores |
| `square/tail/pi2` | Finite | Exact model, Y and S stores |
| `balun/head/pi2` | Finite | Unsupported trailing-via heap alias; strict failure retained |
| `balun/tail/pi2` | Finite | Exact model, Y and S stores |
| `balun/head-tail/calctrans` | Finite | Unsupported trailing-via heap alias; strict failure retained |
| `balun/tail-other/calctrans` | Finite | Numerical mismatch; strict failure retained |
| `wire/empty/pi2` | SIGSEGV, no model | Explicit empty-winding diagnostic |

All nine unobserved runs are retained in
`unjoin_plain_outcomes_original.json.gz`; all eight produced reports, including
the failing cases, are in `unjoin_sessions_original.json.gz`. The tail-other
numerical mismatch is now isolated by the independent assembly and instruction
captures below. The earlier trailing-via heap-alias failures remain separate
and unresolved.

## Coupled tail-other numerical divergence

`unjoin_assembly_original.json.gz` retains the first actual upper impedance
assembly from all eight original model-producing UNJOIN scripts. The ninth
plain outcome, the empty-winding fault, remains in the required parent archive.
These read-only observations stop at assembly return before inversion, then
terminate the isolated inferior; they do not observe command termination.
Every original filament input, material value, count and defined upper cell
remains present. Minimal environment guards precede observation. No numerical
code, input, register, memory, allocation, CPU affinity or result is replaced.

The complete 1,685-entry CPU and compiled-browser assembly reports agree
exactly. Seven sessions have zero upper-entry differences, including the two
cases whose later via stamp aliases CAP. The 47-filament tail-other coupled
case differs at exactly two upper entries: `(9,42)` and `(9,45)`.

`unjoin_mutual_traces_original.json.gz` reruns the unchanged tail-other script
and captures both actual pair calls. Their arguments match the independently
observed assembly records. Every reached helper and selected elementary
instruction output is retained: two complete pair returns, two canonical
statuses, two complete canonical coordinate outputs, two spatial helper
returns, ten FPATAN, two FCOS, two FSIN, two FYL2XP1 and six FYL2X stores.
Both FCOS calls at `0x80614cc` consume `00504a60a2da0fc9fe3f` and return
`00b467cd33f304b5fe3f`; the current runtime returns
`01b467cd33f304b5fe3f`. This independently confirms the same instruction and
operand implicated in JOIN. All the other captured elementary-instruction
stores and canonical results match. The complete-pair and spatial-helper
returns differ in both cases, giving six required trace differences.

The actual production request also checks every generated filament and
material record against the original, with zero differences. An observer
records the arguments and result of the real assembly call and returns its
unmodified result; native inputs never replace generated geometry or values.
The production result retains all 4,418 capacitance components exactly. The
two upper-entry differences propagate to 368 of 4,418 inductive-admittance
components, all 23 Y/Z/model words and all eight S words. These 401 production
differences remain required, in addition to the two independent assembly and
six trace comparisons. Complete CPU and browser reports agree exactly,
including all those required differences. This is an identified cause, not an
implemented FCOS correction or whole-simulator parity claim.

The assembly archive is 24,522 bytes, SHA-256
`9856a53bc2aa90ee158d56988692e560fa74e76119925965e1c6a83fbadb015c`.
The helper/instruction archive is 6,348 bytes, SHA-256
`cdefe00c76213ee681e6f91c1b9022c5944abaccebe25cbea0ac1a5c4b959eac`.
Both retain mandatory parent hashes and exact capture commands.
The new seven-test suite requires zero numerical differences and is a separate
required browser CI job. Four provenance/input/target-integrity tests pass in
both runtimes; the three assembly, helper/instruction and production-model
tests fail their exact zero-difference assertions in both. All earlier
full-model, JOIN, UNJOIN and numerical
gates remain required, with their existing exact expectations.

```sh
python tools/capture_unjoin_assembly_original.py --reference ~/github/asitic-re \
  --library-path /path/to/i386/libs
python tools/capture_unjoin_mutual_traces_original.py --reference ~/github/asitic-re \
  --library-path /path/to/i386/libs
PYTHONPATH=src:tests python -m unittest test_unjoin_assembly_original -v
python tools/audit_unjoin_assembly_original.py --output /tmp/unjoin-assembly-cpu.json
node tools/check_unjoin_assembly_original.mjs /path/to/pyodide.mjs /tmp/unjoin-assembly-wasm.json
```

Both strict audits exit nonzero. The existing runtime, mathematical
approximations and tolerances are unchanged; no operand-specific correction
or native output table is introduced. The source package remains
`8ef350c4fd0013ba`, and this branch remains undeployed.

## Trailing via aliases a capacitance cell

The earlier trailing-via diagnostic was based on an incomplete model of native
behavior. The original stores the *following* conductor index for a via. A
trailing via therefore targets `(n,n)` of a declared `n`-by-`n` inductance
matrix. It can complete and produce a finite report instead of faulting.

New read-only observers capture the first actual `add_via_impedance` entry,
return and subsequent node-equation inputs for the two failing cases. Their
actual pointer relationships show:

| Session | Matrix size | Trailing stamp aliases |
| --- | ---: | --- |
| `balun/head/pi2` | 3 | CAP row 2, column 0 |
| `balun/head-tail/calctrans` | 24 | CAP row 23, column 0 |

The out-of-range stamp leaves the defined inductance matrix entries untouched
but changes an entry in the separately allocated CAP matrix. Ignoring it or
moving it to the last valid inductance diagonal gives wrong finite models.
The runtime retains an explicit unsupported diagnostic until the original
allocation/alias behavior is reproduced.

`audit_unjoin_compiled.mjs` computes CAP from current geometry and compares
all 1,170 binary64 input words against actual native node inputs. Four words
differ: real and imaginary components of the two aliased cells. Replaying the
via arithmetic at the **observed addresses in this diagnostic only** explains
both complete CAP arrays exactly. The audit still exits **1** for the runtime
differences. This is not a proof that those addresses or a row formula apply
to other native allocation histories, and no selected-case correction enters
the application.

The broader cold/warm experiment and the source-derived allocation/free plan
are documented in [STORAGE_LIFETIMES.md](STORAGE_LIFETIMES.md). They preserve
130 observations and match 12,877 storage events, but physical address
placement is still unimplemented; these two model diagnostics remain active.

## Verification

```sh
PYTHONPATH=src:tests python -m unittest test_unjoin_original test_unjoin_sessions_original -v
python tools/build_site.py
node tools/check_unjoin_original.mjs /path/to/pyodide.mjs /path/to/jsdom/lib/api.js
node tools/audit_unjoin_compiled.mjs /path/to/pyodide.mjs /tmp/unjoin-cap-differences.json
node tools/check_unjoin_chrome.mjs /path/to/pyodide /tmp/unjoin-rendered
```

The geometry tests pass. Full model tests retain two errors and one numerical
failure. The full browser comparison also exits nonzero for those same three
sessions; the narrow Chrome interaction/wire-model check passes. The splitting
CI job is mandatory and independent of the already-failing JOIN composition
job. Neither permits deployment with a failed exact model comparison.

The combined CPython UNJOIN, JOIN geometry, ERASE, COPY and PHASE run checks
20 tests and has exactly the two unsupported model errors and one numerical
failure above. The existing mesh DOM/Pyodide regression check also passes.
