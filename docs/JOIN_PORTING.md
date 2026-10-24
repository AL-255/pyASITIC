# JOIN development status

JOIN is a development-branch port, not a released capability. Geometry and
three selected Pi2 sessions match the original binary; a finite coupled session
does not. The failing comparison remains mandatory. Do not deploy this branch
or treat the model discrepancy as harmless rounding.

## Captured behavior

`capture_join_original.py` runs unchanged original command histories with
read-only WHO-entry observers. Its fixture contains 20 histories, 189 states
and 75,924 binary64 coordinate stores, covering all twelve existing generators.
It also retains materials, origins, phase, descriptor kinds, live and stale
friend links, copied descriptors, descriptor reuse, parser rejections and VIA
compatibility warnings. Native termination is recorded for every history.

The Python implementation appends translated copies of the source segment
records in original order, removes source descriptors, and preserves the
original outgoing friend-link behavior. Its geometry arena allocates segment
copies before freeing the source records. FLIP reverses both the visible
segment order and the arena address order. JOIN aliases are ADD, MATE and
COUPLE. The public operation is, for example:

```json
{"command":"JOIN","winding":0,"others":[1,2]}
```

All selected geometry states match exactly in CPython and Pyodide/WASM. Every
state is exercised through project restoration, active winding selection and
GDS export; CPython GDS output is also read by independent gdstk. Real Chrome
checks JOIN controls, source deletion and undo, project/GDS downloads and a
complete wire Pi2 model, with desktop/mobile screenshots. This Chrome check
does not cover the failing coupled model.

## Model outcomes: all eight selected jobs retained

| Original session | Original outcome | Current comparison |
| --- | --- | --- |
| `wire/pi2` | Coordinate-out-of-range diagnostic; no model | Diagnostic retained |
| `square/pi2` | All-NaN Y/S report | Raw report retained; Python contact-grid diagnostic |
| `recycled-transformer/pi2` | All-NaN Y/S report | Raw report retained; Python contact-grid diagnostic |
| `recycled-transformer/calctrans` | All-NaN Y/S/model report | Raw report retained; Python contact-grid diagnostic |
| `finite-wire/pi2` | Finite model | Exact Y, S and model output stores |
| `finite-square/pi2` | Finite model | Exact Y, S and model output stores |
| `finite-balun/pi2` | Finite model | Exact Y, S and model output stores |
| `finite-balun/calctrans` | Finite model | **Fails: all 23 model/Y/Z and eight S words differ** |

`join_plain_outcomes_original.json.gz` records all eight unobserved native
executions. Its `produced_model` flag means a report was produced, not that the
report was finite. `join_sessions_original.json.gz` retains all seven produced
reports and their raw stores. The nonfinite diagnostic handling is not a claim
of full native NaN payload or command-behavior parity.

## First coupled-model discrepancy

Read-only assembly and helper observers on the actual unchanged joined
CALCTRANS script capture 50 filaments, 1,275 defined upper entries and the two
mutual calls at `(12,45)` and `(12,48)`. These observers stop after the selected
return and explicitly do not claim to observe native command termination.
Their operands match the independently captured original assembly records.

The complete capacitance input has **zero differences in 5,000 binary64
components**. Two upper impedance entries differ; inversion propagates them
to 496 of 5,000 inductive-admittance components and every reported model/S
word. The resulting model differences are material.

Both mutual discrepancies first diverge at native FCOS address `0x80614cc`,
with the same raw extended operand:

| Value | Little-endian retained word |
| --- | --- |
| Input R80 | `00504a60a2da0fc9fe3f` |
| Original result R80 | `00b467cd33f304b5fe3f` |
| Current result R80 | `01b467cd33f304b5fe3f` |
| Original result after binary64 store | `f6ac79669ea0e63f` |
| Current result after binary64 store | `f7ac79669ea0e63f` |

The original significand is on a binary64 midpoint. A one-unit retained-word
difference crosses that rounding boundary. The other 20 standalone
instruction replays at their captured operands match. Ideal cosine, the
current scaled-Pi approximation and the experimental P6 emulator calculation
do not reproduce this original result. No input-specific correction, lookup,
fixture substitution or tolerance relaxation is applied.

The portable strict audit reports two upper-entry, two complete-pair and two
raw FCOS differences (six records). The compiled strict audit reports 531
differences: 496 inductive components, 23 model words, eight S words, two upper
entries and two raw FCOS words. Both exit nonzero. The additional failing
pair cases extend the preexisting retained-math discrepancies documented in
the instruction audits; they are not evidence of universal instruction parity.

## Reproduce

From this branch, with the documented Python environment and pinned Pyodide:

```sh
PYTHONPATH=src:tests python -m unittest test_join_original test_join_sessions_original -v
python tools/audit_join_original.py --output /tmp/join-portable-differences.json
python tools/build_site.py
node tools/check_join_original.mjs /path/to/pyodide.mjs /path/to/jsdom/lib/api.js
node tools/audit_join_compiled.mjs /path/to/pyodide.mjs /tmp/join-compiled-differences.json
node tools/check_join_chrome.mjs /path/to/pyodide /tmp/join-rendered
```

The model tests and both strict audits currently fail. The Chrome check passes
only its stated wire model and interaction scope. The combined CPython JOIN,
ERASE, spatial, COPY and PHASE run checks 23 tests and has one failure, the
finite joined CALCTRANS case. Existing regression expectations remain exact.

Mixed-generator creation, general converted-VIA table histories, UNJOIN and
secondary segment groups remain outside this JOIN capture scope. They still
belong to the full recreation objective and require their own original runs.
