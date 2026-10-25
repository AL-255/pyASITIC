# Parser caller frames and catalog comparisons

`parser_callers.py` follows the pinned i386 parser caller, tokenizer return
and command-catalog prologue from `command_runtime.cpp` and the original
instructions. The independent operations cover parser entry to tokenizer
entry, tokenizer return to catalog entry, catalog entry to its first
comparison, and the argument PUSH at every executed alias comparison.
Each operation consumes its actual earlier memory and GP state. All later
owned bytes, GP values and XSAVE bytes are comparison targets only.

The semantic parser also supplies actual argument-count and ordered alias
lookup events to `ParserCallers` on the continuing driver's original Memory.
Its saved registers come from the produced parser entry, and its pointers
come from the caller's real stack arguments. Every comparison writes its
argument through the same source loop. Argument-count errors preserve the
parent local skipped by the original branch. Changing the earlier command
changes the comparisons and stores; no four-word correction or later native
snapshot supplies these effects. The generated 117-row catalog is unchanged.

Tokenizer, strtok, strcmp and scanner instruction bodies and their volatile
register returns are not implemented by this caller component. Independently
verified operation boundaries do not establish a complete instruction-level
parser execution from one entry.

## Native evidence

The read-only capture preserves all 67 jobs cold and warm, including all
134 requests, scripts, stdin and terminal outcomes. One history reaches this
interactive dispatch. It executes 465 alias-argument pushes: 117 at the first
site and 116 at each of the other three sites. All are retained, together
with the older dispatcher entry/history/parse/parsed/kill points and the
new tokenizer/catalog boundaries. The original live catalog-head word is
an earlier input. No instruction, register, memory, allocation, signal,
CPU affinity or native outcome is replaced.

Observed runs retain 132 normal exits, one SIGSEGV and one SIGABRT. Plain
runs retain 128 normal exits, five SIGABRT and one SIGSEGV. The other 133
histories remain present with no reached interactive dispatch.

All 939 points retain 2,678 ordered owners and 666,044 bytes per point:
2,514,642 complete region records and 625,415,316 bytes in total. Repeated
pages and complete owner records are factored losslessly. Conversion checks
that every expanded ordered record equals its original before removing the
dense representation; replay validates every required page and region hash.
Duplicate or invalid owner overrides and corrupt page contents fail.
No address, owner, target word or reserved byte is excluded.

The 680,251-byte fixture has SHA-256
`ef596e868c95e5ea966d32d7a3e168b2dc6b62a82b4d024be059424248c5a643`.
The original 116,952,403-byte page-only archive is retained locally. All
parent fixture hashes remain required.

Complete CPU Python and packaged Pyodide reports are identical:

| Required comparison | Count |
| --- | ---: |
| Histories | 134 |
| Operations, including the three older dispatcher scopes | 471 |
| Alias-argument PUSH operations | 465 |
| Whole owned-memory four-byte units | 78,471,426 |
| Whole owned-memory bytes | 313,706,724 |
| GP values | 8,007 |
| XSAVE bytes | 1,149,240 |
| Differences | 0 |

All ten new tests pass in both runtimes. They cover changed earlier commands,
registers and arguments, the invalid-argument local-store branch, independent
later memory/GP/FP mutations, missing earlier memory, codec failures, and the
actual continuing Memory/register/event handoff. All 38 affected CPU
transition/dispatcher/stdio/input/read/getline/flush tests pass. The new
browser component is required in Pages CI, alongside every older gate.

## Continuing-driver result

The complete eight-shard browser continuation covers all 134 histories,
266 intermediate points and 103,364,142 later region bytes, with no unknown
bytes. The four parser caller words now match. Differences decrease from
28 to 24, all final component words in the rectangular cold history's saved
FP state. All intermediate points, the other 133 histories and all three
printf calls / 102 GP comparisons match. The affected complete CPU result
equals its browser result. A complete current-source CPU cohort was not run;
no full CPU/browser continuation equality is inferred from this one case.

The strict continuation assertion remains zero. Actual earlier FP must still
be propagated before connecting the composed kill-to-handler operation;
this component does not initialize it from a native inner snapshot.
Broader arithmetic, geometry, JOIN/UNJOIN, mapping and whole-program parity
remain unfinished. This branch is not promoted over the deployed Pages site.

The source package is `8ef350c4fd0013ba`. Numerical WASM is unchanged at
SHA-256 `c7869e98f4c18b5414dc172d836e7144ab3ebc0de2de0d1f2eec1a4fe1709186`.

```sh
python tools/capture_parser_callers_original.py --reference ~/github/asitic-re \
  --library-path /path/to/i386/libs --debug-directory /path/to/debug
PYTHONPATH=src:tests python -m unittest test_parser_callers_original
python tools/audit_parser_callers_original.py --output /tmp/parser-cpu.json
python tools/build_site.py
node tools/check_parser_callers_original.mjs /path/to/pyodide.mjs /tmp/parser-wasm.json
```
