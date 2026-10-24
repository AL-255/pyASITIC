"""ASITIC .tek reader. RSH is specified in milliohms per square."""
from dataclasses import dataclass, asdict, field
from pathlib import Path
import math
import re
from .retained_scalar import Real


@dataclass(frozen=True)
class Metal:
    name: str
    height: float
    thickness: float
    resistance: float
    layer: int
    color: str = "#e8b665"
    coordinate_height: float | None = None

    @property
    def geometry_height(self):
        return self.height if self.coordinate_height is None else self.coordinate_height


@dataclass(frozen=True)
class Via:
    name: str
    bottom: int
    top: int
    resistance: float
    width: float
    spacing: float
    overplot1: float
    overplot2: float


@dataclass
class Technology:
    metals: list[Metal]
    vias: list[Via]
    substrate: list[dict]
    chip: dict
    eddy_layers: list[int] = field(default_factory=list)

    @classmethod
    def from_text(cls, text):
        blocks = {"chip": [], "layer": [], "metal": [], "via": []}
        current = None
        eddy_layers = []
        for line in text.splitlines():
            line = line.split(";", 1)[0].strip()
            if not line:
                continue
            match = re.fullmatch(r"<(chip|layer|metal|via)>\s*(\d+)?", line, re.I)
            if match:
                kind = match[1].lower()
                current = {}
                if kind != "chip" and match[2] is not None and int(match[2]) != len(blocks[kind]):
                    raise ValueError(f"{kind} indices must be consecutive from zero")
                blocks[kind].append(current)
            elif current is not None and "=" in line:
                key, value = (p.strip() for p in line.split("=", 1))
                try:
                    value = float(value)
                    if not math.isfinite(value):
                        raise ValueError("Technology values must be finite")
                except ValueError:
                    if key.lower() not in {"name", "color", "techfile", "techpath"}:
                        raise ValueError(f"Invalid technology value: {line}") from None
                current[key.lower()] = value
                if kind=="chip" and key.lower().startswith("eddy") and len(eddy_layers)<2:
                    eddy_layers.append(int(value))
            else:
                raise ValueError(f"Invalid technology line: {line}")
        metals, vias = [], []
        depths = [0.] * (len(blocks["layer"]) + 1)
        for i in range(len(blocks["layer"]) - 1, -1, -1):
            depths[i] = float(Real(blocks["layer"][i]["t"]) + depths[i + 1])
        for i, m in enumerate(blocks["metal"]):
            if m["t"] <= 0 or m["rsh"] <= 0:
                raise ValueError("Metal thickness and sheet resistance must be positive")
            layer = int(m["layer"])
            if not 0 <= layer < len(blocks["layer"]):
                raise ValueError("Metal references an unknown substrate layer")
            if m["d"] < 0 or m["d"] > blocks["layer"][layer]["t"]:
                raise ValueError("Metal height falls outside its substrate layer")
            # Geometry reloads depth - stored(depth - d), while the spectral
            # tables use the first stored top distance. Cancellation in these
            # two binary64 stores is observable in eddy and mutual terms.
            top_distance = float(Real(depths[layer]) - m["d"])
            coordinate_height = float(Real(depths[layer]) - top_distance)
            metals.append(Metal(str(m.get("name", f"M{i+1}")).upper(), m["d"],
                                m["t"], float(Real(m["rsh"])*.001), layer, str(m.get("color", "#e8b665")),coordinate_height))
        for i, v in enumerate(blocks["via"]):
            bottom, top = int(v["bottom"]), int(v["top"])
            if not (0 <= bottom < len(metals) and 0 <= top < len(metals)) or bottom == top:
                raise ValueError("Via must connect two distinct metal layers")
            if v["width"] <= 0 or v.get("space", 0) < 0 or v.get("r", 0) < 0:
                raise ValueError("Invalid via dimensions or resistance")
            vias.append(Via(str(v.get("name", f"VIA{i+1}")).upper(), bottom, top,
                            v.get("r", 0), v["width"], v.get("space", 0),
                            v.get("overplot1", 0), v.get("overplot2", 0)))
        if not metals:
            raise ValueError("Technology must contain at least one metal layer")
        return cls(metals, vias, blocks["layer"], blocks["chip"][0] if blocks["chip"] else {},eddy_layers)

    @classmethod
    def default(cls):
        return cls.from_text(Path(__file__).with_name("CMOS.tek").read_text())

    def metal_index(self, value):
        if isinstance(value, int) or str(value).lstrip("-").isdigit():
            index = int(value)
            if 0 <= index < len(self.metals):
                return index
        for i, metal in enumerate(self.metals):
            if metal.name == str(value).upper():
                return i
        raise ValueError(f"Unknown metal: {value}")

    def via_index(self, value):
        for i, via in enumerate(self.vias):
            if str(value).upper() == via.name or str(value) == str(i):
                return i
        raise ValueError(f"Unknown via: {value}")

    def to_dict(self):
        return asdict(self)
