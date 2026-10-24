# Linux i386 signal-frame serialization

`signal_frame.py` reproduces legacy signal delivery from the interrupted CPU
state, existing guest stack, signal action/mask, CPU XSAVE layout and loader
VDSO image. All 130 observed deliveries match in portable Python and packaged
Pyodide. This independently verifies the kernel stack-writing component
needed by the rectangular command-continuation fault; it does not supply the
missing interrupted CPU state to that continuation.

## Inputs and stores

The legacy i386 record retains its historical unused FP area. The active
FP state is allocated separately above it. The serializer resolves the return
stub from the earlier VDSO ELF32 symbol table, stores the signal context,
mask and legacy return signature, and preserves unused record bytes. The
record fields and return behavior follow the [Linux signal-frame
layout](https://github.com/torvalds/linux/blob/v7.0/arch/x86/include/asm/sigframe.h)
and [32-bit signal
interface](https://github.com/torvalds/linux/blob/v7.0/arch/x86/kernel/signal_32.c).

| Offset in the legacy record | Contents |
| ---: | --- |
| 0 | Return stub pointer |
| 4 | Signal number |
| 8 | 88-byte interrupted register context |
| 96 | Historical 624-byte FP area, preserved |
| 720 | High word of the saved signal mask |
| 724 | Eight-byte legacy return signature |

The XSAVE area is aligned to 64 bytes, preceded by the 112-byte i386 FSAVE
prefix. The legacy record has the i386 entry stack alignment. These addresses
derive from the interrupted ESP and the earlier CPU layout, not from a later
observed handler ESP. Allocation/alignment and software extension fields
follow the [Linux FP signal
interface](https://github.com/torvalds/linux/blob/v7.0/arch/x86/kernel/fpu/signal.c).

The serializer expands FXSAVE's abridged x87 tags, rotates physical tags using
TOP, and packs eight ten-byte extended values. It independently matches the
pre-delivery kernel's 108-byte legacy ptrace record. Full/zero/special/empty
tags and nonzero TOP additionally have explicit tests. The corresponding
kernel interface is [FP register
conversion](https://github.com/torvalds/linux/blob/v7.0/arch/x86/kernel/fpu/regset.c).

The save writes legacy register slots and declared extended components while
preserving reserved gaps. In particular, the PKRU component reserves eight
bytes but only its low four bytes are stored. Copying a zero-filled eight-byte
ptrace component incorrectly overwrites an old stack word. The handler's
general registers, signal mask and initialized FP/SIMD state are independently
generated too. CPU feature sizes/offsets and initial PKRU come from a separate
CPUID/RDPKRU probe executed before capture.

RT actions, alternate stacks, additional action flags, compacted/restricted
XSAVE and additional component types remain explicit unsupported paths.
Malformed XSAVE inputs fail before changing guest stack bytes. The currently
captured CPU exposes feature mask `0x2e7` and a 2,440-byte standard XSAVE area;
these are fixture machine inputs, not runtime lookup keys.

## Read-only native evidence

`capture_signal_frames_original.py` retains all 134 existing histories with
their unchanged requests, scripts, stdin and cold/warm disk states. Each
plain/GDB pair starts from identical files. The launcher uses the explicit
minimal environment introduced for command stack capture, and the observer
rejects unexpected inferior environment names before reading stack data.

At the `rt_sigaction` syscall boundary it reads the earlier installed action.
At SIGQUIT delivery it reads registers, XSAVE, the legacy FP regset, signal
mask, entire stack and VDSO. GETREGSET/GETSIGMASK and procfs reads do not set
inferior values. The observer records the resulting stack, registers, mask
and FP state at the native handler's first instruction.

The unchanged kill PLT instruction is stepped over by GDB's normal breakpoint
protocol before the signal. This establishes the earlier debug trap number
1 and error code 0 used in the saved context. This original has no earlier
handled memory fault in these histories, so its bootstrap CR2 remains zero.
Those thread inputs describe this observation protocol; the serializer
requires callers to supply their own interrupted thread state.

Later handler bytes and registers are comparison outputs only. Tests mutate
them and require differences without changing generated source outputs.
Mutating the earlier contents of reserved frame/XSAVE bytes changes the
retained output bytes, proving they are not filled from the later native dump.

## Results and remaining continuation work

The independent strict audit covers all 134 cases. Four native histories
fault before signal delivery and remain explicitly present: square/64/contacts
cold, pilot-width3/1/contacts cold and warm, and pilot-boundary/1/coarse warm.
The rectangular cold history delivers SIGQUIT and subsequently reaches
SIGABRT. The ABI serializer does not claim to predict the earlier application
faults in cases with no signal-delivery input.

| Compared observation | Count | Differences |
| --- | ---: | ---: |
| Signal deliveries | 130 | 0 |
| Entire stack words, including untouched bytes | 4,392,960 | 0 |
| Handler general/segment registers | 2,210 | 0 |
| Handler XSAVE bytes | 317,200 | 0 |
| Independent earlier legacy FP bytes | 14,040 | 0 |

GDB runs retain 129 normal exits, four SIGSEGV and one SIGABRT. Fresh plain
runs retain 129 normal exits, four SIGABRT and one SIGSEGV. Compared with the
earlier command-capture plain runs, pilot-width3/1/coarse warm,
pilot-width3/1/contacts cold and pilot-boundary/1/coarse cold change from abort
to normal. Neither those native differences nor the four missing deliveries
are recast as successfully simulated application histories.

The full continuing [command-history gate](COMMAND_TRANSITION.md) remains
mandatory and still reports 912 differing boundary words. Its initial driver
inputs are not replaced with the pre-signal inputs used in this component
comparison. Deriving that interrupted CPU state, reproducing earlier loader
and application stack stores, and connecting signal delivery to the continuing
history remain work. All earlier numerical/heap gates and the production
trailing-via guard remain intact. This checkpoint is not deployed as whole
program equivalence.

All 74 affected CPU tests pass. The nine new tests and complete signal audit
also pass in packaged Pyodide, version `2b18ff083ee49d15`. The unchanged
continuation audit was rerun on that package: 130 main histories and three
additional histories pass, while the rectangular case retains 463 words at
interactive parser entry and 449 words at SIGABRT. The numerical WebAssembly
binary remains SHA256
`c7869e98f4c18b5414dc172d836e7144ab3ebc0de2de0d1f2eec1a4fe1709186`.

A further local hardware-watch diagnostic covers every one of the 463
pre-parse differences, up to four watched words per unchanged-original run. The
largest last-writer groups are loader lookup/fixup functions (156 words),
signal-installation functions (48), and libc formatting/buffering paths.
Seventeen words have no observed user-space writer and require investigation
at kernel I/O boundaries. This classification is diagnostic evidence, not
a table used to generate source memory. The full difference gate is retained.

The compressed fixture is 2,618,385 bytes, SHA256
`1784ce9c11d225a196f705c1f5a92a462059631a27bf653caf52b8ea54ff58d9`;
its uncompressed SHA256 is
`11931d169a21ee25191aebdccd14548e2a07d66f7d8740adfbf0922c558ede1e`.

```sh
python tools/capture_signal_frames_original.py --reference /path/to/asitic-re --library-path /path/to/native-libraries
PYTHONPATH=src:tests python -m unittest test_signal_frames_original -v
python tools/audit_signal_frames_original.py --output /tmp/signal-audit.json
python tools/build_site.py
node tools/check_signal_frames_original.mjs /path/to/pyodide.mjs /tmp/signal-wasm-audit.json
```

The required `signalframes` CI suite runs the component comparison in addition
to the existing continuing-history suite. Diagnostic reports remain local.
