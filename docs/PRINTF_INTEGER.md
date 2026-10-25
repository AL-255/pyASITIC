# Original i386 integer formatting

`printf_integer.py` translates the pinned libc's `_itoa_word` and integer
output paths. `printf_format.py` dispatches signed decimal, unsigned
decimal, octal and hexadecimal conversions, with native `h`, `hh` and
i386 `l` modifiers, signs, alternate prefixes, padding, width and
precision. Zero with zero precision retains its native empty-digit
behavior; alternate octal retains its single zero. Digits come from the
actual earlier libc tables. Host string formatting and recorded output
do not supply simulator results.

The original ASITIC corpus is unchanged: 134 histories, 4,105 formatter
calls and 104,036 captured helpers, including both native fault outcomes.
Integer support completes 396 additional calls, including all 132 native
`asctime` formatters. The complete audit now executes 2,129 calls and
compares 710,969,455 four-byte units, 36,193 final registers, 5,194,760 FP
bytes and 933,980 registers at 27,470 helper boundaries. Registers, FP
and helpers match. All earlier required memory differences remain;
the newly executed calls add their own required targets.

The full CPU and merged browser reports agree in every counter, case
and difference. The complete gate retains 1,976 unfinished floating-point
calls and 762 rseq CPU-field word differences. The entry gate still
executes all 4,105 prefixes and retains the same 380 rseq word differences.
All eight CPU and browser shards exit nonzero on these required gates.
No conversion, owner, terminal outcome or later-state assertion is removed.

An independent request matrix supplements these state checks. A small
i386 harness makes normal variadic `snprintf` calls into the same pinned,
unmodified libc (SHA-256
`e936bd40e5479b27721efeade1b502623436a8be2bd8bd0f0ccf8c4f7229a0d0`).
Its startup invokes `__libc_start_main`; argument types match the requested
conversion. No inferior instruction, affinity, allocation, register or
return-state substitution is used. The harness records only lengths and
result bytes. These text probes do not replace the ASITIC memory/register/
FP/helper assertions or establish register parity for every probe format.

All 5,472 requests are independently generated before execution: six
conversion letters, four modifiers, twelve flag/width/precision patterns
and nineteen values spanning zero, radix transitions and the signed
character, short and integer boundaries. The original 3,456 requests
remain unchanged in the expanded set. The capture stores the harness,
compiler command, binary hash, minimal environment and input hash.
The compressed archive is 22,240 bytes, SHA-256
`01ef3727cb1f5b5e3205821ed07b9481824f617263d789cecdb9b196decb4c24`.

The source matrix uses one earlier native ELF image, independent
stack/TLS inputs and a memory buffer. The stack starts with a nonzero
pattern. Native output is only a comparison target. All 5,472 results
match in CPU Python and Pyodide, with identical complete reports. Seven
tests pass in both runtimes. They require changed requests and digit
tables to affect results, reject missing earlier tables and foreign libc
builds, and detect modified later output. The separate required CI job
runs every matrix request.

The expanded browser test exposed a reference cycle between the formatter
and its integer helper. A weak reference now breaks that ownership cycle.
The regression disables cyclic collection and requires each request's
formatter and memory to be released. All requests remain required; the
browser matrix is not reduced to fit its memory limit.

```sh
python tools/capture_printf_integer_original.py
PYTHONPATH=src:tests python -m unittest test_printf_integer_original
python tools/audit_printf_integer_original.py --output /tmp/integer-cpu.json
python tools/build_site.py
node tools/check_printf_integer_original.mjs /path/to/pyodide.mjs /tmp/integer-wasm.json
```

The subsequent [floating ABI flow](PRINTF_FP_FLOW.md) now implements the
captured binary64 floating paths with produced FP state. Long-long
integers, localized/grouped formatting and remaining parser/error/flush
branches stay unfinished. No call snapshot initializes continuing replay; the
broader 198-difference gate remains required. The verified source package
is `487886e57d1cec75`. The numerical module remains unchanged at SHA-256
`c7869e98f4c18b5414dc172d836e7144ab3ebc0de2de0d1f2eec1a4fe1709186`.
