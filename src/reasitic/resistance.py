"""Ports of resistance.cpp RESIS and RESISHF (0x0804eedc / 0x0804d70c)."""
import math

FREQUENCY_FACTOR = float.fromhex("0x1.921fb544418ecp+4")
UNIT_SCALE = float.fromhex("0x1.a36e2eb1c432dp-14")


def _high_factor(u, aspect):
    first, cube, last = aspect**1.19, u**3, (aspect-1)**1.8
    skin = (float.fromhex("0x1.b945b6c3760bfp-2")*u)/(float.fromhex("0x1.4fdf3b645a1cbp-5")*first+1)
    fraction = (float.fromhex("0x1.496bb98c7e282p+0")*u+float.fromhex("0x1.1d5cfaacd9e84p+0"))/(float.fromhex("0x1.4978d4fdf3b64p+0")*cube+float.fromhex("0x1.3ac710cb295eap+0"))
    return skin+fraction+float.fromhex("0x1.cac083126e979p-9")*last


def _via(s, technology):
    return technology.vias[s.metal-len(technology.metals)].resistance/(s.nx*s.ny)


def resistance_dc(shape, technology):
    """Series conductor resistance in ohms, including via array counts."""
    return sum(_via(s,technology) if s.metal>=len(technology.metals)
               else s.length/s.width*technology.metals[s.metal].resistance
               for s in shape.segments)


def resistance_hf(shape, technology, frequency_hz):
    """Native empirical skin-effect model; RESISHF accepts Hz, not GHz."""
    if not math.isfinite(frequency_hz) or frequency_hz < 0:
        raise ValueError("Frequency must be finite and nonnegative")
    result = 0
    for s in shape.segments:
        if s.metal >= len(technology.metals):
            result += _via(s,technology)
            continue
        m = technology.metals[s.metal]
        u = math.sqrt(frequency_hz*FREQUENCY_FACTOR*1e-9*s.width*UNIT_SCALE/m.resistance)
        if u >= 2.5:
            if s.width < m.thickness:
                raise ValueError("ASITIC's high-frequency model requires width ≥ metal thickness")
            factor = _high_factor(u,s.width/m.thickness)
        else:
            factor = float.fromhex("0x1.8fc504816f007p-7")*u**(3+0.01*u*u)+1
        result += factor*s.length/s.width*m.resistance
    return result
