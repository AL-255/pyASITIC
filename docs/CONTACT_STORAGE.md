# Source-generated contact and group bytes

`contact_storage.py` now materializes the initialized contact/group fields from
`contacts.cpp` and the later numbering stores in `potential_solver.cpp`.
It uses the same retained contact geometry as production, including its
binary64 physical bounds and integer grid indices. Addresses come from the
[source-derived contact allocation history](CAP_PRELUDE.md), not an object
address table selected by geometry.

This is another producer for the shared guest memory under development. It is
not yet connected to production electrical solves. The normal trailing-via
guard and every existing numerical/allocator release gate remain enabled.
The subsequent [complete CAP storage check](CAP_STORAGE.md) also regenerates
the four numerical buffers before cleanup at their predicted allocations.

## Store semantics

After successful contact construction, the writer sets:

- The NUL-terminated group name, translated endpoint coordinates, width/length
  cell counts, metal, first-contact pointer and next-group pointer.
- Each contact's four physical bounds, four integer grid indices, metal and
  next-contact pointer, in the original final linked-list order.

The group name's remaining bytes and group `+124` are untouched. The incoming
contact `+52` word comes from an earlier stack slot in the original builder.
Without that caller history it is explicitly unknown; copying it invalidates
any old known heap bytes at the destination. It is never implicitly zeroed or
replaced with a captured output. An explicit caller-provided history word can
be copied when available.

`number_contacts` later writes consecutive contact indices in linked order.
`number_groups` writes the group `+124` indices during capacitance reduction.
Consequently all 60 contact bytes become defined without depending on the
temporary stack value. Group name padding remains untouched throughout.

The writer materializes completed prepared lists at already allocated guest
addresses. It does not claim intermediate construction snapshots, partial
failure cleanup, secondary segment chains or complete allocator byte stores.
The selected CALCTRANS histories use the source's first automatic-copy name,
`source + '_'`; an existing collision requires the as-yet-unported native
random-state history and is rejected explicitly by the comparison.

## Independent original observations

`capture_contact_storage_original.py` extends the read-only allocator observer
with full group/contact bytes at two native boundaries:

1. `0x8052ec7`, before CAP matrix construction and contact numbering.
2. `0x8056524`, the contact-release entry after matrix/contact/group numbering
   and before their first free.

The fixture retains all 65 selected histories in both cold and warm cache
states, including every exploratory pilot, both split-balun commands and the
later cold `square/64/contacts` node-load fault. Scripts, input-file/cache
hashes, original/DSO/libc provenance, allocator snapshots, full plain outcomes
and observer commands are retained. The preceding fixtures are unchanged.
This independent capture has 126 normal plain exits, three SIGABRT exits and
one SIGSEGV exit. These observed outcomes do not establish deterministic
undefined-memory behavior across runs.

The source-generated comparison first predicts allocation placement from the
earlier contact-entry allocator snapshot, then writes into initially unknown
guest memory. It does not initialize records from the captured object bytes.
Every initialized range is compared byte for byte at both stages:

- **130 observations and 9,744 object-stage checks**, covering 1,842 group and
  3,030 contact allocation identities at two stages.
- **558,096 defined bytes**, with zero differences in CPython and packaged
  Pyodide/WebAssembly.
- **306,528 unknown bytes** explicitly remain unknown at their respective
  stages. These are unwritten group bytes and the temporary contact index;
  they are not counted as matching numerical data.

Tests also initialize old heap bytes with nonzero sentinels to check preserved
padding, invalidate the incoming stack word, and verify numbering overwrites
that word independently. Changing a captured physical-bound bit must fail
comparison without changing the generated records.

## Checks and remaining work

The mandatory `prelude` WASM suite now runs all four contact-storage tests in
addition to the existing contact/cache tests and full regenerated-matrix
comparison. Ordinary Python discovery includes the same tests. No earlier
JOIN/UNJOIN, numerical, heap or mapping gate is removed or relaxed.

```sh
python tools/capture_contact_storage_original.py --debug-directory /tmp/debug/usr/lib/debug --reference /path/to/asitic-re --library-path /path/to/native-libraries
PYTHONPATH=src:tests python -m unittest test_contact_storage_original test_contact_geometry_original test_cap_prelude_original -v
python tools/audit_contact_storage_original.py --output /tmp/contact-storage-audit.json
python tools/build_site.py
node tools/check_cap_prelude_original.mjs /path/to/pyodide.mjs /tmp/prelude-audit.json /tmp/contact-storage-wasm-audit.json
```

Earlier process/scene allocations, unknown incoming bytes, complete allocator
metadata stores, intermediate numerical workspaces, repeated-command cleanup
and the known logarithm/cosine and JOIN/UNJOIN discrepancies still need work.
The complete production simulator's original-binary parity remains unproven.
