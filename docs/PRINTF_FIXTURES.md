# Lossless native printf snapshots

The printf capture being developed records every post-driver buffer-write
boundary, including full earlier/later regions, all registers, XSAVE and
nested child register boundaries. Repeating loader metadata and large
region lists in every snapshot would exceed browser fixture limits. The
storage helpers compact those records without removing any owner or byte.

`tools/printf_fixture.py` factors identical contexts and FP records by
SHA-256. Ordered region lists use complete templates plus indexed updates.
Each reconstructed list has its own hash of the full ordered region keys,
which include address, size and content hash. Decoding rejects malformed
indices, duplicate/out-of-order updates, altered templates, conflicting
fields and changed context/FP contents.

Region page lists use indices into a complete page-key table. Each page is
compressed separately; when smaller, it stores XOR against a full base
page at the same captured address and extent. Every base and reconstructed
page is checked against its original SHA-256. Bases cannot form chains.
The bounded decoded-page cache keys on both identity and encoded content;
missing or changed earlier content cannot reuse a previous cached value.
The source simulator does not read this fixture encoding.

`tools/pack_printf_fixture.py` checks every expanded snapshot field and
ordered region reference against its dense input before discarding that
representation. It separately verifies each original page byte and ordered
record page list. The output records the dense archive hash and checked
boundary/page counts. Snapshot expansion creates independent region/page
lists, preserving later-target mutation checks. Memory loading retains the
exact mapped union and every gap and unknown byte.

```sh
python tools/pack_printf_fixture.py dense.json.gz compact.json.gz
python tools/split_printf_fixture.py compact.json.gz printf_buffer_original.manifest.json
PYTHONPATH=src:tests python -m unittest test_printf_fixture
```

The two-history prototype contains 426 buffer writes and 852 complete
before/after snapshots. Its dense JSON is 42,503,592 bytes; compact JSON is
6,852,561 bytes. Conversion verifies all fields and pages. CPU Python and
Pyodide produce identical complete audit reports from both representations:
100,536,246 four-byte units, 7,242 registers, 1,039,440 FP bytes and all
12,512 entry/return registers of 368 memcpy children, with zero differences.
These figures establish the prototype's representation and component
parity. The full capture subsequently retained all 134 histories and
28,143 buffer writes, with 24,306 memcpy children. Its 56,286 boundary
snapshots and 166,195 unique pages pass the lossless conversion checks;
the complete native source comparisons remain a separate required gate.

The full compact archive is 174,431,134 bytes (352,610,814 bytes of JSON).
Six parts store its exact compressed byte sequence, with independent part
hashes and a complete archive hash in `printf_buffer_original.manifest.json`.
No part exceeds 32 MiB. `printf_archive.py` verifies the complete sequence,
then streams it through gzip and JSON loading without concatenating large
compressed/uncompressed temporary buffers. Metadata must agree with the
manifest; invalid or missing parts fail rather than loading another file.
The complete archive SHA-256 is:

```text
16d280fb69d7fe291fdd732378f4351eb105d3013c3e2dfee10f0b2a875431d6
```

Codec tests run in CPU Python and Pyodide. They verify round trips,
owner order, independent expanded targets, mapping gaps and unknown bytes,
malformed metadata and indices, changed FP/contexts/manifests, full/delta
page checksums, missing/corrupt bases after the cache has been primed,
archive streaming across part boundaries, complete byte identity, and
rejection of corrupt parts or altered manifest metadata.
No existing capture, comparison target, numerical result or tolerance was
changed.
