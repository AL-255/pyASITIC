# Source mapping and verification

Reference checkout: `~/github/asitic-re`, revision recorded in each fixture.

| Python | C++ source under `recomp_cpp/src/` | Current evidence |
| --- | --- | --- |
| `geometry.py`, `model.py`, `symmetric_geometry.py` | `shape_construction.cpp`, `spiral_construction.cpp`, `winding_construction.cpp`, `composite_geometry.cpp`, `symmetric_construction.cpp` | Original SAVE records for nine creator families, coordinates/layer/width and DC reports |
| `devices.py` | `winding_construction.cpp`, `shape_prompt_transformer.cpp`, `console_geometry.cpp` | Original SAVE records and DC reports for both planar transformer and balun windings; independent combined GDS round-trip |
| `transformer3d.py` | `transformer3d.cpp`, `shape_creation_mirror.cpp` | Original SAVE/DC fixture plus seven live C++ creator sessions, including fractional turns, phase/orientation metadata and different metal thicknesses; 14 full winding LMAT matrices in CPython/WebAssembly |
| `technology.py` | `technology_text.cpp`, `technology_records.cpp` | Sample CMOS technology; additional technology variants remain to validate |
| `resistance.py` | `resistance.cpp` | Original DC reports for nine families; twelve live C++ cases at five frequencies (1 MHz–100 GHz) |
| `inductance.py` | `analysis_commands.cpp`, `segment.cpp`, `canonicalize.cpp`, `intersection.cpp`, `parallel.cpp`, `separation.cpp`, `planar.cpp`, `spatial.cpp` | Twelve live C++ INDUCTANCE command reports, including symmetric, nonparallel, stacked and via geometry |
| `solver.py` | `geometry.cpp`, `filament_setup.cpp`, `filaments.cpp`, `impedance.cpp`, `vias.cpp`, `solver.cpp` | 24 complete C++ LMAT matrices, coarse 1 GHz and refined 2 GHz, within 1e-8 Ω per component in both CPython and WebAssembly |
| `gds.py` | Native ribbon and `layout_export.cpp` via pitch conventions | Independent gdstk round-trip for nine generators, units, coordinates, layer mapping, via counts and cut area |
| `bridge.py`, `web/worker.js` | New browser interface | Generation, estimates, sweeps and exports exercised in pinned Pyodide WebAssembly runtime |

All twelve creator IDs in the reference's creator process suite now have Python
implementations and original saved-geometry fixtures. This is a creator-surface
milestone, not a claim of universal geometry or electrical parity. The fixture
tolerance is 5.1e-7 µm, covering only the rounding of six decimal
places in native SAVE output. It is not a geometry approximation tolerance.
SAVE's uninitialized via thickness, ordinary NX/NY and ring N are excluded.
Native keyword input rounds numbers and angles to binary32; the direct Python
API accepts binary64 values. Tests account for that boundary explicitly.

Native ring and polygon builders ignore PHASE in the referenced source; this is
preserved. Square exit segments retain the winding's thickness, even when the
exit metal has a different thickness. Multi-metal construction in the reference
does not automatically insert vias between stacked windings; this is preserved.
Symmetric polygon construction starts from the reference console's zeroed
`polygon_metal` history; the first crossover can therefore use the primary metal.
Symmetric coils quantize to whole turns; symmetric polygon side counts are even.

The original INDUCTANCE estimate is distinct from the frequency-dependent
filament solver behind LMAT and PI2. The LMAT path now assembles and reduces the
full no-eddy filament impedance matrix. Its dense complex inverse uses partial
pivoting in binary64 rather than the original i386 LAPACK symmetric factorization.
The case selector's extended-precision 5000-unit translation is reproduced with
exact rational rounding to a 64-bit binary significand. Rounding both translated
endpoints to binary64 caused large errors in some refined meshes; the matrix
fixtures catch that regression.

The current web app labels its estimate Q value as
QLF (the native DC-loss extrapolation), not network quality or HF Q. Inductance
does not change with frequency in estimate mode. LMAT's separate series Q is
Im(sum Z)/Re(sum Z). Eddy currents, substrate loss,
capacitance and resonances are not yet included.

Outstanding validation: broader rotated/fractional/negative-phase geometry
fixtures, arbitrary technology files, segment-kernel precision fixtures, real
browser interaction and rendered layout checks. The current environment has no
browser connection; WebAssembly runtime execution is tested separately from UI.
The adaptive edge mesh branch is ported but still needs native fixtures. Its
original sqrt(dot) normalization can be invalid for some coordinates; Python
reports that failure explicitly. Current LMAT supports one series shape without
shunt-segment groups and caps the browser matrix at 256 filaments.

Paired devices keep separate electrical shapes. The layout shows both windings,
the winding picker selects the shape used by estimates/LMAT, and GDS contains
both. The coupling button uses the original estimate path; the full transformer
network analysis remains pending.

`3DTrans`, `3DMIRRORTRANS`, `Trans3D` and `TransMIM` are aliases of creator ID 10,
not separate generator algorithms. The 3D builder is generated into standalone
Python by `tools/port_transformer3d.py`, with explicit 64-bit-significand rational
arithmetic for the recovered extended operations. It does not load C++ or the
reference executable at runtime. Emission order, strict fractional-turn loops,
asymmetric terminal placement, and retained thickness fields are preserved.
The original builder records orientation/phase metadata without transforming
the segments; the UI reports this when non-default metadata is supplied.
3D terminals also retain distinct primary-block width/thickness fields used by
the mutual kernel, separate from the scalar width used by RESIS and LMAT mesh
setup. Fractional-turn reference sessions detect the missing-field regression.
