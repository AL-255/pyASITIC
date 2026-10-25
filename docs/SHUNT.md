# Native JOINSHUNT and parallel conductor groups

`JOINSHUNT`, `ADDSHUNT`, `MATESHUNT` and `SHUNT` attach source primary
segments as parallel branches of a target's primary segments. The webpage
offers **Join in shunt · parallel branches** in the layout edit menu. Source
segments match target segments from the end. Joining removes the source
descriptor; undo and saved project histories reproduce the original scene.

The implementation follows `geometry_edit.cpp::join_shunt_geometry_shapes`,
`composite_geometry.cpp`, the original filament setup/contact construction,
and command 421. Secondary records are explicit segment objects with their
own coordinates, materials and mesh counts. Primary and group links remain
distinct. Native COPY and longitudinal subdivision reverse branch lists;
the copied child NEXT links retain their original relation to primary
records. This matters to subsequent translation and SPTOWIRE: the original
walks child NEXT in those paths, rather than the group chain. The port
preserves that behavior, including repeated translation of primary records.
An explicit COPY metal refresh affects the primary record only.

Each conductor group contributes all its primary/secondary filaments to one
contiguous reduction group. CAP similarly folds all the group's contacts,
with the original child-contact prepending order. Forced reference mesh
counts affect primary records only. CALCTRANS retains both native clone and
COPY stages before reversing the second primary chain and joining it; the
additional copies affect multi-branch ordering. Mesh counts include parallel
branches. GDS and preview polygons include every physical branch ribbon.
The original has no GDS exporter; polygon verification uses independently
captured original ribbon coordinates and materials. Native conductor
estimates and GEOM metrics still visit primary records, following the source.

## Original evidence

Nineteen unchanged geometry scripts cover all twelve creators, repeated
joins, shorter/longer sources, self-joining, duplicate arguments, negative
phase and breakup. Plain runs retain 17 normal exits and two SIGSEGVs.
Read-only WHO-entry observers retain 124 complete states, 2,871 raw 240-byte
records, 51,678 defined XYZ words, 5,742 primary/group pointer links and 211
phase words. Coordinates, materials and all those links match in Python.
Independent `gdstk` readback checks every branch in all 124 GDS streams.

The longer-source and duplicate-source faults become explicit API errors.
The captured self-join removes the target and leaves an empty scene. The
webpage source selector requires a distinct winding, while imported project
histories can reproduce the native self-join. Failed edits preserve the
previous scene and history.

Twelve complete model scripts cover wire, square and balun, coarse/refined
cells, repeated joins, explicit ground, eddy correction and three coupled
requests. Every plain request produces a model and exits normally. The
plain and observed scripts, requests and stdin are checked for equality,
including the explicit ground suffix. Both actual CAP/inductive node inputs
are captured in every case. All 12,256 matrix words and 354 output words
match exactly in portable Python; four undefined metrics use the existing
JSON-null contract. The source is calculated from public inputs and edits;
captured matrices and outputs are comparison targets only.

Separate read-only original filament/assembly observers retain all 155
filament records, indexed count arrays, materials, 76 conductor groups and
3,154 upper impedance entries. Direct upper assembly at native inputs and
observation of actual production construction both match in Python. The
same strict model and assembly tests run with packaged Python and compiled
WASM in the required `shunt` Pages job. No numerical WASM change was needed.

Real Chrome 155 uses the actual module worker and pinned local Pyodide
314.0.7. It checks two shunt joins, coarse/repeated-wire Pi2 and the
repeated-branch coupled model against original Y/S/model outputs. A
six-boundary GDS, project reload, undo, desktop/mobile layouts and the
absence of JavaScript exceptions are checked separately. This is a
three-model real-Chrome check; all twelve models run in packaged Pyodide.
The actual DOM workflow also checks all 124 geometry histories and all twelve
live/downloaded models, including explicit ground. Existing CPU geometry,
mesh and GDS regressions (26 tests), prior breakup/contact regressions (five
tests), and the compiled mesh controls/solve/project workflow pass.

## Unresolved exact phase words

The required geometry test asserts **zero differences** and currently fails
on six raw phase words. Four are the previously opaque capacitor constructor
phase value. Its [earlier loader origin](PHASE_ORIGIN.md) is now traced and
reproduced from genuine resolver-entry memory, but complete startup memory
is not yet connected to the typed scene API. Two result from native command 421 falling through to PHASE
with a deleted source descriptor address as its argument. Negative phase
therefore reverses all endpoints and stores that positive process address.
The [shared-memory dispatcher](SHUNT_STORAGE.md) now reproduces the raw
pointer store from its earlier scene on a continuing source heap. The typed
API reproduces the endpoint reversal and positive direction, but
does not have that absolute native process address: it returns
`electrical_phase: null` and `electrical_phase_sign: 1` for this state.
The webpage displays the known direction. No captured address is substituted
and no phase case is removed from the exact gate.

Broader JOIN/UNJOIN FCOS, logarithm, trailing-via heap aliases and continuing
process-state gates remain unfinished and required. The geometry arena is
not a full native process-heap emulator. This checkpoint does not establish
universal original-binary parity and remains on the undeployed development
branch.

| Archive | Bytes | SHA-256 |
| --- | ---: | --- |
| `shunt_original.json.gz` | 167,206 | `815f4e85de12973deafd751a0235a22c8d32573340ce218d273eb54125c526cd` |
| `shunt_plain_outcomes_original.json.gz` | 4,973 | `b374f4792948d1d3dc538867a3654238bf44fc8c99bec04d3661589bbdbda3b8` |
| `shunt_sessions_original.json.gz` | 96,502 | `22e2152a01c8daa97a747b4de1ec95dbb10631f3215a07586c6a728062c418c8` |
| `shunt_assembly_original.json.gz` | 31,076 | `d2b9974c75c395f514dd3622a95685cbb81498dd555af828ef3d40fff0f10c65` |

Original scripts, plain outcomes, observer commands, minimal launch
environment guards, binary/library digests and parent hashes remain in the
archives. Coupled sprintf taps observe output only. No native numerical
instruction, memory, register, allocation, affinity or returned result is
replaced. The source package is `98e4fb1aab0b0378`; numerical WASM remains
SHA-256 `c7869e98f4c18b5414dc172d836e7144ab3ebc0de2de0d1f2eec1a4fe1709186`.

```sh
python tools/capture_shunt_original.py --reference ~/github/asitic-re \
  --library-path /path/to/i386/libs
python tools/capture_shunt_sessions_original.py --reference ~/github/asitic-re \
  --library-path /path/to/i386/libs
python tools/capture_shunt_assembly_original.py --reference ~/github/asitic-re \
  --library-path /path/to/i386/libs
PYTHONPATH=src:tests python -m unittest test_shunt_original test_shunt_sessions_original -v
python tools/build_site.py
node tools/check_shunt_original.mjs /path/to/pyodide.mjs /path/to/jsdom/lib/api.js /tmp/shunt-report.json
node tools/check_shunt_chrome.mjs /path/to/pyodide /tmp/shunt-chrome
```

The first unit test and browser job retain the six phase-word failures;
browser project/edit/GDS/model checks continue after that assertion and the
job still exits unsuccessfully. Passing model checks cannot waive the raw
geometry gate.
