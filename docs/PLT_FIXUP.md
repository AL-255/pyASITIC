# PLT binding in the continuing process

The source now executes the first console `signal` import through the i386
PLT trampoline, `_dl_fixup` and ELF lookup using loader metadata captured
before simulation. Stores continue in the existing simulation Memory.
On identical fresh inputs this resolves 158 previously differing stack words,
reducing the strict rectangular continuation from 816 to 658 differences.
All remaining differences and all older fixtures remain required failures.

## Source operations and earlier inputs

`plt_fixup_storage.py` follows [glibc 2.39
dl-runtime.c](https://github.com/bminor/glibc/blob/glibc-2.39/elf/dl-runtime.c)
and the pinned loader's ordinary i386 trampoline. It preserves incoming
volatile registers, emits map/relocation and saved-register stack stores,
reads the ELF relocation/symbol/version and scope, executes `LoaderLookup`,
computes the symbol address and updates the GOT unless `dl_bind_not` is set.
The trampoline restores the caller's registers and transfers to the target
with its original return word and arguments. Target-entry memory/registers
derive from these operations.

The observed `strcat` symbol is an IFUNC. Its selector reads the earlier libc
CPU-feature pointer, usable-feature bytes and architecture preference byte,
executes the pinned conditional selection, and emits its PC-thunk stack word.
The resolver result is not an input. Unit tests exercise the three selector
branches; these synthetic cases are not counted as additional original calls.
Other IFUNC bodies, multithreaded scope locking, auditing and alternate PLT
layouts remain explicit unsupported paths.

For continuing calls, import selection searches the ELF relocations by name.
The i386 PLT slot address follows the ELF `.plt` address/size and relocation
index. The earlier GOT value distinguishes an unresolved slot from a bound
import. PLT pushes are emitted only when needed; subsequent calls use the
existing binding. ELF section headers and hashes are metadata inputs. No
executable image is loaded or executed by Python.

The ABI remains pinned to the original and documented Ubuntu i386 builds:

| Image | SHA256 |
| --- | --- |
| ASITIC | `72bcb93444604b89a65cb64e5825bfcff0ac740a816120d0f171855206bd572f` |
| Loader | `64f2864e740bf9cc15c01466c438d6ba25c7bc9cf9401d8122287ee7ed05e26d` |
| libc | `e936bd40e5479b27721efeade1b502623436a8be2bd8bd0f0ccf8c4f7229a0d0` |

## First signal binding and retained mask bytes

The new full capture records loader metadata at first-driver entry, alongside
the existing earlier stack: link maps, scopes, hash/symbol/version/string
tables, dynamic entries, PLT relocations/GOT, CPU-feature bytes, TLS and ELF
PLT section metadata. Later per-call PLT/lookup snapshots are never loaded
into the continuing replay.

After closing the script FILE, a successful tcache free leaves the chunk's
size-class index in EDX. `__libc_free` restores errno through its earlier TLS
offset in ECX, and `fclose` returns its saved success status in EAX. The source
derives these volatile registers from earlier allocator/ELF state. Main's
stack adjustment supplies arithmetic flags. The integration test compares
every generated entry register with the independent first PLT entry. No
later observed register constructs the call.

The lookup's `do_lookup_x` flags argument is consequently stored at the old
script workspace plus 4180. The signal wrapper's partially initialized mask
copies that earlier word to workspace plus 3852. The source executes both
producers instead of inserting an observed value or a constant into the mask.
Subsequent signal calls bypass the now-bound PLT. Caller compare flags follow
the original `CMP`. Non-tcache FILE-free returns and interposed signal
implementations remain explicit unfinished paths.

With identical fresh inputs, disabling only the new binding yields 415
pre-parser and 401 final differing words. Executing it yields 336 and 322.
Exactly 158 previously differing addresses are resolved; no new differing
address is introduced. Unknown bytes remain zero. The strict comparison still
exits nonzero for all 658 remaining differences.

## Independent native observations and outcomes

The PLT observer retains all 134 unchanged cold/warm histories. It captures
each resolver entry and the first resolved function entry before execution.
Ordinary target breakpoints explicitly disable after that first observation;
returning `False` from a temporary breakpoint alone must not let later signal
calls overwrite the record. Guards check target ESP and preserved registers.
Signalled exits remain recorded even when GDB has reaped the inferior. The
observer never replaces an instruction result, allocation, register or data.

Only the rectangular cold history executes lazy bindings in this interval:
`signal`, `select`, `_IO_default_uflow`, `_IO_file_underflow`, `_IO_file_read`,
`strcat`, `add_history` and `kill`. The other 133 histories remain explicit
without a component call to evaluate.

| Complete target-entry assertion | Count | Differences |
| --- | ---: | ---: |
| Actual original calls | 8 | 0 |
| Four-byte region units, including short tails and overlaps | 1,332,840 | 0 |
| General/segment registers | 136 | 0 |
| FP/SIMD bytes | 19,520 | 0 |

The PLT capture records 132 next-driver stops, one earlier SIGSEGV and the
rectangular SIGABRT. Plain runs record 128 normal exits, five SIGABRT and one
SIGSEGV. Relative to the lookup capture, plain square/1/coarse cold changes
from normal to SIGABRT and warm from SIGABRT to normal; pilot-width3/1/coarse
warm changes from normal to SIGABRT; pilot-width3/1/contacts cold changes from
SIGABRT to normal and warm from normal to SIGABRT. All outcomes are retained.

The separate continuing capture again retains all 134 unchanged jobs, with
132 next-driver stops, the earlier square/64/contacts cold SIGSEGV and the
rectangular cold SIGABRT. Plain runs record 127 normal exits, five SIGABRT
and two SIGSEGV. Compared with the previous command-transition fixtures,
pilot-width3/1/coarse cold changes from normal to SIGABRT and warm from
SIGABRT to normal; pilot-width3/1/contacts cold changes from SIGABRT to normal;
pilot-boundary/1/coarse cold changes from SIGABRT to SIGSEGV. No native outcome
is replaced to make a comparison pass. Minimal launcher environments and
environment guards precede the new captures.

## Required comparisons and remaining scope

All 105 affected CPU tests pass, including eight new PLT tests and four new
integration tests. The eight PLT tests and complete native-return audit pass
in packaged Pyodide. Integration tests check all earlier contexts and full
boundary owners, generated binding registers/mask propagation, and independence
from later boundary bytes. Removing required earlier bytes causes an explicit
runtime failure; later observations never repair that missing input.

Packaged version `29cea7b8ff84f270` passes the PLT and integration tests in
Pyodide. CPU and Pyodide complete PLT reports are byte-identical. The full
compiled fresh audit checks every one of the 134 histories: all 130 main
histories and three additional histories pass, while the rectangular cold
case retains the 336 + 322 differences above. All 9,479,168 later heap words,
664 allocator events, 135 pre-free buffers, 140 console calls and 132 output
files match. Both the fresh and older full continuing checks still exit
nonzero. Workflow syntax, complete disjoint Python test discovery and patch
validation pass. The numerical WebAssembly binary is unchanged.

Fresh complete and older continuing fixtures remain separate required audits.
Earlier fixtures lack loader context and retain their existing 816 stack
differences. They are not replaced, omitted or permitted to pass by a count or
tolerance exception. The production trailing-via guard remains; this branch
is not promoted as complete binary fidelity.

The remaining seven lazy bindings need their surrounding application/libio
caller operations and frames connected to this replay. Full loader startup
and earlier binding lifetimes are unfinished; recording earlier metadata is
not reproducing process bootstrap. Remaining formatter/buffer/syscall/kernel/
caller stores, later commands/exit, other analyses, older missing-context
gates and known arithmetic/JOIN/UNJOIN differences remain required work.

New mandatory suites `pltfixup` and `loadertransition` supplement all older
strict gates. Diagnostic reports remain local.

| Fixture | Compressed bytes | SHA256 |
| --- | ---: | --- |
| `plt_fixup_original.json.gz` | 2,169,812 | `a27074a76eb562a43d0fee29458516d0b8e6f55232bd243fc0e74e6f94c6c563` |
| `loader_transition_original.json.gz` | 47,073,886 | `ef6ea258e484cfc8f6e5e1e1c074197c1b6d551e998e81a5516f4053feea3e42` |

Uncompressed SHA256 values are
`0ccea525cd920ecb9e2cd4e397bee781bd5088776cd41a21f78ed9d0f3312d68`
and `78fdf314846404fd4ea445a2d6dd2421bcf3c1808524cdd395e9d540bfdd40cf`
respectively.

```sh
python tools/capture_plt_fixup_original.py --debug-directory /path/to/debug/usr/lib/debug --reference /path/to/asitic-re --library-path /path/to/native-libraries
python tools/capture_loader_transition_original.py --debug-directory /path/to/debug/usr/lib/debug --reference /path/to/asitic-re --library-path /path/to/native-libraries
PYTHONPATH=src:tests python -m unittest test_plt_fixup_original test_loader_transition_original -v
python tools/audit_plt_fixup_original.py --output /tmp/plt-audit.json
python tools/build_site.py
node tools/check_plt_fixup_original.mjs /path/to/pyodide.mjs /tmp/plt-wasm.json
node tools/check_loader_transition_original.mjs /path/to/pyodide.mjs /tmp/loader-transition-wasm.json
node tools/check_command_transition_original.mjs /path/to/pyodide.mjs /tmp/command-main.json /tmp/command-extra.json
```
