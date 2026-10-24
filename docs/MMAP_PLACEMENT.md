# Mapped allocations toward native simulation parity

The subsequent [shared-memory component port](SHARED_MEMORY.md) now reproduces
native via stores and the damaged cache chains using byte-backed tcache state.
It preserves this earlier fixture and its unresolved-input audit results.

The development allocator now implements glibc's i386 mmap chunk sizing,
alignment, unmapping, allocation statistics and dynamic mmap/trim thresholds.
It also models the bin bitmap and maximum arena size. This extends the
[arena placement port](HEAP_PLACEMENT.md); it does not yet enable trailing-via
electrical models or derive pre-CAP process state in production.

The algorithms follow glibc 2.39 `malloc/malloc.c`:
<https://github.com/bminor/glibc/blob/glibc-2.39/malloc/malloc.c>.
In particular, mapped allocations have a separate header and page-rounding
rule. Freeing a suitably sized mapping raises the dynamic threshold; the next
same-sized request can then use brk instead. Treating every large request as
a fresh mapping would give different placement in repeated simulations.

The address-space model uses a descending first-fit search over occupied
virtual ranges. Its ceiling comes from independently read process personality,
stack limit, guard-gap configuration, page size and kernel layout settings,
following the x86 layout rules described in the Linux sources:

- <https://github.com/torvalds/linux/blob/v7.0/arch/x86/mm/mmap.c>
- <https://github.com/torvalds/linux/blob/v7.0/arch/x86/include/asm/page_64_types.h>
- <https://github.com/torvalds/linux/blob/v7.0/mm/mmap.c>

The current implementation supports the captured nonrandomized, top-down,
4096-byte-page layout. It explicitly rejects missing policy inputs, randomized
or legacy layouts, alternate page sizes and automatic huge-page placement.
It does not derive a ceiling from a desired allocation address or from a
selected case's returned pointer.

## Original ASITIC evidence

`capture_mapping_allocator_original.py` extends the previous read-only
observer, retaining every one of the 65 selected input configurations in cold
and warm cache states. The new fixture is
`allocator_mappings_original.json.gz`; its parent hashes retain the original
allocator, lifetime and earlier cache experiments unchanged. Plain/GDB pairs
still begin with byte-identical inputs and native cache files in the same cwd.

The new observer records layout inputs from `/proc`, mapped allocation headers
and existing arena snapshots. It reads the process personality rather than
assuming GDB successfully disabled randomization. It performs no inferior
calls and replaces no allocator or numerical operation.

The source plan plus initial snapshots now reproduce:

- All **3,117 allocation addresses and 12,877 allocation/free events** across
  130 observations, including the twenty mmap cases that previously stopped.
- All 130 pre-via boundaries and 129 completed node boundaries, including bin
  order, bin bitmaps, main-heap headers, mapped-chunk headers, malloc parameters,
  maximum arena size and occupied address-range unions.
- All 132 via target addresses and their mapped/unmapped classification. The
  cold `square/64/contacts` target lies outside mapped memory, matching the
  original load fault. No artificial finite value is substituted.

There are zero address or compared-state differences. **Three observations
remain unresolved in the strict audit** because the native stamp corrupts a
tcache chain before node entry: cold `square/1/filaments`, warm
`pilot-width3/1/filaments`, and warm `pilot-boundary/1/filaments`. The observer
records each damaged chain ending at unreadable address `0x8100`; the model
does not yet apply numerical stores to allocator metadata.

The complete plain runs in this independent capture have 123 normal exits,
five SIGABRT exits and two SIGSEGV exits. Their differences from previous
captures are retained evidence of undefined native heap behavior, not a basis
for replacing previous outcomes or promising deterministic faults.

## Independent allocator histories

`capture_mmap_sequences_native.py` compiles a small i386 C/assembly driver and
links it to the same libc. These probes are explicitly **libc observations,
not ASITIC numerical reference outputs**. Matching libc/debug build IDs and
hashes, loader hash, complete sources, build commands, tool versions, plain
exits and GDB observations are recorded in `mmap_sequences_native.json.gz`.

Six independently chosen histories exercise repeated allocation after a
threshold increase, middle-hole reuse, the i386 dynamic-threshold cap,
reverse-order unmapping, multi-megabyte blocks and interleaved arena/mapped
allocations. All 29 allocation addresses, 58 allocation/free events and 64
boundary states match, including mapped ranges and all malloc parameters.
There are no native metadata errors in these probes.

## Gates and remaining work

Nine CPython fixture/placement tests pass; the new three tests also run against
the actual packaged Pyodide allocator. Passing address tests do not waive the
three native damaged-list observations: the new mandatory `mappings` WASM job
runs the full strict audit and still exits 1 for those observations.

The older `heap` suite and every JOIN/UNJOIN numerical gate remain mandatory.
The older snapshot fixture lacks independently captured mapping policy; its
twenty missing-policy boundaries and two native metadata errors remain visible
in its strict audit. No prior fixture, selected input or failure was removed.

Production still needs allocation history before the CAP scope, shared memory
for numerical and allocator writes, complete repeated-ASITIC simulation and
cleanup validation, and the unresolved numerical-instruction differences. The
new placement code remains disconnected from electrical solves. This is not
a claim of complete original-binary parity.

```sh
python tools/capture_mapping_allocator_original.py --debug-directory /tmp/debug/usr/lib/debug --reference /path/to/asitic-re --library-path /path/to/native-libraries
python tools/capture_mmap_sequences_native.py --debug-directory /tmp/debug/usr/lib/debug
PYTHONPATH=src:tests python -m unittest test_mapping_heap_original test_heap_original test_allocation_plan_original -v
python tools/audit_allocator_original.py --fixture tests/fixtures/allocator_mappings_original.json.gz --output /tmp/mapping-differences.json
python tools/build_site.py
node tools/check_mapping_heap_original.mjs /path/to/pyodide.mjs
```

Both strict audit commands still exit 1 for the three damaged-list observations.
