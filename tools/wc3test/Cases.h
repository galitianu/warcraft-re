#pragma once
#include "core/World.h"
#include <cstdint>
#include <string>
#include <vector>

namespace movement {
struct Sample {
    int callback;
    std::uint64_t time_us;
    std::size_t unit;
    wc3::Vec2 position;
    float facing;
    std::uint32_t order;
};
struct Action {
    int callback;
    std::uint32_t order;
    wc3::Vec2 target;
    bool accepted;
};
struct Trace { std::vector<Sample> samples; std::vector<Action> actions; };
// Callbacks are requested at multiples of this, matching the JASS timer period.
inline constexpr std::uint64_t sample_period_us = 20000;
int case_callbacks(int number);
std::size_t case_units(int number);
Trace run(int case_number, wc3::ModelVersion version, std::uint32_t seed = 1,
          bool before_due_update = false);
std::string samples_csv(const Trace& trace);
std::string actions_csv(const Trace& trace);
std::string case_name(int number);
}
