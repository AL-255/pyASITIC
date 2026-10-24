# Rejected P5/P6 logarithm experiment

`candidate.py` translates the table/polynomial evaluation in the unmodified
Bochs files retained here, at revision
[`3e874945d66e5332791b37185d98dec2bfdd2580`](https://github.com/bochs-emu/Bochs/tree/3e874945d66e5332791b37185d98dec2bfdd2580/bochs/cpu/fpu).
`upstream.json` records their verified source paths and SHA-256 checksums.
Upstream notices and `COPYING` are preserved. This experiment is separate from
the ASITIC package and browser artifact; neither imports it.

The translation keeps explicit 67-bit truncation, 64-bit nearest-even steps,
113-bit intermediate rounding and the final extended store. Its tables are
upstream algorithm constants, with no captured output words or special cases
for the failing ASITIC inputs. Exception flags and arbitrary unsupported
encodings are outside this experiment's scope.

Run the independent evidence audit from the repository root:

```sh
python tools/audit_log_instructions_native.py --p6-experiment --output report.json
```

It intentionally exits nonzero while any output differs. On the recorded AMD
Ryzen 9 7940HX, the current guarded evaluation differs in 184 of 8,182 raw
instruction results, and this experiment differs in 560. Each has one
binary64 discrepancy in this input set. The experiment matches 65 of 67
instruction words captured inside unchanged original ASITIC commands, compared
with 53 for guarded evaluation. Those selected failures alone therefore give a
misleading impression of the experiment's suitability as a replacement.

This candidate was rejected. The wider independent input set remains available
for evaluating a future instruction implementation. See
[the logarithm audit](../../../docs/LOGARITHM_AUDIT.md) for provenance, scope and
the separate multiplier-width evidence.
