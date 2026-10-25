# Direct-script and next-command memory

The development replay now continues the same process memory past the first
Pi2/CALCTRANS return, parses the following command, opens its port file and
stops at the next numerical driver entry or native fault. The rectangular
16×8 cold-cache case still differs in reused stack storage. The new mandatory
audit remains nonzero; this checkpoint does not establish whole-program
equivalence or change the deployed trailing-via guard.

The measurements below describe the original command-continuation checkpoint.
The subsequent [signal-installation integration](SIGNAL_INSTALL.md) reduces
the current remaining comparison to 816 words; the older captures and every
comparison remain required.

## Source behavior

`command_storage.py` implements the fixed 260-byte command/argument records,
in-place normalization, delimiter mutation, native command lookup and typed
value stores. `command_catalog.py` mechanically translates all 117 reference
definitions, including aliases and argument types. The exact reference
`command_catalog.inc` is retained independently for a regeneration check.
Unwritten value bytes remain live. Failed scans require an earlier caller
value; an absent value is an explicit unsupported boundary.

`stdio_storage.py` reads the live script FILE buffer, including bytes damaged
by the earlier rectangular cache overwrite. It implements the selected
buffered input/output paths without clearing unused tails. Successful port
setup initializes a FILE linked to the live stream chain, allocates its
buffer, emits the source header and flushes it. Numeric header cells derive
from earlier geometry, technology and command inputs. Later native text,
files, allocation results and memory observations are assertions only.

The header's native timestamp is uninitialized. Read-only hardware watches
identify its last writer in both callers: ordinary 2PORT reuses the filename
source argument pushed by legacy string replace; 2PORTTRANS reuses the memcpy
return address. `NativePortStack` models those original i386 pushes. Calendar
conversion uses the earlier environment and TZif bytes, rather than the
observed timestamp/result. The selected localtime path also reproduces
glibc's old-name free, strdup and null temporary free.

On script EOF the replay closes/frees the script stream, reads the prompt
input and logs it before normalization. The original stdio reader appends a
newline even when fgets retained one. Interactive command records occupy a
different, overlapping native stack frame. QUIT reaches descending packed
cache destruction. Physical following-chunk validation reproduces the native
`double free or corruption (!prev)` abort in the rectangular case, including
the independent fatal-message mapping, without signaling the host process.

## Independent observations and environment

The two new compressed fixtures retain all 134 existing jobs and every
native outcome. They add earlier driver-entry stack, script/stdin FILE,
character tables, timezone and port-settings inputs. They observe complete
later heaps, original script-workspace/port-settings regions at parse/header
boundaries, raw allocation/free events, every freed usable byte, source
console calls, calendar operands/results and generated output files.

Full stack captures require an explicit environment. The capture launcher
now constructs PATH, HOME, LANG, LC_ALL, LD_LIBRARY_PATH, TERM and INPUTRC
without inheriting the agent environment. The observer rejects unexpected
inferior environment names before saving a capture. Tests inspect both that
metadata and the retained stack bytes. Earlier uncommitted captures with an
inherited environment were replaced by fresh unchanged-original runs, not by
editing or masking their bytes. Earlier committed baseline fixtures remain
unchanged.

`port_timestamp_writers_original.json` independently records the two native
last-writer traces; its reproducer uses hardware write watches only. No
inferior instruction, memory, return value or allocation result is replaced.

## Strict comparison

The audit always runs the earlier geometry/cache/CAP/LMAT/node/console
continuation first. It then compares every new event, pre-free byte, complete
heap word, parser/header boundary region, final component region, file byte,
calendar call and source console call. All 134 inputs remain in the compiled
runner, including the earlier pre-node SIGSEGV and the later rectangular
SIGABRT. It does not omit dead stack storage when that storage differs.

The final compiled comparison checks all 130 main histories with zero
differences. Three additional histories also pass. The rectangular cold
history has 912 word differences: 463 before interactive parsing and 449 at
the allocator abort, all in the reused script workspace. Every other new
comparison matches, including all 9,479,168 complete-heap words, 664 allocator
events, 135 pre-free buffers / 10,580 bytes, 132 generated files / 187,415
bytes, 132 calendar calls and 140 console calls. There are no unknown bytes.
The source reproduces the rectangular allocator abort and its message;
matching that fault does not excuse the stack differences.

The 266 parser/header points compare 304,570 component words; the 133
next-entry/fault boundaries compare another 152,285 component words. The
912 differences count boundary observations, not unique addresses. A local
read-only diagnostic identifies lazy `add_history`/`kill` resolution writes
and observes the differing signal-frame bytes already present at the native
SIGQUIT handler entry. Reproducing those loader/kernel stack effects remains
work; later native snapshots are not loaded to repair the replay.

Fresh plain main runs record 123 normal exits, six SIGABRT and one SIGSEGV;
the extra runs record three normal exits and one SIGABRT. Four main outcomes
differ from the earlier node fixture: square/1/coarse cold changes from abort
to normal, its warm pair changes from normal to abort, and both
pilot-width3/1/contacts runs change from normal to abort. Tests preserve these
observations and all older committed outcomes. The new minimal environment
is recorded as an explicit input; it is not claimed to explain every native
plain-process difference.

All 65 affected CPU regressions and all nine new tests in compiled Pyodide
pass. The full compiled audit still exits 1 for the 912 retained differences.
Test planning confirms that every discovered Python test occurs in exactly
one required core shard. Workflow validation and patch whitespace checks
pass. The tested development package version is `df1ae4c5f1d80c26`; the
numerical WebAssembly binary is unchanged.

| Capture | Bytes | SHA256 |
| --- | ---: | --- |
| `command_transition_original.json.gz` | 31,705,388 | `ee0f9c63ea036c9dda52aab7c9cc2fc9828281875ce5d06d1b1053e392da64e9` |
| `command_transition_extended_original.json.gz` | 619,273 | `4eef69009a075ff78320003464cbd0584609cb400e5b8d076ae22f0fc170dd57` |
| `port_timestamp_writers_original.json` | 78,473 | `bf229f6641a68d33c9916ad2169b053e987a27b9e62b130afff4be6883910f5a` |

The uncompressed main and extra capture SHA256 values are respectively
`7b3bc6ea911e8a5a7e507332525f8ddbda5b5ad7f9a091b93dd1dae7319b5c4a`
and `ce4871c81f135804feafc07bfe97ab0c4eb6e106095dddd2931e0ab92f89d596`.

```sh
python tools/capture_command_transition_original.py --debug-directory /path/to/debug/usr/lib/debug --reference /path/to/asitic-re --library-path /path/to/native-libraries --full-output /tmp/command-full.json.gz
python tools/capture_command_transition_extended_original.py --debug-directory /path/to/debug/usr/lib/debug --reference /path/to/asitic-re --library-path /path/to/native-libraries --full-output /tmp/command-extra-full.json.gz
python tools/capture_port_timestamp_writers_original.py --debug-directory /path/to/debug/usr/lib/debug --reference /path/to/asitic-re --library-path /path/to/native-libraries
PYTHONPATH=src:tests python -m unittest test_command_transition_original -v
python tools/build_site.py
node tools/check_command_transition_original.mjs /path/to/pyodide.mjs /tmp/command-audit.json /tmp/command-extra-audit.json
```

The last command is deliberately strict and fails while differences remain.
Reports stay local. The required `commandtransition` CI suite preserves this
failure alongside all earlier fidelity gates.

Remaining work includes the rectangular reused stack writes, later port
solves/cleanup, complete outer dispatch and process exit, other parser and
buffering paths, explicit TZ changes, TZif leap/future-tail behavior, startup,
secondary geometry groups, aliased/singular node paths, broader eddy branches,
the earlier incomplete-context gates and known logarithm/cosine and
JOIN/UNJOIN numerical discrepancies.
