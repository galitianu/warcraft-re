#include "Cases.h"
#include "core/SoftFloat.h"
#include <algorithm>
#include <cmath>
#include <iterator>
#include <iomanip>
#include <limits>
#include <locale>
#include <sstream>
#include <stdexcept>

namespace movement {
using sf_time = wc3::sf::F;
namespace {
// Relative targets are evaluated from this world's state at execution, never from a
// reference. A zero component copies the coordinate, as JASS GetUnitX(u) without an
// addition; others add in float32.
bool execute(wc3::World& world, const scenario::Scenario& s, const scenario::Action& action,
             std::uint32_t& order, wc3::Vec2& target) {
    order = wc3::order_stop;
    target = {};
    if (action.order == scenario::Order::stop) return world.issue_immediate_order(action.unit, order);
    order = wc3::order_move;
    target = action.point;
    if (action.relative) {
        const auto p = world.unit(action.unit).position();
        target = {action.point.x == 0 ? p.x : p.x + action.point.x,
                  action.point.y == 0 ? p.y : p.y + action.point.y};
        if (!(std::abs(target.x) <= 4096 && std::abs(target.y) <= 4096))
            throw std::invalid_argument(s.experiment + ": action at line " +
                std::to_string(action.line) + " targets outside the 64x64 map");
    }
    return world.issue_point_order(action.unit, order, target);
}
// A positive float32 time as an exact count of 2^-24 s (times in [2^-24, 2^39) s).
std::int64_t time_units(wc3::sf::F time) {
    const int shift = static_cast<int>((time >> 23) & 255) - 126;
    const std::int64_t mantissa = (time & 0x7fffff) | 0x800000;
    if (shift < 0 && (mantissa & ((std::int64_t{1} << -shift) - 1)))
        throw std::logic_error("time below 2^-24 s");
    return shift >= 0 ? mantissa << shift : mantissa >> -shift;
}
// The largest float32 not above units * 2^-24 s (units > 0, at least 2^23).
wc3::sf::F floor_time(std::int64_t units) {
    int top = 63;
    while (!(units >> top)) --top;
    if (top < 23) throw std::logic_error("time below 0.5 s");
    const auto mantissa = static_cast<wc3::sf::F>(units >> (top - 23));
    return (static_cast<wc3::sf::F>(top + 103) << 23) | (mantissa & 0x7fffff);
}
// Scenario v2 (docs/scenario-v2.md, docs/mov-0013.md), footman-v4 only. Units are
// created at the setup, frame 0 of the movement clock (0.5 s). The sampler is
// scheduled at s(0) = add(0.5, start) and s(k) = add(s(k-1), period), and a callback
// observes every frame whose clock c(n) <= s(k): the rule (H0) that every retained
// 1/10/20/25/50 ms schedule follows apart from its listed exceptions. MOV-0013's and
// MOV-0014's observed frame exceptions are reported by the comparison, not modelled.
// The library clock is MOV-0014's pre-registered Q17 (docs/mov-0014.md): the 1000 s
// timer reads as if started at s(0) rounded down to 2^-17 s, and its exact remaining
// time is rounded down to float32. At the 0.5 s bootstrap this equals every retained
// clock reading; with a delayed start it predicted every MOV-0013/0014 TICK.
Trace run_scheduled(const scenario::Scenario& s, wc3::ModelVersion version, std::uint32_t seed,
                    bool before_due_update) {
    using namespace wc3::sf;
    if (version != wc3::ModelVersion::v4 || before_due_update)
        throw std::invalid_argument(s.experiment + ": scenario v2 timing is defined for --model v4 --phase after only");
    constexpr std::uint64_t captured[] = {1000, 10000, 20000, 25000, 50000};
    if (std::find(std::begin(captured), std::end(captured), s.period_us) == std::end(captured))
        throw std::invalid_argument(s.experiment + ": v2 runs only the captured 0.001/0.01/0.02/0.025/0.05 s periods");
    const std::size_t units = s.units.size(), callbacks = static_cast<std::size_t>(s.callbacks);
    if (3 + units + (callbacks + 1) * (1 + units + (s.state_clock ? 1 : 0)) + s.actions.size() > max_records)
        throw std::invalid_argument(s.experiment + ": more than 50000 trace records");
    wc3::World world(version, seed);
    const auto frame_steps = world.parameters().heading.exposure_period_steps;
    const auto step_us = world.parameters().step_us;
    Trace trace;
    trace.period_us = s.period_us;
    trace.version = 2;
    trace.start_us = s.start_us;
    trace.state_clock = s.state_clock;
    for (const auto& unit : s.units) {
        const auto id = world.create_footman(unit.position, unit.facing);
        if (unit.move_speed) world.set_move_speed(id, *unit.move_speed);
        trace.names.push_back(unit.name);
    }
    for (std::size_t id = 0; id < world.unit_count(); ++id)
        trace.speeds.push_back(world.unit(id).move_speed());
    std::size_t sequence = 2 + world.unit_count(); // BEGIN, WATCH units, RUN.
    const F setup = world.parameters().heading.clock_start;
    // JASS reals are the scenario's decimal tokens converted to float32.
    const F start = s.start_us ? add(setup, bits(scenario::decimal_to_float(s.start_text))) : setup;
    const F period = bits(scenario::decimal_to_float(s.period_text));
    const F timeout = bits(1000.0f);
    const std::int64_t timer_start = time_units(start) & ~std::int64_t{127};  // 2^-17 s grid
    const std::int64_t remaining_base = time_units(timeout) + timer_start;
    const F aux = s.state_clock ? bits(static_cast<float>(*s.state_clock)) : 0;
    F scheduled = start;
    std::size_t next = 0;
    for (int callback = 0; callback <= s.callbacks; ++callback) {
        if (callback > 0) scheduled = add(scheduled, period);
        // A frame due at the same float32 time runs first (20 ms evidence).
        while (!greater(world.frame_clock(world.steps() / frame_steps + 1), scheduled))
            for (std::uint32_t i = 0; i < frame_steps; ++i) world.step();
        const std::uint64_t state_us = world.steps() * step_us;
        trace.tick_sequences.push_back(sequence++);
        trace.reported_time.push_back(value(sub(timeout, floor_time(remaining_base - time_units(scheduled)))));
        const auto requested = static_cast<std::uint64_t>(callback) * s.period_us;
        for (std::size_t id = 0; id < world.unit_count(); ++id) {
            const auto& unit = world.unit(id);
            trace.samples.push_back({callback, requested, id, unit.position(), unit.facing(),
                                     unit.current_order(), sequence++, state_us});
        }
        for (; next < s.actions.size() && s.actions[next].at_us == requested; ++next) {
            std::uint32_t order;
            wc3::Vec2 target;
            const bool accepted = execute(world, s, s.actions[next], order, target);
            trace.actions.push_back({callback, order, target, accepted, sequence++, state_us, s.actions[next].unit});
        }
        if (s.state_clock) {
            // The aux clock started at setup: sub(D, sub(add(setup, D), now)).
            const auto& unit = world.unit(0);
            trace.events.push_back({callback, value(sub(aux, sub(add(setup, aux), scheduled))),
                                    unit.position(), unit.facing(), sequence++, state_us});
        }
    }
    if (next != s.actions.size()) throw std::logic_error("unscheduled scenario action");
    return trace;
}
}
// One scenario's schedule (docs/scenario-v1.md). Each callback samples after
// the due update, then runs that callback's actions in file order. Until Phase 5
// a hard-coded MOV-0001..0010 table ran the same loop; the committed scenarios
// reproduced it byte for byte (docs/phase-5-scenarios.md) before it was removed.
Trace run(const scenario::Scenario& description, wc3::ModelVersion version, std::uint32_t seed,
          bool before_due_update) {
    if (description.version == 2) return run_scheduled(description, version, seed, before_due_update);
    const auto& s = description;
    wc3::World world(version, seed);
    const auto step_us = world.parameters().step_us;
    // Runner capability, separate from scenario validity: the C++ canonical timing
    // and footman-v4's library clock are defined for the demonstrated period only.
    if (s.period_us != sample_period_us)
        throw std::invalid_argument(s.experiment + ": this runner supports only the 0.020000 s period");
    if (sample_period_us % step_us != 0)
        throw std::invalid_argument("step_us must divide the sample period");
    const std::size_t units = s.units.size(), callbacks = static_cast<std::size_t>(s.callbacks);
    if (3 + units + (callbacks + 1) * (1 + units) + s.actions.size() > max_records)
        throw std::invalid_argument(s.experiment + ": more than 50000 trace records");
    Trace trace;
    trace.period_us = s.period_us;
    for (const auto& unit : s.units) {
        const auto id = world.create_footman(unit.position, unit.facing);
        if (unit.move_speed) world.set_move_speed(id, *unit.move_speed);
        trace.names.push_back(unit.name);
    }
    for (std::size_t id = 0; id < world.unit_count(); ++id)
        trace.speeds.push_back(world.unit(id).move_speed());
    std::size_t sequence = 2 + world.unit_count(); // BEGIN, WATCH units, RUN.
    // footman-v4 models the library clock: a one-shot 1000 s timer read from the
    // periodic sampler, whose scheduled time advances by add(time, period) from
    // the movement clock's start. Elapsed is timeout - (expiry - now).
    const bool timer_model = world.parameters().soft_float;
    const sf_time start = world.parameters().heading.clock_start;
    const sf_time timeout = wc3::sf::bits(1000.0f), expiry = wc3::sf::add(start, timeout);
    const sf_time period = wc3::sf::bits(0.02f);
    sf_time scheduled = start;
    std::size_t next = 0;
    for (int callback = 0; callback <= s.callbacks; ++callback) {
        const std::uint64_t sample_step =
            static_cast<std::uint64_t>(callback) * (s.period_us / step_us);
        // Diagnostic before-phase omits only updates exactly at the sample time, so
        // its state lags the stamped callback time by one step (see identity).
        // The due step still runs before issuing callback actions in both phases.
        const auto steps_before_sample = sample_step -
            (before_due_update && callback > 0 ? 1 : 0);
        while (world.steps() < steps_before_sample) world.step();
        trace.tick_sequences.push_back(sequence++);
        if (timer_model) {
            if (callback > 0) scheduled = wc3::sf::add(scheduled, period);
            trace.reported_time.push_back(wc3::sf::value(
                wc3::sf::sub(timeout, wc3::sf::sub(expiry, scheduled))));
        }
        for (std::size_t id = 0; id < world.unit_count(); ++id) {
            const auto& unit = world.unit(id);
            trace.samples.push_back({callback, sample_step * step_us,
                id, unit.position(), unit.facing(), unit.current_order(),
                sequence++, world.steps() * step_us});
        }
        while (world.steps() < sample_step) world.step();
        // Actions run after this callback's samples, in file order at equal times.
        const auto now_us = static_cast<std::uint64_t>(callback) * s.period_us;
        for (; next < s.actions.size() && s.actions[next].at_us == now_us; ++next) {
            const auto& action = s.actions[next];
            std::uint32_t order;
            wc3::Vec2 target;
            const bool accepted = execute(world, s, action, order, target);
            trace.actions.push_back({callback, order, target, accepted,
                                     sequence++, world.steps() * step_us, action.unit});
        }
    }
    if (next != s.actions.size()) throw std::logic_error("unscheduled scenario action");
    return trace;
}
std::string samples_csv(const Trace& trace) {
    std::ostringstream out;
    out.imbue(std::locale::classic());
    out << "callback,t,unit,x,y,facing,order\n";
    for (const auto& sample : trace.samples) {
        out << sample.callback << ',' << std::fixed << std::setprecision(6)
            << static_cast<double>(sample.time_us) / 1000000.0 << ',' << trace.names.at(sample.unit)
            << std::defaultfloat << std::setprecision(std::numeric_limits<float>::max_digits10)
            << ',' << sample.position.x << ',' << sample.position.y << ',' << sample.facing
            << ',' << sample.order << '\n';
    }
    return out.str();
}
std::string actions_csv(const Trace& trace) {
    std::ostringstream out;
    out.imbue(std::locale::classic());
    out << "callback,t,unit,order,target_x,target_y,accepted\n";
    for (const auto& action : trace.actions) {
        out << action.callback << ',' << std::fixed << std::setprecision(6)
            << static_cast<double>(action.callback * trace.period_us) / 1000000.0
            << ',' << trace.names.at(action.unit) << ',' << action.order << ',' << std::defaultfloat
            << std::setprecision(std::numeric_limits<float>::max_digits10);
        if (action.order == wc3::order_move) out << action.target.x << ',' << action.target.y;
        else out << ',';
        out << ',' << (action.accepted ? 1 : 0) << '\n';
    }
    return out.str();
}
}
