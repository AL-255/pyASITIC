# Source mapping and verification

Reference checkout: `~/github/asitic-re`, revision recorded in each fixture.

| Python | C++ source under `recomp_cpp/src/` | Current evidence |
| --- | --- | --- |
| `geometry.py`, `model.py`, `symmetric_geometry.py` | `shape_construction.cpp`, `spiral_construction.cpp`, `winding_construction.cpp`, `composite_geometry.cpp`, `symmetric_construction.cpp` | Original SAVE records for nine creator families, coordinates/layer/width and DC reports |
| `devices.py` | `winding_construction.cpp`, `shape_prompt_transformer.cpp`, `console_geometry.cpp` | Original SAVE records and DC reports for both planar transformer and balun windings; independent combined GDS round-trip |
| `transformer3d.py` | `transformer3d.cpp`, `shape_creation_mirror.cpp` | Original SAVE/DC fixture plus seven live C++ creator sessions, including fractional turns, phase/orientation metadata and different metal thicknesses; 14 full winding LMAT matrices in CPython/WebAssembly |
| `precision.py` | `shape_construction.cpp` point/shape rotation | Retained radius/angle arithmetic, asymmetric cosine/sine angle spills, and native midpoint evaluation; exact rotated-wire endpoint doubles from BSAVE and matching unequal-cell mesh dimensions in CPython/WebAssembly |
| `filament.py`, `native/filament.cpp` | `filaments.cpp`, `numerics.cpp`; original `0x0806597c` | 2,220 intact original records / 19,980 exact finite components or nonfinite classifications in Python and compiled WebAssembly; all adaptive edge branches, arbitrary interpolation indices, asymmetric spills, destination Z preservation, signed zeros and extreme scales |
| `mesh.py`, `web/app.js` | Native longitudinal subdivision and filament counts from `geometry.cpp`, `filament_setup.cpp` | Exact production-count reuse, Pi4 pad and explicit CALCTRANS winding mesh conventions; actual DOM reproduces 360-filament rejection, fits to 60 and successfully solves Pi2; presets, invalidation and project persistence |
| `technology.py` | `technology_text.cpp`, `technology_records.cpp` | Original coordinate-height words from 41 actual CLI sessions across CMOS/BiCMOS/GF180; retained cumulative depths, separate nominal bottom distance and two-store geometry heights; broader reader commands remain to validate |
| `resistance.py` | `resistance.cpp` | Original DC reports for nine families; twelve live C++ cases at five frequencies (1 MHz–100 GHz) |
| `inductance.py` | `analysis_commands.cpp`, `segment.cpp`, `canonicalize.cpp`, `intersection.cpp`, `parallel.cpp`, `separation.cpp`, `planar.cpp`, `spatial.cpp` | Twelve live C++ INDUCTANCE command reports, including symmetric, nonparallel, stacked and via geometry |
| `solver.py` | `geometry.cpp`, `filament_setup.cpp`, `filaments.cpp`, `impedance.cpp`, `vias.cpp`, `solver.cpp` | 36 complete C++ LMAT matrices: coarse 1 GHz, refined 2 GHz, and unequal inductive/capacitive length cells; within 1e-8 Ω per component in CPython and WebAssembly |
| `impedance.py`, `native/impedance.cpp` | `impedance.cpp`, `geometry.cpp` | 23 actual original complete upper matrices / 4,648 exact components, 2,094 original mesh-pair outputs, immutable input and symmetric reconstruction checks; actual original longitudinal clone fields including refined polygons |
| `polygon.py`, `native/polygon.cpp` | `spiral_construction.cpp`, `shape_construction.cpp` | 42 actual original creator calls / 12,288 raw XY stores exact in portable Python and compiled WebAssembly; fractional turns, 3–32 sides, positive/negative rotations and production inputs |
| `ring.py`, `geometry.py`, `command_numbers.py` | `winding_construction.cpp`, `command_runtime.cpp`; original ring `0x0805b450` | 45 original creators / 12,588 exact XY stores in Python and WebAssembly; full keyword/default snap inputs, 3–128 sides, gap/orientation boundaries; three complete original Pi2 Y/model/S/resonance sessions including eddy; independent GDS readback and actual form/project/model/export handlers |
| `geometry.py` square/via emission, `model.py`, `precision.py` | `spiral_construction.cpp`, `shape_construction.cpp`, `geometry.cpp`; original square `0x08056670` | 126 complete original creators / 14,742 exact XYZ stores plus origins, widths, metal/thickness and defined via counts; keyword/interactive inputs, quarter-turn boundaries, rotations, reverse phase and exits; four complete original Pi2 electrical sessions and independent GDS readback |
| `symmetric_geometry.py`, `native/symmetric_geometry.cpp`, symmetric keyword inputs | `symmetric_construction.cpp`, `shape_prompt_symmetric.cpp`; original square `0x08059854` / polygon `0x0805a45c` | 114 original creators / 60,804 exact XYZ stores plus origins/widths/metals/thickness/via counts; whole-turn and maximum-turn cases, rotations, integer phase, odd/fractional sides, crossover history, defaults and binary64 interactive construction; eight complete Pi2/2PORT sessions, independent GDS and actual form/project/download checks in both runtimes |
| `geometry.py` multi-metal stacking and keyword input | `composite_geometry.cpp`, shared square/reflect/translate/parser sources; original `0x0805af5c` | 180 original creators / 56,214 exact XYZ stores plus origin/width/metal/thickness; fractional and maximum turns, two to five metals, rotations, phase, defaults and binary64 interactive construction; independent GDS, four full Pi2/2PORT sessions, three invalid stack transcripts and actual form/project/export handlers in Python/Pyodide |
| `geometry.py` capacitor/VIA modes, `web/app.js` numeric input serialization | `console_geometry.cpp`, `shape_construction.cpp`, `shape_prompts.cpp`, `shape_creation_primitives.cpp`, `command_runtime.cpp`; original wire `0x08057998`, via `0x08057b78`, join `0x08078890` | 84 original creators / 2,520 exact XYZ stores and origin bits; plate dimension/default/metal/rotation modes, interactive VIA counts/phase/retries and independent GDS cuts; four complete capacitor Pi2/2PORT sessions and 32 raw via resistance returns in both runtimes; 64 native VIA keyword rejections and the standalone Pi2 fault retained |
| `contact_geometry.py`, `potential.py` | `contacts.cpp`; original preparation `0x08053580` / builder `0x08053a1c` | 50 original setups / 280 builder calls / 338 physical-bound and integer-grid records in Python and WebAssembly; retained placement, native counts/order, parser-forced reference mesh and original thin-wire grid/zero-area histories |
| `potential.py` | `potential_tables.cpp`, `potential.cpp`, `contacts.cpp`, `potential_solver.cpp` | Eight CAP sessions across CMOS/BiCMOS: full potential snapshots, folded admittance matrices, and actual cache FFT samples for every metal pair; browser runtime checks cover all eight reduced matrices |
| `contact_math.py`, `native/contact.cpp` | Original `0x080901c0`; `potential.cpp`, legacy complex DSO | All 41 captured contact matrices / 264,844 components exact in Python and WebAssembly: finite bits including signed zeros, nonfinite classes and both complete 256-contact digests; input table hashes and metadata immutability; ordered zero-term reuse checked across process/frequency edits |
| `fft.py`, `native/fft.c` | Original machine-code routine at `0x080912c0`; `potential_tables.cpp` | 83 direct original-binary FFT/reflected-grid cases, 17,342 bit-identical binary64 output components including signed zeros/subnormals, verified in Python and compiled WebAssembly; pinned compiler reproduces the module byte for byte |
| `x87_math.py`, `native/fft.c` | Original clipped cosh at `0x0809123c`, tanh through transfer-up at `0x0808f004`; `potential_tables.cpp` | 20,014 direct original-binary scalar cases match bit for bit in Python and compiled WebAssembly; retained argument formation and exponent reduction fix the grounded-wire raw-potential reference without widening tolerance |
| `network.py` | `combined_network.cpp`, `node_equations.cpp`, `network.cpp`, `two_port_output.cpp` | Eight no-eddy PI2 sessions: CAP/inductive/nodal snapshots, 15-digit Y/S output, printed L/R/C/Q/shunt-R/resonance reports; isolated node/S checks and JSON/WebAssembly interfaces |
| `network_metrics.py`, `retained_scalar.py`, `native/network*.cpp` | `network.cpp`, `two_port_output.cpp` | 3,435 intact-original records / 96,180 binary64 output components and 6,673 finite retained returns match exactly in portable Python and compiled WebAssembly; signed zeros/nonfinite classes, independent models, all ZIN modes and S conversion; operation isolation and caller immutability |
| `network.py` Pi3/Pi4 | `analysis_dispatch.cpp`, `extended_analysis.cpp`, `composite_geometry.cpp` | Eight more wire/square PI3/PI4 sessions at 1/5 GHz, including precise native 2PORT/2PORTPAD Y/S records, printed Q, explicit ground, pad mesh sentinels, and distinct-origin wire/spiral joins |
| `transformer.py`, `native/transformer.cpp` | `later_analysis.cpp`, `console_analysis.cpp`; original inverse `0x0808800c`, model `0x08089cb0`, folded nodes `0x08053e00` | 67 direct original-executable extraction cases / 1,541 exact finite output components or nonfinite classifications; 15 finite original CALCTRANS/2PORTTRANS sessions plus six original nonfinite histories; omitted/explicit references, termination boundary, swapped windings, eddy correction, and actual coupled-model/sweep/export DOM handlers |
| `web/analysis-views.mjs`, `web/app.js` | New static plotting/circuit interface | Selectable L/R/Q plots, log/linear sampling, curve gaps for undefined values, point-to-circuit inspection, Pi-family diagrams, ground/pad controls, SVG/CSV/JSON exports; pure-view checks and rendered SVG visual inspection |
| `quadrature.py` | `quadrature.cpp` | DQK15I transformed rule, DQPSRT ranking, DQELG epsilon extrapolation and DQAGIE adaptive infinite integration; direct 32-bit C++ probe covers 60 integrations and 36 rules, including convergence/failure statuses and exact evaluation/subdivision counts |
| `green.py` | `green.cpp`, `legacy_complex.cpp` | 186 direct 32-bit C++ object probes: propagation constants, complex tanh, reflection, layered/limiting integrands, oscillating/reflection kernels; realistic and extreme conductivities, zero frequency/wave number, decay cutoff and native nonfinite classifications |
| `oscillatory.py` | `oscillatory.cpp` | Native DQK15W/DQCHEB/DGTSL/DQC25F/DQAWOE/DQAWFE: 176 oscillatory rules, 88 weighted rules, 4 Chebyshev transforms, 8 pivoted tridiagonal cases, 168 adaptive integrals and 80 Fourier runs with per-cycle values/statuses and extrapolation history |
| `green_integration.py` | `green_integration.cpp` | 58 complete integrations: native selector boundaries, warm-up callbacks, final scaling, partial statuses and retained Fourier history |
| `eddy.py`, `solver.py` | `eddy.cpp`, `solver.cpp` | 16 EDDY ON LMAT matrices across CMOS/BiCMOS wire, square, polygon and via-exit cases; coarse/refined meshes and square Eddy.out snapshots |
| `network.py` eddy integration | `combined_network.cpp`, `extended_analysis.cpp` | Eight additional PI2 and eight PI3/PI4 sessions with EDDY ON, compared using native precise Y/S outputs and printed metrics |
| `resonance.py` | `analysis_commands.cpp`, `network.cpp` | 184 direct native search traces and 12 complete SELFRES SLOW sessions: reversed bounds, differential excitation, native device reference, refined unequal meshes, CMOS/BiCMOS, joined capacitor geometry and layered eddy correction; streamed JSON/WebAssembly progress |
| `extended.py`, `linear.py` | `extended_node.cpp`, `extended_twoport.cpp`, `general.cpp`, `node_equations.cpp` | 68 native extended-node cases, including noncontiguous native strides, exact finite column stamps and systems beyond the 64-column LU panel boundary |
| `symmetric.py`, `native/matrix_*.cpp`, `native/soft_real.hpp` | Original ZSYTF2 `0x0809bcf8` / ZSYTRI `0x08095bf8`; `symmetric.cpp`, `complex.cpp`, `blocked.cpp` | 44 directly verified original factor/inverse cases, exact Python/compiled pivots and output bits, tiny/huge scales, signed zeros, partial singularity; complete original factor/inverse digests for 128/256-entry systems including two-entry pivots; four original dense Pi2 sessions at 189 filaments / 63 contacts; six separate C++-reference eigen rotations retain component checks |
| `parallel.py`, `solver.py` | `parallel.cpp`, `separation.cpp`, `numerics.cpp`, `impedance.cpp` | 175 native self-integral/cross-section/separation/parallel/full-segment probes; retained filament self-impedance diagonals in complete PiX sessions |
| `mutual_geometry.py`, `mutual_kernel.py`, `native/mutual*.cpp`, `native/retained_math.cpp` | `segment.cpp`, `canonicalize.cpp`, `intersection.cpp`, `parallel.cpp`, `separation.cpp`, `numerics.cpp`, `planar.cpp`, `spatial.cpp`, `x87.hpp` | 2,561 intact original scalar/pair outputs, including 426 independently captured threshold/degeneracy cases; exact Python and compiled binary64 outputs, statuses and warning presence; 2,094 actual original mesh pairs feed 23 exact complete upper assemblies; 2,683 separately labeled compiled native-instruction stores; twelve finite eddy-off and three eddy-on coupled sessions exact at raw SI output boundaries |
| `extended.py` PiX pipeline | `potential_solver.cpp`, `extended_twoport.cpp`, `extended_node.cpp`, `console_analysis.cpp` | Ten complete PIX sessions across CMOS/BiCMOS, wires, square/polygon coils, vias, joined capacitors and multimetal windings; unfolded CAP, final LMAT, node vectors, full-precision Pi/ZIN reports, direct port Y for all ten and six native 2PORTX Y/S exports |
| `gds.py` | Native ribbon and `layout_export.cpp` via pitch conventions | Independent gdstk round-trip for nine generators, units, coordinates, layer mapping, via counts and cut area |
| `bridge.py`, `web/worker.js` | New browser interface | Generation, estimates, sweeps and exports exercised in pinned Pyodide WebAssembly runtime |
| `presets.py`, `technologies/` | GF180MCU interconnect sections 2–4 and drawn layer/via specifications, revision de3240d | All 45 documented stacks / 73 `.tek` variants; nominal sheet resistance, independent drawing dimensions and MIM placement, three unmodified C++ distributed-network sessions, GDS readback, WebAssembly and actual process-selection DOM handlers; substrate and planar-model assumptions documented in `docs/GF180.md` |

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
full filament impedance matrix. Its inverse now follows the original upper
complex-symmetric factorization and inverse, including the n-cell workspace
that selects unblocked factorization, one/two-pivot paths and eigen rotations.
Full symmetric output is reconstructed from the native inverse's defined upper
triangle. Filament self terms retain length/log arithmetic until native stores,
and reduction accumulators spill each real/imaginary addition explicitly.
Python 3.14's compensated complex sum is deliberately avoided at that boundary.
The case selector's extended-precision 5000-unit translation is reproduced with
exact rational rounding to a 64-bit binary significand. Rounding both translated
endpoints to binary64 caused large errors in some refined meshes; the matrix
fixtures catch that regression.
The clone's native length threshold tests the smaller inductive/capacitive cell,
but its ceiling count divides by the inductive cell. Unequal-cell reference
matrices catch swapping those fields. The symmetric-polygon command fixture
also records the native default origin (radius + half transition gap), which
matters to the original translated-basis rounding in fine meshes.

The current web app labels its estimate Q value as
QLF (the native DC-loss extrapolation), not network quality or HF Q. Inductance
does not change with frequency in estimate mode. LMAT's separate series Q is
Im(sum Z)/Re(sum Z). CAP now computes layered-substrate capacitance and substrate
loss independently. Pi2 combines those two distributed solvers and reports the
original frequency-dependent network metrics. Native eddy correction is optional
for LMAT, Pi2/Pi3/Pi4/PiX and CALCTRANS. The fast Pi path and multiport networks
remain pending. SELFRES SLOW now repeats the distributed solver through the
original midpoint search.

The plotted sweep defaults to distributed Pi2. Estimate sweeps remain an explicit
selection. Starter geometry is placed at (100, 100) µm so its contacts resolve
inside the sample process. Browser workers require the compiled numerical module
to initialize; validation asserts that the backend is active. The portable Python
fallback and compiled path have separate exact kernel checks. See
[docs/PERFORMANCE.md](docs/PERFORMANCE.md) for timings and remaining bottlenecks.

Outstanding validation: broader rotated/fractional/negative-phase geometry
fixtures, arbitrary technology files, segment-kernel precision fixtures, real
browser interaction and rendered layout checks. The current environment has no
browser connection; WebAssembly runtime execution is tested separately from UI.
The adaptive edge mesh branches have direct original record fixtures; broader
complete electrical sessions using adaptive edge meshes remain to validate. Their
original sqrt(dot) normalization can be invalid for some coordinates; Python
reports that failure explicitly. Current LMAT supports one series shape without
shunt-segment groups and caps the browser matrix at 256 filaments.

Paired devices keep separate electrical shapes. The layout shows both windings,
the winding picker selects the shape used by estimates/LMAT, and GDS contains
both. The coupling button uses the original estimate path; the CALCTRANS panel
solves both windings together and displays the native coupled equivalent.

Pi2 clones the geometry once using the original inductive/capacitive length
thresholds, requests the filament solver's admittance mode, converts folded CAP
to nodal admittance, and solves the two native drive/bias experiments. Its
general node factorization follows the original general LU sequence, with the
retained compiled backend described below. End-to-end Y/S comparisons use max(1e-10,
1e-8 relative) per component; separate snapshot/node checks guard the stage
boundaries. Eight independent fixtures cover wires, square/polygon coils,
capacitor plates, multi-metal coils, via corrections, unequal cells, an explicit
ground wire, and CMOS/BiCMOS. Their 64 × 64 FFT on a 128 µm chip complements the
CAP fixtures' original 128 × 128 grids.

Public Y matrices and Pi RC shunts follow native output port order: public port 1
is the internal y22 node. Differential impedance retains the native reciprocal
y21-squared determinant. The native 50 Ω S conversion repeats y22 in both
factors of the first diagonal numerator; this changes s11 for asymmetric devices
and is deliberately preserved. The app and CSV label these as ASITIC S values.
Pi2 resonance is the native narrowband Pi formula, not a frequency search.
Undefined native metrics (for example differential shunt R for a one-segment
wire with a zero RC branch) are JSON null and appear as Undefined in the app.
Native printed Pi metrics have only three significant digits; full Y/S records
provide the stronger numerical comparisons. More devices, grounds with vias,
near-singular networks and process stacks remain to validate.

PI3 dispatch uses the same combined network backend as PI2, with a required
parser-type-0 reference. It preserves the reference's ordinary mesh counts;
Pi2's optional type-8 reference forces -1/-1. A later 2PORT command can therefore
have different Y inputs from the preceding Pi3 command. PI4 copies the two parser-type-8 pads (-1/-1 mesh counts),
clones the winding, joins the three structures, solves the combined network,
then subtracts the pad-only folded capacitance contribution before extracting
the Pi model. Native copied-segment order, coordinate translation and the
wire-target/square-or-polygon-source origin promotion are preserved. The API
also retains the native optional PI4 reference default (the original device),
which can make some overlapping-contact configurations singular. The UI offers
that reference and an explicit ground strip/other winding.

The supplied Linux fast PI implementation deliberately retains a native FLDCW
fault at 0xfffffffc before conductor block construction (`model.cpp`). It cannot
produce a finite conductor Pi model in the reference. The Pi circuit view
therefore shows the topology and this explicit limitation; it does not label
Pi2 values as fast PI output. Pi2/Pi3/Pi4 diagrams and sweeps use their respective
validated native paths. UI interactions still require a connected browser for
full verification; SVG plots/circuits are separately rendered and inspected.

PIX uses the original device-reference default, clone thresholds, unfolded CAP
principal reduction, impedance-mode LMAT and a (2n+2)-unknown system for segment
voltages/currents. Its LU follows native abs-one pivot ranking, 64-column panels,
rounded reciprocal/scaling and BLAS update order. Both off-diagonal ports are
retained separately. General CAP inversion and Pi2's node solve preserve their
native retained operations and stores, with independent original matrix/node
and complete electrical-session gates.

The direct node probes require exact finite half-column stamps, including
signed zero, and compare Y/current/voltage results at max(1e-12 absolute, 1e-10
relative). Symmetric factor/inverse and eigen probes use the same finite
tolerance and exact pivots. Parallel/separation elementary probes use 1e-12
relative down to 1e-300 absolute, with exact zero and rejection classifications.
Retained arithmetic uses Decimal guard precision and selected exact rational
rounding; full x87 exception flags and universal bitwise equality are not claimed.

Ten complete PIX sessions compare unfolded admittance at max(1e-16 S, 1e-8
relative), final segment impedance at max(1e-8 ohm, 1e-8 relative), current/voltage
vectors at max(1e-10 absolute, 1e-8 relative), and every Pi metric from full-precision
native formatter arguments. A cancellation-sensitive fine wire's RC shunt
required the original parallel/separation stores and symmetric inverse; its
comparison was retained while replacing the approximate arithmetic.

The CLI's snapshot dumper loops rows by rows even for one-column current/voltage
slices. Its underlying RHS allocation contains two solution columns. The output
tap retains those two allocated columns and derives the four native port values;
the undefined third and later columns are excluded. This supplies independent
Y comparisons for every PIX case. Native 2PORTX uses extended analysis only for
types 0,1,16,17,18. Wires and joined capacitor/multimetal structures use its Pi2
fallback, while PIX itself calls the extended backend for every type. The UI's
PiX sweep repeats PIX directly and does not substitute that 2PORTX fallback.

SELFRES retains the native ignored iteration-limit argument, hard 100 observed
samples / up to 101 analyses, strict 0.01-ohm reactance test, frequency-step
stop, reversed-bound ordering and native fast quantization arithmetic. The
controlled-callback probe compiles unmodified `analysis_commands.cpp` into
function sections to discard unrelated console commands, then links native
network/complex objects. Exact sample frequencies, counts and reported results
are checked across 184 cases, including the strict 0.01-ohm boundary, zero-step exhaustion and NaN impedance.
Finite progress values use max(1e-12 absolute, 1e-12 relative).

Twelve physical sessions compare the complete distributed search against the
unmodified CLI. A printf/sprintf tap records its already-computed progress and
reported frequency at full precision; it changes no numerical arguments or
solver algorithms. Input reactance uses max(1e-8 ohm, 1e-8 relative), and stopping
frequencies agree within 1e-10 GHz. Native command frequency arguments are
stored as binary32 **after conversion to hertz** (100 GHz becomes 99999997952
Hz); direct Python and JSON requests use binary64 hertz. The fixtures account
for this input boundary rather than weakening search comparisons.

The search assumes a suitable resonance interval; it does not evaluate endpoint
signs or guarantee a zero crossing. It can report the next midpoint without
evaluating it, so the API and UI retain the last actual model frequency. A
frequency-resolution stop is shown explicitly. The command's device-reference
default is preserved, alongside explicit grounds. The production binding uses
SLOW: fast conductor SELFRES invokes the same unavailable analytical path as
fast PI. Controlled fast-callback tests validate quantization only. Arbitrary
nonfinite frequency/step inputs, failed-network incoming-state histories and
all geometry/process combinations remain outside the evidence. Generated
console capacitors are joined type 21 and use the combined network path; the
separate native type-4 capacitive dispatch is not implied by these fixtures.

The eddy-current dependency port has started with the native infinite-interval
integrator. Its rule coefficients, adaptive subdivision, error ranking,
extrapolation and nonconvergence status handling follow `quadrature.cpp`.
Decimal guard precision preserves the original explicit binary64 stores and
unspilled arithmetic; it does not reproduce every x87 instruction rounding.
Direct object probes compare values/errors with max(1e-13 absolute, 1e-12
relative) and require exact statuses, subdivision counts and evaluation counts.
These dependency tests are supplemented by complete Green integration, LMAT
stamping and Pi-family comparisons described below.

The eddy Green kernels now preserve the original complex record spills, with
64-bit-significand arithmetic for the layered integrand and legacy division.
Decimal guard precision alone left small imaginary residues in native -z/z
cases; after division by zero wave number, those changed native NaNs to
infinities. The fixtures retain those classifications and exact zero results.
The native reflection callback returns only exponential decay, discarding the
reflection/cosine values; that behavior is preserved. Finite comparisons use
max(1e-14 absolute, 1e-12 relative), with relative checks down to 1e-300 absolute
for reflection decay and the before/after ln(FLT_MAX) cutoff cases. Full x87
exception flags, signed NaN payloads, arbitrary extreme inputs and process
stacks remain outside the current evidence.

Oscillatory integration retains the native weighted-rule constants (which
differ slightly from DQK15I), the DQCHEB butterfly, DGTSL pivot ordering, and
both moment-generation branches around |par| = 24. Cache rows and their
computed count follow the source, including a one-row cache and the 15/25
evaluation threshold. DQAWOE leaves its subdivision count zero on initial
return. DQAWFE preserves the native direct-sum jump's previous table tail,
zero-frequency bound-zero behavior, negative sine sign, partial results and
three explicit extrapolation-history cells. Tests require native statuses,
evaluation/subdivision/cycle/cache counts and per-cycle status lists. Finite
values use max(1e-13 absolute, 1e-12 relative); cancellation-limited error
estimates use max(1e-12 absolute, 1e-10 relative). These are algorithm
conformance tolerances, not guarantees of integration accuracy for every
integrand or a claim of matching all x87 flags/roundoff histories.

The Green wrapper retains the source's discarded warm-up samples, the
|separation| < 1e-10 DQAGIE selector, DQAWFE cosine weighting (in addition to
the oscillating callback's cosine), physical scaling and three history cells.
All 58 direct native cases require exact statuses and callback counts; finite
values use max(1e-12 absolute, 1e-12 relative). Three native nonfinite cases
retain their NaN classification and partial-result status.

EDDY ON stamps impedance before via corrections and reinverts it for the Pi
driver. Mode 1 uses packed square indices; other shapes use segment folding.
The original omitted final square index, via-consuming off-diagonal traversal,
primary-block widths and axial length-minus-two-width rules are preserved.
The eight geometry/process fixtures cover coarse 1 GHz and refined 2 GHz
matrices; tolerance is max(1e-8 ohm, 1e-8 relative) per component. The eight
additional Pi2 fixtures retain their existing Y/S tolerances. Pi3/Pi4 model
checks now use actual original model-command inputs, distinct from subsequent
2PORT records, with exact compiled output checks and the unchanged portable
component tolerances.
These paths run in CPython and WebAssembly; arbitrary process stacks and all
creator/eddy combinations still need independent fixtures.

The technology reader retains the first two repeated EDDY layer declarations.
A single layer selects the original pure-decay reflection callback; two layers
select the layered oscillating callback. Native results can consequently have
large negative conductor resistance; the app exposes a diagnostic and preserves
those values. Short/wide joined segments can produce native NaN impedances;
Python reports this failure explicitly. Eddy correction defaults off. With no
EDDY layers, the square path preserves the native skip/warning, while the
segment path rejects the undefined incoming-index history of the reference.

Static releases version the HTML asset references, module imports, worker and
Python archive together so cached solvers do not receive newer UI controls.

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

The CAP port follows the original spectral-transfer recursion and positive-sign,
unnormalized FFT. Its native .tek rho conversion is ohm-cm × 10000 (ohm-µm).
An explicit ground argument receives the parser's -1/-1 mesh-count convention;
it therefore uses the original chip/FFT-derived ground contact cells. Contacts
retain the original axis-aligned rectangle approximation and integer grid
quantization, including for polygon segments. The FFT twiddle recurrence and
butterflies retain a 64-bit binary significand with decimal guard precision;
ordinary binary64 FFT intermediates contaminated small substrate-loss terms.
The matrix checks were retained while recovering that rounding behavior.

Potential snapshot comparisons use max(1e-9 Ω, 1e-8 relative) per component;
reduced admittances use max(1e-16 S, 1e-8 relative). Native snapshots print ten
significant digits. Actual cached FFT entries are checked separately. This is
numerical conformance evidence, not bitwise equality or validation for all
process stacks. FFT grids are limited to powers of two from 2 to 256; contact
matrices are limited to 256 contacts. Green tables are generated on demand and
kept in a bounded in-memory cache instead of native cache files. Unfolded
geometries, non-square FFT storage quirks, unusual process stacks, and native
invalid-contact histories still need broader independent validation.

The browser contact-potential kernel now retains each original 80-bit operation
and explicit binary64 spill, including the asymmetric first subtraction in the
axis and two-dimensional sums. Its zero-frequency term is evaluated once for
each ordered metal pair per call. The fallback's equivalent reuse is scoped to
one solve and has byte-identical complete-result checks across frequency and
substrate edits. An isolated loader executes the intact original contact routine
and legacy-complex DSO with checksum-pinned inputs. Forty-one matrices check
264,844 components, including signed zeros, subnormals, nonfinite classifications,
rectangular grids with sufficient backing, noncontiguous metals, and two complete
256-contact output digests. Production raw potential matrices remain checked
against all eight existing native snapshots with unchanged tolerances. This
establishes contact arithmetic at given coefficients/tables, not bitwise equality
of the preceding spectral generation or the complete network solve.

CAP general inversion and Pi2/Pi3/Pi4 node solves now use ZGETRF/ZGETRI/ZGETRS
instead of the earlier binary64 elimination. PiX shares the same backend.
Absolute-one pivot ranking, reciprocal scaling, 64-column factor panels,
triangular blocks, exterior swaps and BLAS spill order follow the reference.
The CAP driver's n-cell workspace selects the original unblocked final inverse
step. A compiled 80-bit path supports up to 514 node unknowns and retains the
network matrix-vector accumulation order. Direct original-machine-code
fixtures check 33 cases / 2,571,696 components, including complete large-system
digests, singular statuses, signed zeros and nonfinite classifications. The
portable path rounds each retained operation to the original significand.
Whole-simulator bitwise equivalence remains unproven: remaining stamping/reduction,
broader spectral inputs and process/geometry coverage still require work.

The Python and browser spectral table generators use retained 80-bit arithmetic
for transfer/source terms, both regional kernels, wave numbers, square roots,
normalization and every recorded spill. Complex zero products remain explicit,
including in nonfinite histories. Original Y-axis thickness offsets and the
nx+1 generation / ny+1 transform strides are preserved. A direct original loader
checks 1,728 regional/transfer calls and 33 whole tables (556,434 components),
including rectangular grids and 256×256 digests. Only allocation/deletion/status
boundaries are replaced; coefficient sentinels and rectangular padding have
explicit zero backing. Arbitrary original allocator histories are not implied.

Frequency coefficients preserve the retained native weight and scalar complex
division, rather than Python's modern complex reciprocal. Eighty-eight groups
execute the intact original CAP initialization loop, captured before cache I/O.
All 3,556 output components have exact finite-bit or nonfinite-classification
checks in both Python and WebAssembly. The portable coefficient implementation
also preserves negative zero on unary negation. Source hashes and boundary
adaptations are recorded in `native/spectral-source.json`. Both table paths have
exact original-boundary checks; existing complete electrical snapshots retain
their tolerances alongside the stricter original-session gates.

CALCTRANS discretizes both windings, reverses the secondary segment order,
joins them, stamps the junction termination into folded CAP, and solves the
original inductive-admittance/node equations. Terminations below 1e-10 ohm
select 1e15 S. The original command parser rounds numerical input to binary32;
the browser reproduces that boundary for frequency in GHz, termination and
mesh values. Direct Python/JSON callers supply SI binary64 inputs.

Omitting the reference differs from explicitly naming the first winding: the
original parser marks the named winding's mesh counts before CALCTRANS copies
it. The Python path applies that convention to private copies and preserves
caller shapes. Both reference histories are captured independently. The native
Y/Z diagonal ordering and mutual sign are preserved, including negative model
values, coupling greater than one, and undefined coupling. The displayed dots
correspond to Z12 = Rg - jωM. JSON represents nonfinite metrics as null.

The coupled fixture executes the actual original binary (SHA256
`72bcb93444604b89a65cb64e5825bfcff0ac740a816120d0f171855206bd572f`)
and original legacy-complex DSO. A nonnumerical sprintf tap captures full model
precision. Regenerate with `tools/capture_transformer.py --reference
~/github/asitic-re --native-library-path PATH_TO_32_BIT_LIBRARIES`.
The 15 finite sessions compare model values, Y/S outputs and nodal CAP with
unchanged component tolerances. Six original all-nonfinite histories, including
collapsed 3D contacts and explicit-reference invalid inductive meshes, receive
bounded diagnostics rather than fabricated finite models. They do not establish
equivalence for arbitrary original invalid-memory or allocator histories.

Each coupled session also records the original Y, Z and SI model doubles as
little-endian hexadecimal words before text formatting. The compiled extractor
reproduces Z/model outputs from all 21 original Y records exactly at finite
boundaries, with nonfinite values compared by classification. This isolates the
extractor from differences in the preceding electromagnetic solve.

Run the separate strict end-to-end audit after `tools/build_site.py` with
`node tools/audit_transformer_parity.mjs /path/to/pyodide.mjs`. It exits nonzero
for any differing finite output bit. All 15 finite coupled sessions now match
their 345 raw SI Y/Z/model outputs (undefined coupling by classification), with
eddy off/on. The regular WebAssembly suite requires these same exact session
boundaries. The portable Python fallback retains component comparisons.

Original debugger snapshots isolated matching CAP inputs and filament self
diagonals from differing mutual terms before inversion. The new compiled path
preserves the original 5000-unit basis translation, retained cross/dot products,
intersection tests, geometric-mean separation, case table and nonparallel spills.
All input geometry bits form the cache key; cached data has no frequency weight
or eddy correction. Production meshes cross the Python/JavaScript boundary in
batches of at most 256 pairs. Estimate and coupling calls use the same backend.

Elementary evaluation uses binary128 guard precision around the original
extended operations. Native trig behavior near pi/2 and pi differs from a
modern libm function: Intel documents an internal Pi approximation and the
corresponding scaled function argument in its [x87 implementation
article](https://www.intel.com/content/www/us/en/developer/articles/technical/the-difference-between-x87-instructions-and-mathematical-functions.html).
The mutual kernel follows that behavior over its [-4,4] angle domain; it does
not replace native near-zero values with mathematical zeros. These bounded
sin/cos helpers remain separate from the wide Green-integrand helpers.
Four standalone scalar and 28 instruction raw extended results still differ
despite matching every captured binary64 store. Their words remain recorded
for further validation. Broader complete electrical coverage,
command-input boundaries and universal whole-simulator equality
remain open.

The reflection/layered Green and eddy paths now run the original infinite/Fourier
algorithms and square/segment stamps with retained operations. Direct debugger
captures observe 165 actual original Green returns, every callback point,
7,740 imported cosine returns, and nineteen complete stamps across coarse/fine
LMAT and coupled sessions. Six stamps and 42 returns are original BiCMOS
layered sessions. The stamp gates compare 4,058 matrix components
exactly and preserve caller wire/configuration records.

The imported cosine's 53-bit glibc algorithm is separate from ASITIC's x87
FSIN/FCOS behavior. Its original table, polynomial and argument reduction are
adapted under LGPL-2.1-or-later, with full notices and source provenance in
`native/glibc`. Another 4,658 version-bound native-library sin/cos cases match
at binary64 boundaries, including large-argument reduction. The numerical
source download supplies all kernel sources and build materials; CI extracts
and rebuilds that archive byte for byte.

The separate `tools/audit_imported_math.mjs` remains a deliberately failing
strict diagnostic: 11 of 2,057 extreme native `pow(x,1.5)` cases differ by one
binary64 ULP, originating in the hardware FYL2X retained result. Its reference
data is preserved. Observer callbacks retain the portable path. Passing the
captured sessions is not evidence of universal
bitwise equality for those additional boundaries.

Layered kernels preserve the original legacy complex sqrt, exp, sinh/cosh and
tanh, with retained arithmetic between their original binary64 stores. Separate
wide trig helpers reduce against the native internal Pi with split products
and preserve the instruction's unchanged-operand behavior outside |x|<2^63.
The checksum-pinned original/DSO loader captures 3,532 original calls plus
2,658 separately identified native FCOS/FSIN instruction calls. Every captured
binary64 component matches; finite raw Green results also match. Twenty-five
finite standalone trig raw extended results differ, and the explicit strict
`tools/check_layered_green.mjs --raw-trig` diagnostic fails on them. The fixture
keeps those words and the CPU/control-word provenance unchanged. Complete
consumed Green returns, callback histories and eddy matrix stamps have separate
exact gates. Broader whole-session parity remains necessary.

The open mesh panel exposes all five shared cell sizes above the simulation
panels. Counts run without electrical solves and use the solver's own width/
thickness count helper plus the same longitudinal clone and pad/reference
preparation. Browser analyses check this budget before building CAP/LMAT and
cache it across frequency samples. Explicit fitting doubles conductor cell sizes
until the mesh fits; CAP cells are preserved. Coarsening cannot remove native
base segments or forced 3×3 pad/reference filaments, so irreducible cases report
the required count. No automatic geometry simplification or solver substitution
is applied. Project version 1 gains optional mesh fields while older projects
remain loadable.

Pi metrics and S conversion now preserve the original retained arithmetic in
both Python and the compiled browser path. The original loader checks 3,435
records / 96,180 binary64 outputs and 6,673 finite retained returns. This covers
independent shunt/resonance inputs, all ZIN modes, terminated input impedance,
nonreciprocity, signed zeros, tiny/large values and nonfinite classifications.
The Python scalar type rounds exact rational operations after every step and
uses an integer midpoint comparison for correctly rounded square root. This
API does not expose hardware exception flags or NaN payloads.

Complete CLI capture records the actual model Y/model stores, resonance ST0
return and S-conversion Y/S stores. Pi4's intermediate pad and final reports are
kept separately; Pi3's type-0 reference can differ from a later type-8 2PORT
history. Original coordinate-height words independently check the reader's two
stored subtractions. Nominal process height and geometry coordinate height stay
separate. At identical Y inputs every captured CLI metric/S stage matches.
All 41 complete sessions additionally match all finite Y/model/S outputs and
resonance. The strict `tools/check_pi_sessions.mjs /path/to/pyodide.mjs` audit
is mandatory in CI without exclusions; `--audit-full` remains compatible.
Original captured words remain unchanged. This is scoped progress, not universal
original-binary parity.

The remaining square/via discrepancy was isolated at identical native filament
inputs: two diagonal resistances rounded differently when Decimal guard digits
were converted to binary64. Assembly now rounds every retained operation and
preserves the native angular-frequency/nanosecond stores. Twenty-three actual
original upper assemblies check 4,648 output components; independent original
pair replay checks 2,094 geometry-only terms. Production always computes those
terms and never reads oracle data.

Polygon spirals now preserve the original distinct sector spills, decrement
cancellation and radius history, native-Pi trig and vertex/recentering stores.
Forty-two complete original creators check 12,288 raw XY components in both
backends. The native clone's coarse branch copies existing endpoints unchanged;
re-evaluating end = start + (end - start) had changed the final two whole-session
results. Actual subdivision follows independently normalized primary/outer/inner
directions, retained distances and stores. Original clone fields, including
refined polygons, are checked directly against the assembly context records.
Repeated mesh checks and frequency samples reuse a bounded cache of immutable
subdivision coordinates keyed by every input bit. Each clone still owns fresh
segment fields; changing one solve's geometry cannot affect later solves.

The portable mutual path also retains the canonical basis and coplanar distance,
angle and hyperbolic stores. General BLAS products/updates now round after each
operation instead of using Decimal guard precision alone. Their interaction had
amplified small input differences in the polygon PiX resonance. The intact
original polygon PiX session now has a strict portable Y/model/resonance bit
check, alongside direct original coarse polygon mesh-pair checks. Other portable
table/matrix stages still require broader exactness work; the compiled path's
full original-session gates remain separate.
Parallel self/separation kernels also retain each arithmetic operation and the
native logarithm/exponential reduction. This corrects a coupled wire case whose
ground resistance amplified a small parallel mutual error. Range-boundary tests
preserve nearest-even extended overflow/underflow while scalar rounding reuses
bounded immutable powers of two and checks overflow only in the largest binade.

Portable whole-pair dispatch now retains the vertical-separation products until
their difference is stored, rather than subtracting separately rounded products.
The spatial formula preserves its distinct distance, denominator, ordinate and
angle stores. Planar and spatial trigonometry share native internal-Pi reduction;
intersection projections preserve the original strict threshold and asymmetric
end bounds. All 2,135 previous original primitive stores and all 2,094 captured
mesh-pair stores now match in Python as well as WebAssembly. The 23 complete
portable upper-assembly checks compute their own pair values and retain exact
matrix comparisons. Existing captured input/output words remain unchanged.

An additional 426 whole-pair cases are independently observed in the original
executable by `tools/capture_mutual_boundaries_original.py`. These cover direction
reversal, normalization/coplanarity thresholds, near-orthogonal angles,
intersection endpoints, large translations, subnormal/huge lengths and nonfinite
coordinates/cross sections. Python and compiled paths require exact finite bits
(including signed zeros), native nonfinite classes, statuses and warning
presence. Hardware exception flags and NaN payload equivalence remain outside
the public API; the separately recorded raw instruction differences remain open.

The Python CI runner partitions core discovery into eight round-robin groups.
Planning verifies a complete disjoint set of unique test IDs and records each
group's digest. Each runner re-discovers its group with GDS validation installed
and requires that digest before execution. Local unsharded discovery still runs
the complete core suite. Deployment requires every shard and every existing
native process/frequency and WebAssembly group.

Portable contact integration now follows `native/contact.cpp` through retained
layer transfers, separately stored metal heights, legacy complex division and
the original axis/combined summation order. The first selected axis difference
and first combined difference spill to binary64 at their native boundaries;
other terms retain their extended values until the original stores. Complex
scaling preserves its explicit zero products for native IEEE nonfinite behavior.
Integer index/area operations retain signed 32-bit wrapping. Zero terms remain
local to one solve and are keyed by the ordered source/target metal pair.

The same 41 intact-original contact fixtures now gate all 264,844 components in
Python as well as WebAssembly. Two tests require the complete single-metal and
multi-metal 256-contact digests; smaller matrices check each finite output word
and nonfinite class. Table hashes are verified before and after computation,
and original fixture words remain unchanged. This establishes contact arithmetic
at identical table/coefficient inputs. Portable table generation is checked
separately; matrix and complete-session differences remain parity work.
The contact correction also closes the square PiX session's raw Y/model/S and
resonance stores and the forced-reference coupled-wire session's full SI Y/Z/
model record. Both now have strict portable end-to-end regressions alongside
the established polygon PiX result. No formerly exact captured Python session
was lost in the complete-session audit.

Portable spectral arithmetic now mirrors `native/spectral.cpp` in
`spectral_math.py`, including the zero coefficient records beyond either end,
retained transfer products, regional weighting and explicit binary64 stores.
Source helpers restore every depth byte. Rectangular generation preserves all
boundary zero writes: the native nx+1 producer stride can overwrite earlier
samples before the ny+1 FFT consumer reads them. Nonfinite tanh/cosh arguments
retain the captured original classifications. The bounded table cache uses
packed configuration bytes to distinguish signed-zero inputs.

Python checks all 1,728 original scalar requests and all 33 whole tables
against unchanged finite words/digests and nonfinite classes. The complete
original-session gate additionally requires every raw Y/model/S and resonance
store across all 41 captured Pi2/Pi3/Pi4/PiX sessions in both implementations.
The earlier separate square/polygon PiX tests are included in that full gate.
These checks do not establish universal binary equivalence.

`node_math.py` mirrors `native/node.cpp`: folded CAP accumulation, both branch
differences, two retained right-hand sides, the native general solve and final
determinant/divisions. The original product reads column-major branch records
as row-major data, so the Python driver transposes that input before the dot
products. All 54 captured folded-node boundaries now have strict Python and
compiled gates, including asymmetric 128/256-node systems and actual coupled
session inputs. Caller matrices must remain unchanged.

Symmetric factor/inverse arithmetic now uses the same retained scalar for
complex magnitudes, square roots, eigen rotations, pivot weights and dot sums.
The existing 44 original fixtures require exact Python factors/inverses; the
complete 128-dominant and 256-dominant/paired digests have separate tests. The
original workspace, one/two-entry pivot paths and store order are preserved.

Portable QUADPACK operations and the discarded Green warm-up samples retain
every original scalar rounding. Reflection decay preserves the FLDL2E,
FRNDINT, F2XM1 and FSCALE reduction. Green results keep their public binary64
value and a separate retained return consumed by physical eddy stamps. Rounding
that return before the length/frequency products changes otherwise matching
circuits. Python now checks all 165 original raw extended Green returns, every
one of 74,726 callback points, and all 19 complete physical matrix stamps.
All 15 finite original coupled sessions also require their raw SI Y/Z/model
stores; the six original invalid histories retain their bounded diagnostics.

A separate 418-case instruction audit enters the unchanged exponent sequence
at `0x080949b8` with supplied 80-bit operands. Binary64 outputs, nonfinite
classes and extended exponent ranges match, including normal/subnormal and
overflow boundaries. Five finite raw returns differ by one retained bit;
`python tools/audit_exp_original.py --raw` deliberately fails until those match.
These instruction differences remain open alongside the previously recorded
trig, extreme-power and mutual intermediates. They are not excluded from the
complete consumed Green-return or electrical-session gates.

External frequency inputs now have a separate command-number boundary.
`command_runtime.cpp` type 5 reads binary64 GHz, multiplies by its default 1e9
scale in retained arithmetic, then stores binary32 Hz. `command_numbers.py`
implements that direct store without an intermediate binary64 rounding. The
webpage preserves the original GHz number through the worker request; JSON
`frequency_ghz` takes precedence over `frequency_hz`. SELFRES parses its bounds
and step once, preserving the original binary64 search iterations. Typed SI
solver calls and requests containing only Hz fields remain unchanged.

Seventeen complete sessions captured from the unchanged original parser check
every Y/model store and resonance classification, including neighboring GHz
inputs around binary32-Hz halfway boundaries. Three additional original
CALCTRANS sessions require every raw SI Y/Z/model store. Both Python and
WebAssembly require exact finite output bits. Actual webpage handlers additionally check
fractional and halfway textbox values, Pi2/coupled sweeps, computed-frequency
plot bounds/CSV exports, CAP/LMAT/estimate requests and SELFRES bounds. This
does not establish parity for every other command-number or creator boundary.

The fractional coupled gate exposed a portable via-stamp resistance store
that previously relied on Decimal guard precision. `vias.py` now follows
`native/vias.cpp` operation by operation with retained division, logarithm,
frequency products and final matrix additions. All 1,214 existing original
via records now require exact finite binary64 bits in Python too, including
signed zero; nonfinite outputs retain their classifications. No fixture
outputs or tolerances were loosened.

Ring vertices now follow `build_ring_shape` through the rounded cosine and
ribbon stores, live retained step/radii/angles, final center-X cosine spill,
native bounds traversal and retained recentering offsets. All 45 unchanged
original creator captures require every center/outer/inner XY bit, including
gap zero/full-turn cases and negative orientations. Three additional original
ring electrical sessions require every raw Y/model/S store and the finite
resonance return in both Python and WebAssembly, with eddy off/on.

New webpage ring, square and polygon definitions set `native_keyword=true`. This applies original
type-7 length scaling, binary32 stores and the default binary64 0.1 um snap
grid, plus both type-10 angle stores and the original asymmetric negative wrap.
Direct typed dimensions remain binary64 and unsnapped unless this flag is
selected. The flag is preserved through simulation, GDS and saved projects;
other creator keyword boundaries remain separate work. Existing projects keep
their stored input mode when loaded; newly generated webpage rings/squares/polygons select the
native keyword boundary. Actual DOM tests independently decode downloaded
GDS coordinates against the original rows and compare the downloaded Pi model
against original electrical stores. Project form restoration also resolves
named metal/via layers to selector indices, preventing regeneration on the
default top metal after loading a named-layer project.

Square construction now preserves the explicit pitch store, live retained
turn coordinates and individual endpoint/exit/via stores. Rotation and
reflection first store the new origin, then translate with the retained
old-minus-new origin difference. Subtracting the unrounded local minimum had
incorrectly forced some original nonzero edge coordinates to zero. Native
trigonometric angle spills remain explicit. All 126 captured square creators
require every XYZ bit and defined metadata, including full-binary64 interactive
dimensions, six near-quarter keyword inputs and both current directions.
Square keyword numbers use original length/angle stores, the default snap
grid, binary32 turn input and retained maximum-turn selection. Other creator
keyword boundaries remain separate work.

The full-binary64 square electrical case isolated another CAP difference at
identical original creator geometry and identical inductive matrices.
`contact_geometry.py` now follows `contacts.cpp` through retained global/local
coordinates, count selection, the explicit offset/step/endpoint spills and
integer grid conversion. Physical bound stores do not round the live grid
operands early. All 50 original setups / 280 builder calls / 338 contact
records retain physical-bound bits and integer indices; one native zero-area
history has a bounded diagnostic. The original thin wire at y=20 straddles
the grid because of retained arithmetic, while y=20.125 produces zero area;
the earlier generic collapse test now uses that independently captured case.
Four new complete original square sessions require every Y/model/S store
and finite resonance return in both runtimes, including typed interactive
inputs, rotations, reverse phase and eddy correction. The captured original
out-of-chip history is separately required to retain its bounded error.

Contact geometry reuse keys every consumed binary64 value by its bytes,
plus native integer dimensions/counts, metal count and the per-call contact
limit. The bounded cache stores frozen contacts in immutable tuples; each
caller receives fresh list containers. Frequency and substrate coefficients
do not participate in this geometry calculation. Original record replay and
tests of origin/endpoint edits, forced reference counts, changed limits and
caller mutation protect the reuse boundary.


Polygon keyword creation now uses the original type-7 dimension/origin stores,
default snap grid, type-4 binary32 turns and type-10 angle conversion. The
maximum-turn calculation retains the original cosine/division and quantizes
whole and fractional parts separately. Keyword quantization reloads the
binary64 fractional-product spill; interactive creation writes that spill but
floors the live retained operand. The same distinction applies to requested
turns. Multiplying the entire binary64 turn count by the side count had rounded
some values upward across an integer boundary: the original interactive
three-sided `1.3333333333333333` input produces three segments, while that shortcut
produced four. Typed polygon dimensions/angles remain unsnapped binary64/degree
inputs, but their turn truncation now follows the original interactive path.

All 77 new unchanged-original SPIRAL captures require all 34,758 XYZ stores,
widths, thicknesses, metals and origins through both private parsed creation
and public builds. Cases cover 3–32 sides, negative/positive angles, phase
invariance, omitted defaults, 18 near-fraction keyword inputs and full-binary64
interactive dimensions. Independent gdstk decoding checks every conductor's
GDS coordinates/layers on the 1 nm grid. Three invalid native histories preserve
the original maximum-turn/chip-dimension diagnostics, including binary32 turn
input rounding above a non-binary64-exact maximum. Six complete original
polygon Pi2/2PORT SLOW sessions require every raw Y/model/S bit and finite
resonance return in Python and compiled WebAssembly, including eddy, fractional
GHz input, negative angles and both interactive turn boundaries. Actual DOM
checks cover new native form definitions, named layers, saved input mode,
independently decoded downloaded GDS, and native/typed Pi2 JSON downloads.
Other creator input boundaries and whole-simulator equivalence remain open.


RESIS and RESISHF now follow `resistance.cpp` through their distinct norms,
retained arithmetic and accumulation. RESIS keeps its total in extended
precision; RESISHF stores the total to binary64 after every segment. Both
conductor paths retain `(dz*dz + dy*dy) + dx*dx` through sqrt/division, unlike
the ignored scalar helper's stored XY norm. Skin-effect powers preserve the
64-bit integer fast path and FYL2X/F2XM1/FSCALE sequence, including the high
branch's aspect spill and individual power result stores. Via count products
wrap as signed i386 int32. Public APIs still accept Hz; command GHz parsing
continues to apply at the existing bridge boundary.

Thirty-four unchanged-original CLI histories capture all consumed segment and
technology inputs, parsed Hz and raw ST0 returns: 270 finite returns and two
native NaNs. At these identical inputs the earlier binary64/Python-pow path
differed in 111 finite output stores. Both portable Python and compiled
WebAssembly now require every finite retained-return bit and final binary64
store, with bounded diagnostics for the native undefined thin-conductor cases.
The initial resistance port matched 31 public creator histories. Subsequent
WIRE input and symmetric geometry ports close the three recorded input gaps;
all 34 public histories now require the actual native consumed stores as well
as the raw return and final resistance output bits.

The browser makes one bounded resistance call for up to 20,000 segments and
uses the portable path for larger custom shapes. The binding checks record
lengths, operation/frequency, via flags/counts and output size; empty inputs,
caller buffers and recovery after invalid requests are tested. Actual DOM
checks compare preview DC, fractional-GHz HF estimates, the original 1/10/100
GHz resistance sweep and CSV values, followed by an exact original Pi2 solve
in the same interpreter to check shared-buffer/elementary-plan isolation.


Pages promotion compares a fully validated candidate against actual site-URL
receipts in GitHub's deployment history, then checks commit ancestry. The
previous tip-only guard skipped 8b41e73's Deploy step after all 31 checks passed
because a newer main commit existed; repeated pushes could therefore keep the
site on an older release. The new guard accepts validated ancestors of current
main when they advance the published version, rejects rollback/divergent
candidates, and retains the serialized Pages deployment job. Successful skipped
environment jobs have empty site URLs and do not count as publication. A site
URL is conservatively retained after a later job failure. Pagination, initial
publication, rebuilds, skipped jobs, out-of-order completion, divergent commits,
post-publish failure and API failures have explicit regression checks. The
metadata API permission is read-only; all existing numerical/creator gates
still precede publication. See GitHub's [deployment status API](https://docs.github.com/en/rest/deployments/statuses#list-deployment-statuses)
and [commit comparison API](https://docs.github.com/en/rest/commits/commits#compare-two-commits).


WIRE keyword input now follows type-7 length/width/origin conversion and default
snapping, type-10 angle stores and the integer phase rule (`0` becomes `+1`).
Missing keyword origin Y takes the parsed conductor width, whereas typed calls
retain origin zero. Interactive WIRE uses unsnapped binary64 inputs and the
actual native primitive-orientation behavior: a prompt value of 37 is stored
as 37 radians rather than converted from degrees. The explicit
`native_interactive=True` mode preserves that behavior without changing ordinary
typed degree inputs. Modes are mutually exclusive, with original interactive
phase/chip bounds. New webpage WIRE definitions and shared analysis ground/pad
strips opt into keyword parsing. Project loading restores wire defaults and
phase direction, preserves both modes through simulation/GDS/project downloads,
and explains the interactive angle interpretation before regeneration.

All 101 unchanged-original wire captures require every XYZ/origin bit and
scalar/primary width, thickness and metal stores; uninitialized conductor mesh
counts remain excluded. Cases include thin widths, both current directions,
negative/positive angles, the rotation threshold, omitted origin/metal defaults,
integer phase coercion and full-binary64 interactive dimensions/angles. Independent
gdstk readback and a separate browser-stream decoder check every exported ribbon
on the 1 nm grid. Six whole Pi2/2PORT SLOW sessions require all finite Y/model/S
bits and resonance classifications, including eddy and both input modes.

Two additional unchanged-original sessions have all-NaN port matrices and are
retained in full. The coarse-grid case's captured native contact is
`[14,34,15,15,4]`, with zero Y span. The finer-grid case has nonzero contact area
but still produces a native NaN model; Python reproduces its raw matrix/model
classes and all defined metric stores. Both cases retain direct native stdout
and independently observed physical/grid contact bounds. A raw metric replay
requires the original finite downstream stores even for the NaN matrices.
The webpage now gives an explicit nonfinite-admittance error instead of a generic
JSON serialization failure; direct Python numerical returns are unchanged.
No failing finite native history was removed or assigned a tolerance.

Both WIRE input gaps in the resistance audit are closed. All original 270 finite
retained resistance returns and two native NaNs remain unchanged; public requests
now match the exact resistance-consumed inputs in all 34 histories after the
symmetric geometry port described below. Whole-simulator equivalence and other
creator input boundaries still require work.


### Symmetric geometry retained stores and public input parity

The released float implementation differed at 11,448 XYZ stores across 81 of
102 initially captured creators when given the original parsed configurations.
The replacement preserves the actual state machines and binary64 stores, rather
than adjusting final coordinates or electrical outputs. Square span/vertical
updates retain the width-plus-spacing expression. Polygon endpoints distinguish
the live incremented angle from its stored angle, retain the radial decrement,
and spill the endpoint sector cosine and initial inner-edge Y at the original
locations. Crossover-metal history, both via calls around a bridge, rotation and
phase reversal remain in native order.

The final original-binary fixture contains 114 complete creators / 60,804 XYZ
stores, including same-metal crossovers, maximum turns, whole-turn parsing
boundaries, odd/fractional sides, ±360-degree inputs and integer phase conversion.
Every defined origin, scalar width, conductor thickness, metal and via count is
also required; native uninitialized conductor mesh counts and via thickness are
excluded explicitly. Full-binary64 interactive constructions are tested through
the typed API. The keyword API and webpage now apply the original snapped
lengths, F32 turns/angles, default transition gaps/origins and layer defaults.
Project regeneration preserves omitted derived defaults until their displayed
fields change, avoiding an extra snap of a default that the original never
parsed as a length argument.

`native/symmetric_geometry.cpp` batches complete state machines into conductor
and via-request events; shared process construction supplies the original
metal/via geometry. There is no Python callback per trigonometric operation.
The kernel has fixed capacity for 60,000 events and at most 20,000 side-turns.
Its source correspondence is recorded in `native/symmetric-geometry-source.json`.
Both Python and compiled WebAssembly require every captured store, independent
GDS conductors/layers/via counts, and eight complete original Pi2/2PORT sessions
with exact Y/model/S/resonance outputs, including eddy. The original out-of-chip
failure transcript remains a required bounded diagnostic. This closes the last
resistance-consumed public creator input gap; all 34 resistance histories now
match. These fixtures do not establish exhaustive interactive prompt/history or
parser-clearance boundary parity, or whole-simulator equivalence.


The scoped timing record `docs/benchmarks/2026-10-24-symmetric-geometry.json`
compares the two retained implementations in one pinned Pyodide runtime. For a
105-segment symmetric polygon, six warm builds have medians of 63.52 ms for the
portable path and 3.67 ms for the compiled batch, with identical geometry hashes.
`tools/benchmark_symmetric_geometry.mjs` reproduces the measurement. This is a
geometry-only measurement; it does not compare complete electrical simulations
or the original native executable.


### Multi-metal square copy, reflection and join stores

`MMSQUARE` uses the shared exact square constructor without an exit, then copies
the preceding layer's local segments at the first winding's origin. Each copy
changes metal, reflects about the original branch-selected axis, reverses segment
order and reverses segment directions. All copies finish before any joins.
Joining retains the difference between each copy's origin and the first winding's
origin through the final coordinate store. The previous Python implementation
copied the preceding origin, joined immediately and formed its translation with
a binary64 subtraction. At identical original parsed configurations, 36 XYZ
stores differed across four of the first 174 captured creators.

The port now requires 180 complete original creators / 56,214 XYZ stores, plus
all origins, scalar widths, metal indices and conductor thicknesses. Fixtures
include all quarter-turn classes, rotations, phase conversion/wrapping, the
maximum supported turn count, two to five sample-process metals, native defaults
and full-binary64 interactive construction. The original interactive prompt
rejects turns below one, unlike keyword creation; three captures preserve its
warning and explicit retry to one turn. No failing finite native history is
removed. Independent GDS readers verify conductor coordinates and process layers.

The public native-keyword mode and webpage now apply the original square parser's
outer dimensions, snapped lengths/origins, F32 turns/angles, integer phase and
penultimate-metal default for the bottom layer. Typed calls keep their existing
binary64 inputs and bottom-metal default. Effective project defaults prevent
stale layer/orientation/origin fields from a previous project. Four unchanged
original Pi2/2PORT sessions require every captured admittance, model, scattering
and resonance output, including eddy and full-binary64 inputs. The original
quarter-turn infinite resonance is preserved in the fixture and maps to `null`
through the existing public JSON contract; finite outputs retain exact checks.
Three same/reversed-metal stacks retain original diagnostic transcripts and a
bounded public error. Source correspondence is in `native/multimetal-source.json`.
Inner-hole keyword adapters and exhaustive prompt-state/parser boundary coverage
remain unverified; this does not establish whole-simulator equivalence.


### Capacitor plates, working VIA input and original failed paths

`CAPACITOR` creates each plate independently with `build_wire_shape`, then joins
the second plate using the retained origin difference. Native keyword input
accepts either length or width, copying a missing dimension after parsing;
default Y is the parsed plate width, the default bottom metal is the penultimate
process metal, and phase is always positive even if an unused PHASE key is
present. Native interactive dimensions/origins retain binary64 input. Its degree
prompt stores the entered angle as radians, exactly like the observed WIRE
prompt; projects identify this quirk before regeneration uses keyword degrees.
Same-metal plate pairs remain permitted in the native modes because the original
accepts them and can produce a model with some nonfinite metrics. Their raw
finite model stores and nonfinite classifications remain required.

The working VIA path is interactive. It uses integer scanning for counts and
phase, unsnapped origin coordinates, and explicit ±1 direction. Captures retain
fractional integer inputs and invalid-count/phase retries. The original command
inventory marks VIA's keyword argument as type 11, but the parser implements only
types 0..10. All 64 intact-original keyword histories therefore fail with
`Unknown argument type` before the VIA shape parser or constructor runs. The
public native-keyword mode preserves this failure; the webpage generates VIA
arrays through the working interactive mode. No command table or numerical
instruction was patched to manufacture a working keyword path.

All 84 original creators / 2,520 XYZ stores also require exact origin bits,
scalar widths, layer indices, conductor thicknesses and via counts; uninitialized
via thickness fields are excluded explicitly. Independent GDS readback checks
plate polygons, via layers/counts and every cut coordinate. Original same-metal
capacitor behavior, both missing/zero dimension errors, all VIA keyword errors,
and the original standalone VIA Pi2 signal-11 transcript remain in fixtures.
The latter produces a bounded public diagnostic before attempting a model.
Four complete capacitor Pi2/2PORT sessions check every captured Y/model/S/
resonance store, including eddy and raw-radian interactive input, with public
nulls only for original nonfinite outputs. Another four standalone VIA histories
check all 32 original raw retained RESIS/RESISHF returns and final scalar bits in
both runtimes. Source correspondence is in `native/primitive-source.json`.

The shared request and project encoder preserves negative-zero numeric input as
an accepted numeric string instead of allowing JavaScript JSON serialization to
replace it with positive zero. A captured VIA origin requires the original sign
bit through actual form regeneration, project save/open and GDS requests.
Typed input conventions remain intact. The browser's via-count bound remains
1–1000; these fixtures do not claim unrestricted original sizes, exhaustive
prompt/descriptor histories, a functioning original VIA keyword path, or
whole-simulator equivalence.
