# Interactive capacitor phase from earlier loader state

The raw phase value of a fresh interactive capacitor comes from a previous
lazy `strcmp` binding. It is not a chosen electrical phase. The original
interactive capacitor prompt never initializes the phase field, so its
argument descriptor retains a stack word from the dynamic loader. Keyword
capacitor input does initialize the phase field and follows a separate path.

The shared-memory PLT replay now implements the missing pinned i386 glibc
`strcmp` IFUNC selector. It follows usable SSE4.2, then SSSE3, then ia32
selection from the earlier CPU feature word, including the PC-thunk return
store. ELF relocation, symbol lookup, IFUNC selection and the complete target
entry execute from the earlier guest memory. No native function address or
captured phase value is a runtime input.

## Source of the word

Let `t` be ESP at the native lazy resolver entry. The trampoline calls
`_dl_fixup`; its lookup-call frame then enters `_dl_lookup_symbol_x` with
ESI holding the ELF symbol-name pointer. That function's ESI save writes the
pointer at `t - 140`. The pointer is derived from the earlier dynamic string
table and symbol entry; the Python implementation does not contain the
observed `0x08049d56` value.

In the four captured fresh interactive capacitor histories, the later argument
descriptor's phase field at offset `0xac` occupies that same stack slot.
A hardware write watch starts at resolved `strcmp` target entry. It records
zero value changes before capacitor constructor entry. The constructor's
incoming phase and the completed WHO descriptor retain the generated pointer.
Three later value changes occur when the caller reuses this stack storage;
they occur after the capacitor has consumed and copied its phase value.

The earlier observed slot starts at zero. Source replay generates the later
pointer through the loader's actual saves; initializing it with the expected
phase would fail to demonstrate this provenance. A mutation test changes the
later constructor/descriptor phase expectations and requires two failures,
without changing the generated source stack.

The selector follows primary glibc 2.39 sources
[`strcmp.c`](https://github.com/bminor/glibc/blob/glibc-2.39/sysdeps/i386/i686/multiarch/strcmp.c)
and [`ifunc-ssse3-sse4_2.h`](https://github.com/bminor/glibc/blob/glibc-2.39/sysdeps/i386/i686/multiarch/ifunc-ssse3-sse4_2.h),
checked against the pinned Ubuntu libc resolver at offset `0xa3e10`.
Their SHA-256 digests are respectively
`dea188c399ab4f37a929613a0e1ae05056e033415f6472c174ca05c6b3eca37d` and
`bbc409c2bd1398dd5b775a64d5a7b31afd02116bc946d13c2eb7ce8a8e23897f`.
The translated runtime remains under the existing glibc attribution and
LGPL notice in `plt_fixup_storage.py` and `web/GLIBC-LGPL-2.1.txt`.

## Evidence and scope

Four unchanged original interactive creators cover zero, positive, negative
and full-turn orientation inputs. Each plain script exits normally. The
read-only observer records the earlier native `strcmp` resolver entry, its
target entry, constructor arguments, later WHO descriptor and write-watch
events. The observer preserves original numerical instructions, memory,
registers, allocation decisions, CPU feature bits and outcomes. The earlier
input includes ELF lookup metadata, GOT, TLS, CPU flags, full stack,
registers and XSAVE. Later observations are assertions only.

Portable Python and packaged Pyodide both match:

- Four complete native resolver calls and all **666,424 memory words**.
- **68 register values** and **9,760 FP-state bytes**.
- **16 later phase-word assertions**, covering parsed metadata and raw bytes
  at constructor entry and in the completed descriptor.

All three new tests and eight existing PLT tests pass in Python. The required
`phase-origin` Pages job runs the new tests and complete report in packaged
Pyodide; the existing PLT job remains required too. Existing original PLT
fixups retain their complete native target-word/register/FP comparisons.

The archive `phase_origin_original.json.gz` is 1,236,471 bytes, SHA-256
`87d14a9657b21e6a981bfdde246fc7ee4927d7cedca015a36be89dd8f54b5079`.
It retains plain outcomes, capture commands, parent hashes, minimal process
environments and original binary/library digests. No archive is included in
the runtime package. Source package: `9b098b20ad2a4225`; numerical WASM remains
SHA-256 `c7869e98f4c18b5414dc172d836e7144ab3ebc0de2de0d1f2eec1a4fe1709186`.

## Remaining integration

This proves an earlier source of the capacitor word and executes a previously
unsupported loader path. It does not replay every startup, prompt or previous
command between resolver entry and capacitor creation. The typed webpage
API still lacks that complete shared startup memory. Its four capacitor
phase-word differences and the two JOINSHUNT deleted-source-address
differences remain in the strict zero-difference gate; none is exempted or
replaced with a recovered constant. Initial scene construction, secondary
groups in shared-memory geometry setup and integration into the continuing
process remain required work, along with the known numerical/heap gates.
The development branch remains undeployed.

```sh
python tools/capture_phase_origin_original.py --reference ~/github/asitic-re \
  --library-path /path/to/i386/libs --debug-directory /path/to/libc/debug
PYTHONPATH=src:tests python -m unittest test_phase_origin_original test_plt_fixup_original -v
python tools/audit_phase_origin_original.py --output /tmp/phase-origin-cpu.json
python tools/build_site.py
node tools/check_phase_origin_original.mjs /path/to/pyodide.mjs /tmp/phase-origin-wasm.json
node tools/check_plt_fixup_original.mjs /path/to/pyodide.mjs /tmp/plt-regression.json
```
