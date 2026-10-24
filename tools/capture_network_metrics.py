"""Capture original Pi extraction, input impedances, shunts and scattering."""
import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
import random
import struct
import subprocess
import tempfile

from capture_original_symmetric import ORIGINAL_SHA256, LEGACY_SHA256

ROOT = Path(__file__).resolve().parents[1]


def number(x):
    return x if math.isfinite(x) else "nan" if math.isnan(x) else "inf" if x > 0 else "-inf"


def cases():
    rng = random.Random(8890000)
    rows = []
    def add(y, frequency=1e9, load=(50., 0.), port=None, differential=None, model=None, **metadata):
        rows.append(dict(input=[int(model is not None), frequency, rng.randrange(3) if port is None else port,
                                rng.randrange(2) if differential is None else differential, *load, *y,
                                *([0.] * 12 if model is None else model)], **metadata))
    for name in ("network", "network_eddy", "pi_models", "pi_models_eddy", "pix", "gf180_network"):
        fixture = json.loads((ROOT / f"tests/fixtures/{name}.json").read_text())
        for i, c in enumerate(fixture["cases"]):
            y = c["admittance_matrix"]
            if y is None:
                # The fixture's diagnosed failure has no metric input record.
                continue
            native = [v for point in (y[1][1], y[1][0], y[0][1], y[0][0]) for v in point]
            for port, differential in itertools.product(range(3), range(2)):
                add(native, c["frequency_hz"], port=port, differential=differential, production_fixture=name, production_case=i)
    sessions = json.loads((ROOT / "tests/fixtures/pi_sessions_original.json").read_text())["cases"]
    for index, c in enumerate(sessions):
        native = [struct.unpack('<d', bytes.fromhex(v))[0] for v in c["model"]["Y"]]
        frequency = struct.unpack('<d', bytes.fromhex(c["model"]["frequency_bits"]))[0]
        for port, differential in itertools.product(range(3), range(2)):
            add(native, frequency, port=port, differential=differential, session_index=index)
    for _ in range(1024):
        scale = 10. ** rng.uniform(-250., 250.)
        y = [rng.uniform(-2, 2) * scale for _ in range(8)]
        add(y, 10. ** rng.uniform(-250., 250.), load=[rng.uniform(-2., 2.) * scale for _ in range(2)])
    edge = [0., -0., 1., -1., 1e-100, 1e100, 5e-324, float.fromhex('0x1.fffffffffffffp1023'), math.inf, -math.inf, math.nan]
    for a, b, c in itertools.product(edge, repeat=3):
        add([a, b, c, a, b, c, c, b], frequency=a, load=(b, c))
    for i in range(-32, 33):
        threshold = struct.unpack('<d', struct.pack('<Q', struct.unpack('<Q', struct.pack('<d', 1e-10))[0] + i))[0]
        add([threshold, 0., 0., 0., 0., 0., 0., threshold])
    for _ in range(512):
        # Independent model records exercise each shunt and resonance formula,
        # including signed values, without passing through the extractor.
        model = [rng.uniform(-2., 2.) * 10. ** rng.uniform(-100., 100.) for _ in range(12)]
        add([1., 2., 3., 4., 5., 6., 7., 8.], model=model)
    for value in edge:
        add([0.] * 8, model=[value] * 12)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, required=True)
    args = parser.parse_args()
    original = args.reference / "run/asitic.linux.2.2"
    legacy = args.reference / "run/libs/libstdc++-2-libc6.1-1-2.9.0.so"
    for path, sha in ((original, ORIGINAL_SHA256), (legacy, LEGACY_SHA256)):
        if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
            raise ValueError(f"Unexpected oracle checksum: {path}")
    rows = cases()
    source = ROOT / "tools/original_network_metrics_probe.cpp"
    flags = ["-m32", "-O2", "-mfpmath=sse", "-msse2", "-ffp-contract=off", "-fno-pie", "-fno-pic", "-fno-stack-protector", "-fno-exceptions", "-fno-rtti", "-nostdlib", "-no-pie", "-Wl,-Ttext-segment=0x10000000"]
    with tempfile.TemporaryDirectory(prefix="pyasitic-original-metrics-") as directory:
        work = Path(directory)
        binary, payload = work / "probe", work / "input.bin"
        subprocess.run(["g++", *flags, str(source), "/lib/i386-linux-gnu/libc.so.6", "-Wl,--dynamic-linker=/lib/ld-linux.so.2", "-o", str(binary)], check=True)
        payload.write_bytes(struct.pack("<I", len(rows)) + b"".join(struct.pack("<I25d", c["input"][0], *c["input"][1:]) for c in rows))
        run = subprocess.run([str(binary), str(original.resolve()), str(legacy.resolve()), str(payload)], capture_output=True, start_new_session=True, timeout=120)
        if run.returncode or len(run.stdout) != 4 + len(rows) * 264:
            raise RuntimeError(f"Original metrics probe failed {run.returncode}: {len(run.stdout)} bytes, {run.stderr[:300]}")
    before = struct.unpack_from("<H", run.stdout)[0]
    after = struct.unpack_from("<H", run.stdout, len(run.stdout) - 2)[0]
    if before != after or before != 0x37f:
        raise RuntimeError(f"Unexpected x87 control word {before:#x}/{after:#x}")
    for i, c in enumerate(rows):
        raw = run.stdout[2 + 264 * i:2 + 264 * (i + 1)]
        c["input"] = list(map(number, c["input"]))
        c["output_bits"] = raw[:224].hex()
        c["extended_bits"] = [raw[224 + 10 * j:234 + 10 * j].hex() for j in range(4)]
        if "session_index" in c:
            model=json.loads((ROOT / "tests/fixtures/pi_sessions_original.json").read_text())["cases"][c["session_index"]]["model"]["M"]
            if raw[:96].hex() != ''.join(model):
                raise AssertionError("Independent original Pi extractor differs from actual CLI model at identical Y/frequency")
    output = dict(reference="Intact original Pi extractor 0x08089e40, ZIN 0x0804e8b0, imaginary ZIN 0x0804e7c0, terminated ZIN 0x0804e9b0, shunt 0x0804e354, resonance 0x0804ec50 and scattering 0x08087d14, with the original bundled complex DSO. Only the status boundary is replaced; no numerical instructions are replaced. Mode 1 supplies independent model records for shunt/resonance checks. Output stores and retained returns are captured separately.", original_sha256=ORIGINAL_SHA256, legacy_sha256=LEGACY_SHA256, control_word_before=before, control_word_after=after, session_fixture_sha256=hashlib.sha256((ROOT / "tests/fixtures/pi_sessions_original.json").read_bytes()).hexdigest(), probe_source=source.read_text(), compile_flags=flags, cases=rows)
    (ROOT / "tests/fixtures/network_metrics_original.json").write_text(json.dumps(output, separators=(",", ":"), allow_nan=False) + "\n")
    print(len(rows), "original network metric records captured")


if __name__ == "__main__":
    main()
