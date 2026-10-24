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
| `potential.py` | `potential_tables.cpp`, `potential.cpp`, `contacts.cpp`, `potential_solver.cpp` | Eight CAP sessions across CMOS/BiCMOS: full potential snapshots, folded admittance matrices, and actual cache FFT samples for every metal pair; browser runtime checks cover all eight reduced matrices |
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
| `symmetric.py`, `native/matrix_*.cpp`, `native/soft_real.hpp` | Original ZSYTF2 `0x0809bcf8` / ZSYTRI `0x08095bf8`; `symmetric.cpp`, `complex.cpp`, `blocked.cpp` | 44 directly verified original factor/inverse cases, exact compiled pivots and output bits, tiny/huge scales, signed zeros, partial singularity; complete original factor/inverse digests for 128/256-entry systems including two-entry pivots; four original dense Pi2 sessions at 189 filaments / 63 contacts; portable Python factors and six eigen rotations retain component checks |
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
retained separately. General CAP inversion and Pi2's node solve still use their
previous binary64 elimination helpers; those are separate validation boundaries.

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
portable path retains Decimal guard precision and component-tolerance checks.
Whole-simulator bitwise equivalence remains unproven: remaining stamping/reduction,
broader spectral inputs and process/geometry coverage still require work.

The browser's full spectral table generator now uses retained 80-bit arithmetic
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
adaptations are recorded in `native/spectral-source.json`. The portable table
fallback and complete electrical snapshots retain their existing tolerances.

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

The Python CI runner can partition core discovery into four round-robin groups.
Planning verifies a complete disjoint set of unique test IDs and records each
group's digest. Each runner re-discovers its group with GDS validation installed
and requires that digest before execution. Local unsharded discovery still runs
the complete core suite. Deployment requires every shard and every existing
native process/frequency and WebAssembly group.
