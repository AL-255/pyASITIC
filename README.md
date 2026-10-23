# pyASITIC

Python reconstruction of ASITIC, with a static browser application for GitHub
Pages. The reference is [`AL-255/asitic-re`](https://github.com/AL-255/asitic-re),
specifically its `recomp_cpp` reconstruction. This repository implements the
algorithms through a Python API; it does not invoke the reference executable at
runtime. The browser accelerates retained FFT, spectral math, contact potentials and matrix
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
- `LMAT` filament solver with longitudinal and cross-section meshing,
  impedance assembly, inversion/reduction and via corrections. The web app
  displays L, R, series Q and the complex matrix, with full matrix CSV download.
  Uses the original symmetric factor/inverse and retained parallel mutual kernels.
  The browser's compiled matrix path is checked bit for bit against original
  factors/inverses, including 128- and 256-entry systems.
- Optional native `EDDY ON` substrate correction, including square packing,
  segment folding, layered Green integration and convergence diagnostics.
  Preserves native negative-resistance results and reports nonfinite failures.
- Original layered-substrate `CAP` solver: contact discretization, layered
  spectral Green functions, reflected FFT tables, potential-matrix inversion,
  and admittance reduction. Includes explicit ground winding selection, total
  capacitance, substrate equivalent resistance and admittance CSV download.
  Compiled contact arithmetic matches 41 original-binary matrices exactly at
  finite output boundaries, including complete 256-contact systems.
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
  `PI3` requires an explicit reference; `PI4` solves with two pad strips and
  subtracts their capacitive contribution using the original de-embedding path.
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
- GDSII export with actual via cuts and metal landing pads. Default mapping:
  metal index + 1, via index + 100; datatype 0. GF180 presets supply their drawn
  layer numbers. Python/JSON callers can override the mapping.
  Units are micrometres, with a 1 nm export grid.
- Browser preview, pan/zoom, process-file import, project save/open, conductor
  estimates, selectable L/R/Q frequency plots, linear/log frequency scales,
  progressive Pi2/Pi3/Pi4 sweeps, sample-to-circuit inspection, plot SVG and CSV
  download. Python runs in a
  module worker using pinned Pyodide 314.0.7; the runtime loads from jsDelivr.

Records use binary64 with selected retained-precision intermediates matching the
reference's x87 arithmetic.
Bitwise numerical equality is not claimed. Original saved geometry fixtures are
compared at their 6-decimal printed precision (5.1e-7 µm).
Foundry design rules and layer mapping must come from the user's process.

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

The Pages workflow runs Python core checks, every native potential-reference
process/frequency group, and eleven WebAssembly groups in parallel. FFT/CAP and
SELFRES checks print case progress. Fixture-derived grouping keeps all native
cases covered; deployment waits for every group and publishes only the current
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
