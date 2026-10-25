# Native SPTOWIRE conversion

`SPTOWIRE`, `DEMOLISH`, `SP2WIRE` and `BREAKUP` convert a winding into
individual segment objects. The webpage exposes this as **Break up into
segments** in the layout edit menu. The original generator inputs and command
history remain in saved projects, so regeneration and undo replay the same
conversion. Every resulting object remains selectable and exportable to GDS.

The port follows `geometry_edit.cpp::convert_geometry_to_wires` and the
original command 424. For each primary segment, it allocates a descriptor and
a copied segment, retains the source origin, local coordinates, material,
phase and defined descriptor fields, and appends `_0`, `_1`, etc. to the name.
The original assigns native descriptor kind 21, which the port retains as a
general joined object. All new records are allocated before the source is
released. Incoming friend pointers are not cleared; the geometry arena
preserves their later descriptor reuse effects. New objects have no friend.

The original does not reject an existing generated name. The scene therefore
retains duplicate names, and later edit commands resolve the newest matching
descriptor, following the native head-first name lookup. An empty source chain
faults in the original removal routine; the API reports that fault explicitly
and the webpage disables this conversion for an empty selection. No host signal executes.

## Original evidence and checks

Twenty unchanged scripts run both plainly and under read-only WHO-entry
observers. They cover all twelve existing creators, all four command aliases,
repeated breakup, moved/phased/copied/renamed leaf objects, three paired
descriptor histories, duplicate names and the selected empty-chain fault.
The 111 snapshots retain all 22,788 defined binary64 XYZ stores, materials,
widths/thicknesses, via counts, native kinds/origins/phase/header fields and
live/stale friend identities. Both plain and observed cohorts retain 19
normal exits and one SIGSEGV. Minimal environment guards precede every
observation; no instruction, register, memory, allocation, result or outcome
is replaced.

Portable Python matches every checked record. Independent `gdstk` readback
checks all 111 GDS streams against the original ribbon coordinates, origins,
metal/via layer assignments and via counts. The browser repeats every history
through actual edit handlers, winding selection, project save/restore,
regeneration, undo and GDS download. Its separate GDS stream decoder checks
the downloaded polygons against the same original records, including duplicate
names. It also verifies that the empty-chain fault cannot append an edit.

Eight additional unchanged model scripts select first/last converted wires,
square and balun leaves, two coupled models made from individual leaves, eddy correction and a
converted via. All eight unobserved outcomes are retained. Seven produce
finite reports; the converted-via Pi2 request faults with SIGSEGV and produces
no model. All seven reports retain exact Y/model/S/resonance outputs; both
coupled sessions also retain their complete CAP/inductive node matrices.
CPU and packaged Pyodide require exact results. The real browser form and
download handlers compare all seven live and downloaded models too.

Real Chrome 155 additionally runs the actual module worker with pinned local
Pyodide 314.0.7. First/last converted-wire Pi2/Y/S/model downloads, the
two-boundary GDS file, saved project, empty-selection guard and undo all pass
with no JavaScript exceptions. Desktop/mobile screenshots were rendered and
inspected, with no horizontal overflow. This Chrome check covers the two wire
models; the complete seven-model cohort runs in the packaged Pyodide/DOM check.

All five new CPU tests pass. Pyodide passes the four applicable unit tests;
the `gdstk` test requires CPython, and its full browser GDS scope is checked by
the separate stream decoder. The required `breakup` Pages job runs the
complete browser workflow. Existing erasure, JOIN, UNJOIN, copy/link and phase
regressions remain required; all 17 affected CPU tests pass. The existing
mesh DOM/compiled-solver regression check also passes.

| Archive | Bytes | SHA-256 |
| --- | ---: | --- |
| `breakup_original.json.gz` | 40,795 | `79e248979cae0c1a9d33e4c9f5d73a1a224b5031fab6dcd1595cfa2435f3c678` |
| `breakup_plain_outcomes_original.json.gz` | 3,945 | `3de8056a8f6cd9bae506d936ae805a37ab42c10318b266836e715441295f6438` |
| `breakup_sessions_original.json.gz` | 14,291 | `1f79d038fc96bc55b9f08890c2edf75eb31a527727e1c3a704ef2ded5c78bffc` |

All parent hashes, original scripts and capture commands remain available.
The model observer's coupled sprintf tap observes output only; no captured
result enters the runtime package. This cohort covers primary segment chains.
JOINSHUNT secondary groups, arbitrary native name-buffer overflows and the
broader numerical/allocator/continuation gates remain unfinished. The existing
JOIN/UNJOIN FCOS differences are not corrected or waived by this feature.
This development branch remains undeployed.

The source package is `9cfb2195efa429fc`; numerical WASM is unchanged at
SHA-256 `c7869e98f4c18b5414dc172d836e7144ab3ebc0de2de0d1f2eec1a4fe1709186`.

```sh
python tools/capture_breakup_original.py --reference ~/github/asitic-re \
  --library-path /path/to/i386/libs
python tools/capture_breakup_sessions_original.py --reference ~/github/asitic-re \
  --library-path /path/to/i386/libs
PYTHONPATH=src:tests python -m unittest test_breakup_original test_breakup_sessions_original -v
python tools/build_site.py
node tools/check_breakup_original.mjs /path/to/pyodide.mjs /path/to/jsdom/lib/api.js
node tools/check_breakup_chrome.mjs /path/to/pyodide /tmp/breakup-chrome
```
