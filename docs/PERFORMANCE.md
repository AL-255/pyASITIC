# Pi performance and original-binary checks

The browser runs Python in Pyodide 314.0.7. Numerical loops written in Python
were the principal cost: retained FFT butterflies, spectral arithmetic, and
matrix inversion. The FFT, retained exponential helpers, contact potentials and symmetric
factor/inverse now run in a compiled
WebAssembly module. Per-table memoization reuses spectral values and interface
ratios only at identical inputs. Filament mutual terms use bounded caching of
ordered binary geometry records; frequency scaling and eddy terms are evaluated
for each solve.

The original reference is the unmodified `asitic.linux.2.2`, SHA256
`72bcb93444604b89a65cb64e5825bfcff0ac740a816120d0f171855206bd572f`.
It is executed in an isolated process session because its exit path signals the
process group. The reference's legacy 32-bit libraries are supplied explicitly.

Measurements on the development host, 2026-10-23: square 80 µm, width 5 µm,
spacing 3 µm, one turn, M1 with M2 exit, origin (10,20), 1 GHz, eddy off;
inductive cells 20/3/0.5 µm and contact cells 50/8 µm. The 64-grid case uses a
128-µm chip; the 128-grid case uses the original CMOS 512-µm chip. This is a
comparison of complete analyses, not a claim that different FFT grids are
electrically interchangeable.

| FFT grid | Original cold | Browser before acceleration | After FFT/spectral step | After matrix step, cold / cached |
| --- | ---: | ---: | ---: | ---: |
| 64 × 64 | 39 ms | 5.7 s | 1.1 s | 0.93 s / 33 ms |
| 128 × 128 | 160 ms | 23.6 s | 3.0 s | 2.67 s / 32 ms |

The matrix step reduces the previous release's cached 34-filament solve from
173–177 ms to 32–33 ms. A denser mesh (inductive cells 5/1.5/0.5 µm, contact cells
still 50/8 µm) produces 189 filaments and 63 contacts:

| FFT grid | Original cached | Previous release cached | Compiled matrix cached | First request, previous / current |
| --- | ---: | ---: | ---: | ---: |
| 64 × 64 | 21.2 ms | 18.12 s | 0.686 s | 23.86 s / 6.26 s |
| 128 × 128 | 21.1 ms | 18.15 s | 0.668 s | 20.72 s / 3.30 s |

This is about a 27× cached improvement on the dense case. The previous release
is commit `56173c9`. Complete per-request samples are saved in
`benchmarks/2026-10-23-matrix.json`. That release left about a 32× native/browser gap
on the dense cached case. The reported >10,000× user configuration has not yet
been reproduced.

The contact step batches each metal pair into the compiled retained-arithmetic
kernel and reuses its position-independent term within that call. Compared with
the matrix release (`05e556a`), the measured cached 189-filament / 63-contact
case improves another 1.5×:

| FFT grid | Matrix release cached | Contact step cached | Original cached | Contact step first request |
| --- | ---: | ---: | ---: | ---: |
| 64 × 64 | 0.686 s | 0.451 s | 21.2 ms | 6.04 s |
| 128 × 128 | 0.668 s | 0.452 s | 21.1 ms | 3.07 s |

The 34-filament / 17-contact case takes 20/28 ms cached and 0.95/2.69 s on its
first request at 64/128 grids. The contact step leaves the large cold spectral
generation and geometry costs. The dense cached case remains about 21× slower
than the original executable. Complete samples and input settings are saved in
`benchmarks/2026-10-23-contact.json`; these observations are not timing thresholds.

Cold browser timing is the first request for each FFT grid in one interpreter,
excluding interpreter loading. Geometry caches persist between the two grids;
the first dense case pays their initial cost. The native cold estimate
subtracts the median empty-session process time from a one-analysis session;
cached native timing subtracts one-analysis from 21-analysis sessions and divides
by 20. The 34-filament native cached values were approximately 0.5–0.6 ms. Browser cached values
are the third identical request in one interpreter. Raw samples are retained by
the benchmark tools. The remaining native/browser gap is substantial.

The last measured portable CPython fallback took about 4.3/19.7 s cold in these two cases and
about 91 ms cached. Its retained precision correction increases cold work.
The webpage requires the compiled backend at initialization. Runtime and
validation assertions check that the compiled backend is active.

Before the matrix step, profiling a cached 34-filament case attributed about 80%
of Python runtime to three symmetric matrix inversions. The compiled path keeps
the original pivot, eigen-rotation and binary64-store behavior. Geometry caching
alone made only a small difference. Contact-potential evaluation and remaining
spectral/matrix assembly are the next performance targets.

Reproduce the comparison after building the static site:

```sh
python tools/build_site.py
python tools/benchmark_pi.py --reference ../asitic-re \
  --native-library-path '/path/to/asitic-re/run/libs:/path/to/32-bit-libraries' \
  --output /tmp/native-pi.json
node tools/benchmark_pi.mjs /tmp/native-pi.json \
  /path/to/pyodide/pyodide.mjs /tmp/browser-pi.json
```

Use `--dense --skip-python` with `benchmark_pi.py` to reproduce the denser native
inputs/timing without spending time on the portable Python fallback, then pass
that output to the same browser benchmark tool.

Accuracy gates include 83 FFT/reflected-grid cases with 17,342 exact output
components and 20,014 exact cosh/tanh cases from the actual original binary.
Matrix gates cover 44 original cases plus complete 128/256-entry factor/inverse
digests, and four complete original dense Pi2 sessions.
Full CAP, Pi2/Pi3/Pi4/PiX, eddy and resonance fixtures retain their existing
tolerances. Exact agreement of these kernels does not establish universal
bitwise agreement of the whole simulator. Contact gates now compare 41 original
matrices (264,844 output components), finite values bit for bit and nonfinite
values by classification, plus all eight production raw potential and reduced
CAP snapshots with unchanged tolerances. Spectral generation and the remaining
network arithmetic still require further precision work.
