#pragma once
#include "Scenario.h"
#include "core/World.h"
#include <cstdint>
#include <optional>
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
    std::size_t unit = 0;
};
// v2 STATE event (docs/scenario-v2.md): the aux clock and the unit's state after
// the callback's actions.
struct StateEvent {
    int callback;
    float clock;
    wc3::Vec2 position;
    float facing;
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
    std::vector<std::string> names;  // watch order
    std::uint64_t period_us = 0;
    // v2 only.
    int version = 1;
    std::uint64_t start_us = 0;
    std::optional<int> state_clock;
    std::vector<StateEvent> events;
};
// Callbacks are requested at multiples of this, matching the JASS timer period.
inline constexpr std::uint64_t sample_period_us = 20000;
// The canonical v1 contract's record limit; longer schedules are rejected.
inline constexpr std::size_t max_records = 50000;
struct CaseIdentity {
    std::string experiment;
    std::string map_revision;
    int callbacks;
};
// Runs a validated scenario description (docs/scenario-v1.md) on the World API.
// Throws std::invalid_argument for schedules this runner cannot represent.
// `pathing`, if given, replaces the model's unit pathing (predictions only; traces
// still name the version, so canonical runs never pass it).
Trace run(const scenario::Scenario& description, wc3::ModelVersion version, std::uint32_t seed = 1,
          bool before_due_update = false, const wc3::UnitPathing* pathing = nullptr);
std::string samples_csv(const Trace& trace);
std::string actions_csv(const Trace& trace);
}
