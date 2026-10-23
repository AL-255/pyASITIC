# Source mapping and verification

Reference checkout: `~/github/asitic-re`, revision recorded in each fixture.

| Python | C++ source under `recomp_cpp/src/` | Current evidence |
| --- | --- | --- |
| `geometry.py`, `model.py` | `shape_construction.cpp`, `spiral_construction.cpp`, `winding_construction.cpp`, `composite_geometry.cpp` | Original SAVE records for seven creator families, coordinates/layer/width and DC reports |
| `technology.py` | `technology_text.cpp`, `technology_records.cpp` | Sample CMOS technology; additional technology variants remain to validate |
| `resistance.py` | `resistance.cpp` | Original DC reports for seven families; high-frequency tests pending |
| `gds.py` | Native ribbon and `layout_export.cpp` via pitch conventions | New export format; GDSII validation pending |

The fixture tolerance is 5.1e-7 µm, covering only the rounding of six decimal
places in native SAVE output. It is not a geometry approximation tolerance.
SAVE's uninitialized via thickness, ordinary NX/NY and ring N are excluded.
Native keyword input rounds numbers and angles to binary32; the direct Python
API accepts binary64 values. Tests account for that boundary explicitly.

Native ring and polygon builders ignore PHASE in the referenced source; this is
preserved. Square exit segments retain the winding's thickness, even when the
exit metal has a different thickness. Multi-metal construction in the reference
does not automatically insert vias between stacked windings; this is preserved.

Outstanding validation: rotated/fractional/negative-phase variants, live source
comparisons, arbitrary technology files, all high-frequency resistance branches,
GDSII round-trip through an independent reader and browser execution.
