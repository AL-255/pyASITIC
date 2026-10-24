# Pi performance and original-binary checks

The browser runs Python in Pyodide 314.0.7. Numerical loops written in Python
were the principal cost: retained FFT butterflies, spectral arithmetic, and
matrix inversion. The FFT, complete spectral table generation, layer coefficients, contact potentials,
symmetric/general factors and inverses, triangular solves and network dot
products now run in a compiled
WebAssembly module. Both backends cache complete tables at identical inputs;
the portable table fallback also memoizes spectral values and interface ratios.
Filament mutual terms now use a retained compiled case table and bounded packed
caching of all input geometry bits; frequency scaling and eddy terms are
evaluated for each solve. Scalar estimate/coupling calls share the same backend.

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

The general-matrix step replaces CAP's earlier Gauss–Jordan inverse and the
Pi2-family's magnitude-ranked elimination with the original absolute-one LU,
inverse workspace and triangular solves. PiX shares that backend. Network dot
products now use retained compiled arithmetic. CAP reduction and node stamping
also preserve the native accumulation order rather than Python 3.14's
compensated complex `sum`.

| FFT grid | Contact release cached | General step cached | General step first request |
| --- | ---: | ---: | ---: |
| 64 × 64 | 0.451 s | 0.339 s | 5.90 s |
| 128 × 128 | 0.452 s | 0.348 s | 2.96 s |

This is another 1.3× cached improvement at 189 filaments / 63 contacts. The
34-filament / 17-contact case takes 14/23 ms cached and 0.89/2.65 s on its first
request at 64/128 grids. The dense cached case remains about 16× slower than the
original. Full inputs, raw samples and current results are saved in
`benchmarks/2026-10-23-general.json`; previous browser samples are from
`27ccf16`, and native timing samples are retained from the original benchmark.

The spectral-table step moves complete metal-pair generation into the retained
kernel: transfer/source recursion, Green kernels, wave numbers, normalization
and FFTs. Layer coefficients also follow the original retained frequency weight
and scalar complex inverse. Compared with `e86a3b3`, measured first requests are:

| FFT grid | 34 filaments, previous / current | 189 filaments, previous / current |
| --- | ---: | ---: |
| 64 × 64 | 0.89 s / 0.33 s | 5.90 s / 5.38 s |
| 128 × 128 | 2.65 s / 0.78 s | 2.96 s / 1.10 s |

Cached identical-frequency solves remain about 14/23 ms at 34 filaments and
0.35 s at 189 filaments. The first dense 64-grid request still pays the large
initial geometry cost; caches persist into its 128-grid request. Raw samples
and complete current results are in `benchmarks/2026-10-23-spectral.json`.

A separate benchmark follows the webpage's eleven distinct, linearly spaced
Pi2 requests from 0.1 to 20 GHz. It includes geometry/table work and Python JSON
transport, excluding interpreter loading and DOM rendering:

| Mesh / FFT grid | General release | Spectral-table step |
| --- | ---: | ---: |
| 34 filaments / 64 × 64 | 7.27 s | 2.01 s |
| 34 filaments / 128 × 128 | 27.94 s | 8.58 s |
| 189 filaments / 64 × 64 | 15.23 s | 10.45 s |
| 189 filaments / 128 × 128 | 31.49 s | 12.21 s |

The 128-grid sweeps improve about 3.3× and 2.6× for the two meshes. Both versions
run sequentially with the same requests. One portable Python regression process
overlapped the first part of the sequence on the development host. Inputs,
per-point times and L/R/Q results are in
`benchmarks/2026-10-23-spectral-sweeps.json`. These are browser comparisons;
original-binary sweep timing has not been measured by this tool.

The retained mutual step (2026-10-24) moves the signed pair dispatch, canonical
basis, cross-section separation and planar/spatial formulas into bounded
compiled batches. A paired run against the deployed mesh release `b9c0b53`
uses the same requests and one interpreter per version:

| Mesh / FFT grid | Previous first request | Retained mutual first request |
| --- | ---: | ---: |
| 34 filaments / 64 × 64 | 0.336 s | 0.192 s |
| 34 filaments / 128 × 128 | 0.788 s | 0.787 s |
| 189 filaments / 64 × 64 | 5.192 s | 0.693 s |
| 189 filaments / 128 × 128 | 0.352 s | 0.339 s |

The dense first 64-grid request improves about 7.5×. Geometry caches persist
between FFT cases, so the dense 128-grid row already benefits from its earlier
64-grid geometry solve. Current cached dense requests take about 0.33–0.34 s;
matrix inversion remains a substantial cost. The retained original cached
measurement is about 21 ms. These measurements establish a geometry-work
improvement, not native-speed parity or a universal timing bound. Complete
inputs, per-request samples and results are in
`benchmarks/2026-10-24-mutual.json`; native timings are retained from the earlier
2026-10-23 original-binary measurements, not remeasured for this step.

The eleven-point distinct-frequency dense 64-grid sweep improves from 10.41 s
to 5.83 s. The corresponding 128-grid run is 12.18 s / 12.31 s, with little
change after geometry reuse; frequency-dependent tables and matrix work remain.
The two small-mesh sweeps measure 2.01 s / 1.93 s and 8.53 s / 8.81 s at 64/128
grids. Versions run sequentially with separate interpreters. Raw inputs and
every sample are in `benchmarks/2026-10-24-mutual-sweeps.json`; these are browser
comparisons, excluding interpreter loading and DOM rendering.

The retained folded-node/via step (2026-10-24) moves the complete node assembly,
voltage differences and final Y conversion into one compiled call. Its main
purpose is exact retained arithmetic: two one-ULP assembly differences in the
captured eddy-enabled balun input had amplified during factorization. At identical
CAP/inductive inputs, all 54 direct-original node cases now match, including
all 15 finite coupled-session inputs and 256-entry systems. The via boundary
also checks 1,214 original stamps exactly (nonfinite values by classification).
Those measurements precede the reflection Green/eddy step below.

A matched complete-Pi2 run against `c0a94b8` shows a small cached improvement:

| Mesh / FFT grid | Previous cached | Retained node/via cached | Current first request |
| --- | ---: | ---: | ---: |
| 34 filaments / 64 × 64 | 14.4 ms | 14.3 ms | 0.192 s |
| 34 filaments / 128 × 128 | 23.1 ms | 22.4 ms | 0.786 s |
| 189 filaments / 64 × 64 | 0.341 s | 0.324 s | 0.697 s |
| 189 filaments / 128 × 128 | 0.349 s | 0.338 s | 0.333 s |

Cold timings are essentially unchanged, and the dense cached case remains
about 16× slower than the retained original timing. Versions ran sequentially,
with separate interpreters and no overlapping validation processes. Complete
requests, all samples and output metrics are in
`benchmarks/2026-10-24-nodes.json`; original timings are retained from the
2026-10-23 measurements and have not been remeasured for this step.

The reflection Green/eddy step (2026-10-24) moves the native infinite/Fourier
integration, retained physical scaling and square/segment stamping into the
compiled module. It preserves native partial results and warnings. Imported
binary64 sin/cos use the original glibc algorithm and table, separately from
ASITIC's x87 trigonometric instructions. All fifteen captured finite coupled
sessions now match every raw SI Y/Z/model output boundary; full raw matrix
stamps, retained returns and callback traces are checked independently.

A matched run against `c638d35` measures complete eddy-enabled analyses:

| Analysis | Previous cached | Compiled reflection cached | Improvement |
| --- | ---: | ---: | ---: |
| Pi2, 34-filament square | 59.6 ms | 16.4 ms | 3.6× |
| Pi2, 7-filament polygon | 279 ms | 12.5 ms | 22.3× |
| Pi2, 12-filament multimetal | 783 ms | 37.7 ms | 20.8× |
| CALCTRANS, 8-filament wire pair | 211 ms | 16.9 ms | 12.5× |
| CALCTRANS, 11-filament transformer | 443 ms | 28.6 ms | 15.5× |
| CALCTRANS, 24-filament balun | 1.111 s | 61.0 ms | 18.2× |

The balun's first request measures 1.114 s / 71.4 ms. Versions ran sequentially
with separate interpreters and no overlapping validation processes, using ten
identical requests and case order, three times per case. Cold table/geometry
work is included in each first request and caches persist between cases.
All inputs, all samples and full result objects are saved in
`benchmarks/2026-10-24-eddy.json`. These compare browser releases; original-binary
timing was not measured by this experiment. Layered Green/observer fallbacks and
the separately failing extreme-power audit remain open numerical boundaries.

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
That fallback measurement predates the general LU change.
The webpage requires the compiled backend at initialization. Runtime and
validation assertions check that the compiled backend is active.

Before the matrix step, profiling a cached 34-filament case attributed about 80%
of Python runtime to three symmetric matrix inversions. The compiled path keeps
the original pivot, eigen-rotation and binary64-store behavior. Geometry caching
alone made only a small difference. Contact-potential evaluation and remaining
spectral/matrix assembly were subsequent performance targets. A current dense
cached profile puts most remaining time in symmetric filament inversions.

Reproduce the comparison after building the static site:

```sh
python tools/build_site.py
python tools/benchmark_pi.py --reference ../asitic-re \
  --native-library-path '/path/to/asitic-re/run/libs:/path/to/32-bit-libraries' \
  --output /tmp/native-pi.json
node tools/benchmark_pi.mjs /tmp/native-pi.json \
  /path/to/pyodide/pyodide.mjs /tmp/browser-pi.json
node tools/benchmark_sweep.mjs /tmp/native-pi.json \
  /path/to/pyodide/pyodide.mjs dist /tmp/browser-sweep.json
```

Use `--dense --skip-python` with `benchmark_pi.py` to reproduce the denser native
inputs/timing without spending time on the portable Python fallback, then pass
that output to the same browser benchmark tool.

Accuracy gates include 83 FFT/reflected-grid cases with 17,342 exact output
components and 20,014 exact cosh/tanh cases from the actual original binary.
Matrix gates cover 44 original cases plus complete 128/256-entry factor/inverse
digests in Python and WebAssembly, and four complete original dense Pi2 sessions.
Full CAP, Pi2/Pi3/Pi4/PiX, eddy and resonance fixtures retain their existing
tolerances. Exact agreement of these kernels does not establish universal
bitwise agreement of the whole simulator. Contact gates now compare 41 original
matrices (264,844 output components), finite values bit for bit and nonfinite
values by classification, plus all eight production raw potential and reduced
CAP snapshots with unchanged tolerances. End-to-end assembly/reduction and
broader geometry/process inputs still require independent verification.
General-matrix gates check 33 original cases / 2,571,696 components, including
complete dense 514-entry factor/inverse/solve/product digests. Finite outputs
match bit for bit and nonfinite classifications match; caller inputs remain
unchanged. These establish the tested matrix boundaries, not universal
whole-simulator equality.
The Python and compiled spectral gates check 1,728 original regional/transfer
calls and 33 complete tables (556,434 components), including rectangular and
256×256 table digests. The Python path preserves the original coefficient
sentinels, intermediate stores and zero writes where rectangular table strides
overlap. Its bounded table cache keys include every input byte, so signed-zero
coefficient changes cannot reuse a different native configuration.
Another 88 groups / 3,556 components compare the intact original CAP coefficient
loop with both Python and compiled implementations. Finite bits and nonfinite
classifications match; source helpers must restore depth bytes. These extend
the checked boundaries without establishing universal electrical parity.

Both implementations now require exact complete outputs for all 41 captured
Pi sessions and all 15 finite coupled sessions. The Python folded-node gate
checks all 54 original boundaries, including asymmetric systems up to 256
nodes. Portable Green integration checks all 165 retained returns and every
callback point, followed by all 19 physical eddy stamps. These gates preserve
the raw return until the original physical-matrix store; an early Python float
conversion loses bits even when the standalone binary64 integral matches.

The expanded core suite runs in eight complete disjoint groups. Large symmetric
matrix cases are separate tests so their original digests can run in parallel;
every test ID remains required before deployment. This changes validation
scheduling, not the webpage's accelerated solver.

Portable retained rounding now quantizes dyadic sums/products with integer
shifts, while general rational divisions retain the existing path. A local
100,000-product rounding benchmark changed from 0.308 s to 0.180 s; 20,025
wide-exponent and boundary cases matched the previous exact quantizer. This is
a scalar microbenchmark, not a whole-simulation speedup. Original electrical
and matrix gates remain required for the optimized implementation.

The additional exponent instruction audit matches all 418 binary64 outputs and
extended range classifications. Its separate `--raw` mode still reports five
one-bit extended differences. The existing strict extreme-power and raw-trig
audits also remain open; matching the checked electrical sessions is not a
claim of universal instruction or simulator parity.

The square/contact geometry correction (2026-10-24) preserves the original
contact placement stores before grid conversion. Repeated geometry is keyed
by the exact consumed input bytes and integer settings, with fresh containers
for each caller. Retaining these operations without reuse added repeated CAP
setup work; the bounded cache restores comparable cached-request costs.

| Mesh / FFT grid | Previous cached | Corrected without reuse | Corrected cached | Corrected first request |
| --- | ---: | ---: | ---: | ---: |
| 34 filaments / 64 × 64 | 16.0 ms | 24.6 ms | 13.9 ms | 0.222 s |
| 34 filaments / 128 × 128 | 25.6 ms | 33.7 ms | 23.5 ms | 0.823 s |
| 189 filaments / 64 × 64 | 0.339 s | 0.378 s | 0.343 s | 0.790 s |
| 189 filaments / 128 × 128 | 0.352 s | 0.384 s | 0.353 s | 0.391 s |

Each version ran sequentially in a fresh interpreter, sharing that interpreter
across its FFT cases; no local validation overlapped these timings. Cached
values are the third identical request. The first request for each case may
reuse state from the earlier cases, so it is not a fresh-browser cold time.
The corrected uncached/cached complete JSON results were identical. Initial
setup remains somewhat slower than the preceding implementation. All samples,
requests, versions and output metrics are in
`benchmarks/2026-10-24-contact-geometry.json`. Native timings are inherited from
the earlier benchmark input and were not remeasured. These four cases do not
establish universal performance or original-binary equivalence.


Conductor resistance now uses the original retained norm, power sequence and
DC/HF accumulation stores. A separate batch kernel keeps this precision change
small relative to full network solves. On the development host, a 95-segment
polygon's direct HF-resistance calls at typed 1e9 / 1e11 Hz took median
0.75 / 0.96 ms over five subsequent calls, versus 0.30 / 0.47 ms for the earlier
binary64/Python-pow implementation. First calls were 1.19 / 1.06 ms. These
figures exclude interpreter/kernel loading and geometry construction and are
not fresh-browser or full-solve timings. The corrected arithmetic costs more;
the earlier outputs differed from the original binary at many captured stores.
The sequential per-release protocol and every sample are preserved in
[the resistance measurement](benchmarks/2026-10-24-resistance.json).
