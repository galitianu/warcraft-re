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
    std::size_t seq;
    std::uint64_t state_us;
};
struct Action {
    int callback;
    std::uint32_t order;
    wc3::Vec2 target;
    bool accepted;
    std::size_t seq;
    std::uint64_t state_us;
};
struct Trace {
    std::vector<Sample> samples;
    std::vector<Action> actions;
    std::vector<std::size_t> tick_sequences;
    std::vector<float> speeds;
    // footman-v4 only: the oracle library's TimerGetElapsed at each callback.
    std::vector<float> reported_time;
};
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
