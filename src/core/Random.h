#pragma once
#include <cstdint>
#include <random>
#include <string>

namespace wc3 {
// An implementation stream, not a hypothesis about WC3's random algorithm.
class Random {
public:
    explicit Random(std::uint32_t seed) : seed_(seed), engine_(seed) {}
    std::uint32_t seed() const { return seed_; }
    std::uint32_t next() {
        ++draws_;
        return static_cast<std::uint32_t>(engine_());
    }
    // Seed and draw count uniquely determine this implementation stream's full
    // state. Do not use operator<< on the engine: libc++ and libstdc++ encode
    // the same mt19937 state differently. This is not a WC3 RNG hypothesis.
    std::string state() const {
        return "mt19937 seed=" + std::to_string(seed_) + " draws=" + std::to_string(draws_);
    }
private:
    std::uint32_t seed_;
    std::mt19937 engine_;
    std::uint64_t draws_ = 0;
};
}
