# Original binary64 decimal conversion component

`printf_float_digits.py` translates the decimal conversion in glibc 2.39
[`stdio-common/printf_fp.c`](https://github.com/bminor/glibc/blob/glibc-2.39/stdio-common/printf_fp.c)
and [`dbl2mpn.c`](https://github.com/bminor/glibc/blob/glibc-2.39/sysdeps/ieee754/dbl-64/dbl2mpn.c).
It retains the i386 32-bit limb extents, power-of-ten scaling, destructive
digit generation, rounding carry, general-format notation changes, signs
and field padding. It accepts binary64 argument bits, field controls and
an explicit earlier rounding mode. Python float formatting, decimal
logarithms, recorded output and later native state do not supply results.
The translated code is LGPL-2.1-or-later; its copyright and bundled license
are identified in the module.

The pinned original libc remains SHA-256
`e936bd40e5479b27721efeade1b502623436a8be2bd8bd0f0ccf8c4f7229a0d0`.
Its decimal core uses `TZCNT` at offset `0x5a163` on a potentially zero low
limb. The independent probe executes that instruction with zero and records
32; the source implements that actual 32-bit zero behavior. The probe and
audit reject a different native contract rather than treating an undefined
source-level bit scan as an arbitrary digit decision.

`capture_printf_float_digits_original.py` builds a standalone i386 program
with ordinary `__libc_start_main` startup and typed variadic `snprintf`
calls into the unmodified pinned libc. It also calls the actual
`__mpn_extract_double` at offset `0x51ed0`, resolving the loaded libc base
using `dlsym`/`dladdr`. Its four-limb destination begins with a nonzero
pattern. The resulting count, exponent, sign, two mantissa limbs and two
untouched limbs are independent targets. Nonfinite arguments retain their
normal decimal formatting path and do not enter mantissa extraction.

All 73,360 text requests are declared before native execution: lowercase
and uppercase `e/f/g`, flags, widths, default/zero/positive precisions,
signed zeros, infinities, NaN payloads, subnormals, adjacent representable
values around decimal carry/notation boundaries, all 2,048 biased
exponents with three significands and both signs, and 4,096 seeded random
bit patterns. Additional requests reach precision 1,074 and width 4,096.
The standalone probe uses standard `fesetround` calls to request all four
rounding modes as earlier inputs. It links the installed i386 libm,
SHA-256 `6ff63f39b4c1fc4a04b91cc86da32aceec1d758e3b440b753b937f95ce1690b6`.
This does not modify the original ASITIC process, its CPU state or any
original result. No request is selected or removed based on its result.

The archive records probe source, compiler command, executable hash,
minimal environment, input hash and the actual native targets. It is
1,350,504 compressed bytes, SHA-256
`dc065c652087e78ed1f68a491d65aa8231605171ab734a3baf0857b42b15e894`.
Adding extraction targets preserved every output from the first text-only
capture. Reports stay local.

The component matches all 73,360 text outputs and all 70,281 finite
extractions in both CPU Python and Pyodide. Their complete reports are
identical. Six regression tests pass in both runtimes and require every declared request, detect
modified output/extraction targets, exercise changed argument bits and
rounding controls, and reject unsupported or foreign native contracts.
The independent browser job supplements the complete formatter gates.
The verified source package is `faa6feb8ad5e9fbb`; the numerical module
remains unchanged at SHA-256
`c7869e98f4c18b5414dc172d836e7144ab3ebc0de2de0d1f2eec1a4fe1709186`.

This is a decimal digit component, **not a completed formatter ABI**.
`PrintfFormat` still rejects floating conversions. All 1,976 original
floating formatter calls remain required and unfinished, alongside all
earlier memory/register/FP/helper comparisons and rseq differences.
No text-only path is wired in while claiming that unchanged incoming FP
state is a produced result. Original stack allocations, limb helper
boundaries, x87 argument preparation/classification, FP exception/status
behavior, complete return state, long double, hexadecimal floating
conversion, locale and allocation/error paths still need implementation
and independent state checks. Whole-parent and continuing replay remain
unfinished.

```sh
python tools/capture_printf_float_digits_original.py
PYTHONPATH=src:tests python -m unittest test_printf_float_digits_original
python tools/audit_printf_float_digits_original.py --output /tmp/decimal-cpu.json
python tools/build_site.py
node tools/check_printf_float_digits_original.mjs /path/to/pyodide.mjs /tmp/decimal-wasm.json
```
