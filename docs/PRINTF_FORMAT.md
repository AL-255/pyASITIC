# Original formatter source and complete required targets

`printf_format.py`, `strchrnul_storage.py`, `strlen_storage.py` and
`printf_padding.py` translate the pinned i386 glibc 2.39 formatter entry,
literal spans, narrow strings, decimal width/precision parsing, scalar
string probes and padding stores. They use the same guest memory and
buffer writer as `PrintfFile`. They do not call host string formatting,
load expected output, or substitute a later native snapshot. The
[integer component](PRINTF_INTEGER.md) adds native int32 paths. The
[floating ABI flow](PRINTF_FP_FLOW.md) now executes binary64 decimal
conversion with the original scratch stores, helper calls and produced
FP state. The independent [decimal](PRINTF_FLOAT_DIGITS.md) and
[x87](X87_FORMAT_STATE.md) components supply additional native checks.
Extended/hexadecimal, wide, positional, registered-handler, null-string
and remaining flush/error paths stay explicit unfinished branches.

`capture_printf_format_original.py` observes every formatter invocation
in the existing 67 jobs, cold and warm. This includes calls outside the
previous `vfprintf` parent, such as the native `asctime` formatter. The
original executable, legacy DSO, environment and original scripts are
unchanged. Generic memory buffers retain their actual declared bounds;
only FILE-mode buffers read a FILE object or obtain external descriptor
metadata. No non-FILE pointer is reinterpreted as a FILE.

Earlier owned data includes stack, heap, arena, ELF read-only/data/GOT
sections, full `struct pthread`, format bytes with actual aligned padding,
locale controls, the complete loader-declared static TLS extent and actual
output-buffer owners. Later complete memory,
heap/errors, 17 registers, XSAVE bytes and every captured helper entry and
return remain assertions. All overlapping owners and partial words are
retained. The initial write boundary supplies a separate prefix audit,
without removing conversions or helpers from the complete audit.

The first full capture omitted the libc GOT locale slot. Its complete
134-history archive was retained locally as evidence at SHA-256
`481f3fc5f8aa36fde89b2bc461240f8ea9897ae864a51fb020d60d65e58851e4`.
The source failed on that unknown earlier word; it did not infer the word
from later state. A corrected capture owns the GOT sections at entry.

The full archive retains all 134 histories, 4,105 formatter
calls and 104,036 captured helpers: 3,973 FILE-buffer calls and 132
memory-buffer calls. Both native fault histories remain present (one
SIGSEGV, one SIGABRT), alongside 132 normal observed runs. The lossless
codec verifies 12,315 states, 54,708 pages and every ordered owner. The
two-part archive is 56,824,093 bytes, SHA-256
`3229e7382362788a7f958b89e50f22ee8ce9ec0f72c6a3570b2dac91021b5693`.
The earlier 56,655,603-byte archive is retained unchanged locally at
`/tmp/pyasitic-printf-format-before-static-tls`, SHA-256
`edc7724655ee6279ee2f224b41f351ed5c0d23cd0fb321734173447e74b41278`.
The static-TLS recapture preserves every request/script/stdin/variant,
native outcome and per-history call/helper count. It corrects the missing
earlier ctype TLS slot without inferring a pointer from later state.

The entry audit executes every one of the 4,105 prefixes. It compares
1,374,813,338 four-byte units, 69,785 final registers, 10,016,200 FP
bytes and 139,570 registers at 4,105 search-helper boundaries. Registers,
FP and helpers match; 868 kernel-maintained rseq CPU-field word occurrences remain
required memory differences.

The complete CPU and browser audits execute all 4,105 calls, adding all 1,976 formerly
unfinished floating calls to the literal/string/integer paths, including
the nine-column `%-11.11s` format and all 132 native `asctime` formatters.
It compares 1,374,813,338 four-byte units, 69,785 final registers,
10,016,200 produced FP bytes and 3,537,224 registers at all 104,036 helper
boundaries. Registers, FP, helpers and non-kernel memory match. The gate
still fails on 4,048 rseq CPU-field word occurrences. No conversion,
owner or overlapping assertion is removed.

Eight disjoint CPU and browser shards run the complete required tests.
Their merged reports agree exactly in every case, counter and difference.
All sixteen final shard runs execute eleven tests: ten pass, and the
combined native comparison retains two failing subtests. All exit nonzero.
Both native comparison subtests (prefix and complete) remain failing
because the kernel-maintained rseq words are required. The new regression
checks require actual earlier FP and TLS inputs, changed float arguments
to reach output, and produced FP bytes to match their changed native
state. Reports retain every case, counter and difference.

The rseq words are part of the complete pthread owner and are not
exempted. CPU affinity, the inferior, return state and recorded targets
are not changed to hide CPU migration.
The pinned libc debug type places `rseq_area.cpu_id_start` and `cpu_id`
at pthread offsets 1184 and 1188 (`0x4a0` and `0x4a4`), with a complete
pthread size of 1216 bytes. The full static-TLS owner also includes those
words, and both overlapping assertions stay required. These targets need external kernel-event
modeling; the formatter's string instructions do not write them.

Both strict audits, all native histories and all original terminal
outcomes remain required. Tests mutate targets and earlier string input,
require unknown bytes to fail, check scalar alignment and bounded reads,
and reject absent capture boundaries. The browser runner executes the
same tests and emits both complete reports locally. Eight disjoint CI
shards are required; the unfinished formatter gates must fail.

```sh
python tools/capture_printf_format_original.py --reference ~/github/asitic-re \
  --library-path /path/to/i386/libraries --debug-directory /path/to/debug
PYTHONPATH=src:tests python -m unittest test_printf_format_original
python tools/audit_printf_format_original.py --prefix --output /tmp/format-prefix.json
python tools/audit_printf_format_original.py --output /tmp/format-complete.json
python tools/build_site.py
node tools/check_printf_format_original.mjs /path/to/pyodide.mjs /tmp/format-part.json 1 8
```

No formatter call boundary initializes continuing replay. The broader
continuing gate's 198 required differences remain unresolved.
The verified source package is `ba1bb18a1356eb05`; the compiled numerical
module remains unchanged at SHA-256
`c7869e98f4c18b5414dc172d836e7144ab3ebc0de2de0d1f2eec1a4fe1709186`.
