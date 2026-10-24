"""Original network.cpp metrics and two_port_output.cpp S conversion.

Raw records use native y11/y12/y21/y22 ordering and SI units. Public Pi field
names retain the webpage's port order. No modern circuit convention is applied.
"""
from array import array
from collections import namedtuple
import math
from .retained_scalar import Real as R

try:
    from _reasitic_numeric import network_metrics as _compiled_metrics
except ImportError:
    _compiled_metrics = None

TWO_PI = float.fromhex("0x1.921fb54442d18p+2")
PI_KEYS = ("inductance_h", "resistance_ohm", "capacitance_first_f", "capacitance_second_f",
           "resistance_first_ohm", "resistance_second_ohm", "q_first", "q_second",
           "q_differential", "shunt_single_ohm", "shunt_differential_ohm")
Model = namedtuple("Model", "frequency inductance resistance capacitance_second capacitance_first resistance_second resistance_first quality_first quality_second quality_differential shunt_single shunt_differential")


def _pair(z):
    return R(z.real), R(z.imag)


def _spill(z):
    return complex(float(z[0]), float(z[1]))


def _multiply(a, b):
    return a[0] * b[0] - a[1] * b[1], a[1] * b[0] + a[0] * b[1]


def _divide(a, b):
    ar, ai = _pair(a)
    c, d = _pair(b)
    if abs(d) >= abs(c):
        ratio = c / d
        denominator = (ratio * ratio) * d + d
        return _spill(((ar * ratio + ai) / denominator, (ai * ratio - ar) / denominator))
    ratio = d / c
    denominator = (ratio * ratio) * c + c
    return _spill(((ai * ratio + ar) / denominator, (ai - ar * ratio) / denominator))


def _scalar_divide(a, b):
    c, d = _pair(b)
    n = R(a)
    if abs(c) <= abs(d):
        ratio = c / d
        denominator = (ratio * ratio) * d + d
        return _spill(((n * ratio) / denominator, -n / denominator))
    ratio = d / c
    denominator = (ratio * ratio) * c + c
    return _spill((n / denominator, (-n * ratio) / denominator))


def _impedance(y, differential, port):
    if not differential:
        return _scalar_divide(1., y["y22" if port == 1 else "y11"])
    ar, ai = _pair(y["y22"])
    br, bi = _pair(y["y11"])
    cr, ci = _pair(y["y21"])
    product = cr * ci
    determinant = _spill(((ar * br - ai * bi) - R(float(cr * cr - ci * ci)),
                          (ar * bi + br * ai) - (product + product)))
    numerator = _spill(((ar + br) + (cr + cr), (ai + bi) + (ci + ci)))
    return _divide(numerator, determinant)


def _terminated(y, load, port):
    admittance = _pair(_scalar_divide(1., load))
    a, b, c, d = [_pair(y[key]) for key in ("y22", "y11", "y21", "y12")]
    base = _multiply(a, b)
    extra = _multiply(a if port == 1 else b, admittance)
    cross = _multiply(c, d)
    other = b if port == 1 else a
    return _divide(_spill((other[0] + admittance[0], other[1] + admittance[1])),
                   _spill(((base[0] + extra[0]) - cross[0], (base[1] + extra[1]) - cross[1])))


def _shunt(p, differential):
    c = (R(p.capacitance_second) * p.capacitance_first) / (R(p.capacitance_second) + p.capacitance_first) if differential else R(p.capacitance_second)
    resistance = R(p.resistance_second) + p.resistance_first if differential else R(p.resistance_second)
    angular = R(p.frequency) * TWO_PI
    def square(x):
        return 0. if x == 0. else float((x * x) * R(1.))
    a = square((angular * p.inductance) / p.resistance)
    b = square(R(1.) / ((angular * c) * resistance))
    series = (R(a) + R(1.)) * p.resistance
    shunt = (R(1.) + b) * resistance
    return (series * shunt) / (series + shunt)


def _resonance(p):
    ratio = R(p.capacitance_second) / p.inductance
    correction = (R(1.) - (R(p.resistance) * p.resistance) * ratio) / (R(1.) - (R(p.resistance_second) * p.resistance_second) * ratio)
    result = R(1.) / (R(p.inductance) * p.capacitance_second)
    if correction > 0.:
        result *= correction
    return result.sqrt() / TWO_PI


def _extract(y, frequency):
    second = _spill((R(y["y21"].real) + y["y22"].real, R(y["y21"].imag) + y["y22"].imag))
    first = _spill((R(y["y11"].real) + y["y12"].real, R(y["y11"].imag) + y["y12"].imag))
    series = -y["y21"]
    angular = float(R(frequency) * TWO_PI)
    impedance = _scalar_divide(1., series)
    def shunt(z):
        re, im = _pair(z)
        if float((re * re + im * im).sqrt()) > 1e-10:
            inverse = _scalar_divide(1., z)
            return float(R(-1.) / (R(angular) * inverse.imag)), inverse.real
        return 0., 1e15
    c2, r2 = shunt(second)
    c1, r1 = shunt(first)
    differential = _impedance(y, True, 1)
    model = Model(frequency, float(R(impedance.imag) / angular), impedance.real, c2, c1, r2, r1,
                  float(-(R(second.imag) + series.imag) / (R(second.real) + series.real)),
                  float(-(R(series.imag) + first.imag) / (R(series.real) + first.real)),
                  float(R(differential.imag) / differential.real), 0., 0.)
    return model._replace(shunt_single=float(_shunt(model, False)), shunt_differential=float(_shunt(model, True)))


def _scattering(y):
    reference = R(.02)
    a, b, c, d = [_pair(y[key]) for key in ("y11", "y12", "y21", "y22")]
    positive_a, negative_a = (a[0] + reference, a[1]), (reference - a[0], -a[1])
    positive_d, negative_d = (d[0] + reference, d[1]), (reference - d[0], -d[1])
    cross = _multiply(c, b)
    base = _multiply(positive_d, positive_a)
    denominator = _spill((base[0] - cross[0], base[1] - cross[1]))
    def diagonal(x, z):
        v = _multiply(x, z)
        return _divide(_spill((v[0] + cross[0], v[1] + cross[1])), denominator)
    s11, s22 = diagonal(negative_d, positive_d), diagonal(positive_d, negative_a)
    s21 = _divide(_spill(((-R(2.) * c[0]) * reference, (-R(2.) * c[1]) * reference)), denominator)
    s12 = _divide(_spill(((b[0] * -R(2.)) * reference, (-R(2.) * b[1]) * reference)), denominator)
    return [[s11, s12], [s21, s22]]


def probe(rows, operation=3):
    """Bounded raw records shared by the Python fallback and compiled backend."""
    if operation not in range(4) or not 1 <= len(rows) <= 256 or any(len(r) != 26 for r in rows):
        raise ValueError("Invalid network metric batch")
    if _compiled_metrics is not None:
        data = array("d", (v for row in rows for v in row))
        output = array("d", [0.]) * (42 * len(rows))
        if _compiled_metrics(data, output, operation):
            raise ValueError("Invalid network metric configuration")
        return [list(output[i * 42:(i + 1) * 42]) for i in range(len(rows))]
    result = []
    for p in rows:
        if p[0] not in (0, 1) or p[2] not in (0, 1, 2) or p[3] not in (0, 1):
            raise ValueError("Invalid network metric configuration")
        y = {key: complex(*p[6 + 2 * i:8 + 2 * i]) for i, key in enumerate(("y11", "y12", "y21", "y22"))}
        output = [0.] * 42
        if operation in (0, 3):
            model = _extract(y, p[1]) if p[0] == 0 else Model(*p[14:])
            output[1:13] = model
            scalars = [_shunt(model, False), _shunt(model, True), _resonance(model)]
            output[13:16] = map(float, scalars)
            for i, value in enumerate(scalars):
                output[29 + 3 * i:32 + 3 * i] = value.words()
        if operation in (1, 3):
            z = _impedance(y, bool(p[3]), int(p[2]))
            output[16:18] = z.real, z.imag
            imaginary = R(_impedance(y, bool(p[3]), 1).imag)
            output[18] = float(imaginary)
            terminated = _terminated(y, complex(*p[4:6]), int(p[2]))
            output[19:21] = terminated.real, terminated.imag
            output[38:41] = imaginary.words()
        if operation in (2, 3):
            output[21:29] = [v for row in _scattering(y) for z in row for v in (z.real, z.imag)]
        result.append(output)
    return result


def _record(y, frequency=0., port=1, differential=False):
    return [0., frequency, port, int(differential), 50., 0.,
            *[v for key in ("y11", "y12", "y21", "y22") for v in (y[key].real, y[key].imag)], *([0.] * 12)]


def impedance(y, differential=False, port=1):
    value = probe([_record(y, port=port, differential=differential)], 1)[0]
    return complex(*value[16:18])


def extract(y, frequency):
    value = probe([_record(y, frequency)], 0)[0]
    result = dict(zip(PI_KEYS, value[2:13]))
    result["resonant_frequency_hz"] = value[15]
    return {key: v if math.isfinite(v) else None for key, v in result.items()}


def scattering(y):
    value = probe([_record(y)], 2)[0]
    z = [complex(*value[21 + 2 * i:23 + 2 * i]) for i in range(4)]
    return [z[:2], z[2:]]
