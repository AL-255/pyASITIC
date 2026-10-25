# Original public printf entry routines

`printf_entry_storage.py` executes the pinned i386 glibc `printf`,
`fprintf` and public `vfprintf` argument/frame stores, their real internal
`vfprintf` child, and the final return on one Memory/Heap/FILE. It follows
the original `printf.c`, `fprintf.c` and `vfprintf.c`, under LGPL-2.1-or-later.
The source uses the live stdout binding, format and variadic arguments.
`printf` also retains its PIC thunk's otherwise unused stack word. The
public va_list entry forwards the actual pointer without inventing an
argument list. Registers and produced FP state continue through the
[whole parent and formatter](VFPRINTF_WHOLE.md). No inner state snapshot
or captured output supplies execution.

The new read-only capture retains all 67 unchanged jobs, cold and warm:
134 histories, 3,973 public calls (140 `printf`, 3,833 `fprintf`), 123,122
helpers and 7,946 complete formatter entry/return states. Every older
parent call and its complete helper sequence remains, with one additional
internal-vfprintf entry/return assertion per call. Every request, script,
stdin, variant and observed native outcome matches the previous cohort.
The older archives remain unchanged and required. The new plain runs
retain their actual 128 normal, five SIGABRT and one SIGSEGV outcomes;
observed runs retain 132 next-driver stops, one SIGABRT and one SIGSEGV.
No outcome is retried or filtered.

Each public entry owns its earlier full stack, heap/arena, FILE and locks,
descriptor facts, aligned format bytes, original ELF data/GOT/rodata,
complete pthread and loader-declared static TLS, CPU profile and FP image.
Lossless conversion verifies all 15,892 states and 45,197 pages, retaining
38,684 region records, 3,664 contexts and 928 FP images. The two-part
49,706,713-byte archive has SHA-256
`8c8a91fd27db7c008c7f26abfd6ab6bc073d9592af737d61e1ec75427c6a1c8a`.
Part and complete-stream checksums remain mandatory.

The complete CPU and Pyodide reports are identical for every case,
counter and difference. They execute all 3,973 public calls and check
1,327,502,534 final four-byte units, 67,541 final GP values, 9,694,120 FP
bytes and 4,186,148 helper GP values. Its 7,946 inner assertions additionally
check 2,655,005,068 four-byte units, 135,082 GP values and 19,388,240 FP bytes.
All non-kernel memory, heap state, GP/FP and helper comparisons match.
The gate still fails on 10,132 required rseq word assertions: 2,306 per
CPU word at public return, 2,094 per word at formatter return and 666 per
word at formatter entry. Both overlapping pthread/static-TLS owners are
retained. CPU-affinity controls, kernel targets and native outcomes are
not changed to make this comparison pass.

The shared whole-state auditor initializes execution once, at the public
entry. Its observers assert produced inner memory/heap, GP/FP and helper
boundaries without resetting them. Tests mutate earlier strings, later
GP/FP/heap/helper targets and missing input bytes. Neither a later target
nor a recorded child return repairs execution. Eight disjoint browser
shards retain every case; reports stay local.

## Independent native entry and extreme-value probe

An independent i386 caller additionally executes six requests through
each public entry, including explicit `va_list` forwarding. All 18 calls
use declared string, uint32 and raw binary64 arguments. Values include
1.25, negative zero, the least positive subnormal, the largest finite
double, infinity and a quiet NaN. The native program and its complete
earlier entry contexts, later owned states, FP bytes and helper GP pairs
are retained. It uses the same pinned, unmodified libc and minimal
environment, normal native startup and no inferior substitution.

The minimal caller selects libc's old stdout object. This independently
exposed the old xsputn, overflow dispatch, compatibility orientation,
old overflow and zero-length do_write paths. `output_file.py` now follows
those routines through actual modern buffer allocation, descriptor-stat
conversion, malloc and setb. A missing legacy C++ DSO no longer prevents
modern libc callbacks from executing; an attempted C++ callback without
its earlier binding still fails explicitly. Other old output/error paths
remain unsupported, rather than being approximated.

The extreme inputs also exposed two multiprecision omissions. The fixed
source now includes the actual ADD/RET PC thunk at `0x50610`. The unrolled
subtractor's CALL to its next instruction obtains its PC and discards
that word before an indirect jump; it does not create a separate function
frame. `printf_fp_flow.py` now preserves that control flow. Every earlier
instruction remains unchanged, and no later return target is read to
choose the path. The regenerated program has 5,316 instructions and
221,305 bytes, SHA-256
`dc3f3d4a61156e5bc4b9e7ac13ac88ab13ce7e396672fd7ff02f50e6c6fc195c`.

All 18 independent calls now execute with 36 produced inner states and
548 helpers. The strict comparisons include 306 final GP values, 18,632
helper GP values, 43,920 final FP bytes and 87,840 inner FP bytes. Kernel
rseq words, both overlapping owners, and every native outcome remain
required. Its 60 remaining CPU differences are all rseq words: 14 per
word at public return, 14 per word at formatter return and two per word
at formatter entry. The 379,793-byte compressed probe has SHA-256
`ad11d6a591717a95514b4f91ff79b20061b88eef5a1b293e49ded34404b25ba9`.
Its complete CPU and browser reports also agree exactly across all
sixteen runs. Each final shard executes ten tests: eight pass, and both
complete native-state gates fail on their retained rseq assertions.
There are no execution errors. The updated instruction-semantics tests
pass in both runtimes. All twelve combined CPU instruction/flush tests
pass, including every earlier native flush target. The seven browser
flush tests and complete 414-call browser audit also pass with zero
differences across 98,167,038 owned four-byte units, 7,038 registers,
1,010,160 FP bytes, 413 writes and 198,537 emitted bytes. Reports remain local.

The verified source package is `ca0716496014d7f0`; the numerical module
remains unchanged at SHA-256
`c7869e98f4c18b5414dc172d836e7144ab3ebc0de2de0d1f2eec1a4fe1709186`.
This component does not yet connect public printf into the
continuing ASITIC command/console path. Its broader 198-difference gate,
all earlier component gates and complete simulator fidelity remain
unfinished.

```sh
python tools/capture_printf_entry_original.py --reference ~/github/asitic-re \
  --library-path /path/to/i386/libs --debug-directory /path/to/debug
python tools/capture_printf_entry_probe.py --debug-directory /path/to/debug
PYTHONPATH=src:tests python -m unittest test_printf_entry_original
python tools/audit_printf_entry_original.py --output /tmp/entry-cpu.json
python tools/build_site.py
node tools/check_printf_entry_original.mjs /path/to/pyodide.mjs /tmp/entry-part.json 1 8
python tools/merge_vfprintf_whole_reports.py /tmp/entry-part-*.json --output /tmp/entry-all.json
```
