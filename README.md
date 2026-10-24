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
  high-frequency resistance model, including parallel via counts.
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
- `LMAT` filament solver with longitudinal and cross-section meshing,
  impedance assembly, inversion/reduction and via corrections. The web app
  displays L, R, series Q and the complex matrix, with full matrix CSV download.
  Uses the original symmetric factor/inverse and retained parallel mutual kernels.
  The browser's compiled matrix path is checked bit for bit against original
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
  Direct original captures check 165 retained Green returns, every callback
  point and 19 complete matrix stamps exactly. Another 3,532 original Green/
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
  Retained compiled Green-table generation is checked against 33 complete
  original-binary tables through 256×256, with separate native coefficient and
  regional-transfer checks.
- Distributed `PI2` / `PI3` two-port models with optional native eddy correction: combines CAP
  and filament admittance through the original node equations. Reports series
  L/R, two RC shunts, port/differential Q, input impedances, shunt resistance,
  narrowband resonance estimate and native 50 Ω Y/S output, with JSON/CSV export.
  The compiled folded-node stage matches 54 original-binary cases at identical
  CAP/inductive inputs, including 256 nodes and all 15 finite coupled sessions.
  `PI3` requires an explicit reference; `PI4` solves with two pad strips and
  subtracts their capacitive contribution using the original de-embedding path.
  Pi metrics, ZIN and S conversion preserve every retained operation and store
  in both Python and WebAssembly: 3,435 original records check 96,180 binary64
  outputs and 6,673 finite retained returns. Pi3 preserves its ordinary reference
  mesh, distinct from Pi2's forced reference mesh. All 41 captured complete
  original Pi sessions match every finite Y/model/S output and resonance value.
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
  3–32 sides and positive/negative rotations. Longitudinal meshing preserves
  the original copy branch and independently normalized ribbon edges.
- Browser preview, pan/zoom, process-file import, project save/open, conductor
  estimates, selectable L/R/Q frequency plots, linear/log frequency scales,
  progressive Pi2/Pi3/Pi4 sweeps, sample-to-circuit inspection, plot SVG and CSV
  download. Python runs in a
  module worker using pinned Pyodide 314.0.7; the runtime loads from jsDelivr.
- Shared mesh settings with coarse/balanced/fine presets, custom conductor and
  CAP cells, and a filament-count check before electrical solves. “Fit to 256
  filaments” explicitly coarsens conductor cells while preserving CAP cell
  settings. Counts include Pi4 pads or both CALCTRANS windings as selected;
  project downloads preserve all five cell sizes.

Records use binary64 with selected retained-precision intermediates matching the
reference's x87 arithmetic.
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

The Pages workflow runs four disjoint Python core groups, every native potential-reference
process/frequency group, and fifteen WebAssembly groups in parallel. FFT/CAP and
SELFRES checks print case progress. Fixture-derived grouping keeps all native
cases covered. The build plan checks that every discovered core test occurs
exactly once; each runner verifies its planned test-ID digest before execution.
Deployment waits for every group and publishes only the current
main commit. Active validation is retained when another commit is pushed.

Python API:

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
