# Source mapping and verification

Reference checkout: `~/github/asitic-re`, revision recorded in each fixture.

| Python | C++ source under `recomp_cpp/src/` | Current evidence |
| --- | --- | --- |
| `geometry.py`, `model.py`, `symmetric_geometry.py` | `shape_construction.cpp`, `spiral_construction.cpp`, `winding_construction.cpp`, `composite_geometry.cpp`, `symmetric_construction.cpp` | Original SAVE records for nine creator families, coordinates/layer/width and DC reports |
| `devices.py`, `paired_geometry.py`, shared retained joins | `winding_construction.cpp`, `shape_prompt_transformer.cpp`, `shape_creation_transformer.cpp`, `geometry.cpp`; original TRANS `0x080576d4` | 98 original keyword/interactive creators / 38,592 exact XYZ stores, names/origins/scalars, both windings and combined GDS; six actual joined filament meshes, five finite complete CAP/LMAT/Y/Z/model/S sessions and one original all-NaN reference diagnostic; actual form/default/name/project/model/download handlers in Python/Pyodide |
| `transformer3d.py`, native 3D input adaptation | `transformer3d.cpp`, `shape_creation_mirror.cpp`; original constructor `0x08057d40`, terminal `0x08059214` | 96 intact-original creators / 94,824 exact XYZ stores, origins/names/all defined ribbon fields; native spacing boundaries, name/phase scanning and prompt retries, independent combined GDS, twelve raw winding LMAT matrices including eddy; three original all-NaN and three native SIGSEGV coupled histories confirmed without observers; actual form/project/GDS/LMAT/CSV/diagnostic handlers in both runtimes |
| `precision.py` | `shape_construction.cpp` point/shape rotation | Retained radius/angle arithmetic, asymmetric cosine/sine angle spills, and native midpoint evaluation; exact rotated-wire endpoint doubles from BSAVE and matching unequal-cell mesh dimensions in CPython/WebAssembly |
| `filament.py`, `native/filament.cpp` | `filaments.cpp`, `numerics.cpp`; original `0x0806597c` | 2,220 intact original records / 19,980 exact finite components or nonfinite classifications in Python and compiled WebAssembly; all adaptive edge branches, arbitrary interpolation indices, asymmetric spills, destination Z preservation, signed zeros and extreme scales |
| `mesh_counts.py`, `mesh.py`, `web/app.js` | Native longitudinal subdivision and filament counts from `geometry.cpp`, `filament_setup.cpp` | Original default MAXNW=500 and retained divide/FISTPL/clamp rules; 2,116 exact primitive integer stores and six unchanged complete CLI histories with all 3,364 filament constructions, five bitwise finite LMAT reports and one native invalid-case diagnostic. Pi4/CALCTRANS counts, actual DOM 480-filament rejection and fit to 60/Pi2; presets, MAXNW validation and legacy/new project persistence |
| `editing.py`, `scene_heap.py`, `bridge.py`, erasure UI | `console_commands.cpp`, `geometry.cpp`, `geometry_edit.cpp`; original WHO dispatcher snapshots and `0xbc`/`0xf0` allocations | 736 original PHASE/ERASE/reuse states / 843,264 exact XYZ stores, origins/materials/links, seven wire pool sizes and mixed-size polygon/balun reuse; duplicate-argument native SIGSEGV diagnostic; independent GDS including empty cells; four complete Pi2/CALCTRANS model/Y/S/node sessions. A geometry-only allocator reproduces the captured reference glibc reuse rules; arbitrary process-heap histories remain unverified |
| `technology.py` | `technology_text.cpp`, `technology_records.cpp` | Original coordinate-height words from 41 actual CLI sessions across CMOS/BiCMOS/GF180; retained cumulative depths, separate nominal bottom distance and two-store geometry heights; broader reader commands remain to validate |
| `resistance.py` | `resistance.cpp` | Original DC reports for nine families; twelve live C++ cases at five frequencies (1 MHz–100 GHz) |
| `inductance.py`, `conductor_metrics.py`, `native/conductor_metrics.cpp` | `analysis_commands.cpp`, `resistance.cpp`, `segment.cpp`, shared mutual sources; original `0x0804ce78` / DC `0x0804eedc` | 56 intact-original INDUCTANCE/Q histories, 654 exact consumed records, 56 L / 392 QLF binary64 stores and 392 raw DC returns; all self operands/log arguments exact, complete compiled batch and actual estimate/plot/CSV handlers. Four pair binary64 stores and seven raw L returns remain unresolved under the separate strict intermediate audit |
| `solver.py` | `geometry.cpp`, `filament_setup.cpp`, `filaments.cpp`, `impedance.cpp`, `vias.cpp`, `solver.cpp` | 36 complete C++ LMAT matrices: coarse 1 GHz, refined 2 GHz, and unequal inductive/capacitive length cells; within 1e-8 Ω per component in CPython and WebAssembly |
| `impedance.py`, `native/impedance.cpp` | `impedance.cpp`, `geometry.cpp` | 23 actual original complete upper matrices / 4,648 exact components, 2,094 original mesh-pair outputs, immutable input and symmetric reconstruction checks; actual original longitudinal clone fields including refined polygons |
| `polygon.py`, `native/polygon.cpp` | `spiral_construction.cpp`, `shape_construction.cpp` | 42 actual original creator calls / 12,288 raw XY stores exact in portable Python and compiled WebAssembly; fractional turns, 3–32 sides, positive/negative rotations and production inputs |
| `ring.py`, `geometry.py`, `command_numbers.py` | `winding_construction.cpp`, `command_runtime.cpp`; original ring `0x0805b450` | 45 original creators / 12,588 exact XY stores in Python and WebAssembly; full keyword/default snap inputs, 3–128 sides, gap/orientation boundaries; three complete original Pi2 Y/model/S/resonance sessions including eddy; independent GDS readback and actual form/project/model/export handlers |
| `geometry.py` square/via emission, `model.py`, `precision.py` | `spiral_construction.cpp`, `shape_construction.cpp`, `geometry.cpp`; original square `0x08056670` | 126 complete original creators / 14,742 exact XYZ stores plus origins, widths, metal/thickness and defined via counts; keyword/interactive inputs, quarter-turn boundaries, rotations, reverse phase and exits; four complete original Pi2 electrical sessions and independent GDS readback |
| `symmetric_geometry.py`, `native/symmetric_geometry.cpp`, symmetric keyword inputs | `symmetric_construction.cpp`, `shape_prompt_symmetric.cpp`; original square `0x08059854` / polygon `0x0805a45c` | 114 original creators / 60,804 exact XYZ stores plus origins/widths/metals/thickness/via counts; whole-turn and maximum-turn cases, rotations, integer phase, odd/fractional sides, crossover history, defaults and binary64 interactive construction; eight complete Pi2/2PORT sessions, independent GDS and actual form/project/download checks in both runtimes |
| `geometry.py` multi-metal stacking and keyword input | `composite_geometry.cpp`, shared square/reflect/translate/parser sources; original `0x0805af5c` | 180 original creators / 56,214 exact XYZ stores plus origin/width/metal/thickness; fractional and maximum turns, two to five metals, rotations, phase, defaults and binary64 interactive construction; independent GDS, four full Pi2/2PORT sessions, three invalid stack transcripts and actual form/project/export handlers in Python/Pyodide |
| `rectangular_inputs.py`, rectangular native input modes | `shape_prompts.cpp`, `shape_creation_commands.cpp`, original square `0x08056670` / MMSQUARE `0x0805af5c` | 134 intact-original inner-dimension creators / 45,072 exact XYZ stores plus descriptor/origin/scalar fields; keyword precedence, phase and fractional-turn boundaries, both native acquisition modes, signed inner axes, 18 existing outer prompt histories, independent GDS and four complete Pi2/2PORT sessions; actual form/project/input-mode/GDS/model/download handlers in both runtimes |
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
| `printf_file.py`, `output_file.py`, `malloc_top_storage.py`, shared heap stores | Pinned i386 glibc 2.39 printf FILE setup/completion, modern output callbacks, stat conversion and large malloc paths | All 7,946 calls / 134 unchanged histories; complete CPU and eight-shard Pyodide reports identical with zero differences across owned memory, physical heap/error state, registers, FP and 12,975 captured helper calls. Includes 132 buffer allocations through unsorted exact fits, bin splits, fastbin consolidation and top splits. Parent formatting and continuing integration remain unfinished; all 198 earlier continuing differences stay required |
| `vfprintf_storage.py` | Pinned i386 glibc 2.39 `__vfprintf_internal` caller before/after its formatter | All 7,946 caller phases / 3,973 parent calls / 134 histories, with complete CPU and eight-shard browser reports identical and zero differences across owned memory, heap/error state, registers, FP and 20,921 caller helpers. Formatter boundary snapshots are independent component inputs only. Whole-parent execution of the 3,973 formatter bodies and 30,267 middle helpers remains unfinished; the separate formatter component does not establish integration. The 198-difference continuing gate remains required |
| `printf_format.py`, `printf_fp_flow.py`, fixed original instruction source and scalar string/buffer helpers | Pinned i386 formatter entry, literals, narrow strings, integers and binary64 decimal ABI | Full capture retains all 134 histories / 4,105 calls / 104,036 helpers. Complete CPU and eight-shard browser reports agree exactly: every call executes with exact final/helper registers, produced FP and non-kernel memory. Strict gates retain 4,048 complete-call and 868 prefix rseq word occurrences, including overlapping full pthread/static-TLS owners. No conversion, owner or native outcome is removed; no later state seeds continuing replay. See `docs/PRINTF_FORMAT.md` and `docs/PRINTF_FP_FLOW.md` |
| `printf_integer.py` | Pinned i386 int32 digit builder, argument modifiers, sign/prefix/width/precision and buffer output | Completes 396 additional original formatter calls. All 5,472 independent native int32 output requests match in CPU Python and Pyodide; seven tests include modified earlier tables, missing inputs, changed targets and request-memory release without cyclic collection. These output probes supplement the full ASITIC state gates, which remain nonzero. Long-long, localized and remaining error/flush paths are unfinished. See `docs/PRINTF_INTEGER.md` |
| `printf_float_digits.py` | Pinned i386 glibc binary64 MPN extraction, decimal scaling, digit generation and e/f/g rounding | All 73,360 independent native text requests and 70,281 finite mantissa extractions match in CPU Python and Pyodide: all binary64 exponents, four earlier rounding modes and native TZCNT zero behavior. The separate fixed ABI flow now executes all 1,976 formerly unfinished original floating calls with produced x87 state; every target remains required. See `docs/PRINTF_FLOAT_DIGITS.md` |
| `x87_format_state.py` | Masked x87 binary64 argument-copy and decimal classification instructions | Continuous independent 41,072-instruction chain: all 21,028,864 FXSAVE bytes, 123,216 register/store values and 5,902,360 later Linux XSAVE bytes remain required. Used by the complete original formatter component with produced FP state. Stack faults, unmasked exceptions, inexact extended stores and other x87 arithmetic remain unfinished. See `docs/X87_FORMAT_STATE.md` |
| `printf_fp_program.json`, `printf_fp_flow.py` integer semantics | Offline translation of the pinned formatter instruction flow and independent AMD integer flags | All 5,314 instruction bytes/extents retained; runtime guest inputs remain earlier memory. All 16,528 independent native instruction cases / 82,640 register/flag values match in CPU Python and Pyodide. No runtime native executable or output lookup. Whole-parent/continuing integration remains unfinished. See `docs/PRINTF_FP_FLOW.md` |
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

Outstanding validation includes arbitrary technology files, broader complete
command histories, and unresolved intermediate-precision comparisons. Exact
creator and editing fixtures cover the rotations, fractional inputs and phases
listed above; they do not establish universal parity. Headless Chrome now checks
the actual worker, original post-ERASE Y/S output bits, project/GDS downloads,
empty-scene undo and desktop/mobile layouts. Its HTTP server serves the pinned
Pyodide dependency locally; full hosted/CDN operation is verified separately.
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
Inner-opening input is covered separately below. Exhaustive prompt-state/parser
boundary coverage remains unverified; this does not establish whole-simulator
equivalence.


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


### Planar transformer and balun native creation and joined meshes

`paired_geometry.py` adapts the original TRANS/BALUN descriptors before calling
literal retained constructors. TRANS builds both square windings, reflects the
secondary on both axes, shifts the first lead endpoints and updates the primary
origin using the secondary's quarter-turn exit history. BALUN computes each
winding's spacing and inner gap in the native operation order, constructs both
symmetric squares, reflects the secondary and reverses each segment direction.
The interactive and keyword descriptors use different arithmetic associations
for the inner length/gap, preserved independently.

Keyword dimensions/origins use the original binary32 input and 0.1 µm grid;
turns and angles retain their separate native conversions. Interactive input
keeps unsnapped binary64 dimensions and its different prompt turn bounds. The
original accepts interactive TRANS 6.25 and BALUN 13.75 histories rejected by
keyword limits; both remain in the fixtures. Keyword BALUN can produce zero or
negative-turn center records, including N=0 and N=-2, which use the original
cheap two-center-record construction; the webpage permits those same keyword
turn inputs. Standalone symmetric-square bounds remain
unchanged. Omitted balun transition metal defaults to the penultimate process
metal even when it equals an explicitly selected winding metal; specifying that
same layer explicitly is rejected by the original. The webpage preserves the
omission until that field changes.

TRANS name parsing preserves original ASCII normalization and the lower-case
`-p`/`-s` suffixes used when SNAME is absent. Supplying SNAME keeps the primary
name unsuffixed. Original duplicate explicit winding names remain selectable by
index in the webpage. An unequal WS is parsed but ignored with the original
warning; both winding widths use WP. Native zero integer phase becomes +1.
Typed input keeps its previous naming conventions. This work does not claim
original raw-input parity for the separate 3D creator.

All 98 intact-original creations / 38,592 XYZ stores require exact origin bits,
names, widths, conductor thicknesses, metals and defined via counts. Independent
GDS readers check both windings' polygons and via layer/counts. Six additional
complete electrical histories observe actual creation at the model placement,
joined conductor fields, every filament, upper impedance assembly, CAP and LMAT
node inputs, and original SI Y/Z/model/S outputs. Two rotated cases exposed a
shared join bug: arbitrary decimal precision did not reproduce the retained
subtraction/addition before each binary64 store. The join now uses exact retained
scalar operations. All five finite histories require every raw matrix and final
output word in Python and compiled Pyodide. The sixth original history returns
all NaNs after explicit-reference via correction; its bounded diagnostic remains
required instead of a fabricated finite circuit. Original uninitialized fields,
NaN payloads, exception flags and exhaustive parser/prompt states are excluded
from these claims. Capture scripts observe the intact original without changing
numerical instructions or input records; source hashes are in
`native/paired-source.json`.


### Intact-original 3D transformer inputs and matrix returns

The generated 3D arithmetic already matches all 96 newly captured intact-original
creators / 94,824 XYZ stores. These records also require exact origin bits,
normalized names, width/thickness, primary ribbon width/thickness and metal
indices. Unwritten native mesh counts are excluded. The constructor prepends
its two winding lists independently, with asymmetric terminal insertion and no
final rotation, rebasing, list reversal or reciprocal partner links. Orientation
is stored as the entered degree value; phase is scanned as an integer. Neither
transforms the layout. The original 3D command has no keyword argument path;
native keyword API requests produce an explicit diagnostic. Twelve plain CLI
keyword attempts retain three canonical `Invalid Argument(s)` rejections and
nine `Unknown or Mistyped Commnd` replies for the other catalog spellings. The
pre-existing Python aliases remain API conveniences; they are not evidence of
original command-spelling acceptance.

Native interactive input preserves binary64 dimensions, origins and fractional
turns. Names use the original normalized first whitespace token, and duplicate
names are permitted because neither winding exists when the prompt reads them.
The original also accepts zero/negative planar dimensions and origins outside
the chip; those finite histories remain creatable/exportable. Width must be at
least the native binary64 1e-10 threshold and turns at least one. Spacing compares
`(spacing - A*width)/B` against two in retained arithmetic, with the exact native
A/B constants. Four captured valid values were previously rejected by ordinary
float arithmetic; two values accepted by that float check trigger native prompt
retries and now receive the same public rejection. The separate typed API keeps
its prior positive-dimension/name conventions. Native sizes remain bounded by
browser limits, so this is not an unrestricted-range claim.

Independent GDS readers check both complete windings for all 96 cases. Six
additional original electrical histories capture each standalone winding's LMAT
matrix at the actual driver return, requiring every raw complex word, including
eddy correction and different metal thicknesses. All twelve matrices match in
portable Python and compiled Pyodide. Return observers stop explicitly at each
actual return; they do not infer results from an unwinder or leave callbacks at
reused call sites. The full original coupled histories remain in the same
fixtures: three produce all-NaN SI models and three crash with signal 11. Separate
plain CLI runs without GDB or preload confirm those classifications. The public
solver rejects their zero planar-length potential contacts explicitly, preserving
an understandable failure rather than substituting a finite circuit.

The webpage uses native 3D input mode, preserves signed-zero project input and
effective secondary-metal defaults, accepts the original finite dimension/name
histories and displays the metadata-only orientation behavior. Real shipped-
runtime DOM checks cover generation, winding selection, project reload, all GDS
streams, twelve LMAT displays/CSV exports and six failed coupled analyses. The
regeneration tool now references the already-used `geometry_height` field, so
`port_transformer3d.py --check` reproduces the checked-in Python again. Source
correspondence is in `native/transformer3d-source.json`. These cases do not prove
all scan/prompt histories, alternate floating-point control modes, nonfinite
input handling, native fault/NaN-payload emulation or whole-simulator equivalence.


### Inner-opening dimensions and rectangular input modes

Square and MMSQUARE inputs now accept `inner_length` / `inner_height`, mapping
to the original ILEN/IWID descriptor path when outer `length` is absent. A
missing inner height copies the inner length; an outer height (WID) does not
replace IWID. An explicit outer length (LEN) takes precedence over inner values.
The derived outer length and height remain available in the resulting shape's
parameters, while project requests preserve the entered inner fields.

The keyword adapter parses/snaps input lengths exactly as type 7, stores raw
turns as binary32, then expands the dimensions before quantizing turns. Whole
turns produce a doubled integer count; the retained fractional value, its
binary64 1e-10 bias and truncating integer conversion select the quarter-turn
axis increments. Both coil families use this shared keyword expansion. The
interactive prompt keeps binary64 dimensions and quantizes the turns first.
Interactive square expansion retains its own product/addition order. Interactive
MMSQUARE uses only whole turns for each independent X/Y expansion, so fractional
input can differ substantially from the same keyword values. The prompt checks
turn capacity against its sentinel dimension before expansion; it does not
reapply an outer-dimension capacity afterward. Captured small-opening histories
require this behavior. Interactive width/spacing and origins preserve their
original prompt bounds; orientation and phase are fixed at zero/+1.

Native keyword inner axes can be zero or negative when the derived outer
geometry and turn limit remain valid. Eight such intact-original histories are
retained and remain creatable/exportable. Native square phase now uses the
original truncating integer parser and zero-to-positive default, matching the
already-ported multi-metal behavior. The separate typed API preserves prior
outer-dimension conventions; typed inner dimensions use the keyword expansion
formula with unsnapped binary64 inputs unless a native input mode is selected.

All 134 new unchanged-original histories / 45,072 XYZ stores require exact
parsed descriptor dimensions/width/spacing/turns/phase, output origins, scalar
widths, conductor thicknesses, metal indices and defined via counts. Another
18 existing intact-original outer prompt histories now exercise explicit native
interactive mode. Independent GDS readers check every conductor polygon and via
layer/count. Four full original Pi2/2PORT sessions require every finite Y/model/S
and resonance word, retaining nonfinite classifications. Input-mode selectors
and hidden-field exclusion are exercised through real Pyodide and actual DOM
generation, project save/reload, GDS export, circuit display and JSON downloads.
The browser can generate both original paths directly, rather than requiring an
imported interactive project. Uninitialized original fields, unrestricted size
ranges, all malformed/partial scans and exhaustive prompt states remain outside
these claims. Source correspondence is in `native/rectangular-input-source.json`.


### Symmetric keyword transition clearance

The original SYMSQ/SYMPOLY keyword parser runs its transition-clearance test only
when ILEN is explicitly supplied. Omission stores the retained width+spacing sum
as binary64 and bypasses the test; an explicit equal numeric gap can be rejected.
The recreation now preserves that distinction through generation and project
reload. Explicit finite zero/negative gaps are accepted whenever the native
comparison accepts them. A width exceeding the computed radius creates NaN in
the original acos path, and its unordered x87 comparison does not reject it.
The prior separate positive-gap/domain checks therefore rejected original input.

`symmetric_inputs.py` follows the retained radius/division/atan, binary64 radius
and acos stores, half-angle order, binary64 tangent store, retained doubled-width
product and comparison against gap minus the binary64 1e-10 constant. Guarded
transcendental evaluation supplies the consumed stores without reference tables
or fitted corrections. Original square/polygon parser instruction observers
record every explicit operand, intermediate ST0 word, binary64 store, condition
mask and x87 control word; actual constructor entries and static exits establish
acceptance and completed geometry independently. No inputs, allocators, code or
descriptor fields are patched. Source correspondence and addresses are recorded
in `native/symmetric-input-source.json`.

All 840 original histories (780 explicit, 60 omitted) match accept/reject results.
All 780 sets of consumed binary64 radius/acos/tangent stores and nonfinite
classifications match, as do the finite retained radius and comparison operands.
The 682 accepted creators require every one of 92,070 XYZ stores, origin
bits, scalar widths, metals and conductor thicknesses in portable Python and the
compiled browser path. Independent GDS readback and actual DOM regeneration,
project save/reload and GDS-download handlers cover every accepted history.
Zero-gap native ribbons have repeated vertices; GDS now retains their closed
boundaries instead of rejecting or discarding those records. Separately captured
original CIF streams also retain the corresponding degenerate polygon records.

Six complete original Pi2/2PORT histories cover both creators with omitted,
explicit zero and negative gaps. Two finite sessions match all Y/model/S and
resonance stores in both backends and through displayed/downloaded browser
models. Four original sessions return NaN admittance: two have collapsed FFT
contacts and two have zero planar-length contacts with NaN physical bounds and
INT_MIN grid indices. Raw output, independent contact observations, and separate
plain CLI transcripts remain in the fixture. Their defined downstream model and
S values/classifications are checked, and the public frontend retains explicit
contact errors. This does not claim full nonfinite pipeline or fault emulation.

Raw retained transcendental equality is still incomplete: 46 tangent, 20 atan,
10 acos and 10 half-angle words differ in the 780 explicit histories, despite
exact consumed binary64 stores and decisions. `tools/audit_transition_original.py`
reports them; `--raw` deliberately fails until every finite ST0 word matches.
No tolerance is used or unresolved raw record discarded. Interactive symmetric
prompt acquisition, technology WMIN/SMIN branches, unrestricted input ranges and
whole-simulator equivalence remain unproven.


### Interactive symmetric acquisition and process minima

Native interactive symmetric square/polygon inputs now have a separate public
adapter and webpage selector. Dimension, width, spacing and origin values retain
binary64 precision. Whole-turn prompts floor the entered value before checking
capacity, unlike keyword parsing. Symmetric square capacity uses retained
`((length+spacing)/(width+spacing))*0.5`, quarter-turn quantization and a final
floor. Symmetric polygons round odd scanned side counts upward, then compute
the original cosine/radius capacity. Orientation and phase are fixed at zero.
Blank/default square outer length and transition-gap inputs retain the original
binary64 fallback plus 1e-10 store. Project regeneration preserves those omitted
defaults, including the extra bias, rather than converting them into explicit
keyword values.

Metal records now retain SMIN/WMIN, including the original missing/sentinel-zero
and negative-to-0.1 initialization rules. With zero SMIN, spacing must be positive
but a transition gap below zero only warns; no keyword trigonometric clearance
test runs. With nonzero SMIN, square spacing has a warning-only lower bound, so
even captured negative spacings remain usable. The separate retained threshold
and strict gap comparison, binary64 squared operands, transition-width estimate
and WMIN warning follow `shape_creation_symmetric.cpp`. The compiled geometry
guard now permits finite signed spacing; its construction arithmetic is unchanged.
The keyword path continues to require nonnegative spacing.

Thirty-six intact-original successful prompt histories / 10,386 XYZ stores check
every parsed dimension/gap/width/spacing/turn/side/orientation/phase, completed
origin, segment coordinates, scalar widths, metals, conductor thickness and
defined via counts. They include default scans, near-integer turns, the extra
interactive square capacity, below-grid dimensions, negative gaps/spacing and
chip-edge origins. Independent GDS readback and actual Pyodide DOM generation,
input-mode switching, project save/reload and GDS downloads cover every creator.
Six complete original Pi2/2PORT histories include three finite sessions requiring
every Y/model/S/resonance output word and three native NaN sessions. The latter
retain independent collapsed-contact observations, raw downstream outputs and
plain CLI/CIF transcripts; the browser gives explicit contact errors.

Eleven additional original prompt histories do not reach construction. Ten
nonzero-SMIN symmetric polygons repeatedly enforce a maximum-zero spacing or
transition limit, even after an ordinary preceding keyword square command.
One small symmetric square repeatedly requests more transition space because
its required lower bound exceeds its permitted upper bound. The fixture retains
all requests, transcripts and last scanned values. A read-only sscanf breakpoint
stops observation after 1,200 calls, then terminates the captured inferior; this
is explicitly an observation bound, not native termination. No numerical code,
descriptors, inputs or allocator hooks are patched. The adapter provides bounded
errors for these paths rather than synthesizing successful geometry.

These captures do not establish arbitrary prior descriptor/failed-scan history,
all technology parser prefixes, alternate FFT-count initialization, native
NaN-payload/fault emulation or whole-simulator equivalence. Nonzero-SMIN polygon
acquisition remains explicitly unavailable until a successful original history
is established and its required state can be represented faithfully. The 86
retained keyword-clearance intermediate differences documented above remain;
this interactive port neither removes those records nor relaxes their audit.
Source correspondence is in `native/symmetric-interactive-source.json`.


### Whole-coil conductor estimates and Q/QUALITY stores

`conductor_metrics.py` and `native/conductor_metrics.cpp` now retain the original
INDUCTANCE self and mutual accumulators. Metal length uses retained
`sqrt((dx²+dy²)+dz²)` before the unit conversion. Via length uses the absolute Z
difference, and its width/thickness terms multiply the original integer counts
by the via width/spacing. The self logarithm, its constant, the `3*length`
denominator and doubled length remain live through each addition. Mutual values
are binary64 results from the shared pair kernel, added in native linked-list
order without spilling the complete sum. Only the final public L is converted
to binary64.

The same pass preserves the raw DC return, including its different
`(dz²+dy²)+dx²` norm order and signed 32-bit via-count product. The Q / QUALITY
command's low-frequency extrapolation uses the original binary64
`0x1.afc6f70213be5p-28` constant, retained multiplication by parsed frequency and
the retained L return, then division by raw DC. It no longer derives QLF from
already-rounded public L/DC or reassociates the frequency/unit factors. Native
GHz API sweep samples use the shared frequency parser at each computed sample;
typed SI sweeps keep their distinct full-precision frequency boundary.

The compiled batch evaluates the complete self, pair and DC loops in one call,
with 2,000 input records and separate scratch geometry. The existing mutual
primitive is shared rather than copied. A bounded eight-entry cache keys every
consumed geometry/material word, including signed zero, primary ribbon widths
and thicknesses, via dimensions and counts; it contains computed values only.
Changing frequency reuses geometry without changing the original Q arithmetic.
Caller buffers remain immutable, and invalid sizes/type/counts fail before an
output copy. Input acquisition warnings remain attached to each shape.

Fifty-six intact-original command histories cover 654 consumed segments from
all single-winding families, GF180, full-precision symmetric prompts, capacitor
plates and both windings of six 3D histories. Static data-only entry, instruction
and return breakpoints record all self operands, log arguments/returns, pair
stores and accumulators, 448 complete L returns, 392 DC returns and the actual
sprintf binary64 arguments from INDUCTANCE and seven Q commands. Inputs,
numerical code, allocation and runtime imports remain untouched. Unwritten via
primary fields are excluded because these commands never consume them. All
defined data are stored as raw words, including nonfinite classifications.

Both backends require every consumed record, all 56 printed L, all 392 QLF and
all 392 raw DC returns exactly. Self lengths/widths/thicknesses and retained log
arguments also match exactly. Actual DOM handlers check estimate displays for
all 56 projects, an original 1/10/100 GHz QLF plot and CSV, unchanged geometry,
and an exact complete Pi2 solve afterward. The prior `ced6e87` runtime differs
on 20 L and 213 QLF output stores in this matrix; reproduce that comparison with
`tools/audit_conductor_metrics_original.py --baseline`.

Intermediate parity remains incomplete. The stricter `--intermediates` audit
deliberately fails on 34 retained log returns, 28 self-accumulator words, four
binary64 mutual-pair stores and seven complete extended L returns. The pair
differences are polygon case 22/pair 772 and 3D cases 46/79, 52/370 and 54/805
in `conductor_metrics_original.json`. All original records and exact mismatches
remain inspectable; no tolerances, fitted corrections or reference results are
used in runtime. They do not change the captured final command stores, but this
does not establish every possible frequency or external output. Coupling's
translation/history and aggregate stores, GUI area/length statistics, arbitrary
nonfinite payloads and whole-simulator equality still need separate audits.
Source correspondence is in `native/conductor-metrics-source.json`.

The pinned local Pyodide measurement in
`docs/benchmarks/2026-10-24-conductor-metrics.json` compares uncached evaluation
of one 52-segment 3D winding, after shared numerical-plan warmup. Five runs have
median 41.54 ms for the prior per-pair Python orchestration and 11.91 ms for the
complete compiled batch (3.49×). The new result also matches that original L
store; the prior result differs by one binary64 word step. Reproduce it with
`tools/benchmark_conductor_metrics.mjs`. This measures conductor estimation in
that interpreter; complete Pi-family solvers have their separate timing records.


### Complete-command mutual instruction traces

`tools/capture_mutual_command_traces_original.py` observes the four differing
pair stores in `conductor_metrics_original.json` by running their complete
original CLI histories. It records actual helper entries/returns and before/after
x87 instruction operands without modifying numerical code, constants, input
records, allocator state or runtime imports. It stops after the selected pair
returns and then terminates the inferior; this is an observation boundary, not
an assertion that the original command exits. Original executable/legacy-library
and parent-fixture hashes accompany the separate
`mutual_command_traces_original.json` fixture. Existing standalone primitive and
boundary fixtures remain unchanged.

`tools/audit_mutual_command_traces_original.py` is a **strict diagnostic that
currently exits 1**. It independently replays each helper with the actual native
call inputs, as well as all 123 observed math instruction inputs. All four
canonical statuses and coordinate records, all 12 self-helper raw returns, all
49 FPATAN, one FCOS, three FRNDINT, three F2XM1 and three FSCALE words match.
The planar pair first differs at FYL2XP1 `0x08061fcd` by one raw extended ULP.
Each of the three 3D pairs has four equal-argument FYL2X differences at
`0x080b3d5b`, each one raw extended ULP. Retained cross-section cancellation
propagates those differences into the effective separation and the final
parallel pair. The four final pair F64 stores still differ (2 ULP for the planar
pair, 13 ULP for each 3D pair). The diagnostic reports all differences and
accepts no numeric tolerance.

A research-only rational replay of the published Bochs FYL2X/FYL2XP1 algorithm
at commit `5a25c9014f06e0e450576b7e9f25b83368bf6a76` reproduced the problematic
3D logarithm, but failed an existing strict separation output and increased
complete-command self-log raw differences from 34 to 56. It was not incorporated
into the runtime. Matching one hardware case is insufficient evidence for a
universal instruction replacement. These observations narrow the remaining
work without introducing fitted adjustments, fixture lookups or relaxed gates.


### COUPLING accumulation, normalization and mutable translation history

`coupling_metrics.py` and `native/coupling_metrics.cpp` port
`shape_coupling_estimate` in `analysis_commands.cpp`. L1 and L2 are stored to
binary64 before multiplication. The product, square root and final division
retain x87 precision until the actual coefficient output store. The mutual sum
is stored to binary64 after **every** pair; Python's compensated builtin `sum`
and a binary64 `sqrt(l1*l2)` do not reproduce those operations.

For every cross-winding metal pair, the original adds each shape's origin to
its segment endpoints, stores them to binary64, computes mutual, updates the
sum, and subtracts/stores the origins. This can change the local centerline
coordinates even after the subtraction. The port preserves that state for
repeated typed calls. Ribbon edges, via records and primary widths/thicknesses
are untouched, as in the original. The browser's JSON command reconstructs
fresh geometry per request; its preview and saved project remain unchanged.
The JSON command rejects identical winding names with the original self-coupling
error, and typed direct calls reject the same shape object.

The new data-only capture tool runs all 98 original paired creators, all six
previous 3D transformer sessions and eight wire creations. Each history requests
A/B, A/B again, B/A and A/B again. The compressed fixture retains **112 histories,
428 executed calls and 81,996 actual cross-pair input/value/sum records**, before
and after geometry, both inductance input stores, raw k returns, actual sprintf
M/k stores and FPU controls. Five histories are retained with their original
errors: two lowercase generated-name lookups fail after parser uppercasing, one
uses identical names, and two wire dimensions snap below the native minimum.
All terminate normally. No numerical code, data, runtime, allocator or descriptor
was patched. Original executable/library hashes and parent fixture hashes are
checked, and gzip output is deterministic (`mtime=0`).

The portable and compiled tests require every executed original M/k F64 output,
raw k return, consumed geometry/material record and post-call centerline/edge
store. The full compiled cross-winding loop uses a single transport call and
keeps mutable geometry in its own bounded buffers. Transport tests check counts,
shape/array bounds, untouched caller input buffers and rejected-call recovery.
All 101 valid paired/3D projects are additionally restored through the actual
webpage handlers and their Estimate coupling results compared bit-for-bit.
`audit_coupling_original.py --pairs` checks every actual translated pair input,
individual contribution and F64 accumulator without a tolerance. This **strict
diagnostic currently exits 1**: all 81,996 indices, translated inputs and
accumulator stores match, but one pair contribution in reversed call 3 of
`paired_original/92` differs by four F64 ULP. That difference rounds out in its
actual accumulator, and every captured final M/k store and raw k return matches.
The existing mutual primitive's transcendental fidelity remains open; no
correction is applied to that pair. The browser checker accepts `--pairs` and `--baseline` to run the same diagnostic and the
actual previous `4ba28b7` Python implementation against the existing mutual
kernel. That previous browser path differs in **260 / 428 M** and **303 / 428 k**
stores; the port corrects those captured command outputs without fitted constants
or embedded reference results. This does not establish unrestricted original
parser, CPU transcendental, nonfinite payload or whole-simulator equivalence.


### Reversed COUPLING pair instruction trace

`capture_coupling_command_traces_original.py` traces the remaining contribution
in `paired_original/92`, reversed call index 2, pair index 1653, within its
unchanged complete repeated/reversed COUPLING history. It counts only segment
calls returning to native `0x0804d113`, leaving the intervening INDUCTANCE calls
unchanged. The observer records six helper calls and then terminates after the
selected pair returns; this does not assert native command termination.

The strict mutual command audit now covers five complete-command pair traces
and 126 math instruction events. All five canonical statuses/coordinate records
match. The newly traced effective separation and two of its three self-helper
raw returns match. The other self helper first differs at FYL2X `0x0806433f` by
one extended ULP; its later self return differs by two extended ULP, producing
the already recorded four-F64-ULP pair difference. No fitted adjustment or
replacement instruction implementation is introduced. The strict audit still
exits 1 and retains all five differing final pair stores.

### Original GEOM and METALAREA geometry metrics

The previous webpage computed length using Python's `math.dist` and builtin
`sum`, and area by a planar polygon shoelace sum. The original GEOM command
instead uses retained coordinate subtraction, square/add/sqrt order and stored
segment width, with a binary64 length/area accumulator store after every primary
segment. METALAREA is a separate retained sum, admitting only segments whose
3D length is strictly greater than the original `1e-10` threshold. Both count
via segments. These commands do not compute a union of GDS polygons.

`geometry_metrics.py` and `native/geometry_metrics.cpp` port these exact loops.
`Shape.to_dict()` and the webpage now expose the actual GEOM length/area plus
METALAREA, while GDS polygons continue to use the native ribbon-edge records.
The compiled path uses one batch, bounded at 20,000 records; larger typed
geometries retain the portable path. Geometry/material words form a bounded
cache key, including signed zero; all original records remain untouched.

The data-only CLI capture runs 264 creation histories: all 56 conductor
histories, both windings of all 98 paired creators, eight symmetric sessions and
four inner-opening sessions. It retains **260 executed original GEOM/METALAREA
reports, 3,007 primary-segment operands and accumulator events**, complete raw
METALAREA returns and actual sprintf stores. Four lowercase generated-name
lookups fail in the original and remain recorded. For duplicate-name native
lookups, the actual consumed winding is matched against the original parent
constructor records, with requested index and actual matches retained. No
numerical instructions, inputs, allocator, descriptors or runtime imports were
modified.

A separate probe executes intact original GEOM/METALAREA functions on **538
supplied record lists**, including empty vectors, threshold neighbors, signed
zeros, very large/small exponents, invalid nonfinite arithmetic and paired
signaling/quiet NaN payloads. Only nonnumerical sprintf/status sinks are replaced;
the formatter copies the actual original variadic GEOM words. The complete
original creator histories remain separate from this direct primitive probe.

Those cases exposed payload loss in the common portable retained scalar and
compiled-word decoder. `Real` now preserves NaN significands/sign, propagates them
using the already vendored Berkeley SoftFloat 3e 8086 rules, and uses the native
negative indefinite for invalid arithmetic. Its `memory_operand` distinguishes
an arithmetic sNaN memory source from a preceding FLD, which quiets that source.
The distinction is required for the original FSUBL coordinate differences; it
is reproduced in both geometry backends. The SoftFloat redistribution notice
and license accompany the Python package. Exception flags and unrestricted
unsupported extended encodings are still outside these checks.

All **798** captured GEOM length, GEOM area, METALAREA F64 and raw area-return
stores pass a strict bitwise audit in both backends, including all captured NaN
words. Every CLI operand and intermediate accumulator also matches. The prior
`39cdf9c` browser source differs in **67 / 260 length** and **236 / 260 area**
results. Actual project/display handlers are checked for all 260 reports,
followed by a GDS download without geometry mutation and an exact original Pi2
Y/S model. Array shape/count checks, immutable transport inputs and rejected-call
recovery are required. No fixture data or original output lookup is used by the
runtime. These captures do not prove arbitrary geometry, NaN encoding, FPU flag,
parser or whole-simulator equality.


Mesh input and reduction now follow the original command boundaries.
`native_mesh: true` parses positive CELL/CCELL fields using type 7, including
retained micrometre scaling, the initial binary32 store, the default 0.1 µm
snap, and its final binary32 store. CCELL then raises each contact cell to
the larger retained chip-dimension/FFT-size pitch and stores binary64.
MAXNW remains an integer. All webpage analysis/preflight requests select this
mode; entered decimals survive project downloads, and the count feedback shows
effective cells. Direct Python calls and JSON requests without the flag retain
the existing unsnapped binary64 mesh boundary. This covers the default snap
state; arbitrary SNAP/GRID command histories remain separate stateful work.

`mesh_inputs_original.json.gz` records six unchanged original CELL/CCELL
histories, including neighboring length/count thresholds, contact clamping,
and a 200-filament mesh. Read-only observers retain all 30 effective cell
words, count stores, 87,148 constructed filament records, original upper
impedance assembly, ZSYTF2 factors/pivots, ZSYTRI inverses, reduced cells,
and complete LMAT/Pi2/Y/S/resonance outputs. The native assembly, factor and
inverse were already exact for the 200-filament case. Its reduction exposed
another missing arithmetic boundary: FLDL/FADDL/FSTPL after **each** term can
double-round differently from direct binary64 addition. The old reduced real
word was `ce180c6defc41140`; the original and corrected word is
`d1180c6defc41140`. No output corrections or case-specific runtime data are used.

`reduction.py` applies those operations in portable Python. The browser batches
up to 65,536 complex terms through the same retained arithmetic in the existing
matrix buffer. This avoids Python calls per term. Six full original finite
LMAT and Pi2 histories require exact finite stores in both runtimes;
`audit_mesh_input_assembly.mjs` separately checks every assembly/factor/inverse/
reduction store. Both are required in CI. The compiled boundary additionally
checks empty/maximum buffers, immutable inputs, rejected-call output safety
and recovery. Regenerate all captured stages with
`tools/capture_mesh_inputs_original.py --reference ... --library-path ...`;
it invokes the separate read-only inverse-stage capturer after the CLI captures.


Interactive polygon and ring creation is now exposed through
`native_interactive: true` and the shared webpage input-mode selector.
`radial_inputs.py` follows original prompts `0x08066b78` / `0x0806be74`:
full-precision radius, width, spacing and origin, integer side input, positive
phase and zero orientation. Polygon prompts require at least one turn and
quantize the live retained fractional product, rather than the keyword spill.
The interactive ring gap stores wrapped degrees and radians as binary64;
keyword gap/orientation parsing retains its two binary32 stores. Positive
periodic angles are accepted according to the original wrap. Interactive radii
can reach a full chip dimension, while keyword radius validation uses diameter.

The previous positive-inner-radius guard rejected native wide rings even though
the original constructor retains those ribbon points. Native modes now preserve
them; the typed convenience API keeps its existing guard. Negative ring gaps
that produce a negative angular step still raise an explicit diagnostic: the
original prints “Gap too large” and aborts that creation with a structure
violation. These are controlled construction failures, not successful empty
rings or process signals.

`radial_interactive_original.json.gz` captures 120 unchanged original histories:
109 successful shapes / 3,626 segments / 65,268 exact XYZ stores, and eleven
constructor/parser failures. Cases include 3–128 sides, adjacent fractional-turn
inputs, periodic gap/orientation input, wide/negative-inner-radius ribbons,
full-chip radii, sub-nanometre geometry and interactive name normalization.
All defined config, origin, width, thickness and metal fields remain available.
Every successful shape is checked through independent `gdstk` GDS readback;
the real webpage handlers additionally load, regenerate, save/reload and decode
every GDS stream against the captured original coordinates. Omitted project
parameters restore radial defaults rather than retaining the preceding form.

Six additional complete interactive RING/SPIRAL -> Pi2/2PORT histories require
every finite Y/model/S output bit and the captured resonance result in portable
Python and compiled Pyodide. They include eddy correction, live turn truncation,
periodic gap wrapping and a wide ring. Plain unobserved original CLI runs exit
normally, and their CIF polygons match the constructed ribbons under the native
retained scaling/truncation. The new checks are mandatory in CI. Arbitrary
partial scans, retained prompt retry histories, all side-count/resource limits,
and broader geometry-edit/branch-group workflows remain separate work; this
change does not establish whole-program equivalence.
