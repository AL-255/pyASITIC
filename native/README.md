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

The browser calls the compiled kernel once per complete vector or grid, with a
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

Rebuild the checked-in, stripped `web/numeric.wasm` (18.6 KiB):

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
