# Source console writes in the continuous driver replay

`ConsoleStorage` reproduces the reference console emitters and their writes
to already initialized, fully buffered i386 FILE streams. It is used in the
continuous storage audit, with the same `Memory` used by geometry, cache IO,
CAP, LMAT, via stamps, allocator metadata and node input. This is additional
fidelity evidence for the development branch, not whole-program parity or a
change to the deployed simulator's trailing-via guard.

## Inputs and source operations

The earlier driver-entry inputs are the stream bindings and common 36-byte
FILE prefix, recording/progress/timing/dump controls, and cache path strings.
The log's prefix is already in the complete earlier heap: duplicate inputs
must agree and cannot overwrite conflicting earlier heap bytes. The legacy
stdout prefix is a separately captured earlier region outside that heap.
Binding a console to the continuing memory performs no seed stores.

Messages are generated from source templates, computed contact/filament
counts, and the retained-precision frequency divided by 1e9 and spilled to
binary64 before decimal formatting. Native message text and later heap bytes
never enter those calculations. The reference paths are:

- `console_runtime.cpp`: status uses `"\r%s"` on stdout only; output uses
  `"%s"` on stdout/log; errors use `"\n%s"` on stdout and `"\n%s\n"` on the
  enabled log and recording streams. The other message emitter omits the
  log's trailing newline. Each stream is explicitly flushed.
- `potential_solver.cpp`: progress before contact preparation and the CAP
  matrix, and dots after potential fill and output folding.
- `potential_cache.cpp` and `potential_tables.cpp`: failed-open warnings,
  cache generation, status before Green-function fill and before FFT scratch
  allocation, and the cache-writing message after header writes.
- `solver.cpp`: matrix dimensions, inverse status and progress dots. The last
  dot follows the reduced inverse's work-array free and precedes entry into
  `add_via_impedance`, including its independently observed entry boundary.

The successful buffered write/flush path retains every byte beyond the
current write. No NUL terminator or blanket buffer clearing is invented.
Pointers are read from live FILE bytes, not later observations or fixed
diagnostic addresses. Unsupported buffering, timed analysis and matrix dumps
are rejected explicitly; those other source paths remain unfinished.

## Independent native evidence

`capture_console_storage_original.py` extends the read-only driver observer.
All 130 original jobs and all four additional square/rectangular FFT cases
remain. Native messages include kind, text, logging flag and independently
observed setup/prelude/numerical event positions. They are comparison outputs
only. All earlier heap pages, later complete heaps, cache tables, bounded
pre-free arrays and plain-process outputs are retained without filtering.

| Artifact | Compressed bytes | SHA256 |
| --- | ---: | --- |
| `console_storage_original.json.gz` | 22,548,116 | `8d455e39329843fc1ea0e94dbcf7662c2adaa8fdbf914d963795c37112f46a87` |
| `console_storage_extended_original.json.gz` | 505,555 | `2247dfedc97920e1eff4da6cdf85b295651d24de32b42584729dd0ce09d5cd46` |

The full pre-projection capture hashes are
`3117d5874b4ae0bfe9c0508873c87b93736fdd10aa662caa4e6d39200f48bcec`
and `80c5488e478efbebe1c8f4329395407da895ab46bdcdd25eef2a02e252ac5dcd`.
Each fixture identifies its earlier driver fixture by SHA256 and contains
the complete observer script and unchanged native inputs.

Fresh plain runs differ from the previous plain outcomes in six cases.
Four previous `malloc(): unaligned tcache chunk detected` aborts complete in
the fresh run, while both `pilot-boundary/1/coarse` modes now report that same
abort. The old main capture retains 123 normal exits, six SIGABRT and one
SIGSEGV; the new main capture records 125 normal exits, four SIGABRT and one
SIGSEGV. All corresponding GDB stop signals and all four extra plain outcomes
are unchanged. Plain processes use address randomization; GDB uses its default
disabled-randomization setting. These are independent executions of damaged
allocator paths, not evidence that their later cleanup is fixed. Tests record
every changed outcome, and the old full capture and required gate remain.

## Checks and limits

The new required `console` suite compares native call positions as well as
every word of every complete later heap. No text buffer is excluded from the
comparison. Negative controls suppress actual stream writes, change later
expected message text, change an earlier buffer-tail byte, and introduce
conflicting earlier FILE observations. They must expose differences or reject
the contradictory inputs rather than repairing runtime state.

The complete 130-case main and four-case additional browser-kernel audits
both exit zero. Across all 134 histories:

| Observation | Checked | Differences |
| --- | ---: | ---: |
| Console calls, text, logging flags and positions | 3,681 | 0 |
| Complete later heaps | 263 boundaries / 19,456,000 32-bit words | 0 |
| Complete cache tables | 6,030 / 535,324,320 bytes | 0 |
| Pre-CAP freed buffers | 1,474 / 4,699,508 bytes | 0 |
| Bounded numerical pre-free arrays | 2,791 / 1,816,160 bytes | 0 |
| Numerical allocation/free events | 13,013 | 0 |
| Via stores / native mapping faults | 131 / 1 | 0 |
| CAP / inductance binary64 components at node input | 118,956 / 118,956 | 0 |

There are no unknown heap bytes or via targets. Forty-six affected Python
regression tests pass, including seven console/provenance/negative-control
tests. The numerical WASM artifact is unchanged, SHA256
`c7869e98f4c18b5414dc172d836e7144ab3ebc0de2de0d1f2eec1a4fe1709186`.
The separate required old driver gate continues to report 6,363 main and 98
additional missing heap-word stores rather than receiving new input bytes
from these new captures. Its observations and failure conditions are intact.

```sh
PYTHONPATH=src python tools/capture_console_storage_original.py --debug-directory /tmp/debug/usr/lib/debug --reference /path/to/asitic-re --library-path /path/to/native-libraries --full-output /tmp/console-full.json.gz
PYTHONPATH=src python tools/capture_console_storage_extended_original.py --debug-directory /tmp/debug/usr/lib/debug --reference /path/to/asitic-re --library-path /path/to/native-libraries --full-output /tmp/console-extra-full.json.gz
PYTHONPATH=src:tests python -m unittest test_console_storage_original test_driver_history_original -v
python tools/build_site.py
node tools/check_console_storage_original.mjs /path/to/pyodide.mjs /tmp/console-audit.json /tmp/console-extra-audit.json
node tools/check_driver_history_original.mjs /path/to/pyodide.mjs /tmp/old-driver-audit.json /tmp/old-driver-extra-audit.json
```

The older driver fixtures do not have the earlier stream bindings, so their
unaugmented strict gate still reports missing console stores. It remains
required alongside the stronger new experiment. Process/scene/cache startup,
other analysis/eddy and buffering paths, secondary geometry groups, large
array observations, full cleanup after node input, the incomplete older libio
context, and known logarithm/cosine and JOIN/UNJOIN arithmetic differences
remain unresolved. Matching this selected driver-to-node path cannot prove
the requested whole-program equivalence or authorize deployment.
