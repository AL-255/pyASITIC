# Signal installation in the continuing process stack

The source replay now executes the original console's three signal installs
after its direct script returns. This reduces the strict rectangular-case
continuation from 912 to 816 differing boundary words, while keeping all
134 histories, every byte comparison and every older required gate.

## Source operations and earlier state

`signal_install_storage.py` implements the i386 BSD `signal` wrapper and its
`__sigaction` / `__libc_sigaction` call chain. The compiler ABI layout is
pinned to the observed Ubuntu glibc 2.39 binary, SHA256
`e936bd40e5479b27721efeade1b502623436a8be2bd8bd0f0ccf8c4f7229a0d0`.
Code offsets represent return PCs and symbol bindings. They are not numerical
results or tables indexed by simulation inputs.

The mask behavior follows [glibc's BSD
signal implementation](https://github.com/bminor/glibc/blob/glibc-2.39/sysdeps/posix/signal.c)
and [Linux sigaction
wrapper](https://github.com/bminor/glibc/blob/glibc-2.39/sysdeps/unix/sysv/linux/libc_sigaction.c).
Only the low eight bytes of the public mask are initialized. The wrapper
copies 128 bytes into its local kernel action, but the kernel consumes only
eight mask bytes. On return the kernel writes a 20-byte old action; the libc
wrapper again copies 128 mask bytes back to the public structure. The extra
bytes retain and propagate older stack contents. Zero-filling those bytes
would produce different physical memory.

The source emits saved-register, PC-thunk, call, VDSO-register-push and local
structure stores. It preserves padding and unused fields. The return PC,
general registers and integer flags are computed from the call's earlier
state. These integer-only wrappers leave the interrupted FP/SIMD state
unchanged.

The stack guard comes from the earlier startup stack: argc/argv identify the
environment and auxiliary vector, and AT_RANDOM identifies the startup entropy.
The i386 guard uses its first word with the low byte cleared, following
[glibc's guard setup](https://github.com/bminor/glibc/blob/glibc-2.39/sysdeps/unix/sysv/linux/dl-osinfo.h).
No later observed canary is used. Unsupported signal/errno, direction-flag
and non-VDSO paths stop explicitly before changing stack storage.

The continuing replay derives its caller frame and saved main registers from
the earlier active script frame. It installs SIGINT, SIGABRT and SIGQUIT using
the original handlers and call sites. This controlled non-readline launch has
the default inherited actions and an empty siginterrupt set. Other initial
signal state/readline paths remain separate work. The original main-frame
pointer is cached before argument stores overwrite the old script frame;
the subsequent stdin read uses the real main input buffer address.

## Independent unchanged-original observations

The new capture retains all 134 original jobs, unchanged request/script/stdin,
cold/warm files and fresh plain-process outcomes. A minimal environment and
environment-name guard precede every stack capture. Entry is observed after
PLT resolution; return is observed before the caller's next instruction.
Earlier inputs include the complete stack, registers, FP state, libc binding,
siginterrupt mask and uncaught default/ignored disposition. Other previously
caught actions are rejected rather than invented. Return memory/registers
are assertions only.

These independent entry snapshots are never loaded into the continuing
replay. That replay still starts with its earlier driver-entry context and
executes the source signal-installation stores in its existing memory.

| Compared observation | Count | Differences |
| --- | ---: | ---: |
| Complete BSD signal calls | 390 | 0 |
| Entire return-stack words | 13,178,880 | 0 |
| Return general/segment registers | 6,630 | 0 |
| Preserved FP/SIMD bytes | 951,600 | 0 |

Four GDB histories fault before installation: square/1/coarse cold,
square/64/contacts cold, pilot-width3/1/contacts cold, and
pilot-boundary/1/coarse warm. They remain in the fixture and full audit with
no function-call input to evaluate. The rectangular cold case installs all
three handlers and later reaches its native SIGABRT. The component comparison
does not claim to predict the earlier application faults.

The fresh GDB capture records 129 normal exits, four SIGSEGV stops and one
SIGABRT stop. Plain runs record 130 normal exits, three SIGABRT and one
SIGSEGV. Relative to the previous signal-frame capture, the plain
pilot-boundary/1/coarse warm case changes from abort to normal; GDB
square/1/coarse cold changes from normal to SIGSEGV and
pilot-width3/1/contacts warm changes from SIGSEGV to normal. Tests retain these
changes and all older committed evidence.

## Continuing comparison and unresolved producer stores

The earlier four-case continuation now reports 415 differing words before
interactive parsing and 401 at SIGABRT. Ninety-eight previous boundary-word
differences are resolved; two newly visible differences remain at the same
address in the two boundaries. At workspace+3852, an uninitialized mask word
is copied from the earlier `RECT` bytes, whereas the native prior loader
activity leaves a different word. The loader's earlier writes still need
to be implemented. The source does not overwrite this word with the later
observed value or remove it from comparison.

The subsequent independent [loader lookup component](LOADER_LOOKUP.md)
reproduces all eight observed lazy-symbol searches and their complete return
regions/registers. It does not initialize the continuing replay from those
later call frames. Earlier loader state, PLT trampoline and `_dl_fixup`
integration remain required; the 816 differences below are unchanged.

The later [PLT fixup integration](PLT_FIXUP.md) connects the first signal
binding using loader metadata captured before simulation. It resolves 158
stack words on the fresh complete histories, leaving 658 required differences.
Earlier fixtures and checkpoint results below remain separately retained.

All 83 affected CPU tests pass, including the nine new regression tests. The
nine tests and the complete 390-call audit also pass in packaged Pyodide,
version `a95b925e330e962b`. The full compiled continuing audit was rerun: all
130 main histories and three additional histories pass; the rectangular cold
case retains the 816 differences above. All 9,479,168 later heap words and
every other earlier numerical/allocator check remain exact. Test planning
retains every discovered Python test in one required shard; workflow and
patch validation pass. The numerical WebAssembly binary is unchanged.

All complete heaps, allocator events, pre-free bytes, console calls and native
abort behavior still match in that four-case continuation. Full integration
continues to require the remaining loader, formatter/buffer, syscall and
caller-stack stores. Startup, later commands/exit, other analysis branches,
older incomplete-context comparisons and known arithmetic/JOIN/UNJOIN
differences remain unfinished. The production trailing-via guard is retained.

The compressed fixture is 4,896,648 bytes, SHA256
`5cbece3554b8d0a9c8226e4202c40b983774a396d4b5d866e8790f81f6063713`;
its uncompressed SHA256 is
`9ffe295f6cfb7e5ad73c8688146eb20b82ac22d068f99360e0c78c94220cf135`.

```sh
python tools/capture_signal_install_original.py --debug-directory /path/to/debug/usr/lib/debug --reference /path/to/asitic-re --library-path /path/to/native-libraries
PYTHONPATH=src:tests python -m unittest test_signal_install_original -v
python tools/audit_signal_install_original.py --output /tmp/install-audit.json
python tools/build_site.py
node tools/check_signal_install_original.mjs /path/to/pyodide.mjs /tmp/install-wasm-audit.json
node tools/check_command_transition_original.mjs /path/to/pyodide.mjs /tmp/command-main.json /tmp/command-extra.json
```

The independent `signalinstall` suite is mandatory alongside the still-strict
continuing-history suite. Diagnostic reports remain local.
