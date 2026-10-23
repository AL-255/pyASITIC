# reASITIC

Python reconstruction of ASITIC, with a static browser application for GitHub
Pages. The reference is [`AL-255/asitic-re`](https://github.com/AL-255/asitic-re),
specifically its `recomp_cpp` reconstruction. This repository implements the
algorithms in Python; it does not invoke the reference executable at runtime.

This is an active port, **not yet a complete replacement** for ASITIC.

Implemented so far:

- Square and polygon spirals, wires, polygon rings, capacitors, via arrays,
  and multi-metal square windings, preserving native ribbon edge records.
- `.tek` technology loading, conductor DC resistance and the original empirical
  high-frequency resistance model, including parallel via counts.
- GDSII export with actual via cuts and metal landing pads. Default mapping:
  metal index + 1, via index + 100; datatype 0. Python callers can override it.
  Units are micrometres, with a 1 nm export grid.

Python arithmetic is binary64; the reference retains x87 extended intermediates.
Bitwise numerical equality is not claimed. Original saved geometry fixtures are
compared at their 6-decimal printed precision (0.51 nm / 1000).
Foundry design rules and layer mapping must come from the user's process.

## Develop

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Python 3.11+ is required. The core has no third-party dependencies. Reference
fixtures include source scripts, original outputs reduced to defined physical
fields, hashes, and the reference revision. Regenerate with:

```sh
python3 tools/capture_reference.py --reference ~/github/asitic-re
```

## Remaining scope

The full objective includes symmetric square/polygon coils, planar/3D/mirror
transformers and baluns; geometry editing/session commands; filament impedance
and substrate eddy/capacitance algorithms; network, transformer and port metrics;
frequency sweeps and optimization. Work will be validated against the reference
one connected path at a time. No fitted spiral-inductance formula is substituted
for the original electromagnetic solver.

See [PORTING.md](PORTING.md) for the source mapping and validation boundary.
