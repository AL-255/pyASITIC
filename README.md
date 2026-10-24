# pyASITIC

Python reconstruction of ASITIC, with a static browser application for GitHub
Pages. The reference is [`AL-255/asitic-re`](https://github.com/AL-255/asitic-re),
specifically its `recomp_cpp` reconstruction. This repository implements the
algorithms through a Python API; it does not invoke the reference executable at
runtime. The browser accelerates retained FFT, spectral math, filament construction,
mutual inductance, contact potentials and matrix
solves with a small compiled
WebAssembly kernel; a portable Python implementation is also included.

**[Open the workbench](https://al-255.github.io/pyASITIC/)**

This is an active port, **not yet a complete replacement** for ASITIC.

Implemented so far:

- Square, polygon and symmetric square/polygon spirals, wires, polygon rings, capacitors, via arrays,
  and multi-metal square windings, preserving native ribbon edge records.
- Planar transformers, 3D mirror transformers, and baluns with separate winding records, winding
  selection for electrical analysis, and combined GDS export.
- `.tek` technology loading, conductor DC resistance and the original empirical
  high-frequency resistance model, including parallel via counts. Original
  norm/power stores and distinct DC/HF accumulators match all 270 captured
  finite x87 returns across 34 histories in Python and WebAssembly.
- All 45 GF180 interconnect stacks selectable in the process panel, with 73
  downloadable `.tek` variants covering both published MIM gaps, editable
  substrate assumptions and GF180 GDS layer mappings. See [data and model
  assumptions](docs/GF180.md); these are nominal coil models, not calibrated RF
  or MIM PDK models.
- Original `Inductance` and `Coupling` estimate algorithms: segment self terms,
  signed parallel, planar and spatial mutual-inductance cases.
  Both Python and browser segment-pair paths preserve the original retained basis,
  intersection tests, cross-section separation and planar/spatial spill order.
  Direct original-executable gates check 2,561 scalar/pair outputs exactly at
  binary64 boundaries, including 426 independent threshold/degeneracy cases.
  Another 2,094 captured original mesh-pair outputs are exact in both backends;
  2,683 separate native instruction cases check the
  elementary-function stores.
  Whole-coil self/mutual and DC accumulation and the `Q` / `QUALITY` numerator
  retain the original precision. Across 56 complete original command histories,
  all 56 printed L, 392 QLF and 392 raw DC stores match in Python and WebAssembly.
  One compiled call evaluates the whole coil; cached geometry results serve
  repeated-frequency estimates. The broader audit retains four differing pair
  stores and seven extended L returns as unresolved internal precision work.
- `LMAT` filament solver with longitudinal and cross-section meshing,
  impedance assembly, inversion/reduction and via corrections. The web app
  displays L, R, series Q and the complex matrix, with full matrix CSV download.
  Uses the original symmetric factor/inverse and retained parallel mutual kernels.
  Python and compiled symmetric matrix paths are checked bit for bit against original
  factors/inverses, including 128- and 256-entry systems.
  Via corrections preserve the original retained arithmetic and matrix stores;
  1,214 direct-original stamps check 2,428 output components (finite bits and
  nonfinite classifications), including forced-reference cell counts.
  Self impedance and mutual-frequency weighting now preserve the original
  retained stores. Twenty-three complete original upper matrices check 4,648
  output components exactly, including refined polygon clones. The portable
  assembly checks compute every mutual term rather than supplying saved terms.
- Optional native `EDDY ON` substrate correction, including square packing,
  segment folding, layered Green integration and convergence diagnostics.
  Preserves native negative-resistance results and reports nonfinite failures.
  Both reflection and layered paths run inside the compiled browser kernel.
  Direct original captures check both paths against 165 retained Green returns,
  all 74,726 callback points and 19 complete matrix stamps exactly. Another 3,532 original Green/
  legacy-complex calls and 2,658 separate native trig calls match at binary64
  boundaries; raw instruction intermediates still need parity work.
- Original layered-substrate `CAP` solver: contact discretization, layered
  spectral Green functions, reflected FFT tables, potential-matrix inversion,
  and admittance reduction. Includes explicit ground winding selection, total
  capacitance, substrate equivalent resistance and admittance CSV download.
  Python and compiled contact arithmetic match 41 original-binary matrices
  exactly at finite output boundaries: 264,844 components, including two
  complete 256-contact systems. Nonfinite results retain native classifications.
  CAP and Pi-family node solves use the original general LU/inverse sequence;
  the compiled path is checked against original factors, inverses, solves and
  network products across the native 64-column block boundaries.
  Python and compiled Green-table generation are checked against 33 complete
  original-binary tables through 256×256 and 1,728 transfer/regional calls.
  Both preserve coefficient sentinels, source-depth restoration, rectangular
  backing-store writes and retained arithmetic; coefficient loops have separate
  original-binary checks.
- Distributed `PI2` / `PI3` two-port models with optional native eddy correction: combines CAP
  and filament admittance through the original node equations. Reports series
  L/R, two RC shunts, port/differential Q, input impedances, shunt resistance,
  narrowband resonance estimate and native 50 Ω Y/S output, with JSON/CSV export.
  Python and compiled folded-node stages match 54 original-binary cases at identical
  CAP/inductive inputs, including 256 nodes and all 15 finite coupled sessions.
  `PI3` requires an explicit reference; `PI4` solves with two pad strips and
  subtracts their capacitive contribution using the original de-embedding path.
  Pi metrics, ZIN and S conversion preserve every retained operation and store
  in both Python and WebAssembly: 3,435 original records check 96,180 binary64
  outputs and 6,673 finite retained returns. Pi3 preserves its ordinary reference
  mesh, distinct from Pi2's forced reference mesh. All 41 captured complete
  original Pi sessions match every finite Y/model/S output and resonance value
  in Python as well as the compiled browser path. All 15 finite captured coupled
  sessions also require exact raw SI Y/Z/model stores in both paths.
  The strict audit is mandatory in CI; broader device/process coverage remains
  necessary for universal original-binary parity.
- Extended `PIX` two-port model with unfolded capacitance, segment impedance
  and the original extended node equations. Includes circuit display, PiX
  sweeps and Y/S/model exports. Python/JSON callers can request matrix and
  voltage/current diagnostics with `include_matrices=True` / `true`.
- Three-terminal Pi circuit diagrams with labeled series L/R and RC shunts,
  shared ground/pad settings, and circuit SVG download. The native fast `PI`
  conductor path faults before producing values; its view shows that limitation.
- Original `SELFRES SLOW` search with repeated distributed network solves,
  single-ended/differential input reactance, streamed sample progress, a trace
  plot and JSON/CSV/SVG export. Reports the native stopping criterion and keeps
  the last evaluated circuit separate from a possibly unevaluated result.
- `CALCTRANS` coupled-winding analysis with native junction termination,
  optional reference strip and eddy correction. Displays the seven-value
  equivalent circuit, Y/Z/S exports, and selectable coupling, L/M/R sweep plots.
  The compiled extractor matches 67 direct original-executable cases exactly
  at finite output boundaries. Complete-session checks cover 15 finite cases
  and explicit diagnostics for six original nonfinite histories.
  All fifteen captured finite eddy-off/on sessions match every raw original SI
  Y/Z/model output bit, with undefined coupling by classification. The compiled
  reflection and layered Green/eddy paths also match the captured boundaries
  above. Observer fallbacks and broader complete-session coverage still need
  parity work.
- GDSII export with actual via cuts and metal landing pads. Default mapping:
  metal index + 1, via index + 100; datatype 0. GF180 presets supply their drawn
  layer numbers. Python/JSON callers can override the mapping.
  Units are micrometres, with a 1 nm export grid.
- Polygon spirals retain native radial decrement, angle spills, vertex stores
  and recentering. Forty-two complete original creators check 12,288 XY
  components exactly in Python and WebAssembly, including fractional turns,
  3–32 sides and positive/negative rotations. Another 77 complete original
  keyword/interactive cases check 34,758 XYZ stores and independent GDS exports.
  Webpage polygons now use original grid/angle parsing, binary32 turn input and
  retained side-based truncation; typed dimensions remain unsnapped binary64.
  Six complete polygon Pi2 sessions match every Y/model/S/resonance store in
  Python and WebAssembly, including fractional turn boundaries and eddy.
  Longitudinal meshing preserves the original copy branch and independently
  normalized ribbon edges.
- WIRE keyword input now preserves native dimension/origin snapping, angle
  conversion, default origin Y and integer phase handling. All 101 original
  creators / 1,818 XYZ stores match in both runtimes; independent GDS readers
  confirm the exported ribbons.
  Six complete finite-port Pi2 histories match original model/S/resonance
  stores. Two original NaN histories retain their contact evidence and defined
  downstream values, with explicit browser diagnostics.
- Symmetric square/polygon construction preserves retained span, angle and
  radius updates, crossover metal history and via placement. All 114 original
  creators / 60,804 XYZ stores match in Python and compiled WebAssembly, with
  independent GDS readback. Eight complete Pi2/2PORT sessions match every
  captured electrical output, including eddy and binary64 interactive inputs.
  Explicit transition-gap validation now matches 840 additional original input
  histories. The 682 accepted creators match 92,070 XYZ stores and GDS readback,
  including zero/negative gaps and omitted defaults that bypass native validation.
  Two additional finite Pi2/2PORT sessions match all captured electrical stores;
  four original NaN histories retain contact evidence and explicit browser errors.
  The webpage also offers the original interactive symmetric input mode, with
  full precision, prompt turn limits and technology SMIN/WMIN rules. Another
  36 creators / 10,386 XYZ stores and three finite complete models match the
  original. Eleven repeated-prompt and three NaN histories retain diagnostics.
- Multi-metal squares preserve native copy origins, reflection history and
  deferred joins across up to five sample-process metals. All 180 original
  creators / 56,214 XYZ stores match in Python and Pyodide, with independent GDS
  readback. Four complete Pi2/2PORT sessions preserve every captured electrical
  output, including native nonfinite resonance and three invalid-stack histories.
- Capacitor keyword/interactive modes and working interactive VIA inputs match
  84 original creators / 2,520 XYZ stores and origin bits, with independent GDS
  readback. Four complete capacitor Pi2/2PORT models and 32 retained via
  resistance returns match, including original nonfinite metric classes.
  The broken original VIA keyword command and standalone VIA Pi2 fault retain
  explicit diagnostics; signed-zero input survives request/project round-trips.
- Planar transformer and balun keyword/interactive creation preserves native
  turn limits, names, defaults, lead shifts, origins and reflections. All 98
  original creators / 38,592 XYZ stores match in both runtimes, with combined
  GDS readback. Six complete coupled histories check the actual joined meshes;
  five finite cases match every CAP/LMAT/Y/Z/model/S store, and one original
  all-NaN reference case retains an explicit diagnostic. Optional winding names
  and native default omissions survive webpage generation and project reload.
- 3D transformer native prompt inputs and geometry match 96 intact-original
  creators / 94,824 XYZ stores, including exact primary ribbon widths/thicknesses,
  raw dimensions/origins, name tokens, phase and spacing boundaries. Independent
  GDS readback checks both windings. Twelve original LMAT matrices match every
  output bit, including eddy. Six native coupled histories return NaNs or crash;
  the webpage reports their invalid planar contacts explicitly.
- Square and multi-metal coils can be sized from their inner opening or outer
  edges, with selectable original keyword/grid or interactive/full-precision
  input. All 134 new original creators / 45,072 XYZ stores and four complete
  Pi2/2PORT sessions match, including the original fractional-turn expansion
  differences. Projects preserve both input mode and dimension choice.
- Browser preview, pan/zoom, process-file import, project save/open, conductor
  estimates, selectable L/R/Q frequency plots, linear/log frequency scales,
  progressive Pi2/Pi3/Pi4 sweeps, sample-to-circuit inspection, plot SVG and CSV
  download. Python runs in a
  module worker using pinned Pyodide 314.0.7; the runtime loads from jsDelivr.
- `COUPLING` preserves the original binary64 accumulation, retained square-root
  normalization, and per-pair origin add/subtract stores. All 428 captured calls
  match M/k and raw coefficient returns in both backends, including repeated
  and reversed order. Typed calls retain the original centerline rounding
  changes; webpage requests start from fresh project geometry. The compiled
  path evaluates the complete cross-winding sum in one batch.
- Layout length and area follow original `GEOM` accumulation, with a separate
  `METALAREA` result. All 260 captured complete reports / 3,007 segment operands
  and 538 direct threshold, extreme and NaN-payload cases match their actual
  original output stores in both backends. Both areas use stored segment
  widths and include vias. GDS continues to use the original ribbon edges.
- Mesh settings are available beside models, sweeps, self-resonance and LMAT,
  and from mesh-limit errors, with keyboard focus on the presets. Errors also
  offer a direct fit action that displays adjusted cells before rerunning.
  Shared mesh settings start with
  the Python API’s coarse preset
  (1000 µm). Coarse/balanced/fine presets, custom conductor and
  CAP cells, the original MAXNW width-division cap (default 500), and a
  filament-count check before electrical solves. “Fit to 256 filaments” explicitly coarsens conductor cells while preserving CAP cell
  settings and MAXNW. Counts include Pi4 pads or both CALCTRANS windings as selected;
  project downloads preserve all five cell sizes and MAXNW. Optional automatic
  fitting coarsens over-budget conductor meshes before solving, displays the
  adjusted cells and checks the count again after native input snapping. It is
  off by default; projects preserve the preference. Original retained
  count rounding matches 2,116 captured primitive cases; six complete original
  CLI runs verify MAXNW, filament stores and LMAT reports (five finite reports
  match bit for bit; the native invalid MAXNW=1 case remains a diagnostic).
  Polygon spirals and rings also expose the original full-precision interactive
  input mode. All 120 captured radial creation histories preserve 65,268 XYZ
  stores or their native construction failures; six full Pi2/2PORT histories,
  including a wide ring and eddy correction, match the original output stores.
  Webpage meshes also follow the original 0.1 µm input snap and CCELL grid-pitch
  minimum. Six fractional-mesh histories, including 200 filaments, match the
  original LMAT/Pi2/Y/S outputs exactly. Retained summation preserves native
  double rounding after each term and runs as a compiled browser batch.
- Wire, capacitor, transformer and balun forms also expose original interactive
  input mode. Wire/capacitor angles retain the original literal radians and
  full-precision dimensions. Interactive transformers share one turn count;
  baluns floor the total count before checking capacity and follow the original
  bounds on non-square chips. Interactive primitive names follow native case
  and whitespace normalization. Twenty paired boundary histories and nine name
  histories verify 10,296 XYZ stores and independent GDS readback. Two new
  finite coupled sessions match every Y/Z/model/S and input-matrix output bit;
  a third original all-NaN session retains an explicit collapsed-contact
  diagnostic. All 84 captured interactive wire/capacitor/via/paired creations
  pass actual webpage Generate, project round-trips and decoded GDS checks in
  jsdom with real Pyodide and the shipped numerical kernels.
- Layout editing supports the original MOVE/MOVEX/MOVEY/MOVETO, ROTATE,
  FLIPV/FLIPH and FLIP commands, including their aliases in JSON edit histories.
  Moves preserve native linked transformer/balun behavior; 3D windings remain
  independent. Rotation, reflection and segment-order reversal affect only the
  selected winding. The webpage provides apply/undo/reset controls; Generate,
  project downloads, GDS and electrical analyses replay the same history.
  Fifteen unchanged-original histories cover all twelve generators and 186
  intermediate states / 29,052 exact XYZ stores. Sixty complete point-rotation
  traces verify the retained instructions and cancellation-sensitive output
  stores. Independent GDS readback checks all representable states, with
  explicit export diagnostics for original layouts beyond GDSII's int32 range.
  Three edited Pi2/CALCTRANS sessions match the original Y/model/S outputs and
  complete coupled input matrices in both Python and the shipped browser runtime.
- COPY, RENAME, BEFRIEND and UNFRIEND extend the same edit history to scenes
  with multiple windings. Copies preserve full stored geometry; an optional
  metal refresh updates every segment's height and thickness. Native directed
  friend links, including stale one-way links and self-linked moves, are retained.
  The webpage can select any scene winding and any distinct second winding for
  coupling, CALCTRANS and Pi/CAP references. Generator defaults stay separate
  from copied/renamed descriptors when projects regenerate; undo/reset can
  recover after removing the selected copy. Seventeen unchanged-original
  histories cover 229 states, including native rejections, with 117,630 exact
  XYZ stores and independent GDS checks. Duplicate-destination COPY reports an
  error instead of returning the incomplete descriptor left by the native
  rejection. Five complete copied-winding Pi2/CALCTRANS sessions, including an
  explicit Pi2 reference and a VIA copied onto a conductor metal, retain exact
  original model outputs and coupled inputs. A metal-converted VIA can run Pi2;
  the unconverted standalone VIA retains the original fault diagnostic. CAP's
  original NaN totals with that VIA as a reference are retained as a diagnostic.

- PHASE / PH replays the original sign predicate and reverses segment endpoints
  while retaining segment order. Repeated signs preserve the stored state;
  switching a negative phase to zero produces the native sticky zero state.
  Creator forms preserve signed integer keyword phases across project reload
  and regeneration, including polygon/ring zero-to-positive normalization.
  All 320 captured states / 98,190 XYZ stores across 20 creator modes and
  6 complete phased
  Pi2/CALCTRANS sessions retain original coordinates and model outputs. The
  standalone interactive capacitor's uninitialized initial native phase word
  is represented by its observed positive predicate, without inventing its
  address value; subsequent specified phase stores are compared exactly.
- ERASE / DEL / DELETE / RM removes a resolved winding list using the native
  outgoing-peer clearing behavior. Descriptor identities survive erasure and
  reuse, including stale friend links and mixed-size allocation histories.
  The geometry arena follows the reference [glibc 2.39 cache, bin, split and
  coalescing rules](https://github.com/bminor/glibc/blob/glibc-2.39/malloc/malloc.c).
  All 736 captured scenes / 843,264 XYZ stores match, including polygon and
  balun allocation stress and the native parser's rejection of more than ten
  ERASE arguments. The repeated-descriptor native fault is an explicit API
  diagnostic. Four complete post-erasure Pi2/CALCTRANS sessions match raw model,
  Y/S and coupled-node outputs. Empty scenes support GDS/project downloads,
  regeneration, undo/reset and preservation of omitted generator defaults.
  Real Chrome checks additionally verify worker execution, original Y/S bits,
  actual downloads and responsive empty-scene rendering with locally served
  pinned Pyodide. The geometry-only arena is not a full native process-heap
  emulator; broader allocator-dependent command histories remain unverified.

Development [geometry storage replay](docs/GEOMETRY_STORAGE.md) now derives
clone/COPY/JOIN addresses and complete records from earlier process state.
All 140 native observations match 2,750 allocation/free events, 1,017,272
geometry bytes and 91,440 string-pool bytes in Python and packaged WebAssembly.
The same allocator continues through contact/cache preparation. Integrating
those earlier bytes with the numerical history and fixing the remaining exact
parity failures are still required; production trailing-via guards stay enabled.

[Pre-CAP storage](docs/PRELUDE_STORAGE.md) additionally reproduces all 975 FFT
scratch arrays and 130 stream buffers in the 130 selected native histories:
4,526,080 bytes match exactly in the compiled browser backend. Four added small
square/rectangular histories match in portable Python too. FILE/header records
and other intervening stores still need integration before the earlier and
later byte histories can run continuously.

[FILE/header replay](docs/LIBIO_STORAGE.md) now covers every pre-free buffer in
those 130 histories: 1,430 buffers / 4,667,260 bytes match exactly, including
source allocator footer writes and external cache-header padding. The added
rectangular case still fails strict heap-state validation from native
cache-table corruption; that failure remains a required gate.

The subsequent [shared cache replay](docs/CACHE_STORAGE.md) now adds actual
table allocations/content as earlier inputs and reproduces the original
rectangular overwrite at its guest addresses. All 134 newly captured histories
match complete table digests, pre-free buffers and physical heap walks,
including the damaged walk: 6,030 tables / 535,324,320 bytes. All four small
histories also match in portable Python. A clipping negative control leaves
final table digests unchanged but correctly fails physical-walk checks. The
older incomplete-context `libio` audit remains nonzero and required; startup,
allocator byte decisions and joining the later numerical history remain open.

The [continuous driver replay](docs/DRIVER_HISTORY.md) now carries the same
heap/memory through CAP and LMAT to node input, without a CAP-entry reset.
Live cache reads correct the rectangular CAP discrepancy, and native freed
matrix observations correct lower-triangle storage. All 134 selected histories
remain in the stronger comparison, including no-via wires. Complete later
heaps and bounded numerical frees are now independent observations; missing
heap stores remain strict failures in a new required CI suite.

[Allocator pointer stores](docs/ALLOCATOR_STORES.md) now reproduce bin,
fastbin and large-bin size-ring writes. All captured physical headers match,
including previously differing unused fields. The 6,461 remaining heap-word
differences are confined to traced stdout/log buffers and remain required
failures; numerical and pre-free-buffer comparisons still match exactly.

The subsequent [source console replay](docs/CONSOLE_STORAGE.md) adds earlier
stream bindings and generates the original status/warning/progress messages.
All 134 independently recaptured histories now match 3,681 console calls and
every one of 19,456,000 compared later heap words, alongside all numerical and
cache checks. Expected message text never seeds runtime memory. The earlier
incomplete-context gates remain required and nonzero, and six changed native
plain-process exit outcomes are recorded explicitly. Startup, other branches,
full cleanup and known arithmetic differences remain unfinished; this is not
whole-program equivalence or a deployed trailing-via change.

Records use binary64 with selected retained-precision intermediates matching the
reference's x87 arithmetic. The [native logarithm audit](docs/LOGARITHM_AUDIT.md)
adds 8,182 instruction cases and 10,327 multiplier cases with complete request
and original-command provenance. It rejects an isolated P5/P6 replacement that
improves selected failures but worsens the independent set. The strict audit
remains nonzero; no runtime arithmetic or existing expected words were changed.

Universal bitwise numerical equality is not yet established. Original saved geometry fixtures are
compared at their 6-decimal printed precision (5.1e-7 µm).
Foundry design rules and layer mapping must come from the user's process.

The [layered eddy benchmark](docs/benchmarks/2026-10-24-layered-eddy.json)
records identical requests on the previous and compiled browser builds. Repeated
BiCMOS PiX requests improve from about 1.72 s to 44 ms; a 96-filament polygon
LMAT improves from 7.38 s to 214 ms. These measurements exclude interpreter
loading and rendering and do not compare against original-binary speed.

## Develop

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 tools/build_site.py
python3 -m http.server 8765 --directory dist
```

Open `http://localhost:8765`. Python 3.11+ is required. The core has no third-party dependencies. Reference
fixtures include source scripts, original outputs reduced to defined physical
fields, hashes, and the reference revision. Regenerate with:

```sh
python3 tools/capture_reference.py --reference ~/github/asitic-re
python3 tools/capture_analysis.py --reference ~/github/asitic-re
python3 tools/capture_transformer3d.py --reference ~/github/asitic-re
python3 tools/capture_potential.py --reference ~/github/asitic-re
python3 tools/capture_network.py --reference ~/github/asitic-re
python3 tools/capture_quadrature.py --reference ~/github/asitic-re
python3 tools/capture_green.py --reference ~/github/asitic-re
python3 tools/capture_oscillatory.py --reference ~/github/asitic-re
python3 tools/capture_pi_models.py --reference ~/github/asitic-re
python3 tools/capture_green_integration.py --reference ~/github/asitic-re
python3 tools/capture_eddy.py --reference ~/github/asitic-re
python3 tools/capture_network.py --reference ~/github/asitic-re --eddy
python3 tools/capture_pi_models.py --reference ~/github/asitic-re --eddy
python3 tools/capture_resonance.py --reference ~/github/asitic-re
python3 tools/capture_resonance_physical.py --reference ~/github/asitic-re
python3 tools/capture_extended_nodes.py --reference ~/github/asitic-re
python3 tools/capture_symmetric.py --reference ~/github/asitic-re
python3 tools/capture_parallel.py --reference ~/github/asitic-re
python3 tools/capture_pix.py --reference ~/github/asitic-re
```

Install `gdstk==1.0.2` to enable the independent GDS reader tests. CI runs those
tests and the same source archive inside the pinned WebAssembly runtime before
deploying to Pages. No external simulation service is required.

The Pages workflow runs eight disjoint Python core groups, every native potential-reference
process/frequency group, and fifteen WebAssembly groups in parallel. FFT/CAP and
SELFRES checks print case progress. Fixture-derived grouping keeps all native
cases covered. The build plan checks that every discovered core test occurs
exactly once; each runner verifies its planned test-ID digest before execution.
Deployment waits for every group. A validated commit on the current main
history can advance the published site while newer commits are still checking.
The publication guard rejects builds older than the version already published;
active validation is retained when another commit is pushed.

Python API:

WIRE uses ordinary degrees and unsnapped binary64 dimensions by default.
`build("wire", native_keyword=True, ...)` applies the original command parser,
including its 0.1 µm grid. `native_interactive=True` instead preserves the original
interactive WIRE quirk: its orientation prompt stores the supplied value directly
as radians, despite labeling it as degrees. The two modes are mutually exclusive.
New webpage wires and ground/pad strips use keyword mode. Saved projects retain
their mode until regenerated; loaded interactive projects show the angle notice.

Square and ring creation preserve the original retained coordinate arithmetic,
including origin stores and translation after square rotation. Exact gates
cover 126 original squares / 14,742 XYZ stores, full binary64 interactive
dimensions, near-quarter keyword turns, exit vias and independent GDS readback.
Four additional original square Pi2 sessions match every Y/model/S/resonance
store, including reversed phase and eddy correction.

Ring creation also preserves its original retained vertex arithmetic, including
its final endpoint spill and recentering. New webpage rings also use ASITIC's
keyword parsing and default 0.1 µm snap grid. Python can select that boundary
with `build("ring", native_keyword=True, ...)` or the corresponding square
call; JSON requests use the same top-level flag. New webpage squares also
select this mode. Ordinary typed calls retain unsnapped binary64 dimensions.
The exact gate covers 45 original creators / 12,588 XY stores and three complete
original Pi2 sessions, including eddy correction and finite resonance results.

The webpage's GHz inputs follow the original command parser: read a double,
multiply by 1e9 with retained precision, then store binary32 Hz. For example,
`0.1234567` GHz is solved at `123456704` Hz. Plots and CSV exports use the
computed frequency. JSON requests can select this boundary with
`frequency_ghz` (or `first_ghz` / `last_ghz` / `step_ghz` for searches);
these fields take precedence over their Hz counterparts. Typed Python solver
arguments and JSON `*_hz` fields preserve their existing binary64 SI behavior.

```python
from reasitic import Technology, build, inductance_estimate, resistance_hf, write_gds
from pathlib import Path

tech = Technology.default()
coil = build("square", technology=tech, length=100, width=5,
             spacing=2, turns=2.5, metal="M5", exit_metal="M4")
print(inductance_estimate(coil, tech))  # nH, original INDUCTANCE estimate
print(resistance_hf(coil, tech, 2e9))  # ohms
Path("coil.gds").write_bytes(write_gds(coil, tech))

from reasitic import solve_pi2
model = solve_pi2(coil, tech, 2e9, length_cell=50, width_cell=3,
                  thickness_cell=.5)
print(model["pi"])  # SI units; eddy currents disabled

from reasitic import solve_self_resonance
ground = build("wire", technology=tech, length=160, width=10, metal="M1", y=150)
search = solve_self_resonance(coil, tech, 1e9, 100e9, .1e9, ground=ground)
print(search["frequency_hz"], search["reason"])

from reasitic import build_device, solve_transformer
# Resolve the 3 µm contacts on a 2 µm FFT grid.
tech.chip.update(chipx=128, chipy=128, fftx=64, ffty=64)
primary, secondary = build_device(
    "transformer", technology=tech, length=80, height=70, width=3,
    spacing=2, turns=1.25, secondary_turns=1, metal="M4",
    exit_metal="M3", x=10, y=10)
coupled = solve_transformer(primary, secondary, tech, 1e9)
print(coupled["model"])  # SI units; native CALCTRANS port/sign convention
```

`python -m reasitic request.json` runs the same JSON interface used by the worker;
add `--gds coil.gds` to export a layout request. See `src/reasitic/bridge.py`.

## Remaining scope

The full objective includes geometry editing/session commands;
broader substrate eddy-current and coupled-device validation; multiport
networks; optimization. Work will be validated against the reference
one connected path at a time. No fitted spiral-inductance formula is substituted
for the original electromagnetic solver.

Pi2's resonance value is an estimate from the model at the chosen frequency.
`SELFRES SLOW` instead repeats network solves, following the native search. It
does not verify endpoint signs, so a resolution-based stop is not independent
proof of resonance. Native S conversion preserves an
ASITIC first-diagonal quirk for asymmetric devices; see the fidelity notes.

See [PORTING.md](PORTING.md) for the source mapping and validation boundary.
