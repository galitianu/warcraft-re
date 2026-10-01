#pragma once
// Scenario v1 (docs/scenario-v1.md): an engine-independent description of one
// movement experiment, read from a strict YAML subset. Parsing knows nothing about
// the World, the canonical trace contract or any reference; Cases.cpp maps it onto
// the World API and rejects what the current runner cannot represent.
#include "core/World.h"
#include <cstdint>
#include <optional>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

namespace scenario {
// Every invalid description throws this; wc3test exits 2 without writing traces.
struct Error : std::runtime_error {
    using std::runtime_error::runtime_error;
};
struct Unit {
    std::string name;
    std::string type;                // WC3 unit rawcode; v1 supports hfoo only
    wc3::Vec2 position;              // float32 of the declared decimal
    float facing = 0;                // degrees in [0, 360)
    std::optional<float> move_speed; // requested SetUnitMoveSpeed value, never pre-clamped
};
enum class Order { move, stop };
struct Action {
    std::uint64_t at_us = 0;  // requested time; a whole number of observation periods
    std::size_t unit = 0;     // index into Scenario::units
    Order order = Order::move;
    bool relative = false;    // move: offset from the unit's position at execution
    wc3::Vec2 point;          // move target, or offset when relative
    int line = 0;
};
struct Scenario {
    std::string experiment;
    std::string map_revision;
    std::vector<Unit> units;     // creation order = watch order
    std::uint64_t period_us = 0; // requested sampler period
    int callbacks = 0;           // periodic callbacks after callback 0
    std::vector<Action> actions; // file order; equal times execute in this order
};
Scenario parse(std::string_view text);
// Exact decimal to nearest float32 (ties to even), as a C++ float literal would.
float decimal_to_float(std::string_view text);
std::string sha256_hex(std::string_view bytes);
}
