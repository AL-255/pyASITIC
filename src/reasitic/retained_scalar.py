"""Portable nearest-even x87 scalars for the network metric formulas.

Finite arithmetic uses exact rationals, rounded after every operation to the
64-bit significand and extended exponent range. Signed zero and IEEE nonfinite
classes are preserved. This module does not emulate exception flags or payloads.
"""
from fractions import Fraction
from math import copysign, isfinite, isnan, isqrt


def _exponent(value):
    n, d = value.numerator, value.denominator
    e = n.bit_length() - d.bit_length()
    below = n < (d << e) if e >= 0 else (n << -e) < d
    if below:
        e -= 1
    return e


def _power(e):
    return Fraction(1 << e) if e >= 0 else Fraction(1, 1 << -e)


def _round(value):
    if not value:
        return value
    sign = -1 if value < 0 else 1
    value = abs(value)
    e = _exponent(value)
    if e > 16383:
        return None
    shift = max(e - 63, -16445)
    scaled = value / _power(shift)
    q, r = divmod(scaled.numerator, scaled.denominator)
    if 2 * r > scaled.denominator or (2 * r == scaled.denominator and q & 1):
        q += 1
    result = q * _power(shift)
    return None if result >= _power(16384) else sign * result


class Real:
    """Retained scalar; binary64 stores are explicit calls to float()."""
    __slots__ = ("value", "kind", "negative")

    def __init__(self, value=0.):
        if isinstance(value, Real):
            self.value, self.kind, self.negative = value.value, value.kind, value.negative
            return
        self.kind = 0
        self.negative = copysign(1., value) < 0 if isinstance(value, float) else value < 0
        if isinstance(value, float) and not isfinite(value):
            self.value, self.kind = Fraction(0), 2 if isnan(value) else 1
        else:
            self.value = Fraction(value)

    @classmethod
    def _result(cls, value, negative=False):
        result = cls(0.)
        result.negative = value < 0 if value else negative
        rounded = _round(value)
        if rounded is None:
            result.kind = 1
        else:
            result.value = rounded
        return result

    def __float__(self):
        if self.kind:
            return copysign(float("nan" if self.kind == 2 else "inf"), -1. if self.negative else 1.)
        if not self.value:
            return -0. if self.negative else 0.
        try:
            return float(self.value)
        except OverflowError:
            return -float("inf") if self.negative else float("inf")

    def __neg__(self):
        result = Real(self)
        result.negative = not self.negative
        result.value = -self.value
        return result

    def __abs__(self):
        return -self if self.negative else Real(self)

    def __add__(self, other):
        other = Real(other)
        if self.kind == 2 or other.kind == 2:
            return Real(float("nan"))
        if self.kind or other.kind:
            if self.kind and other.kind and self.negative != other.negative:
                return Real(float("nan"))
            return Real(self if self.kind else other)
        return Real._result(self.value + other.value, self.negative and other.negative)

    __radd__ = __add__

    def __sub__(self, other):
        return self + -Real(other)

    def __rsub__(self, other):
        return Real(other) - self

    def __mul__(self, other):
        other = Real(other)
        negative = self.negative != other.negative
        if self.kind == 2 or other.kind == 2 or (self.kind == 1 and not other.kind and not other.value) or (other.kind == 1 and not self.kind and not self.value):
            return Real(float("nan"))
        if self.kind or other.kind:
            return Real(-float("inf") if negative else float("inf"))
        return Real._result(self.value * other.value, negative)

    __rmul__ = __mul__

    def __truediv__(self, other):
        other = Real(other)
        negative = self.negative != other.negative
        if self.kind == 2 or other.kind == 2 or (self.kind and other.kind) or (not self.kind and not other.kind and not self.value and not other.value):
            return Real(float("nan"))
        if self.kind or (not other.kind and not other.value):
            return Real(-float("inf") if negative else float("inf"))
        if other.kind:
            return Real(-0. if negative else 0.)
        return Real._result(self.value / other.value, negative)

    def __rtruediv__(self, other):
        return Real(other) / self

    def __eq__(self, other):
        other = Real(other)
        if self.kind == 2 or other.kind == 2:
            return False
        return self.kind == other.kind and (self.negative == other.negative if self.kind else self.value == other.value)

    def __lt__(self, other):
        other = Real(other)
        if self.kind == 2 or other.kind == 2:
            return False
        if self.kind:
            return self.negative and (not other.kind or not other.negative)
        if other.kind:
            return not other.negative
        return self.value < other.value

    def __le__(self, other):
        return self < other or self == other

    def __gt__(self, other):
        return Real(other) < self

    def __ge__(self, other):
        return Real(other) <= self

    def sqrt(self):
        if self.kind == 2 or (self.negative and (self.kind or self.value)):
            return Real(float("nan"))
        if self.kind or not self.value:
            return Real(self)
        shift = max(_exponent(self.value) // 2 - 63, -16445)
        scaled = self.value / _power(2 * shift)
        n, d = scaled.numerator, scaled.denominator
        q = isqrt(n // d)
        midpoint = d * (2 * q + 1) ** 2
        if 4 * n > midpoint or (4 * n == midpoint and q & 1):
            q += 1
        return Real._result(q * _power(shift))

    def words(self):
        """Little-endian significand halves and sign/exponent for diagnostics."""
        if self.kind:
            sig, exponent = (1 << 63) if self.kind == 1 else (3 << 62), 0x7fff
        elif not self.value:
            sig, exponent = 0, 0
        else:
            value = abs(self.value)
            e = _exponent(value)
            exponent = max(e + 16383, 0)
            sig = int(value / _power(e - 63 if exponent else -16445))
        return sig & 0xffffffff, sig >> 32, exponent | (0x8000 if self.negative else 0)
