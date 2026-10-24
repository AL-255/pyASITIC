# Native trig instruction audit

This audit investigates the retained FCOS discrepancy in the joined coupled
model. It does **not** supply a runtime correction. JOIN remains on its
development branch with the exact model comparison failing; see
[JOIN_PORTING.md](JOIN_PORTING.md).

## Independent evidence

`capture_trig_instructions_native.py` compiles an i386 instruction driver using
packed 10-byte operands and results. Each request executes FCOS or FSIN, then
stores the actual extended result. The fixture records the complete source,
source hash, compiler and flags, libc and loader hashes, CPU/microcode and
before/after x87 control words (`0x37f`). The driver is separate from ASITIC.

The recorded host is an AMD Ryzen 9 7940HX, family 25, model 97, stepping 2,
microcode `0xa60120a`. These observations apply to that host; they are not
proof of identical outputs on other x87 implementations.

The fixture contains **11,669 instruction observations**:

| Input family | FCOS/FSIN observations |
| --- | ---: |
| Fixed-seed ordinary binary64 | 4,096 |
| Fixed-seed ordinary extended | 2,048 |
| Extended neighbors of independently chosen angle boundaries | 2,112 |
| Binary64 neighbors of independently chosen angle boundaries | 2,048 |
| Tiny extended inputs | 1,024 |
| Wide arguments | 320 |
| Zero neighborhood | 8 |
| Out-of-range arguments | 8 |
| Separately identified actual-original operands | 5 |

All 11,664 independent inputs are generated before their returned words are
examined. The other five are every FSIN/FCOS event in the three named original
trace parents. Their inputs and outputs match the unchanged-original words
exactly. Two anchors are distinct calls using the same failing FCOS operand;
the count is observations, not unique operands. No operand, instruction or
result is patched.

## Rejected alternatives

[Intel's instruction discussion](https://www.intel.com/content/www/us/en/developer/articles/technical/the-difference-between-x87-instructions-and-mathematical-functions.html)
describes the finite internal Pi approximation and the resulting scaled
mathematical functions. That description does not specify all internal
arithmetic and does not prove that evaluating an ideal function reproduces
every returned instruction word.

The strict audit compares three calculations without changing the application:

1. The current guarded, scaled-Pi runtime calculation.
2. An unscaled ideal function, using the same guarded decimal evaluation.
3. The scaled ideal function rounded to 68 significand bits, then to the
   64-bit retained significand. This hypothesis was motivated by the separate
   logarithm multiplier-lattice observations; that evidence does not establish
   the cosine algorithm.

| Calculation | Raw R80 differences / 11,669 | Binary64-store differences |
| --- | ---: | ---: |
| Current scaled calculation | 117 | 2 |
| Unscaled ideal function | 1,478 | 758 |
| Scaled ideal with 68-bit intermediate | 298 | 2 |

Every calculation still differs at both failing joined-model FCOS calls. The
68-bit intermediate hypothesis therefore fails even to resolve the selected
case, and introduces more raw differences across independent inputs. The
unscaled alternative introduces many additional binary64 differences. Neither
is a valid replacement, and neither is shipped.

The current calculation differs on 115 independent observations plus the two
joined-model anchors. Only those two anchors cross binary64 rounding boundaries
in this corpus. Raw discrepancies still matter because ASITIC can retain these
values for later arithmetic. Passing a binary64-only comparison would not prove
retained-instruction parity.

## Reproduce

```sh
python tools/capture_trig_instructions_native.py
python tools/audit_trig_instructions_native.py --output /tmp/trig-differences.json
PYTHONPATH=src:tests python -m unittest test_trig_instruction_fixture -v
```

The native capture requires an i386 libc and dynamic loader. Their paths can
be provided with `--libc` and `--loader`. Captures on a different CPU must be
identified as a different observation, not silently substituted for this one.

The comparison audit exits **1** for the remaining differences. Fixture tests
verify complete input coverage, provenance, all original anchors and the
architectural unchanged-operand behavior for the selected out-of-range inputs;
they are not claims that the current runtime is exact.
