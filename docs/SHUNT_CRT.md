# Continuing through the main ELF destructor

The continuing source now completes the main executable's ELF finalizer,
both application global destructors and legacy unwind-frame deregistration.
It returns to the actual loader traversal on the same memory and allocator
and reaches MesaGL's ELF finalizer. That next body remains unimplemented.
Complete caller/lock/frame stack, GP and FP execution and the earlier missing
lazy bindings remain strict failures. This development branch is not deployed.

## Original source order and live stores

The reference executable's `_fini` at `0x080b4784` calls
`__do_global_dtors_aux` at `0x0804af20`. The latter checks its completion
word, walks the actual cursor/table at `0x080cb984`, advances the cursor before
each indirect call, calls `__deregister_frame_info(0x080d0560)` and only then
marks completion. `decomp/output/asitic.c` and the intact executable agree
on this order. The table contains `destroy_log_path_strings` (`0x0804bdb0`)
followed by `destroy_port_command_state` (`0x08060cb0`). No captured later
callback sequence supplies the source loop.

The application destructors invoke the actual member destructors at
`0x080b2240` and `0x080b3b40`, with their original in-charge argument of two.
The log object destroys five string members in reverse offset order; the
port object destroys its member at offset `0x74`. They share the existing
`LegacyStrings.destroy` reference-count and SGI pool implementation. Pool
release now executes the live pthread lock/unlock operations around the
actual free-list writes. Each lock keeps its own complete entry/return
assertions, including the held lock and published owner/count fields.
The original pinned libc ordinary-mutex path is used for this cohort;
contended/multithreaded and other unimplemented branches remain explicit.

The pinned legacy runtime's `__deregister_frame_info` at offset `0x3084c`
walks its actual linked registry, compares `fde_begin`, unlinks the matching
node through its preceding link and returns that node. The main record is
at the head in these genuine earlier inputs. The source algorithm also walks
interior links; descriptive `frame_nodes` metadata is not consulted. The
registry lock follows the original binary branch. All four earlier frame
records have zero `pc_begin` and null sort-array pointers in the captured
cohort, so this main deregistration performs no malloc free. The source's
optional sorted-table release branch remains unverified by this cohort.
The later three native frees still belong to X11's unexecuted finalizer.

## ELF values without fabricated caller state

The source resolves the main import from its real relocation, symbol/hash,
scope and version metadata. The selected provider is the legacy runtime,
not a hardcoded observed return. The value entry follows the ordinary
[glibc lookup algorithm](https://github.com/bminor/glibc/blob/glibc-2.39/elf/dl-lookup.c)
and uses the existing ELF readers. It performs the real relocation-counter,
provider-used and GOT stores. Bound imports bypass lookup, and a changed
earlier provider symbol changes the resulting binding. The source shares
the existing CPU-feature-based IFUNC selectors with the complete PLT ABI
implementation; all eight earlier native binding cases, including their
IFUNC targets, remain checked.

This value entry does not construct imaginary caller registers or an
unrelated guest scratch stack. Its native stack/GP/FP counterparts remain
required by the complete audits. The existing full lookup/fixup ABI tests
also remain unchanged and passing. The new entry lets the actual destructor
algorithm advance while leaving its missing CPU execution visible.

## Genuine earlier inputs and complete later targets

A new read-only capture retains every unchanged fourteen-script cold/warm
history and all parent solve, command, output, allocator, cleanup and exit
targets. Every native plain and observed run exits normally. Genuine
first-driver inputs add the CRT cursor/table/completion bytes, both global
objects, every initial string Rep, the pool/mutex, and the legacy registry
head, four records, mutex and weak-control slot. No later destructor result,
GOT value, returned node, callback order, free or process status initializes
the full source replay.

There are **420 native CRT calls / 840 phases**, covering the main finalizer,
CRT traversal, both application/member destructors, registry removal and
eight mutex operations per history. Each point retains all seventeen
registers, XSAVE, allocator state and event count, complete stack, mapped
heap, arena, stream-list head, and every previous stdio/exit owner plus the
new CRT owners. All previous owners stay in their original order, and the
new earlier owners are appended. No mismatching field or range is excluded.

| Complete assertion transport | Regions | Captured bytes |
| --- | ---: | ---: |
| All parent exit phases with new earlier owners | 514,500 | 4,245,131,100 |
| Main CRT/member/registry/mutex phases | 147,000 | 1,212,894,600 |

Every region is expanded and hash-checked even when its source phase is not
yet reached. Heap dictionaries are factored losslessly: **3,780 states / 56
distinct bodies**, with independent mutable expansions. Five complete byte
banks are external files; their compressed SHA-256, entry and byte counts
and every individual content hash remain required. The original exit
fixture and its two-bank transport are unchanged.

The independent component starts once at the genuine main-fini entry, then
executes all fifteen calls per history without using any later snapshot.
All non-stack memory, pool/mutex/registry/ELF stores, allocator states and
all **252 defined return values** match the native outputs. It checks
**293,119,240 word units / 812 output boundaries**, with zero unknown bytes.
Its strict report still fails with **33,256 differences**: 31,632 stack
words, 812 missing GP boundaries and 812 missing FP boundaries. No phase,
runtime, argument, defined-return or non-stack failure is waived.

The full continuing source checks all thirty CRT phases per history and
returns from the actual main object/fini calls before entering MesaGL. It
still retains the earlier loader relocation-counter deficit at every reached
exit/CRT boundary, instead of substituting counts from this capture. The
broader complete gate remains failing; finishing the main destructor does
not establish full binary fidelity.

| Full continuing assertion | Checked |
| --- | ---: |
| Exit calls entered / complete memory boundaries | 196 / 252 |
| Complete exit word units | 90,968,040 |
| CRT calls entered / complete memory boundaries | 420 / 840 |
| Complete CRT word units | 303,226,800 |
| Defined CRT argument words / return values | 364 / 252 |
| Computed initialized-object order positions | 532 |
| Unknown compared bytes | 0 |

The complete audit retains **1,548,913 failures**, including all earlier
requirements. Of the new exit/CRT word failures, 232,885 exit and 778,320 CRT
words are in the stack, and 252 exit plus 840 CRT words expose the earlier
loader-counter deficit. The 2,688 later exit phases remain missing, together
with complete GP/FP, X11 free/heap/event and final-process requirements.
The larger full report reflects added required boundaries, not a tolerance
change or a passing program result.
The complete CPU and final packaged WebAssembly reports are byte-identical:
312,712,119 bytes each, SHA-256
`f04ce72d96f5e3702a5af8260afc675bf037adf0c14904e60728035f0d9a5929`.

Nine new regression tests cover every complete native region and provenance,
all independent outputs and defined returns, actual full continuation,
modified later-target independence, changed cursor/registry/binding inputs,
missing earlier bytes, descriptive-inventory independence, transient lock/pool
ordering despite identical final memory, repeat-completion and contention.
They supplement the complete failing audit, rather than converting it into
a passing gate.
All 90 targeted portable regression checks and all nine new WebAssembly
checks pass; CI discovery includes all nine. The prior complete exit report
is unchanged in every field at 664,133 strict failures. The older 130+4
command reports are likewise identical (zero and 816 differences), and all
eight printf/parser shard reports retain their parent fields, including
shard five's 24 saved-FP failures. The downloadable native source archive
rebuilds the unchanged numerical module byte for byte.

`shunt_crt_original.json.gz`: 101,404,446 bytes, SHA-256
`d18df5f02f39182ff797d44c4c22dc32d1dc408e4f81c4fa7ddb3480f874a7be`.
The five byte-bank files and their exact hashes are recorded in its
`external_banks` manifest and verified by `exit_fixture.read_fixture`.
Each file is below 100 MiB; no captured byte was removed to meet that limit.

Source package `eb65311d39f5302c` contains all 198 current runtime source
files, byte for byte, and no fixtures. Numerical WASM remains
`c7869e98f4c18b5414dc172d836e7144ab3ebc0de2de0d1f2eec1a4fe1709186`.

```sh
python tools/capture_shunt_crt_original.py --reference ~/github/asitic-re \
  --library-path /path/to/i386/libs --debug-directory /path/to/libc/debug
PYTHONPATH=src:tests python -m unittest test_shunt_crt_original -v
python tools/audit_shunt_crt_original.py --isolated --output /tmp/crt-isolated.json
python tools/audit_shunt_crt_original.py --output /tmp/crt-full-cpu.json
python tools/build_site.py
node tools/check_shunt_crt_original.mjs /path/to/pyodide.mjs /tmp/crt-full-wasm.json
```
