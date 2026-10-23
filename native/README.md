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
in `matrix-source.json`. A fixed 256-entry matrix limit matches the browser's
filament limit. Calls copy column-major Python records into separate bounded
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

`contact.cpp` follows the original contact-potential routine's subtraction
order, extended intermediates and binary64 stores. Its complex division uses
the legacy DSO's ratio/denominator arithmetic, including its IEEE behavior at a
zero denominator. Typed metal records replace native byte offsets. Python
preserves contact order and table selection; one compiled call processes both
ordered directions of a metal pair. The position-independent term is reused
only within that call. The portable Python fallback also reuses this term within
one solve, keyed by ordered metal indices; it does not share values across
frequencies or process edits.

`capture_contact_potential.py` executes the intact original routine at
`0x080901c0` with the checksum-pinned executable and legacy-complex DSO.
The 41 cases cover square and rectangular grids, boundaries, noncontiguous metal
indices, layer transfers, subnormals, signed zeros, large values and nonfinite
classifications. All 264,844 output components are checked: finite values bit for
bit, nonfinite values by classification, and two complete 256-contact matrices
by output digest. Input table digests check the deterministic recipe. Rectangular
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
The full Python pipeline also checks 15 finite original CALCTRANS/2PORTTRANS
sessions and diagnoses six original nonfinite histories. Those complete
electrical comparisons retain component tolerances; they do not establish
whole-simulator bitwise equality.

Rebuild the checked-in, stripped `web/numeric.wasm` (113.4 KiB):

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
