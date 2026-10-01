#include "core/SoftFloat.h"
#include <array>
#include <cmath>
#include <numbers>

namespace wc3::sf {
namespace {
std::int32_t s32(std::uint32_t v) { return static_cast<std::int32_t>(v); }
int clz(std::uint32_t v) { return v ? std::countl_zero(v) : 32; }
std::uint32_t high32(std::uint32_t a, std::uint32_t b) {
    return static_cast<std::uint32_t>((static_cast<std::uint64_t>(a) * b) >> 32);
}

// Tables. Each formula reproduces every entry of the corresponding retail table;
// the closest any value comes to a rounding boundary is noted, so double-precision
// libm results are exact here.
struct Tables {
    // Reciprocal mantissas: floor(2^23 (2/(1+x) - 1) + 2/(1+x)^2), x = i/1024
    // (margin 0.0004).
    std::array<std::uint32_t, 1026> recip{};
    // floor(sin(i pi / 2048) 2^31); the quarter-turn entry saturates (margin 0.0012).
    std::array<std::uint32_t, 1026> sin{};
    // floor(acos(i / 1024) 2^29) (margin 0.001); entry 1024 is 2^20 in retail.
    std::array<std::uint32_t, 1026> acos{};
    // Near 1: float32(acos(1 - d 2^-24)) 2^34 for the d each index represents
    // (margin 4e-6 float32 ulp).
    std::array<std::uint32_t, 138> acos_near_one{};
    Tables() {
        for (int i = 0; i <= 1024; ++i) {
            const double x = i / 1024.0;
            recip[i] = i == 0 ? 0x800000u : static_cast<std::uint32_t>(
                std::floor((2.0 / (1.0 + x) - 1.0) * 8388608.0 + 2.0 / ((1.0 + x) * (1.0 + x))));
            sin[i] = i == 1024 ? 0x7fffffffu : static_cast<std::uint32_t>(
                std::floor(std::sin(i * std::numbers::pi / 2048.0) * 2147483648.0));
            acos[i] = i == 1024 ? 0x100000u : static_cast<std::uint32_t>(
                std::floor(std::acos(x) * 536870912.0));
        }
        for (int i = 0; i < 138; ++i) {
            double d;
            if (i >= 136) d = 0;
            else if (i >= 128) d = 1;
            else if (i >= 124) d = 2;
            else if (i >= 120) d = 4;
            else d = std::ldexp(16 - i % 8, 13 - i / 8);
            const float a = static_cast<float>(std::acos(1.0 - std::ldexp(d, -24)));
            acos_near_one[i] = i == 0 ? 0x7fffffffu
                : static_cast<std::uint32_t>(static_cast<double>(a) * 17179869184.0);
        }
    }
};
const Tables& tables() {
    static const Tables t;
    return t;
}

F normalize_sum(std::int64_t total, std::uint32_t exponent) {
    if (total == 0) return 0;
    const std::uint32_t sign = total < 0 ? 0x80000000u : 0;
    std::uint32_t magnitude = static_cast<std::uint32_t>(total < 0 ? -total : total);
    const int shift = 8 - clz(magnitude);
    magnitude = shift >= 0 ? magnitude >> shift : magnitude << -shift;
    const std::uint32_t e = static_cast<std::uint32_t>(shift + 0x1ff) << 23;
    return (e + exponent) | (magnitude & 0x7fffff) | sign;
}
// Integer part toward zero, by masking fraction bits.
F truncate(F a) {
    const int e = static_cast<int>((a >> 23) & 0xff) - 127;
    if (e < 0) return 0;
    if (e >= 23) return a;
    return a & static_cast<std::uint32_t>(s32(0x80000000u) >> (e + 8));
}
bool is_integer(F a) { return truncate(a) == a; }
F ipow(F base, std::uint32_t n) {
    F result = one;
    while (n) {
        if (n & 1) result = mul(result, base);
        base = mul(base, base);
        n >>= 1;
    }
    return result;
}
F trig(F radians, int quadrant_offset) {
    const F turns = mul(radians, 0x4822f983);  // 2^20 / 2pi
    std::int32_t v = 0;
    const int e = static_cast<int>((turns >> 23) & 0xff);
    if (e >= 0x7f) {
        const std::uint32_t m = (turns & 0x7fffff) | 0x800000;
        const int shift = 0x96 - e;
        const std::uint32_t magnitude = shift >= 0 ? m >> shift : m << -shift;
        v = s32(turns & 0x80000000u ? 0u - magnitude : magnitude);
    }
    const std::uint32_t b = static_cast<std::uint32_t>(v) & 0xff;
    std::uint32_t w = b | (b << 8);
    w |= w << 16;
    const int index = (v >> 8) & 0x3ff;
    const int quadrant = ((v >> 18) + quadrant_offset) & 3;
    const auto& t = tables().sin;
    std::uint32_t r;
    if (quadrant & 1) {
        const std::uint32_t hi = t[1024 - index], lo = t[1023 - index];
        r = hi - high32(w, hi - lo);
    } else {
        r = t[index] + high32(w, t[index + 1] - t[index]);
    }
    if (quadrant & 2) r = 0u - r;
    F f = i2f(s32(r));
    if (f & 0x7f800000) f -= 0xf800000;  // / 2^31
    return f;
}
F exp_nonnegative(F x) {
    if (x & 0x7f800000) x += 0x1000000;  // * 4
    const F whole = truncate(x);
    const F fraction = sub(x, whole);
    F quarter = fraction - 0x1000000;      // / 4, flushed if it underflows
    if (s32((fraction - 0x1800000) ^ fraction) < 0) quarter = 0;
    F p = mul(0x3c1a534c, quarter);
    p = mul(add(p, 0x3d296ec9), quarter);
    p = mul(add(p, 0x3e2ab479), quarter);
    p = mul(add(p, 0x3effffbd), quarter);
    p = mul(add(p, one), quarter);
    p = add(p, one);
    return mul(p, ipow(0x3fa45af2, static_cast<std::uint32_t>(f2i(whole))));  // e^(1/4)
}
F log_mantissa(F m) {  // ln(m) for m in [1, 2), rational approximation
    const F a = add(m, one), b = add(m, 0xbf800000);
    const F q = b == a ? one : mul(b, recip(a));
    const F q2 = mul(q, q);
    F s = mul(q, add(one, mul(0xbe88d424, q2)));
    if (s & 0x7f800000) s += 0x800000;
    const F u = add(one, mul(0xbf19bf59, q2));
    return s == u ? one : mul(s, recip(u));
}
}

F add(F a, F b) {
    const std::uint32_t ea = a & 0x7f800000, eb = b & 0x7f800000;
    if (ea == 0) return b;
    if (eb == 0) return a;
    std::int64_t sa = static_cast<std::int64_t>(((a & 0x7fffff) | 0x800000) << 1);
    std::int64_t sb = static_cast<std::int64_t>(((b & 0x7fffff) | 0x800000) << 1);
    if (a & 0x80000000u) sa = -sa;
    if (b & 0x80000000u) sb = -sb;
    const std::int32_t difference = s32(eb - ea);
    std::uint32_t exponent;
    if (difference > 0) {
        if (difference >= 0xb800000) return b;
        sa >>= difference >> 23;
        exponent = eb;
    } else {
        if (difference <= s32(0xf4800000u)) return a;
        sb >>= (ea - eb) >> 23;
        exponent = ea;
    }
    return normalize_sum(sa + sb, exponent);
}
F sub(F a, F b) { return add(a, neg(b)); }
F mul(F a, F b) {
    const std::uint32_t sign = (a ^ b) & 0x80000000u;
    const std::uint32_t ea = a & 0x7f800000, eb = b & 0x7f800000;
    const std::uint32_t ma = a & 0x7fffff, mb = b & 0x7fffff;
    if (ma == 0 || mb == 0) {  // a power of two scales the exponent only
        if (ea == 0 || eb == 0) return 0;
        const std::int32_t e = s32(ea + eb - 0x3f800000u);
        const F r = static_cast<std::uint32_t>(e) | ma | mb | sign;
        return e - 0x800000 >= 0 ? r : 0;
    }
    const std::uint32_t hi = high32((ma | 0xff800000u) << 8, (mb | 0xff800000u) << 8);
    const std::uint32_t top = hi >> 31;
    const std::int32_t e = s32(ea - 0x3f800000u + eb);
    const F r = ((top << 23) + static_cast<std::uint32_t>(e)) | (((hi >> top) >> 7) & 0x7fffff) | sign;
    return e - 0x800000 >= 0 ? r : 0;
}
F recip(F a) {
    const auto& t = tables().recip;
    const std::uint32_t m = a & 0x7fffff, index = m >> 13, c = m << 19;
    std::uint32_t w = (c >> 13) | c;
    w = (w >> 13) | c;
    const std::uint32_t e = t[index] - high32(w, t[index] - t[index + 1])
        - (a & 0x7f800000) + 0x7e800000;
    return s32(e - 0x800000) >= 0 ? e | (a & 0x80000000u) : 0;
}
F div(F a, F b) { return a == b ? one : mul(a, recip(b)); }
F sqrt(F a) {
    if (s32(a) <= 0) return 0;
    const int e = static_cast<int>((a >> 23) & 0xff) - 127;
    const std::uint32_t m = a & 0x7fffff;
    std::uint32_t x = ((m | 0xff800000u) << 8) | (m >> 15), root = 0, remainder = 0;
    for (int i = 0; i < 16; ++i) {
        remainder = (remainder << 2) | (x >> 30);
        x <<= 2;
        root <<= 1;
        if (root < remainder) { remainder -= root + 1; root += 2; }
    }
    root >>= 1;
    const F mantissa = (((root - 0xb504) * 0xb505u) >> 8) | 0x3f800000;
    const int odd = e & 1;
    const int half = (e - odd) / 2;  // toward zero, as retail
    const F scale = (static_cast<std::uint32_t>(half + 0x7f) << 23) | (odd ? 0x3504f3u : 0u);
    return mul(scale, mantissa);
}
F i2f(std::int32_t v) {
    if (v == 0) return 0;
    const std::uint32_t sign = v < 0 ? 0x80000000u : 0;
    std::uint32_t magnitude = v < 0 ? 0u - static_cast<std::uint32_t>(v) : static_cast<std::uint32_t>(v);
    const int leading = clz(magnitude), shift = leading - 8;
    magnitude = shift >= 0 ? magnitude << shift : magnitude >> -shift;
    return (static_cast<std::uint32_t>(31 - leading + 0x7f) << 23) | (magnitude & 0x7fffff) | sign;
}
std::int32_t f2i(F a) {
    const int e = static_cast<int>((a >> 23) & 0xff);
    if (e < 0x7f) return 0;
    const std::uint32_t m = (a & 0x7fffff) | 0x800000;
    const int shift = 0x96 - e;
    const std::uint32_t magnitude = shift >= 0 ? m >> shift : m << -shift;
    return s32(a & 0x80000000u ? 0u - magnitude : magnitude);
}
F sin(F radians) { return trig(radians, 0); }
F cos(F radians) { return trig(radians, 1); }
F acos(F a) {
    const auto& t = tables();
    std::uint32_t x = a & 0x7fffffff;
    if (x <= 0x3f7e8000) {
        const F scaled = a + 0xf000000;  // * 2^30
        std::int32_t c = f2i(scaled);
        if (static_cast<std::uint32_t>(c + 0x3fffffff) > 0x7ffffffe) c = c > 0 ? 0x3fffffff : -0x3fffffff;
        const std::uint32_t shifted = static_cast<std::uint32_t>(c) << 12;
        const std::uint32_t w = shifted | (shifted >> 20);
        const int index = (c >> 20) & 0x3ff;
        std::uint32_t r;
        if (c >= 0) {
            const std::uint32_t hi = t.acos[index];
            r = hi - high32(w, hi - t.acos[index + 1]);
        } else {
            const std::uint32_t hi = t.acos[1024 - index], lo = t.acos[1023 - index];
            r = (0x6487ed51u - hi) - high32(w, lo - hi);  // pi 2^29 - acos(|x|)
        }
        F f = i2f(s32(r));
        if (f & 0x7f800000) f -= 0xe800000;  // / 2^29
        return f;
    }
    if (x > one) x = one;
    const std::uint32_t d = one - x;
    const int leading = clz(d);
    const std::uint32_t rest = leading < 32 ? ~d << leading : 0;
    const std::uint32_t index = ((static_cast<std::uint32_t>(leading) * 8 - 0x78) | (rest >> 28));
    const std::uint32_t w = rest << 4;
    const std::uint32_t v = t.acos_near_one[index];
    F f = i2f(s32(v - high32(w, v - t.acos_near_one[index + 1])));
    if (f & 0x7f800000) f -= 0x11000000;  // / 2^34
    return a & 0x80000000u ? sub(pi, f) : f;
}
F log(F x) {
    const int e = static_cast<int>((x >> 23) & 0xff) - 127;
    const F r = log_mantissa((x & 0x7fffff) | 0x3f800000);
    const F whole = e ? i2f(e) : 0;
    return mul(0x3f317218, add(whole, mul(r, 0x3fb8aa3b)));  // ln2 (e + ln(m) log2(e))
}
F exp(F x) {
    if (s32(x) < 0 && (x & 0x7fffffff)) return recip(exp_nonnegative(neg(x)));
    return exp_nonnegative(x);
}
F pow(F base, F exponent) {
    if (is_integer(exponent) && !(s32(exponent) < 0 && (exponent & 0x7fffffff)))
        return ipow(base, static_cast<std::uint32_t>(f2i(exponent)));
    if (!(base & 0x7f800000)) return 0;
    return exp(mul(log(base), exponent));
}
F fmod(F a, F b) {
    const F y = b & 0x7fffffff;
    const F q = mul(a, recip(y));
    const int e = static_cast<int>((q >> 23) & 0xff) - 127;
    const F fraction = e < 0 ? q : e < 23 ? sub(q, truncate(q)) : 0;
    F r = mul(fraction, y);
    if (s32(r) > 0) return value(r) >= value(y) ? sub(r, y) : r;
    return value(neg(y)) >= value(r) ? add(r, y) : r;
}
F atof(std::string_view text) {
    int sign = 1;
    std::size_t i = 0;
    if (!text.empty() && (text[0] == '-' || text[0] == '+')) { sign = text[0] == '-' ? -1 : 1; ++i; }
    std::int32_t digits = 0;
    int significant = 0, scale = 0, after_point = 0;
    bool started = false;
    for (; i < text.size(); ++i) {
        const char c = text[i];
        if (c == ' ' || c == ';' || c == '\t') break;
        if (c >= '0' && c <= '9') {
            started = started || c != '0';
            if (started) ++significant;
            if (significant <= 9) { scale += after_point; digits = digits * 10 + (c - '0'); }
            else { if (significant == 10) --after_point; scale += after_point; }
        } else if (c == '.' && !after_point) after_point = 1;
        else break;
    }
    const F n = digits ? i2f(sign * digits) : 0;
    if (scale >= 0) {
        const F p = ipow(0x41200000, static_cast<std::uint32_t>(scale));
        return p == n ? one : mul(n, recip(p));
    }
    return mul(n, ipow(0x41200000, static_cast<std::uint32_t>(-scale)));
}

F wrap_angle(F a) {
    if (value(abs(a)) >= value(two_pi)) a = fmod(a, two_pi);
    return less(a, zero) ? add(a, two_pi) : a;
}
F angle_to(F target, F current) {
    const F d = sub(current, target);
    if (less(d, zero)) return greater(neg(d), pi) ? sub(neg(two_pi), d) : neg(d);
    return greater(d, pi) ? sub(two_pi, d) : neg(d);
}
F vector_angle(F x, F y, F length) {
    constexpr F epsilon = 0x3727c5ac;  // 1e-5
    if (abs(length) <= epsilon) return 0;
    const F a = acos(div(x, length));
    if (abs(a) <= epsilon) return 0;
    return less(y, zero) ? sub(two_pi, a) : a;
}
F length(F x, F y) { return sqrt(add(mul(x, x), mul(y, y))); }
}
