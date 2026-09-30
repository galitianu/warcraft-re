#include "core/World.h"
#include <algorithm>
#include <cmath>
#include <limits>
#include <numbers>

namespace wc3 {
namespace {
constexpr float degrees_per_radian = 180.0f / std::numbers::pi_v<float>;
float wrap(float angle) {
    angle = std::fmod(angle, 360.0f);
    if (angle < 0.0f) angle += 360.0f;
    // Adding 360 to a tiny negative float can round to exactly 360.
    return angle >= 360.0f ? 0.0f : angle;
}
// [-180, 180). Float headings of exactly opposite directions land a few ULPs
// either side of 180, so resolve that neighborhood explicitly as clockwise.
float angle_delta(float target, float current, float tie_degrees) {
    const float delta = wrap(target - current + 180.0f) - 180.0f;
    return 180.0f - std::abs(delta) <= tie_degrees ? -180.0f : delta;
}
float heading(Vec2 delta) {
    return wrap(std::atan2(delta.y, delta.x) * degrees_per_radian);
}
}

Model model(ModelVersion version) {
    constexpr float unlimited = std::numeric_limits<float>::infinity();
    if (version == ModelVersion::v1) {
        return {.name = "footman-v1", .position_period_steps = 1, .facing_period_steps = 1,
                .facing_phase_steps = 1, .move_delay_steps = 0,
                .movement_angle_limit = 180.0f,
                .turn_ramp_radians = {unlimited, unlimited, unlimited}};
    }
    return {.name = "footman-v2", .position_period_steps = 5, .facing_period_steps = 30,
            .facing_phase_steps = 10, .move_delay_steps = 10};
}
World::World(ModelVersion version, std::uint32_t seed)
    : model_(model(version)), random_(seed) {}

std::size_t World::create_footman(Vec2 position, float facing) {
    Unit unit;
    unit.position_ = position;
    unit.facing_ = wrap(facing);
    unit.speed_ = model_.default_speed;
    units_.push_back(unit);
    return units_.size() - 1;
}
void World::set_move_speed(std::size_t id, float requested) {
    units_.at(id).speed_ = std::clamp(requested, model_.min_speed, model_.max_speed);
}
bool World::issue_point_order(std::size_t id, std::uint32_t order, Vec2 target) {
    auto& unit = units_.at(id);
    if (order != order_move) return false;
    unit.order_ = order_move;
    unit.target_ = target;
    unit.command_step_ = steps_;
    unit.turn_updates_ = 0;
    return true;
}
bool World::issue_immediate_order(std::size_t id, std::uint32_t order) {
    auto& unit = units_.at(id);
    if (order != order_stop) return false;
    unit.order_ = order_none;
    return true;
}
void World::step() {
    ++steps_;
    const bool position_due = steps_ % model_.position_period_steps == 0;
    const bool facing_due = steps_ >= model_.facing_phase_steps &&
        (steps_ - model_.facing_phase_steps) % model_.facing_period_steps == 0;
    const float tie = model_.opposite_tie_degrees;
    for (auto& unit : units_) {
        if (unit.order_ != order_move) continue;
        const Vec2 delta{unit.target_.x - unit.position_.x,
                         unit.target_.y - unit.position_.y};
        const float distance = std::hypot(delta.x, delta.y);
        if (position_due && distance <= model_.stop_radius) {
            unit.order_ = order_none;
            continue;
        }
        const float direction = heading(delta);
        if (facing_due) {
            const float limit = model_.turn_ramp_radians[
                std::min(unit.turn_updates_, 2u)] * degrees_per_radian;
            const float change = angle_delta(direction, unit.facing_, tie);
            unit.facing_ = wrap(unit.facing_ + std::clamp(change, -limit, limit));
            ++unit.turn_updates_;
        }
        if (!position_due || steps_ - unit.command_step_ <= model_.move_delay_steps)
            continue;
        if (std::abs(angle_delta(direction, unit.facing_, tie)) > model_.movement_angle_limit)
            continue;
        const float dt = static_cast<float>(model_.step_us * model_.position_period_steps)
            / 1000000.0f;
        const float travel = std::min(unit.speed_ * dt, distance);
        unit.position_.x += delta.x / distance * travel;
        unit.position_.y += delta.y / distance * travel;
    }
}
}
