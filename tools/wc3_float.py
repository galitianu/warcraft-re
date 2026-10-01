"""WC3 1.29.2 (9231) float32 helpers needed to print values the way the game does.

The arithmetic mirrors src/core/SoftFloat.cpp (add, mul, i2f, f2i): truncating
soft-float on IEEE-754 binary32 bit patterns, reconstructed from static analysis
of the retail executable (docs/footman-v4-model.md). `r2sw` reproduces JASS
R2SW(value, 1, decimals) as captured: R2SW_9 STATE values in JASS-0001-p001 and
MOV-0012, and R2SW_6 samples and clocks in every canonical fixture.
"""
import struct

M32 = 0xffffffff


def bits(value):
    return struct.unpack('<I', struct.pack('<f', value))[0]


def _s32(v):
    v &= M32
    return v - (1 << 32) if v & 0x80000000 else v


def _clz(v):
    v &= M32
    return 32 - v.bit_length()


def add(a, b):
    ea, eb = a & 0x7f800000, b & 0x7f800000
    if ea == 0:
        return b
    if eb == 0:
        return a
    sa = ((a & 0x7fffff) | 0x800000) << 1
    sb = ((b & 0x7fffff) | 0x800000) << 1
    if a & 0x80000000:
        sa = -sa
    if b & 0x80000000:
        sb = -sb
    diff = _s32(eb - ea)
    if diff > 0:
        if diff >= 0xb800000:
            return b
        sa >>= diff >> 23
        exponent = eb
    else:
        if diff <= _s32(0xf4800000):
            return a
        sb >>= ((ea - eb) & M32) >> 23
        exponent = ea
    total = sa + sb
    if total == 0:
        return 0
    sign = 0x80000000 if total < 0 else 0
    magnitude = abs(total) & M32
    shift = 8 - _clz(magnitude)
    magnitude = magnitude >> shift if shift >= 0 else (magnitude << -shift) & M32
    e = ((shift + 0x1ff) << 23) & M32
    return ((e + exponent) & M32 | (magnitude & 0x7fffff) | sign) & M32


def sub(a, b):
    return add(a, b ^ 0x80000000)


def mul(a, b):
    sign = (a ^ b) & 0x80000000
    ea, eb = a & 0x7f800000, b & 0x7f800000
    ma, mb = a & 0x7fffff, b & 0x7fffff
    if ma == 0 or mb == 0:
        if ea == 0 or eb == 0:
            return 0
        e = _s32(ea + eb - 0x3f800000)
        return ((e & M32) | ma | mb | sign) & M32 if e - 0x800000 >= 0 else 0
    wide_a = ((ma | 0xff800000) << 8) & M32
    wide_b = ((mb | 0xff800000) << 8) & M32
    exponent = _s32(ea - 0x3f800000 + eb)
    high = (wide_a * wide_b) >> 32
    top = high >> 31
    mantissa = ((high >> top) >> 7) & 0x7fffff
    return (((top << 23) + exponent) & M32 | mantissa | sign) & M32 if exponent - 0x800000 >= 0 else 0


def i2f(v):
    if v == 0:
        return 0
    sign = 0x80000000 if v < 0 else 0
    magnitude = abs(v)
    lz = _clz(magnitude)
    shift = lz - 8
    magnitude = (magnitude << shift) & M32 if shift >= 0 else magnitude >> -shift
    return (((31 - lz + 0x7f) << 23) | (magnitude & 0x7fffff) | sign) & M32


def f2i(a):
    e = (a >> 23) & 0xff
    if e < 0x7f:
        return 0
    mantissa = (a & 0x7fffff) | 0x800000
    shift = 0x96 - e
    v = mantissa >> shift if shift >= 0 else mantissa << -shift
    return -v if a & 0x80000000 else v


def r2sw(value_bits, decimals):
    """R2SW(value, 1, decimals): integer part, then the fraction scaled and rounded."""
    negative = _s32(value_bits) < 0 and value_bits & 0x7fffffff
    magnitude = value_bits & 0x7fffffff
    whole = f2i(magnitude)
    fraction = sub(magnitude, i2f(whole)) if whole else magnitude
    digits = f2i(add(mul(fraction, bits(10.0 ** decimals)), 0x3f000000))
    return ('-' if negative else '') + '%d.%0*d' % (whole, decimals, digits)
