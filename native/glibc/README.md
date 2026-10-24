The files in this directory adapt glibc 2.39's IBM Accurate Mathematical
Library sin/cos implementation under LGPL-2.1-or-later. Copyright and license
notices are retained in the adapted and upstream files; see COPYING.LIB.
Source URLs and checksums are recorded in source.json.

The adapted code keeps the original polynomial, 440-double lookup table,
argument reduction and operation order. WebAssembly binary64 operations replace
the original temporary 53-bit x87 precision mode. Host errno and floating-point
exception flags are not emulated. The other ASITIC x87 trigonometric instructions
remain separate retained-80 implementations.

The webpage links native-sources.zip, which contains the complete numerical
kernel sources, upstream/adapted library files, notices, original compiled
module and build script. After extracting it, rebuild or verify with:

    python tools/build_kernels.py --download-zig
    python tools/build_kernels.py --download-zig --verify

The pinned compiler may instead be supplied with --zig /path/to/zig.
This rebuilds the complete module, so modifications to this library can be
relinked with all the application's other kernel sources. Python application
sources are supplied separately in reasitic.zip and in the project repository.
