# reASITIC

Python reconstruction of ASITIC, with a static browser application for GitHub
Pages. The reference is [`AL-255/asitic-re`](https://github.com/AL-255/asitic-re),
specifically its `recomp_cpp` reconstruction. This repository implements the
algorithms in Python; it does not invoke the reference executable at runtime.

**[Open the workbench](https://al-255.github.io/reASITIC/)**

This is an active port, **not yet a complete replacement** for ASITIC.

Implemented so far:

- Square, polygon and symmetric square/polygon spirals, wires, polygon rings, capacitors, via arrays,
  and multi-metal square windings, preserving native ribbon edge records.
- Planar transformers, 3D mirror transformers, and baluns with separate winding records, winding
  selection for electrical analysis, and combined GDS export.
- `.tek` technology loading, conductor DC resistance and the original empirical
  high-frequency resistance model, including parallel via counts.
- Original `Inductance` and `Coupling` estimate algorithms: segment self terms,
  signed parallel, planar and spatial mutual-inductance cases.
- No-eddy `LMAT` filament solver with longitudinal and cross-section meshing,
  impedance assembly, inversion/reduction and via corrections. The web app
  displays L, R, series Q and the complex matrix, with full matrix CSV download.
- GDSII export with actual via cuts and metal landing pads. Default mapping:
  metal index + 1, via index + 100; datatype 0. Python callers can override it.
  Units are micrometres, with a 1 nm export grid.
- Browser preview, pan/zoom, process-file import, project save/open, conductor
  estimates, logarithmic frequency sweeps and CSV download. Python runs in a
  module worker using pinned Pyodide 314.0.7; the runtime loads from jsDelivr.

Python arithmetic is binary64; the reference retains x87 extended intermediates.
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
```

Install `gdstk==1.0.2` to enable the independent GDS reader tests. CI runs those
tests and the same source archive inside the pinned WebAssembly runtime before
deploying to Pages. No external simulation service is required.

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
```

`python -m reasitic request.json` runs the same JSON interface used by the worker;
add `--gds coil.gds` to export a layout request. See `src/reasitic/bridge.py`.

## Remaining scope

The full objective includes geometry editing/session commands;
substrate eddy/capacitance algorithms; network, transformer and port metrics;
EM frequency sweeps and optimization. Work will be validated against the reference
one connected path at a time. No fitted spiral-inductance formula is substituted
for the original electromagnetic solver.

See [PORTING.md](PORTING.md) for the source mapping and validation boundary.
