# Complete CAP buffers before cleanup

The production capacitance calculation now exposes immutable observations of
its final full contact admittance, reduced, folded and output matrices.
These are the same values used by `solve_capacitance`; no alternate solver or
captured numerical input is involved. This extends the
[contact byte stores](CONTACT_STORAGE.md) toward reproducing the native bytes
that remain after CAP buffers are freed.

`capacitance_storage` extracts the CAP portion of the existing combined-network
allocation plan. Its allocations, workspace frees and later cleanup retain the
same order and sizes. The full combined-network history remains independently
required and unchanged. `ComplexView.write` stores a complete matrix in the
original column-major guest layout, preserving any stride padding.

## Why the intermediate matrices matter

Tracing all 132 via targets in the selected 130 histories gives 50 targets in
the live CAP output, two in the live inductive output and one unmapped target.
The remaining 79 reach freed heap memory: 22 cached chunks, 36 bin chunks and
21 locations in the top chunk. The most recent complete numerical allocation
covering 34 targets is `cap.folded`; another 24 were covered by `cap.full`.
Their bytes can survive cleanup and affect later out-of-range native via
stores. A total capacitance or only the folded output cannot reconstruct them.

These are diagnostic address relationships from complete histories, not a
runtime target-to-value table. The implementation writes every element of all
four matrices, independent of whether a later target reaches it.

## Original observations and exact checks

`capture_cap_storage_original.py` records every final CAP buffer at native
`release_potential_contacts` entry, `0x8056524`. This is before their first
contact or matrix free. It uses read-only GDB observations and preserves all
65 selected scripts in both cold and warm cache states, including exploratory
pilots and both split-balun commands. The cold `square/64/contacts` later node
fault remains present. Prior fixtures are unchanged.

The fixture retains complete matrices, descriptors, scalar/array allocation
events, allocator snapshots, original plain outcomes, file/cache hashes,
binary/DSO/libc provenance and the exact observer commands. This independent
capture has 125 normal plain exits, four SIGABRT exits and one SIGSEGV exit;
the observations do not establish deterministic undefined-memory outcomes.

The comparator independently generates geometry, mesh, contact counts and CAP
matrices from the request. Starting with the earlier contact-entry allocator
snapshot, it predicts allocation placement through the pre-cleanup boundary,
then fills initially unknown guest memory from the generated matrices. Native
buffer bytes serve only as expected values.

The packaged Pyodide/WebAssembly check matches every selected observation:

- **130 histories and 520 complete matrices**.
- **841,328 binary64 words**, compared without tolerances.
- **780 allocation addresses and 1,040 allocation/free events** between CAP
  matrix entry and the pre-cleanup boundary.
- **Zero differences**, including complete contact inverse buffers through
  192 contacts and both split-balun configurations.

Portable tests separately check the first cold/warm native history. Tests also
verify immutable observations, unchanged generated matrices when an original
expected word is changed, exact signed-zero stores, aliasing, stride padding
and dimension validation. The full compiled corpus is mandatory rather than
substituted with these smaller portable cases.

## Required checks and remaining work

The new mandatory `capstorage` WASM suite runs the tests and all 130 complete
buffer comparisons. Python discovery includes the portable/provenance tests.
Every older prelude, contact, shared-memory, heap/mapping and JOIN/UNJOIN gate
remains required.

```sh
python tools/capture_cap_storage_original.py --debug-directory /tmp/debug/usr/lib/debug --reference /path/to/asitic-re --library-path /path/to/native-libraries
PYTHONPATH=src:tests python -m unittest test_cap_storage_original test_allocation_plan_original -v
PYTHONPATH=src python tools/audit_cap_storage_original.py --output /tmp/cap-storage-portable-audit.json
python tools/build_site.py
node tools/check_cap_storage_original.mjs /path/to/pyodide.mjs /tmp/cap-storage-audit.json
```

This checks matrix bytes while all four buffers are still live. Replaying
their cleanup, allocator metadata stores and subsequent numerical allocations
into the same byte memory is still required before these values can replace
the raw via-entry heap inputs. Earlier process/scene/cache history, numerical
workspace contents and repeated-command cleanup also remain unfinished.
The production trailing-via guard remains enabled. Other known logarithm,
cosine and JOIN/UNJOIN discrepancies continue to prevent release of this
development branch; complete original-binary parity is not yet established.
