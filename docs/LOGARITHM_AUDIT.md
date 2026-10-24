# Native logarithm evidence

The five remaining complete-command mutual-pair discrepancies include
one-bit differences at the original `FYL2X` and `FYL2XP1` stores. A mathematically
guarded logarithm is insufficient to establish exact agreement with those
instruction outputs. This audit preserves the differences without using them
as runtime substitutions.

The capture tool builds a small i386 instruction driver, separate from ASITIC.
Its source, compiler flags, source hash, libc/loader hashes, CPU/microcode and
before/after x87 control words are stored in both fixtures. The control word is
`0x037f`. Every captured input and output is a defined ten-byte extended word;
no ABI padding enters the comparison.

`log_instructions_native.json.gz` contains 8,115 independent, fixed-seed inputs:
logarithm table/crossover boundaries, ordinary and wide exponents, extended
subnormals, and small positive/negative `log1p` arguments. It also contains all
67 relevant instruction operands from the existing unchanged-original command
traces. The driver's outputs match every one of those original words. The
parent hashes and the complete request set are checked by the fixture-integrity
tests; these tests make no claim of simulator logarithm parity.

The strict audit compares every word and exits nonzero on any difference:

```sh
python tools/audit_log_instructions_native.py --output report.json
python tools/audit_log_instructions_native.py --p6-experiment --output report-with-experiment.json
```

Natural-log rows call the actual Python `_log` helper. Unit-multiplier and
`FYL2XP1` rows evaluate the current guarded formulas at the captured instruction
inputs; they do not reconstruct an upstream caller argument or add a binary64
spill. This is a component audit, not an end-to-end simulator test.

On the recorded AMD Ryzen 9 7940HX (microcode `0xa60120a`), guarded evaluation
has 184 raw-word differences, including one binary64 difference. The isolated
[P5/P6 experiment](../tools/experiments/p6_log/README.md) has 560 raw-word
differences, also including one binary64 difference. It improves the small set
of previously identified command failures but worsens the independent set, so
it was not adopted. No simulator algorithms, tolerances or captured expected
values were changed by this investigation.

## Multiplier experiment

`log_multipliers_native.json.gz` records 10,260 multiplier observations across
ten arguments, plus the same 67 original-command operands. Three arguments
come from the differing original instructions; seven are independent ordinary
arguments. Each group uses 1,026 multipliers, including exact one, the native
`FLDLN2` constant, and fixed-seed 64-bit significands in `[1,2)`.

```sh
python tools/audit_log_multiplier_width.py --output width.json
```

This audit intersects the exact nearest-even rounding intervals implied by the
native outputs, including the smaller spacing below powers of two and open
tie boundaries for odd significands. Its stated model is one input-dependent
logarithm followed by an exact multiply and one final extended rounding.

All ten groups have nonempty intersections and each admits one value on a
68-bit-significand lattice. Six groups admit no value on a 67-bit lattice.
This rules out a fixed 67-bit logarithm under that model; it does not prove an
exact internal width, identify polynomial/table rules, or establish a complete
instruction emulation. Recovered values are diagnostic output and never enter
the simulator. Exception flags are not inferred.

Regenerate on a host matching the recorded original instruction outputs:

```sh
python tools/capture_log_instructions_native.py
python tools/capture_log_instructions_native.py --suite multipliers
```

The tool rejects captures if any of the 67 original-command instruction words
changes. CPU-dependent differences remain explicit; a different processor's
result is not accepted as a replacement for the existing original reference.
