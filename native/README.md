# Retained-precision numerical kernels

`fft.c` follows ASITIC's positive-sign FFT, reflected-grid traversal, operation
order, and binary64 stores. Arithmetic between stores uses Berkeley SoftFloat
3e's 80-bit format with its default 64-bit significand and nearest-even rounding.
The nine phase constants cover the solver's supported FFT dimensions (2–256,
with reflected transforms up to 512). They are recorded independently in
`src/reasitic/fft_constants.py` and `tests/fixtures/potential_fft.json`.

The fixture generator calls the original executable's intact FFT instructions
at `0x080912c0` through an isolated i386 loader. It also compares the reconstructed
C++ routine. Its 83 cases cover signed zeros, subnormals, large/small values,
random vectors, impulses, alternating inputs and rectangular reflected grids.
Both the portable Python FFT and compiled browser FFT must match every output
component bit for bit. This establishes the tested FFT boundary, not universal
electrical parity for the whole simulator.

The browser calls the compiled kernel once per complete vector, grid or matrix, with a
Python-owned buffer copied into and out of separate bounded WebAssembly memory.
The solver retains a portable Python implementation for environments without
the compiled module.

`network.cpp` and `network_scattering.cpp` preserve the original Pi extractor,
single-ended/differential and terminated ZIN, shunt resistance, resonance and
50-ohm S conversion. The historical diagonal ordering, ignored differential
y12 input, squared-real spill and all original model stores remain unchanged.
`network_metrics.py` uses the same formulas with exact rational arithmetic,
nearest-even 64-bit significands, extended exponents and an integer square-root
rounding decision in `retained_scalar.py`. Public undefined metrics remain null;
the Python/browser API does not expose x87 exception flags or NaN payloads.

`capture_network_metrics.py` executes intact original entry points and the
original legacy DSO for 3,435 records. All 96,180 binary64 outputs and 6,673
finite retained returns match in Python and WebAssembly. Cases cover normal,
tiny/large/nonfinite values, signed zeros, nonreciprocity, shunt threshold
neighbors, independent model records and every input port/mode. Partial API
operations clear unrelated output fields and preserve caller input buffers.

`capture_pi_sessions.py` independently observes 41 actual original CLI sessions.
Pi4's intermediate pad report and final de-embedded report remain separate.
All captured metric/S stages match at identical Y inputs. All 41 complete
sessions also match every finite Y/model/S output and resonance. The strict
`check_pi_sessions.mjs` audit is mandatory in CI, without session exclusions.
The original words remain unchanged; production calculations never load fixture data. Source hashes and
adaptations are recorded in `network-source.json`.

Technology geometry heights preserve the reader's two binary64 stores:
`depth - stored(depth - d)`. The nominal bottom distance stays separate for
spectral preparation and process display. Pi3 preserves its parser-type-0
reference mesh; Pi2/Pi4 retain type-8 marking. These input histories are covered
by the complete-session gates rather than being inferred from isolated kernels.

`impedance.cpp` preserves self-distance/log/resistance arithmetic and the
binary64 angular-frequency/nanosecond stores before retained mutual weighting.
The unscaled geometry-only pair cache remains computed by the existing kernel.
Python's former 25-digit Decimal resistance evaluation changed an exact
binary64 rounding tie (`0.9750000000000001` became `0.975`). Both backends now
preserve every retained operation and store. `capture_impedance_original.py`
observes 23 actual original fill calls, exact filament records and all defined
upper cells. Another intact-original pair replay supplies unscaled test inputs.
All 4,648 upper components match in Python and WebAssembly; 2,094 actual-mesh
pair outputs also match. The native lower triangle is undefined; the production
API reconstructs the symmetric matrix without changing the tested upper cells.

`polygon.cpp` and the portable `polygon.py` preserve the original distinct
retained/stored sector arguments, shrink/decrement cancellation, radius history,
vertex spills, native-Pi FSIN/FCOS behavior and bounds/recentering order. Actual
original CLI captures check 42 creators / 12,288 XY components, including
fractional turns, 3–32 sides and rotated inputs. Longitudinal cloning now copies
an unchanged segment when the native threshold selects that branch; actual
subdivision retains the original per-edge normalized directions and stores.
Original clone records include refined polygon meshes. Source hashes are in
`assembly-geometry-source.json`. These gates establish captured boundaries;
raw elementary-instruction differences documented below remain open.

The spectral helpers retain `k * (a - b)` until the original store, then follow
the original FLDL2E / FRNDINT / F2XM1 / FSCALE exponent reduction. The F2XM1
fraction is evaluated with binary128 guard precision and stored in the native
80-bit format. Positive cosh clipping and the one explicitly rounded cosh
argument remain distinct. The portable implementation follows the same sequence
with decimal guard precision. Another 20,014 scalar fixtures execute the actual
original cosh and transfer-up instructions, using the original legacy-complex
DSO. Both implementations match every scalar output bit. These finite fixtures
establish the tested boundary; arbitrary x87 inputs remain subject to further
validation.

`matrix_symmetric.cpp` and `matrix_complex.cpp` follow the reference's unblocked
upper symmetric factor/inverse, BLAS operations, eigen rotations and spill order.
`soft_real.hpp` replaces each retained `long double` operation with SoftFloat's
80-bit operation, including square root. Source revision and hashes are recorded
in `matrix-source.json`. Internal symmetric/assembly/sum buffers support 512
entries, with capacity exported to the Python/JS wrappers. The browser's
filament budget remains 256; the larger buffers also cover native comparison
and explicitly budgeted library systems. Calls copy column-major Python records into separate bounded
storage and return the original pivots. The inverse reconstructs its defined
upper triangle into the full symmetric result, as the Python API requires.

`capture_original_symmetric.py` runs the intact original factor/inverse routines
with the original legacy-complex DSO. It independently verifies 44 saved cases
and captures complete upper-triangle digests at 128 and 256 entries, including
two-entry pivots. CI checks every compiled output bit, lower-triangle preservation,
full inverse reconstruction and input immutability. Four dense Pi2 sessions also
compare full native Y/S outputs at 1, 5 and 20 GHz. The portable Python matrix
fallback retains its existing component-tolerance checks; this is not a claim of
universal bitwise parity of that fallback or of the complete simulator.

`symmetric_wide_original.json` adds complete original factor/inverse digests at
288, 384 and 512 entries, including two-entry pivots and stride canaries. The
original probe's backing was enlarged without changing any native numerical
instruction. Earlier fixtures remain unchanged. The kernel module remains
bounded; its static linear memory is now 35 MiB (previously 28.1875 MiB).

`contact.cpp` follows the original contact-potential routine's subtraction
order, extended intermediates and binary64 stores. Its complex division uses
the legacy DSO's ratio/denominator arithmetic, including its IEEE behavior at a
zero denominator. Typed metal records replace native byte offsets. Python
preserves contact order and table selection; one compiled call processes both
ordered directions of a metal pair. The position-independent term is reused
only within that call. The portable Python fallback also reuses this term within
one solve, keyed by ordered metal indices; it does not share values across
frequencies or process edits.
`contact_math.py` now mirrors all retained contact operations in portable Python,
including transfer slopes/offsets, height stores, the asymmetric first-difference
spills, ordered accumulator updates and every complex-division boundary.

`capture_contact_potential.py` executes the intact original routine at
`0x080901c0` with the checksum-pinned executable and legacy-complex DSO.
The 41 cases cover square and rectangular grids, boundaries, noncontiguous metal
indices, layer transfers, subnormals, signed zeros, large values and nonfinite
classifications. All 264,844 output components are checked: finite values bit for
bit, nonfinite values by classification, and two complete 256-contact matrices
by output digest, in both portable Python and the compiled backend. Input table
digests check the deterministic recipe before and after execution. Rectangular
cases provide sufficient backing for the original `nx+1` table stride; they do
not validate the original allocator's behavior. Eight complete production raw
potential and reduced CAP matrices also retain their existing snapshot
tolerances. These checks establish the contact-arithmetic boundary given the
same coefficients and tables; whole-simulator equality needs end-to-end evidence
beyond these isolated component gates.

`matrix_general.cpp` retains the general LU's absolute-one pivots, 64-column
panels, exterior swaps and BLAS coefficient spills. The general inverse uses
the CAP driver's `n`-entry workspace: ZTRTRI still has 64-column triangular
blocks, while ZGETRI selects its unblocked lower-triangle step. Node solves
retain forward row swaps and column-ordered lower/upper substitution.
`general_wrapper.cpp` also follows the native network matrix-vector loop, with
an accumulation spill after each term. Separate bounded storage supports
514-entry PiX systems, corresponding to the application's 256-filament limit.
CAP and Pi2/Pi3/Pi4/PiX all use this backend; the Python fallback follows the
same algorithm sequence with its existing Decimal guard precision.

`capture_original_general.py` executes the intact original ZGETRF, ZGETRI,
ZGETRS and network matrix-vector routines. Thirty-three cases check 2,571,696
output components, finite values bit for bit and nonfinite classifications,
including singular statuses, signed zeros, tiny/large values, pivot ranking,
the 64/65 and 128/129 block boundaries, 256-entry dense and 514-entry dense/diagonal
systems. Every large factor, inverse, three-RHS solve and product is checked
by its complete digest. The capture checks stride canaries; production API
checks also require caller input immutability. The portable fallback has
component-tolerance comparisons and a separate panel-boundary check, rather
than a claim of universal bitwise equality.

`spectral.cpp` follows the native transfer/source recursions, regional Green
kernels and complete table generator. It preserves retained wave numbers and
square roots, mixed-term spills, complex zero products, opposite Y-axis
half-thickness offsets, repeated legacy complex normalization and the differing
generation/transform strides. It calls the existing retained hyperbolic and FFT
implementations inside the same module. One Python call produces a metal pair's
complete X, Y and combined tables; no per-sample Python/JavaScript calls are
needed. The bounded storage supports the application's 2–256 power-of-two grids.

`capture_original_spectral.py` executes intact original transfer, regional and
table-generation routines. Only allocation, deletion and status boundaries are
replaced. Its 1,728 regional/transfer calls and 33 complete tables check 556,434
components, finite values bit for bit and nonfinite classifications. Cases
include both height branches, multiple layers, zero/large/tiny coefficients,
source-depth restoration, rectangular grids and complete 256×256 table digests.
Capture arrays provide explicit zero-backed coefficient sentinels and sufficient
rectangular padding. They do not certify arbitrary original uninitialized
allocation histories. The portable table fallback retains its existing native
snapshot tolerances.

Layer initialization also retains the frequency weight until the original
stores and uses the legacy scalar complex inverse, which has different zero
terms from complex/complex division. `capture_original_coefficients.py` enters
the actual CAP driver with an empty contact-preparation boundary and captures
its coefficients at the subsequent cache-load boundary. The weight/coefficient
instructions and DSO imports are unchanged. Its 88 groups / 3,556 components
check both compiled and portable implementations, including signed zeros,
subnormals, extreme frequencies and nonfinite classifications. Inputs to that
oracle are already stored ohm-µm resistivities; the production reader conversion
retains the original multiply-by-10000 store separately.

`transformer.cpp` follows the original reciprocal Y-to-Z conversion and
seven-value CALCTRANS extraction. It preserves native diagonal labels, ignores
the unused y12 input, and retains live inductances until the coupling output
spill. Source provenance is recorded in `transformer-source.json`.
`capture_transformer.py` executes the intact original inverse/model routines
and folded node driver using the checksum-pinned original and legacy DSO.
Sixty-seven cases check 1,541 output components, finite values bit for bit
and nonfinite values by classification,
including nonreciprocal inputs, extreme scales and folded-node results.
Twenty-one raw Y records from complete original sessions independently check
the compiled Z/model outputs at their SI binary64 boundaries as well.
The full Python pipeline also checks 15 finite original CALCTRANS/2PORTTRANS
sessions and diagnoses six original nonfinite histories. All 345 raw SI
Y/Z/model components in those finite sessions match exactly, including eddy
off/on. This scoped evidence does not establish whole-simulator bitwise equality.

`filament.cpp` follows the original filament interpolation, including all three
adaptive edge branches, retained complements and weights, asymmetric X/Y spills,
and unchanged destination Z fields during edge blending. Typed request records
replace the original ribbon and technology offsets. One bounded call builds a
whole mesh. `capture_filaments.py` executes the intact original routine at
`0x0806597c`; its 2,220 records check 19,980 output components in both Python and
WebAssembly, finite values bit for bit and nonfinite values by classification.
Cases include arbitrary interpolation indices, nonplanar ribbon corners,
signed zeros, extreme scales and native invalid sqrt(dot) histories. Production
solves diagnose nonfinite coordinates explicitly. Source provenance is recorded
in `filament-source.json`.

`mutual.cpp` and `mutual_nonparallel.cpp` retain the original signed segment
dispatch, canonical basis, intersection projection history, self/cross-section
helpers, parallel case table and planar/spatial formulas. Filament solves use
bounded batches of pairs, with frequency-independent packed results cached by
all input geometry bits. Estimate/coupling calls share the same retained path.
Source hashes and adaptations are recorded in `mutual-source.json`.

`retained_math.cpp` evaluates elementary functions with binary128 guard
precision between native retained stores. It preserves the original FLDLN2
constant, exp reduction, atanh crossover and distinct FYL2X/FYL2XP1 paths. Sin/cos
use the internal trigonometric Pi approximation described by Intel, rather
than replacing the native instruction with the mathematical function. Their
original helpers remain restricted to [-4,4], covering the mutual formulas'
stored angles. Separate `wide_sin`/`wide_cos` helpers use split native-Pi
reduction for Green arguments and preserve FSIN/FCOS's unchanged finite operand
at magnitudes at least 2^63. They have their own instruction-oracle coverage.

`capture_mutual.py` executes intact original routines for 2,135 cases, including
939 whole pairs from real meshes and arbitrary planar/spatial geometry. Separate
probe modes execute native x87 instructions for another 2,683 cases. All outputs
match at binary64 boundaries, including signed zeros and nonfinite classes;
statuses, warnings and caller immutability are checked too. Raw extended words
and the oracle CPU/control-word environment remain in the fixture. Four
standalone scalar and 28 instruction intermediates
differ. No universal raw 80-bit instruction equivalence is claimed. All twelve
captured finite eddy-off CALCTRANS sessions now additionally match every raw
original SI Y/Z/model output bit (undefined coupling by classification). The
compiled reflection Green/eddy path below also closes the three captured
eddy-enabled sessions.

The portable Python path now also preserves whole-pair separation, intersection,
canonical-basis and planar/spatial operation/store order. Both paths pass those
2,135 original primitive outputs and another 2,094 original mesh-pair outputs;
the portable upper-assembly gate computes those pair terms itself. A separate
intact-original capture adds 426 threshold, reversal, translation, degeneracy
and nonfinite whole-pair cases, required by both backends. Existing fixture
words remain unchanged. These binary64 boundaries do not close the separately
recorded raw extended instruction differences above.

`vias.cpp` follows the original via stamp's retained height, separately scaled
perimeter counts, integer product, logarithm and inductance association. Angular
frequency and reactance spill to binary64 at their original boundaries; the
resistance remains extended until addition to the existing real matrix cell.
The solver preserves via traversal and destination group indices. The compiled
transport accepts original signed/uninitialized counts as well as positive
counts; nonfinite matrix cells produce an explicit diagnostic before inversion.
The portable fallback retains Decimal guard precision, with four-ULP fixture
checks rather than a universal exactness claim.

`capture_vias.py` calls the intact original `0x080657b8` routine using the
checksum-pinned executable. Only allocation/release and warnings are supplied
as runtime boundaries. It checks untouched matrix padding and descriptor bytes,
as well as the x87 control word. Its 1,214 cases cover height thresholds, signed
zeros, cancellation, integer-product overflow, forced-reference negative counts
and zero counts. All 2,428 compiled output components match finite bits or
nonfinite classification. Source provenance is recorded in `via-source.json`.
This establishes the via-stamping boundary. The independent strict session
audit now also passes the three captured eddy-enabled sessions.

`node.cpp` retains the complete folded-node driver's cap folding, branch
differences, matrix additions, dot products, voltage differences and final
two-port determinant. Each addition/subtraction follows the original retained
operation before its binary64 store; direct binary64 arithmetic can differ by
one ULP at a halfway value and amplify that difference in the solve. The driver
reuses the compiled original general LU/backsolve and legacy-complex divisions.
Its dot products also preserve the original row-major reads of column-major
records, including asymmetric inductive matrices. One bounded call supports
up to 256 branches and returns both port Y and the complete folded CAP matrix.
Caller matrices remain unchanged.

`capture_nodes.py` independently replays intact original folded-node instructions
for 54 cases, including 128/256 entries, asymmetric matrices, extreme scales,
and raw inputs captured at the original node entry in all 15 finite coupled
sessions. Each production replay must also match that original session's Y
record. CI checks all 189,752 output components through exact finite bits or
whole-matrix digests and checks input immutability. Source provenance is in
`node-source.json`. These stage comparisons use identical CAP/inductive inputs;
they do not substitute oracle intermediates into production simulations.

`quadrature.cpp` and `oscillatory.cpp` port the original infinite/Fourier
integration algorithms with retained arithmetic and explicit stores. The
reflection/layered callbacks, warm-up, selector, partial results and physical scaling
remain in `green_integral.cpp`. `eddy.cpp` retains square packing, segment
classification and folding, including the original zero additions and via
column traversal. One bounded compiled call stamps a complete reduced matrix;
frequency-dependent values and native warnings are recomputed for each solve.

The original imported sin/cos boundary uses glibc's temporary 53-bit precision,
distinct from ASITIC's FSIN/FCOS instructions. A mathematically rounded cosine
can differ from that original routine near pi/2. The adaptation in `glibc/`
therefore preserves the original algorithm, coefficients, lookup table and
argument reduction, with LGPL notices and complete rebuildable sources. See
`glibc/source.json` and `glibc/README.md` for provenance and modifications.

`capture_eddy_original.py` observes actual original CLI calls without replacing
any functions. Its nineteen coarse/fine contour and coupled stamps check 4,058
matrix components, 165 raw retained Green returns, every callback abscissa,
and 7,740 imported cosine returns. Six stamps and 42 returns come from original
BiCMOS sessions (`--layered`); the original reflection fixture is preserved.
Separate version-bound runtime-library
fixtures check another 4,658 sin/cos outputs, including signed zeros, subnormals,
branch boundaries and large arguments. CI also requires all fifteen complete
finite coupled sessions to match every raw SI Y/Z/model bit. Six original
nonfinite histories retain explicit diagnostics. `eddy-source.json` records
the original ASITIC source hashes.

`green.cpp` and `green_complex.cpp` preserve the layered gamma, tanh, propagation
and oscillating formulas, legacy unscaled complex sqrt, scalar sinh/cosh,
complex exp, binary64 spills and nonfinite behavior. Scalar sinh retains its
F2XM1/FSCALE sequence, distinct from the clipped spectral helper. The original
DSO is used only for capture. `capture_layered_green.py` checks 3,532 intact
original Green/DSO calls and 2,658 separately identified FCOS/FSIN instruction
calls. All captured binary64 components match, including signed zeros. Finite
raw original Green results also match; 25 finite standalone trig raw extended
results differ. `check_layered_green.mjs --raw-trig` retains a strict, deliberately
failing audit for those words. No fixture substitution or output fitting is used.
Observer callbacks retain the portable Python path and its existing component/
trace comparisons; broader complete electrical coverage remains open.
The separate `audit_imported_math.mjs` additionally checks 2,057 native
`pow(x,1.5)` cases and deliberately fails on eleven extreme inputs differing by
one binary64 ULP. Those differences originate in the native FYL2X retained
result. The fixture remains unchanged; the current session/contour gates do
not prove universal x87 instruction equivalence.
The [native logarithm evidence](../docs/LOGARITHM_AUDIT.md) additionally retains
8,182 instruction cases and 10,327 multiplier observations, including every
shared unchanged-original instruction word. It separates actual `_log` calls
from guarded instruction-formula probes and labels the rejected P5/P6 candidate
as an isolated experiment. These diagnostics do not change the numerical module.


The webpage's numerical source download includes every kernel source, upstream
and adapted library files, notices, build script and original module. CI
extracts that archive and requires a byte-identical rebuild, permitting library
modifications to be relinked with the rest of the module.

Rebuild the checked-in, stripped `web/numeric.wasm`:

```sh
python tools/build_kernels.py --download-zig
python tools/build_kernels.py --download-zig --verify
```

The compiler is Zig 0.13.0, pinned by SHA256 from the official download manifest.
Use `--zig /path/to/zig` to supply it locally. CI rebuilds and compares the module
byte for byte before deployment. No compiler is downloaded by the webpage.

`softfloat/` contains only the required source subset and headers from
[Berkeley SoftFloat 3e](https://www.jhauser.us/arithmetic/SoftFloat.html).
The original archive SHA256 is
`21130ce885d35c1fe73fc1e1bf2244178167e05c6747cad5f450cc991714c746`.
Its BSD license is preserved in every source and in `softfloat/COPYING.txt`;
the browser distribution includes that notice. Upstream code is unchanged; line endings and trailing whitespace are normalized.
`platform.h` selects little endian layout, compiler leading-zero operations and
128-bit integer products. The rest of the source selection follows upstream's
fast-64 implementation and 8086 NaN specialization.
