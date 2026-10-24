"""Portable nearest-even x87 scalars for the network metric formulas.

Finite arithmetic uses exact rationals, rounded after every operation to the
64-bit significand and extended exponent range. Signed zero and IEEE nonfinite
classes and NaN payloads are preserved. Exception flags are not emulated.

NaN propagation follows Berkeley SoftFloat 3e, 8086 specialization.
Copyright 2011-2018 The Regents of the University of California.
See SOFTFLOAT-LICENSE.txt for its redistribution conditions and disclaimer.
"""
from fractions import Fraction
from functools import lru_cache
from math import copysign, isfinite, isnan, isqrt
import struct


def _exponent(value):
    n, d = value.numerator, value.denominator
    e = n.bit_length() - d.bit_length()
    below = n < (d << e) if e >= 0 else (n << -e) < d
    if below:
        e -= 1
    return e


@lru_cache(maxsize=256)
def _power(e):
    return Fraction(1 << e) if e >= 0 else Fraction(1, 1 << -e)


def _round(value):
    if not value:
        return value
    sign = -1 if value < 0 else 1
    value = abs(value)
    denominator=value.denominator
    if not(denominator&(denominator-1)):
        # Binary operands and their sums/products are dyadic. Quantize their
        # integer numerator directly instead of dividing two Fractions first.
        # Division/log inputs with other denominators use the general path.
        numerator=value.numerator;bits=numerator.bit_length()
        power=denominator.bit_length()-1;e=bits-1-power
        if e>16383:return None
        shift=max(e-63,-16445);drop=power+shift
        if drop>bits:return Fraction(0)
        if drop>0:
            q=numerator>>drop;remainder=numerator-(q<<drop);half=1<<(drop-1)
            if remainder>half or(remainder==half and q&1):q+=1
        else:q=numerator<<-drop
        if e==16383 and q>=1<<64:return None
        return sign*q*_power(shift)
    e = _exponent(value)
    if e > 16383:
        return None
    shift = max(e - 63, -16445)
    scaled = value / _power(shift)
    q, r = divmod(scaled.numerator, scaled.denominator)
    if 2 * r > scaled.denominator or (2 * r == scaled.denominator and q & 1):
        q += 1
    result = q * _power(shift)
    # Only rounding in the largest binade can overflow. Avoid constructing
    # and comparing a 16,385-bit integer in every ordinary BLAS operation.
    return None if e == 16383 and q >= 1 << 64 else sign * result


class Real:
    """Retained scalar; binary64 stores are explicit calls to float()."""
    __slots__ = ("value", "kind", "negative", "nan_significand")

    def __init__(self, value=0.):
        if isinstance(value, Real):
            self.value, self.kind, self.negative, self.nan_significand = value.value, value.kind, value.negative, value.nan_significand
            return
        self.kind = 0
        self.nan_significand = 0
        self.negative = copysign(1., value) < 0 if isinstance(value, float) else value < 0
        if isinstance(value, float) and not isfinite(value):
            self.value, self.kind = Fraction(0), 2 if isnan(value) else 1
            if self.kind==2:
                word=struct.unpack('<Q',struct.pack('<d',value))[0]
                self.nan_significand=0xc000000000000000|((word&0xfffffffffffff)<<11)
        else:
            self.value = Fraction(value)

    @classmethod
    def memory_operand(cls,value):
        """An arithmetic memory source keeps sNaN status until propagation.

        FLD first quiets a binary64 signaling NaN; FSUBL's memory source is
        instead consumed by the arithmetic operation's NaN selection rule.
        """
        result=cls(value)
        if result.kind==2 and isinstance(value,float):
            word=struct.unpack('<Q',struct.pack('<d',value))[0]
            result.nan_significand=0x8000000000000000|((word&0xfffffffffffff)<<11)
        return result

    @classmethod
    def from_words(cls,low,high,exponent):
        """Decode stored x87 words, retaining the sign and significand of NaNs."""
        sig=int(low)|(int(high)<<32);exponent=int(exponent);power=exponent&0x7fff;negative=bool(exponent&0x8000)
        if power==0x7fff:
            result=cls(-float('inf')if negative else float('inf'))
            if sig!=1<<63:result.kind=2;result.nan_significand=sig
            return result
        if not sig:return cls(-0. if negative else 0.)
        return cls((-sig if negative else sig)*_power((power or 1)-16383-63))

    @classmethod
    def _invalid(cls):
        return cls.from_words(0,0xc0000000,0xffff)

    @classmethod
    def _propagate_nan(cls,a,b=None):
        # SoftFloat 8086 s_propagateNaNExtF80UI: a quiet NaN takes precedence
        # over a signaling NaN. Otherwise select the larger significand,
        # preferring positive on a magnitude tie, then quiet the result.
        candidates=[x for x in(a,b)if x is not None and x.kind==2]
        quiet=[x for x in candidates if x.nan_significand&(1<<62)]
        selected=max(quiet or candidates,key=lambda x:(x.nan_significand,not x.negative))
        result=cls(selected);result.nan_significand|=0xc000000000000000
        return result

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
        if self.kind==2:
            word=(int(self.negative)<<63)|0x7ff8000000000000|((self.nan_significand&0x7fffffffffffffff)>>11)
            return struct.unpack('<d',struct.pack('<Q',word))[0]
        if self.kind:
            return -float('inf')if self.negative else float('inf')
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
            return Real._propagate_nan(self,other)
        if self.kind or other.kind:
            if self.kind and other.kind and self.negative != other.negative:
                return Real._invalid()
            return Real(self if self.kind else other)
        return Real._result(self.value + other.value, self.negative and other.negative)

    __radd__ = __add__

    def __sub__(self, other):
        other=Real(other)
        if self.kind==2 or other.kind==2:return Real._propagate_nan(self,other)
        return self + -other

    def __rsub__(self, other):
        return Real(other) - self

    def __mul__(self, other):
        other = Real(other)
        negative = self.negative != other.negative
        if self.kind==2 or other.kind==2:return Real._propagate_nan(self,other)
        if (self.kind == 1 and not other.kind and not other.value) or (other.kind == 1 and not self.kind and not self.value):
            return Real._invalid()
        if self.kind or other.kind:
            return Real(-float("inf") if negative else float("inf"))
        return Real._result(self.value * other.value, negative)

    __rmul__ = __mul__

    def __truediv__(self, other):
        other = Real(other)
        negative = self.negative != other.negative
        if self.kind==2 or other.kind==2:return Real._propagate_nan(self,other)
        if (self.kind and other.kind) or (not self.kind and not other.kind and not self.value and not other.value):
            return Real._invalid()
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
        if self.kind==2:return Real._propagate_nan(self)
        if self.negative and (self.kind or self.value):return Real._invalid()
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
            sig, exponent = (1 << 63) if self.kind == 1 else self.nan_significand, 0x7fff
        elif not self.value:
            sig, exponent = 0, 0
        else:
            value = abs(self.value)
            e = _exponent(value)
            exponent = max(e + 16383, 0)
            sig = int(value / _power(e - 63 if exponent else -16445))
        return sig & 0xffffffff, sig >> 32, exponent | (0x8000 if self.negative else 0)
