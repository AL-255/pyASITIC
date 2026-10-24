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
the failing cases, are in `unjoin_sessions_original.json.gz`. The numerical
cause of the tail-other coupled mismatch is not yet isolated. Do not assume
that it is the previously captured JOIN cosine operand.

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
