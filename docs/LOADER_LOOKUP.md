# Native lazy-symbol lookup stores

`loader_lookup_storage.py` implements glibc's ELF symbol search and the stack
stores of the pinned i386 `_dl_lookup_symbol_x`, `do_lookup_x`, `check_match`,
loader-local `strcmp` and library-name matching paths. Every observed lookup
between the first simulation return and the next driver entry or native fault
now matches its complete independent return comparison. Connecting these
stores to the continuing replay remains unfinished; its 816 required boundary
differences have not been removed or exempted.

## Source decisions and ABI

The search follows [glibc 2.39's
dl-lookup.c](https://github.com/bminor/glibc/blob/glibc-2.39/elf/dl-lookup.c):
GNU hash and bloom filters, traditional ELF hash buckets/chains, scope order,
symbol type/definition, requested versions, hidden/default versions, visibility,
weak/global binding and the provider's `l_used` store. GNU hash is computed
from the name, and ELF hash is computed lazily when the search needs it.
Dynamic table pointers follow the map's relocated/read-only dynamic-section
state. No symbol-name dispatch table supplies the answer.

The implementation also writes the caller arguments, saved registers,
PC-thunk/call return words, hash/local temporaries, version candidates and
output reference. Untouched stack bytes stay as earlier memory. String
comparison stops on the first differing byte, preserving the native load
boundary when a later byte is unmapped. Return registers, flags, provider and
symbol reference derive from the earlier state and search. No machine code
is loaded or executed by the Python implementation.

ABI offsets are pinned to `/lib/i386-linux-gnu/ld-linux.so.2`, SHA256
`64f2864e740bf9cc15c01466c438d6ba25c7bc9cf9401d8122287ee7ed05e26d`,
build ID `b2433a068fadaab6e01318e14981372cf6c2e92a`. Native debug-type
observations verify the private 632-byte link-map layout, including its
bitfields. Saved-register layouts differ between GNU and ELF hash walks;
the original instruction stores establish both layouts. Addresses in the
runtime are ABI/code offsets, not captured symbol results or numerical fits.

Unresolved-symbol exception/weak-null returns, protected/unique bindings,
dlopen dependency mutation, loader debug output and references absent from
the ordinary PLT path remain explicit unsupported paths. A selected IFUNC
is returned as an ELF symbol at this boundary; invoking its resolver belongs
to the subsequent `_dl_fixup` operation and is not silently approximated.

## All unchanged original histories

The read-only observer launches all 67 unchanged jobs in separate cold and
warm cache states, retaining all 134 histories and fresh plain/GDB outcomes.
It begins at first-driver return and stops at next-driver entry or the
original terminal outcome. The cold rectangular `prelude/fft/16/8` case
executes eight lazy lookups: `signal`, `select`, `_IO_default_uflow`,
`_IO_file_underflow`, `_IO_file_read`, `strcat`, `add_history` and `kill`.
All eight return before the later original SIGABRT. The other 133 histories
contain no lookup in this interval; they remain explicit and are not reported
as additional tested function calls. One of them, `square/64/contacts` cold,
faults in the first driver with SIGSEGV.

Earlier component inputs include full stack/registers/XSAVE, ELF symbol,
string, GNU/ELF hash and version tables, scope vectors, link maps/library
names, loader globals and the unmodified environment whitelist. These are
metadata and memory inputs, not copies of the original executable code.
The environment-name guard runs before stack capture. The unchanged binary
runs in a separate process group, and the observer never replaces inferior
memory, instructions, registers, return values or allocation results.

All input-region addresses and sizes are retained at return, and all their
bytes are assertions. Content-addressed blobs deduplicate repeated regions
in the fixture; initialization uses only `before` references. Altering later
memory/register/FP assertions produces failures, and deleting a later region
fails the owner comparison. Altering an earlier hash-chain or requested
version changes the runtime search. Saved registers and retained padding
also follow mutations of the earlier input.

| Compared observation | Count | Differences |
| --- | ---: | ---: |
| Native lookup calls | 8 | 0 |
| Four-byte region assertions, including short tails and overlapping metadata | 1,290,725 | 0 |
| Return general/segment registers | 136 | 0 |
| Preserved FP/SIMD bytes | 19,520 | 0 |

Fresh GDB outcomes are 132 stops at next-driver entry, one SIGSEGV and one
SIGABRT. Fresh plain processes have 129 normal exits, four SIGABRT and one
SIGSEGV. Relative to the previous signal-installation capture, plain
`pilot-width3/1/coarse` cold and `pilot-width3/1/contacts` cold change from
normal to SIGABRT, while `pilot-width3/1/contacts` warm changes from SIGABRT
to normal. GDB `square/1/coarse` cold, `pilot-width3/1/contacts` cold and
`pilot-boundary/1/coarse` warm change from SIGSEGV to reaching the next
driver. Tests preserve these fresh outcomes and all older committed evidence.
The component comparison does not predict earlier application faults or
claim that a GDB stop at driver entry is a successful process exit.

## Integration boundary and verification

The new resolver is an independent source component. Its entry snapshots are
never loaded into the continuing simulation replay. Integration still needs
earlier loader/bootstrap metadata and the original PLT trampoline,
`_dl_fixup`, IFUNC and surrounding caller operations in the existing process
memory. Using a later observed lookup frame to initialize that replay would
erase the very stack-history differences the strict gate must detect.

One concrete producer is now established: the `flags` stack argument to
`do_lookup_x` is stored at lookup-entry ESP minus 136. For the first `signal`
binding, the pinned PLT trampoline and `_dl_fixup` reserve 136 bytes beneath
the target's entry stack. Their frame relation places this store at the old
script workspace plus 4180, the uninitialized source later copied by signal
installation into workspace plus 3852. The source writes the earlier lookup
flags argument there. Integration must execute that call sequence; it must
not assign a constant or an observed later value to the mask's source word.

The full 134-case compiled continuing gate remains required alongside this
new `loaderlookup` suite. The known rectangular case still has 415 differing
words at interactive parsing and 401 at its final native abort. Kernel signal
delivery, remaining formatter/buffer/syscall/caller stores, later commands and
exit, other analysis branches, earlier missing-context comparisons and known
arithmetic/JOIN/UNJOIN differences are still unfinished. No deployed result
is promoted as complete binary fidelity, and the production trailing-via
guard remains in place.

All 93 affected CPU regressions pass, including ten new lookup tests. The ten
tests and the complete native-return audit pass in packaged Pyodide, version
`b1ec2d125f0f8b16`; CPU and Pyodide audit reports are byte-identical. The full
compiled continuation was also rerun: all 130 main cases and three additional
cases pass, and the rectangular cold case retains exactly the 415 + 401
required differences above. All 9,479,168 later heap words match, with zero
unknown bytes. The continuing check therefore still exits nonzero. Workflow
syntax, complete disjoint Python test discovery and staged patch validation
pass. The numerical WebAssembly binary is unchanged.

The fixture is 888,985 bytes, compressed SHA256
`764918a3a2958351b93f6b8c5eef167c4bcd80bb0d2bfc338e5f7d679efc9f7b`,
uncompressed SHA256
`d6d7ebb30d94203213fa8c55351cd3b7eb10835173390309e4aca85fd71457d4`.
Diagnostic reports remain local.

```sh
python tools/capture_loader_lookup_original.py --debug-directory /path/to/debug/usr/lib/debug --reference /path/to/asitic-re --library-path /path/to/native-libraries
PYTHONPATH=src:tests python -m unittest test_loader_lookup_original -v
python tools/audit_loader_lookup_original.py --output /tmp/lookup-audit.json
python tools/build_site.py
node tools/check_loader_lookup_original.mjs /path/to/pyodide.mjs /tmp/lookup-wasm-audit.json
node tools/check_command_transition_original.mjs /path/to/pyodide.mjs /tmp/command-main.json /tmp/command-extra.json
```
