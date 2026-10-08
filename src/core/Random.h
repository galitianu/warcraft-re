#pragma once
#include <cstdint>
#include <random>
#include <sstream>
#include <string>

namespace wc3 {
// An implementation stream, not a hypothesis about WC3's random algorithm.
class Random {
public:
    explicit Random(std::uint32_t seed) : seed_(seed), engine_(seed) {}
    std::uint32_t seed() const { return seed_; }
    std::uint32_t next() { return static_cast<std::uint32_t>(engine_()); }
    // The complete engine state as decimal text, for exact state comparisons.
    std::string state() const {
        std::ostringstream out;
        out << engine_;
        return out.str();
    }
private:
    std::uint32_t seed_;
    std::mt19937 engine_;
};
}
