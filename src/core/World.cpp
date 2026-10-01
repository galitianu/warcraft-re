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

// footman-v3 arithmetic. WC3 readings fit float32 results rounded toward zero:
// coordinate grids and 180 -> 179.999985 / 45 -> 44.999996 facing round trips.
// Each operation is evaluated in double, then truncated once to float32.
float toward_zero(double value) {
    float result = static_cast<float>(value);
    if (std::abs(static_cast<double>(result)) > std::abs(value))
        result = std::nextafter(result, 0.0f);
    return result;
}
constexpr double two_pi = 2.0 * std::numbers::pi;
constexpr float radians_per_degree_f = static_cast<float>(std::numbers::pi / 180.0);
constexpr float degrees_per_radian_f = static_cast<float>(180.0 / std::numbers::pi);
float to_radians(float degrees) {
    return toward_zero(static_cast<double>(degrees) * radians_per_degree_f);
}
float to_degrees(float radians) {
    const float degrees = toward_zero(static_cast<double>(radians) * degrees_per_radian_f);
    return degrees >= 360.0f ? 0.0f : degrees;
}
// [0, 2pi).
float wrap_radians(float angle) {
    if (angle < 0.0f) angle = toward_zero(angle + two_pi);
    if (angle >= two_pi) angle = toward_zero(angle - two_pi);
    return angle;
}
// (-pi, pi]: an exact reversal turns counter-clockwise (unobserved tie).
double signed_radians(double angle) {
    angle = std::remainder(angle, two_pi);
    return angle <= -std::numbers::pi ? angle + two_pi : angle;
}
// Coordinates live in a frame offset from the map corner; truncation there gives
// the observed 1/2048 grid for [0, 4096) and 1/4096 grid for [-2048, 0).
float frame_add(float coordinate, double delta, float origin) {
    const float internal = toward_zero(static_cast<double>(coordinate) - origin + delta);
    return static_cast<float>(static_cast<double>(internal) + origin);
}
}

Model model(ModelVersion version) {
    constexpr float unlimited = std::numeric_limits<float>::infinity();
    if (version == ModelVersion::v4) {
        Model v4 = model(ModelVersion::v3);
        v4.name = "footman-v4";
        v4.soft_float = true;
        return v4;
    }
    if (version == ModelVersion::v3) {
        // v1/v2 cadence fields are unused; the heading block governs updates.
        Model v3{.name = "footman-v3", .position_period_steps = 0, .facing_period_steps = 0,
                 .facing_phase_steps = 0, .move_delay_steps = 0};
        v3.heading.enabled = true;
        return v3;
    }
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
    : model_(model(version)), random_(seed) {
    clock_.push_back(model_.heading.clock_start);
}

std::size_t World::create_footman(Vec2 position, float facing) {
    Unit unit;
    unit.position_ = position;
    unit.facing_ = wrap(facing);
    if (model_.soft_float) {
        auto& s = unit.soft_;
        const sf::F origin = sf::bits(model_.heading.frame_origin);
        s.x = sf::sub(sf::bits(position.x), origin);
        s.y = sf::sub(sf::bits(position.y), origin);
        s.facing = sf::mul(sf::bits(unit.facing_), sf::radians_per_degree);
        s.heading = s.facing;
        s.facing_target = s.facing;
        s.speed = sf::bits(model_.default_speed);
        unit.facing_ = sf::value(sf::mul(s.facing, sf::degrees_per_radian));
    } else if (model_.heading.enabled) {
        unit.facing_radians_ = wrap_radians(to_radians(unit.facing_));
        unit.heading_radians_ = unit.facing_radians_;
        unit.facing_ = to_degrees(unit.facing_radians_);
    }
    unit.speed_ = model_.default_speed;
    units_.push_back(unit);
    return units_.size() - 1;
}
void World::set_move_speed(std::size_t id, float requested) {
    auto& unit = units_.at(id);
    unit.speed_ = std::clamp(requested, model_.min_speed, model_.max_speed);
    unit.soft_.speed = sf::bits(unit.speed_);
}
bool World::issue_point_order(std::size_t id, std::uint32_t order, Vec2 target) {
    auto& unit = units_.at(id);
    if (order != order_move) return false;
    unit.order_ = order_move;
    unit.target_ = target;
    unit.command_step_ = steps_;
    unit.turn_updates_ = 0;
    // A replaced order abandons the rest of the current batch where it is shown.
    unit.batch_active_ = false;
    if (model_.soft_float) {
        soft_halt(unit);
        const sf::F origin = sf::bits(model_.heading.frame_origin);
        unit.soft_.target_x = sf::sub(sf::bits(target.x), origin);
        unit.soft_.target_y = sf::sub(sf::bits(target.y), origin);
    }
    return true;
}
bool World::issue_immediate_order(std::size_t id, std::uint32_t order) {
    auto& unit = units_.at(id);
    if (order != order_stop) return false;
    unit.order_ = order_none;
    unit.batch_active_ = false;
    if (model_.soft_float) {
        soft_halt(unit);
        unit.soft_.settle = true;
    }
    return true;
}
void World::step() {
    ++steps_;
    if (model_.soft_float) {
        step_soft();
        return;
    }
    if (model_.heading.enabled) {
        step_heading();
        return;
    }
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
// footman-v3. Each logical update first finishes the previous batch's exposure,
// then processes orders: arrival, a turn of at most turn_rate, and movement along
// the updated heading if the pre-turn error was inside the propulsion window.
// Reported facing then accelerates toward the hidden heading.
void World::step_heading() {
    const auto& h = model_.heading;
    const bool update = steps_ >= h.update_phase_steps &&
        (steps_ - h.update_phase_steps) % h.update_period_steps == 0;
    const std::uint32_t exposures = h.update_period_steps / h.exposure_period_steps;
    for (auto& unit : units_) {
        if (unit.batch_active_) {
            const auto elapsed = steps_ - unit.batch_step_;
            if (elapsed % h.exposure_period_steps == 0) {
                const double part = static_cast<double>(elapsed / h.exposure_period_steps) / exposures;
                const auto& a = unit.batch_start_;
                const auto& b = unit.batch_end_;
                unit.position_ = {
                    frame_add(a.x, (static_cast<double>(b.x) - a.x) * part, h.frame_origin),
                    frame_add(a.y, (static_cast<double>(b.y) - a.y) * part, h.frame_origin)};
                if (elapsed >= h.update_period_steps) unit.batch_active_ = false;
            }
        }
        if (!update) continue;
        if (unit.order_ == order_move) {
            const double dx = static_cast<double>(unit.target_.x) - unit.position_.x;
            const double dy = static_cast<double>(unit.target_.y) - unit.position_.y;
            if (std::hypot(dx, dy) <= model_.stop_radius) {
                unit.order_ = order_none;
            } else {
                const float direction = toward_zero(std::atan2(dy, dx));
                const float error = toward_zero(signed_radians(
                    static_cast<double>(direction) - unit.heading_radians_));
                const float turn = std::clamp(error, -h.turn_rate_radians, h.turn_rate_radians);
                unit.heading_radians_ = wrap_radians(toward_zero(
                    static_cast<double>(unit.heading_radians_) + turn));
                if (std::abs(error) <= to_radians(h.propulsion_window_degrees)) {
                    const float dt = static_cast<float>(model_.step_us * h.update_period_steps)
                        / 1000000.0f;
                    const float travel = toward_zero(static_cast<double>(unit.speed_) * dt);
                    const double heading = unit.heading_radians_;
                    unit.batch_start_ = unit.position_;
                    unit.batch_end_ = {
                        frame_add(unit.position_.x, toward_zero(travel * std::cos(heading)), h.frame_origin),
                        frame_add(unit.position_.y, toward_zero(travel * std::sin(heading)), h.frame_origin)};
                    unit.batch_step_ = steps_;
                    unit.batch_active_ = true;
                }
            }
        }
        // Accelerate, cap, then brake along err * (err / max)^(1/4) near the heading.
        const double error = signed_radians(
            static_cast<double>(unit.heading_radians_) - unit.facing_radians_);
        const double magnitude = std::abs(error);
        if (magnitude < h.facing_snap_radians) {
            unit.facing_radians_ = unit.heading_radians_;
            unit.facing_velocity_ = 0.0f;
        } else {
            const double sign = error > 0 ? 1.0 : -1.0;
            const double cap = h.facing_max_velocity_radians;
            const double limit = std::min(cap, magnitude * std::pow(magnitude / cap, 0.25));
            double velocity = unit.facing_velocity_ + sign * h.facing_acceleration_radians;
            if (velocity * sign > limit) velocity = sign * limit;
            unit.facing_velocity_ = toward_zero(velocity);
            unit.facing_radians_ = wrap_radians(toward_zero(
                static_cast<double>(unit.facing_radians_) + unit.facing_velocity_));
        }
        unit.facing_ = to_degrees(unit.facing_radians_);
    }
}

namespace {
constexpr std::uint32_t frame_steps = 5;
// Below this speed (4e-7) a unit is not moving and keeps its stored heading.
constexpr sf::F moving_epsilon = 0x34d6bf95;
}
// The movement clock advances once per 5 ms frame by add(clock, 0.005f), so the
// truncated step depends on the clock's binade; elapsed time is a clock difference.
sf::F World::clock_at(std::uint64_t frame) const {
    while (clock_.size() <= frame) clock_.push_back(sf::add(clock_.back(), sf::bits(0.005f)));
    return clock_[frame];
}
sf::F World::frames_to_seconds(std::uint64_t from_step, std::uint64_t to_step) const {
    return sf::sub(clock_at(to_step / frame_steps), clock_at(from_step / frame_steps));
}
// Position advances by velocity times the frames elapsed since the last
// integration; GetUnitX/Y read that prediction without storing it.
void World::soft_integrate(Unit& unit) const {
    auto& s = unit.soft_;
    const auto frames = steps_ / frame_steps - s.integrated_step / frame_steps;
    if (frames && (s.vx || s.vy)) {
        const sf::F dt = frames_to_seconds(s.integrated_step, steps_);
        s.x = sf::add(s.x, sf::mul(s.vx, dt));
        s.y = sf::add(s.y, sf::mul(s.vy, dt));
    }
    s.integrated_step = steps_;
}
// An order halts the unit; its heading becomes the direction it was moving.
void World::soft_halt(Unit& unit) const {
    auto& s = unit.soft_;
    soft_integrate(unit);
    const sf::F moving = sf::length(s.vx, s.vy);
    if (!sf::less(sf::abs(moving), moving_epsilon)) s.heading = sf::vector_angle(s.vx, s.vy, moving);
    s.vx = s.vy = 0;
}
void World::soft_expose(Unit& unit) const {
    const auto& s = unit.soft_;
    const sf::F dt = frames_to_seconds(s.integrated_step, steps_);
    const sf::F origin = sf::bits(model_.heading.frame_origin);
    unit.position_ = {sf::value(sf::add(sf::add(s.x, sf::mul(s.vx, dt)), origin)),
                      sf::value(sf::add(sf::add(s.y, sf::mul(s.vy, dt)), origin))};
    unit.facing_ = sf::value(sf::mul(s.facing, sf::degrees_per_radian));
}
// footman-v4: each update integrates position, steers the movement heading toward
// the target, sets velocity, retargets the reported facing and advances its smoother.
void World::step_soft() {
    using namespace sf;
    const auto& h = model_.heading;
    const bool update = steps_ >= h.update_phase_steps &&
        (steps_ - h.update_phase_steps) % h.update_period_steps == 0;
    static const F accel = atof("0.07"), cap = atof("0.2"), brake_range = atof("0.2"),
        brake_power = atof("0.25"), snap = atof("0.001"), turn_rate = atof("0.6");
    const F stop_radius = bits(model_.stop_radius);
    const F window = mul(bits(h.propulsion_window_degrees), radians_per_degree);
    constexpr F turn_epsilon = 0x3456bf95;     // 2e-7
    constexpr F velocity_epsilon = 0x3456bf95; // 2e-7, squared speed
    constexpr F retarget_epsilon = 0x34d6bf95; // 4e-7, squared speed
    for (auto& unit : units_) {
        auto& s = unit.soft_;
        if (!update) {
            soft_expose(unit);
            continue;
        }
        soft_integrate(unit);
        bool steer = false;
        F speed = 0, heading = s.heading;
        // Each update re-derives the heading from the velocity; the stored
        // heading is only used while the unit is not moving.
        const F moving = length(s.vx, s.vy);
        if (!less(abs(moving), moving_epsilon) && unit.order_ == order_move)
            heading = vector_angle(s.vx, s.vy, moving);
        const F current = heading;
        if (unit.order_ == order_move) {
            const F dx = sub(s.target_x, s.x), dy = sub(s.target_y, s.y);
            const F distance = length(dx, dy);
            if (!less(stop_radius, distance)) {
                unit.order_ = order_none;
                steer = true;
            } else {
                F error = angle_to(vector_angle(dx, dy, distance), current);
                if (less(abs(error), turn_epsilon)) error = 0;
                if (!greater(abs(error), window)) speed = s.speed;
                if (abs(error)) {
                    const F turn = greater(abs(error), turn_rate) ? turn_rate : abs(error);
                    heading = add(current, error & 0x80000000u ? neg(turn) : turn);
                }
                steer = true;
            }
        } else if (s.settle) {
            steer = true;
        }
        s.settle = false;
        if (steer) {
            if (greater(speed, zero)) {
                // Velocity is replaced through its difference, as retail does.
                const F nx = mul(speed, cos(heading)), ny = mul(speed, sin(heading));
                s.vx = add(s.vx, sub(nx, s.vx));
                s.vy = add(s.vy, sub(ny, s.vy));
                const F squared = add(mul(s.vx, s.vx), mul(s.vy, s.vy));
                if (less(abs(squared), velocity_epsilon)) {
                    s.vx = s.vy = 0;
                } else {
                    if (greater(sqrt(squared), s.speed)) {
                        const F k = mul(s.speed, recip(sqrt(squared)));
                        s.vx = mul(s.vx, k);
                        s.vy = mul(s.vy, k);
                    }
                    const F check = add(mul(s.vx, s.vx), mul(s.vy, s.vy));
                    if (!less(abs(check), retarget_epsilon))
                        s.facing_target = vector_angle(s.vx, s.vy, length(s.vx, s.vy));
                }
            } else {
                s.vx = add(s.vx, sub(zero, s.vx));
                s.vy = add(s.vy, sub(zero, s.vy));
                s.facing_target = wrap_angle(heading);
                s.heading = wrap_angle(heading);
            }
        }
        // Reported facing: accelerate, cap by min(cap, err) * min(err/range, 1)^0.25.
        const F error = angle_to(s.facing_target, s.facing);
        const F magnitude = abs(error);
        if (less(magnitude, snap)) {
            s.facing = s.facing_target;
            s.facing_velocity = 0;
        } else {
            s.facing_velocity = add(s.facing_velocity, accel | (error & 0x80000000u));
            const std::uint32_t sign = s.facing_velocity & 0x80000000u;
            F velocity = abs(s.facing_velocity);
            F limit = greater(cap, magnitude) ? magnitude : cap;
            F ratio = greater(brake_range, magnitude) ? div(magnitude, brake_range) : one;
            if (less(ratio, zero)) ratio = zero;
            else if (greater(ratio, one)) ratio = one;
            if (ratio != one) limit = mul(limit, pow(ratio, brake_power));
            if (greater(velocity, limit)) velocity = limit;
            s.facing_velocity = velocity | sign;
            s.facing = wrap_angle(add(s.facing, s.facing_velocity));
        }
        soft_expose(unit);
    }
}
}
