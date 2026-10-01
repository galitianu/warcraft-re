#pragma once
#include <bit>
#include <cstdint>
#include <string_view>

// Software float32 arithmetic with the observable behaviour of WC3 1.29.2 (9231)
// game simulation, reconstructed from static analysis of the retail executable
// and verified bit for bit against oracle captures (docs/footman-v4-model.md).
// No game code or data is copied: every lookup table is generated here from a
// closed-form formula that reproduces the retail table exactly.
// Values are IEEE-754 binary32 bit patterns; no host floating-point arithmetic
// takes part in a result.
namespace wc3::sf {
using F = std::uint32_t;
inline F bits(float value) { return std::bit_cast<F>(value); }
inline float value(F bits) { return std::bit_cast<float>(bits); }

inline constexpr F zero = 0;
inline constexpr F one = 0x3f800000;
inline constexpr F pi = 0x40490fdb;
inline constexpr F two_pi = 0x40c90fdb;
inline constexpr F radians_per_degree = 0x3c8efa35;  // float(pi / 180)
inline constexpr F degrees_per_radian = 0x42652ee1;  // 57.29578

F add(F a, F b);  // Truncating; operand alignment rounds toward minus infinity.
F sub(F a, F b);
F mul(F a, F b);  // Truncating.
F recip(F a);     // Table interpolation, about 24 bits.
F div(F a, F b);  // a * recip(b), except a == b gives exactly 1.
F sqrt(F a);      // Integer square root; biased slightly high.
F i2f(std::int32_t v);
std::int32_t f2i(F a);  // Toward zero.
F sin(F radians);
F cos(F radians);
F acos(F x);
F log(F x);
F exp(F x);
F pow(F base, F exponent);
F fmod(F a, F b);
F atof(std::string_view text);  // The game's decimal parser, for constants.

inline F neg(F a) { return a ^ 0x80000000u; }
inline F abs(F a) { return a & 0x7fffffffu; }
// Comparisons use the host's IEEE ordering, as the retail code does (SSE comiss).
inline bool less(F a, F b) { return value(a) < value(b); }
inline bool greater(F a, F b) { return value(a) > value(b); }

// Angle helpers used by unit movement.
F wrap_angle(F radians);              // fmod into [0, 2pi), negatives +2pi.
F angle_to(F target, F current);      // target - current wrapped to [-pi, pi].
F vector_angle(F x, F y, F length);   // acos(x / length), 2pi - a when y < 0.
F length(F x, F y);                   // sqrt(x*x + y*y).
}
