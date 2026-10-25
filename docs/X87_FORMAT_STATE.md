# Original formatter x87 state component

`x87_format_state.py` produces the raw register-slot, tag, status and
control changes around binary64 argument copying and decimal
classification. It implements `FLDCW`, binary64 `FLD`, register `FLD`,
exact binary64 `FST/FSTP`, `FSTP ST(0)`, `FABS`, `FXCH`, `FUCOMI/FUCOMIP`,
`FXAM` and `FNSTSW AX`. Slot contents remain 80-bit words. Empty slots
retain their physical bytes as TOP changes. Sticky invalid/denormal
flags, NaN quieting and payloads, signed zero, comparison EFLAGS, C1,
classification codes and the XSAVE active bit are produced by source.
No host floating-point formatter, native return image or recorded output
supplies a result.

The instruction semantics can be checked against the
[Intel instruction reference](https://cdrdv2-public.intel.com/812383/253666-sdm-vol-2a.pdf).
The source requires the separately measured AMD masked error-pointer
profile. Its supported operations retain the earlier pointer fields;
it does not invent a formatter instruction address or copy later
pointer bytes. Other pointer profiles, unmasked exceptions, stack faults,
inexact extended-to-double stores and general x87 arithmetic remain
explicit unfinished boundaries.

`capture_x87_formatter_instructions_native.py` builds a static i386
instruction driver. Its 2,416 requests include positive/negative zero,
subnormals, normal boundaries, infinities, quiet/signaling NaNs and
payloads, every binary64 exponent and 256 seeded random words. All four
rounding modes are explicit earlier `FLDCW` requests in this independent
program. It does not run or modify ASITIC. It does not reset the FPU
between requests: sticky exceptions, old physical slot bytes and
condition codes carry through the entire program.

Each request executes 17 declared instructions, covering the outer
argument copy and the decimal core's ordinary classification operations.
The sequence executes every instruction even for nonfinite values; it
does not replace an original branch or terminal outcome. A deliberately
populated initial EFLAGS value makes the comparison's effects on all
arithmetic flags observable. Every instruction records all 512 FXSAVE
bytes, PUSHFL flags, EAX and the binary64 store destination. All 41,072
instructions and 27,604 distinct raw FXSAVE images remain required.

A second unchanged execution is observed using read-only Linux
`PTRACE_GETREGSET`. Its entire native output stream matches the first
execution. The capture retains 2,420 complete, 2,440-byte Linux XSAVE
observations: bootstrap, three inner points and the end of every request.
Thus full kernel observations span every exponent and argument class,
both signs and all rounding controls.

The initial comparison exposed ten differences, at bytes 464/465 in the
first five observations. They are Linux's software-owned feature word in
the hardware FXSAVE reserved area. The probe now executes CPUID and
XGETBV before its first instruction state and records the supported and
enabled masks. Supplying their intersection at bytes 464..471 produces
all 512 bytes of the kernel view exactly; every raw hardware byte and
complete kernel image is still retained. The initial mismatch diagnostic
remains local at `/tmp/pyasitic-x87-kernel-comparison.json`. Expanding from
five kernel observations to every request preserved all earlier
instruction and kernel targets.

The source audit initializes two chains, once each: the first hardware
image and first kernel image. It then executes all requests continuously
without a case-specific restart or later snapshot input. The required
comparisons cover 21,028,864 hardware-state bytes, 123,216 register/store
values and 5,902,360 later kernel-state bytes. CPU Python and Pyodide
reports agree exactly with zero differences. Five regression tests pass
in both runtimes and check
every declared request and target, require only the two initial images
to initialize execution, detect modified hardware/kernel/register
targets and keep unsupported faults/stores explicit. The archive is
1,699,890 compressed bytes, SHA-256
`de853451169e4618443cfc494d0540e407851dce1458274d14c7d3b2af4d9750`.
Reports remain local. The verified source package is `7a46086e96284bad`;
the numerical module remains unchanged at SHA-256
`c7869e98f4c18b5414dc172d836e7144ab3ebc0de2de0d1f2eec1a4fe1709186`.

This component is not yet bound to `PrintfFormat` or to the
[decimal digit component](PRINTF_FLOAT_DIGITS.md). All 1,976 original
floating formatter calls remain unfinished required targets. Original
formatter stack/GPR stores, limb helper boundaries, allocation/error
paths, long double, hexadecimal and locale paths, whole-parent execution
and continuing replay remain unfinished. The existing full formatter
gates are unchanged and must still fail.

```sh
python tools/capture_x87_formatter_instructions_native.py
PYTHONPATH=src:tests python -m unittest test_x87_formatter_instructions_native
python tools/audit_x87_formatter_instructions_native.py --output /tmp/x87-cpu.json
python tools/build_site.py
node tools/check_x87_formatter_instructions_native.mjs /path/to/pyodide.mjs /tmp/x87-wasm.json
```
