#include "Cases.h"
#include "core/SoftFloat.h"
#include <iomanip>
#include <limits>
#include <locale>
#include <sstream>
#include <stdexcept>

namespace movement {
std::string case_name(int number) {
    if (number < 1 || number > 10) throw std::invalid_argument("case must be 1..10");
    std::ostringstream out;
    out << "MOV-" << std::setw(4) << std::setfill('0') << number;
    return out.str();
}
int case_callbacks(int number) {
    case_name(number);
    return number == 4 ? 600 : 250;
}
std::size_t case_units(int number) {
    case_name(number);
    return number == 2 ? 2 : 1;
}
using sf_time = wc3::sf::F;
Trace run(int case_number, wc3::ModelVersion version, std::uint32_t seed,
          bool before_due_update) {
    const int callbacks = case_callbacks(case_number); // Validates first.
    wc3::World world(version, seed);
    const auto step_us = world.parameters().step_us;
    if (sample_period_us % step_us != 0)
        throw std::invalid_argument("step_us must divide the sample period");
    const float facing = case_number == 3 ? 45.0f : case_number == 9 ? 180.0f : 0.0f;
    const auto moving = world.create_footman({0, 0}, facing);
    if (case_units(case_number) == 2) world.create_footman({0, 384}, 0);
    if (case_number == 4) world.set_move_speed(moving, 100);
    if (case_number == 5) world.set_move_speed(moving, 522);
    Trace trace;
    for (std::size_t id = 0; id < world.unit_count(); ++id)
        trace.speeds.push_back(world.unit(id).move_speed());
    std::size_t sequence = 2 + world.unit_count(); // BEGIN, WATCH units, RUN.
    // footman-v4 models the library clock: a one-shot 1000 s timer read from the
    // periodic sampler, whose scheduled time advances by add(time, period) from
    // the movement clock's start. Elapsed is timeout - (expiry - now).
    const bool timer_model = world.parameters().soft_float;
    const sf_time start = world.parameters().heading.clock_start;
    const sf_time timeout = wc3::sf::bits(1000.0f), expiry = wc3::sf::add(start, timeout);
    sf_time scheduled = start;
    const auto move = [&](int callback, wc3::Vec2 target) {
        const bool accepted = world.issue_point_order(moving, wc3::order_move, target);
        trace.actions.push_back({callback, wc3::order_move, target, accepted,
                                 sequence++, world.steps() * step_us});
    };
    for (int callback = 0; callback <= callbacks; ++callback) {
        const std::uint64_t sample_step =
            static_cast<std::uint64_t>(callback) * (sample_period_us / step_us);
        // Diagnostic before-phase omits only updates exactly at the sample time, so
        // its state lags the stamped callback time by one step (see identity).
        // The due step still runs before issuing callback actions in both phases.
        const auto steps_before_sample = sample_step -
            (before_due_update && callback > 0 ? 1 : 0);
        while (world.steps() < steps_before_sample) world.step();
        trace.tick_sequences.push_back(sequence++);
        if (timer_model) {
            if (callback > 0) scheduled = wc3::sf::add(scheduled, wc3::sf::bits(0.02f));
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
        if (callback == 0 && case_number != 1) {
            // Same literal as JASS, converted to float, not the printed reference.
            move(callback, case_number == 3 ? wc3::Vec2{707.106781f, 707.106781f}
                                           : wc3::Vec2{1000, 0});
        }
        if (callback == 50) {
            const auto p = world.unit(moving).position();
            if (case_number == 6) move(callback, {p.x, p.y + 1000});
            if (case_number == 7) move(callback, {p.x - 1000, p.y});
            if (case_number == 8) move(callback, {500, 0});
            if (case_number == 10) {
                const bool accepted = world.issue_immediate_order(moving, wc3::order_stop);
                trace.actions.push_back({callback, wc3::order_stop, {}, accepted,
                                         sequence++, world.steps() * step_us});
            }
        }
    }
    return trace;
}
std::string samples_csv(const Trace& trace) {
    std::ostringstream out;
    out.imbue(std::locale::classic());
    out << "callback,t,unit,x,y,facing,order\n";
    for (const auto& sample : trace.samples) {
        out << sample.callback << ',' << std::fixed << std::setprecision(6)
            << static_cast<double>(sample.time_us) / 1000000.0 << ",u" << sample.unit
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
            << static_cast<double>(action.callback * sample_period_us) / 1000000.0
            << ",u0," << action.order << ',' << std::defaultfloat
            << std::setprecision(std::numeric_limits<float>::max_digits10);
        if (action.order == wc3::order_move) out << action.target.x << ',' << action.target.y;
        else out << ',';
        out << ',' << (action.accepted ? 1 : 0) << '\n';
    }
    return out.str();
}
}
