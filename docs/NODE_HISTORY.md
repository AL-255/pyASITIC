# Continuous node work arrays and first analysis-driver cleanup

The earlier [console-storage replay](CONSOLE_STORAGE.md) stops at the first
node-equation entry. `NodeStorage` now continues that same `Memory` and heap
through the folded node solve, its array releases, native model reports and
the enclosing PI2/CALCTRANS driver's final CAP/inductance destruction. This
does not yet include outer command-parser cleanup, later commands or exit.

## Source operations

`node_storage(nodes)` follows `node_equations.cpp`: allocate integer pivots,
LU, drive, bias, current and RHS, then free LU, drive, bias, current, RHS and
pivots. The enclosing driver then frees the inductive and capacitive arrays.
Complex constructor zeros are stored immediately after each allocation.
Pivots are initialized by factorization, not invented constructor zeros.

`node_math.folded(..., storage=...)` retains the existing general-LU,
backsolve, difference, matrix-vector and legacy-complex algorithms and exposes
their final work arrays. Pivots are stored one-based. The CAP matrix's node
folding is written back to the live CAP allocation; the source port values
are compared as raw binary64 words. Both node dimensions and allocation sizes
come from computed earlier geometry, not the observed later node descriptor.

The later [branch continuation](SHUNT_NODE_HISTORY.md) also adds the original
guest-global port stores after workspace release. Both computed results and
their actual memory cells are now checked at node/driver return; later observed
port addresses cannot redirect those stores. It extends this source path to
all 28 selected secondary-group histories and retains every older gate.

After the six constructor allocations, `NodeStorage` reads the actual live
CAP/inductive bytes, including the already reproduced via effects. It checks
that all numerical input/work ranges are disjoint before using the existing
batch factor/backsolve implementation. That condition holds in every selected
successful native history. Aliased node workspaces require a literal-memory
factor/backsolve path and remain explicit unsupported cases; they are not
silently copied or repaired. No node-entry or later heap is used as a seed.

The source console generates the node-equation status and PI2/CALCTRANS model
reports from computed ports and retained metrics. Formatting preserves the
native field widths, unit scaling, tabs, newlines and negative-NaN spelling.
Native message text is an independent output only.

## Independent captures

The read-only observer retains every earlier driver/cache/numerical/console
input and observation. After the original first-node stop it continues the
unchanged inferior to the first driver return or actual native fault. It
records every raw libc allocation/free, whether the call returned, every byte
of every array immediately before free, native CAP mutation and Y ports,
complete heaps before the first node free and after node/driver return, and
all console messages with post-node event positions.

The three successful post-node boundary counts are 7, 12 and 14: the first
free has been observed at its entry but has not executed at count 7. Mapping
observations therefore use only completed post-node allocation/free calls.
This matters when driver cleanup releases mapped arrays or trims the heap:
reusing the earlier live-allocation list would dereference released storage.
No debugger memory, return, instruction or allocator result is changed.

All 130 original and four extra square/rectangular FFT histories remain.
There are 133 successful first-driver returns and one pre-node SIGSEGV in
`square/64/contacts/cold`, matching the earlier boundary behavior. The extra
rectangular cold case's damaged physical header walk remains compared.
Work arrays up to 65,536 bytes are captured in full, exceeding the earlier
bounded numerical pre-free observer's 16,384-byte limit.

| Artifact | Compressed bytes | SHA256 |
| --- | ---: | --- |
| `node_history_original.json.gz` | 28,676,022 | `954304855537fe80e868f24c433c40acc81ec03437a8fcf3387e97df2b867a36` |
| `node_history_extended_original.json.gz` | 530,995 | `5ba29a83a4266a8d2fe355aa5a87d827b00270b096536f1fd1373f208dc90151` |

The full pre-projection capture hashes are
`5233a6543c168d4a34d026b78ff7ed33db88952ce37b45bcc8215d196780ddb8`
and `00792da4f2b4e1091a7f4142904f881bb85716a39737aafd1b0a4bb02e38a9bd`.
The parent console fixtures, original/legacy binaries, earlier reference
inputs, exact debugger commands and lossless payload/page banks are hashed.

Fresh plain outcomes are 125 normal, four SIGABRT and one SIGSEGV in the main
set, and three normal plus one SIGABRT in the additional set. Compared with
the previous console capture, `square/1/coarse/cold` and
`pilot-width3/1/coarse/warm` change from normal to SIGABRT, while
`pilot-width3/1/coarse/cold` and `pilot-width3/1/contacts/warm` change from
SIGABRT to normal. The extra outcomes are unchanged. Both complete captures
are retained; these executions do not establish later command/exit cleanup
parity or fix the known plain-process allocator failures.

## Verification

The separate required `nodehistory` suite retains every earlier strict gate.
It compares every post-node heap word, allocation identity/request/interface,
pre-free array byte, port word and source-generated message. A bulk byte
comparison only accelerates equal regions; mismatches and unknown bytes keep
word-level diagnostics and fail the audit.

Negative controls change later node dimensions, expected CAP/port bytes and
the stored final RHS. Changing an expected dimension must not change source
allocations. A wrong final RHS fails full-heap/pre-free checks even when every
port and report still matches; checking port values alone would miss it.

Both the original word-by-word audit and the final bulk-byte implementation
pass every selected history. Across the 130 main plus four additional cases:

| Post-node observation | Checked | Differences |
| --- | ---: | ---: |
| Allocation/free events | 1,862 / 798 allocations | 0 |
| Arrays immediately before free | 1,064 / 2,976,120 bytes | 0 |
| Complete heaps | 399 boundaries / 28,957,696 32-bit words | 0 |
| Port binary64 components at node/driver return | 2,128 | 0 |
| Complete source console calls and positions | 4,080 | 0 |

There are no unknown heap bytes. The unchanged earlier numerical/console
continuation also matches all 263 boundaries / 19,456,000 heap words, 131 via
stores, the one native mapping fault, all numerical workspace/output bits and
all cache tables. Together the two stages compare 662 boundaries and
48,413,696 heap words through first driver return, with zero differences.
Earlier incomplete-context gates remain required and nonzero; they have not
been replaced by these fixtures.

All 52 affected Python regression tests pass, including explicit checks that
the native plain-process faults remain present. The preexisting independent
folded-node gate still matches all 54 cases / 189,752 components for both the
compiled driver and Python driver using compiled general LU, including 256
nodes and 15 complete production-session inputs. The numerical WASM binary
is unchanged, SHA256
`c7869e98f4c18b5414dc172d836e7144ab3ebc0de2de0d1f2eec1a4fe1709186`.

```sh
PYTHONPATH=src python tools/capture_node_history_original.py --debug-directory /tmp/debug/usr/lib/debug --reference /path/to/asitic-re --library-path /path/to/native-libraries --full-output /tmp/node-history-full.json.gz
PYTHONPATH=src python tools/capture_node_history_extended_original.py --debug-directory /tmp/debug/usr/lib/debug --reference /path/to/asitic-re --library-path /path/to/native-libraries --full-output /tmp/node-history-extra-full.json.gz
PYTHONPATH=src:tests python -m unittest test_node_history_original test_console_storage_original test_driver_history_original -v
python tools/build_site.py
node tools/check_node_history_original.mjs /path/to/pyodide.mjs /tmp/node-audit.json /tmp/node-extra-audit.json
node tools/check_nodes.mjs /path/to/pyodide.mjs
```

Remaining work includes outer command/parser and process cleanup, startup and
initial stream/global context, other analysis/eddy/buffering branches,
secondary geometry groups, aliased or singular node workspaces, earlier large
matrix pre-free observations, the older incomplete-context gates, and known
logarithm/cosine and JOIN/UNJOIN arithmetic discrepancies. This selected
driver continuation is not proof of whole-program equivalence and does not
remove the production trailing-via guard or authorize deployment.
