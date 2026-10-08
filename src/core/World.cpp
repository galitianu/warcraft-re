#include "core/World.h"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <limits>
#include <map>
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
        v4.pathing.enabled = true;
        // Retail stops lie in [14.607, 15.90): MOV-0004 stopped at 14.607 and MOV-0018-b's
        // u1 did not stop at 15.90. 15.5 is half the Footman's collision size, a guess.
        v4.stop_radius = 15.5f;
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
World::World(ModelVersion version, std::uint32_t seed) : model_(model(version)), random_(seed) {
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
    sequence_.push_back(units_.size() - 1);
    return units_.size() - 1;
}
namespace {
template <class T> void put(std::string& out, const T& value) {
    char bytes[sizeof(T)];
    std::memcpy(bytes, &value, sizeof(T));
    out.append(bytes, sizeof(T));
}
void put(std::string& out, Vec2 v) {
    put(out, v.x);
    put(out, v.y);
}
}
std::string World::snapshot() const {
    std::string out = "wc3-world-snapshot 2\n";
    put(out, steps_);
    put(out, static_cast<std::uint64_t>(units_.size()));
    for (const auto& u : units_) {
        put(out, u.position_);
        put(out, u.target_);
        put(out, u.facing_);
        put(out, u.speed_);
        put(out, u.order_);
        put(out, u.command_step_);
        put(out, u.turn_updates_);
        put(out, u.facing_radians_);
        put(out, u.heading_radians_);
        put(out, u.facing_velocity_);
        put(out, u.batch_active_);
        put(out, u.batch_step_);
        put(out, u.batch_start_);
        put(out, u.batch_end_);
        const auto& s = u.soft_;
        for (const sf::F f : {s.x, s.y, s.vx, s.vy, s.heading, s.facing, s.facing_velocity,
                              s.facing_target, s.target_x, s.target_y, s.speed})
            put(out, f);
        put(out, s.integrated_step);
        put(out, s.settle);
        put(out, static_cast<std::uint64_t>(u.route_.size()));
        for (const auto& waypoint : u.route_) put(out, waypoint);
        put(out, static_cast<std::uint64_t>(u.route_index_));
        put(out, u.route_partial_);
        put(out, u.hold_);
        put(out, static_cast<std::uint64_t>(u.blocker_));
        put(out, u.planned_update_);
    }
    for (const auto id : sequence_) put(out, static_cast<std::uint64_t>(id));
    const auto rng = random_.state();
    put(out, random_.seed());
    out += rng;
    return out;
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
    unit.hold_ = 0;
    unit.blocker_ = no_unit;
    // A replaced order abandons the rest of the current batch where it is shown.
    unit.batch_active_ = false;
    if (model_.soft_float) {
        soft_halt(unit);
        const sf::F origin = sf::bits(model_.heading.frame_origin);
        unit.soft_.target_x = sf::sub(sf::bits(target.x), origin);
        unit.soft_.target_y = sf::sub(sf::bits(target.y), origin);
    }
    if (model_.pathing.enabled) {
        // The route is planned at the unit's next update, without waiting out a replan.
        unit.route_.clear();
        unit.planned_update_ = update_index() - model_.pathing.replan_updates;
        // Retail processes the most recently ordered unit first (MOV-0018-b, MOV-0020-c).
        sequence_.erase(std::find(sequence_.begin(), sequence_.end(), id));
        sequence_.insert(sequence_.begin(), id);
    }
    return true;
}
bool World::issue_immediate_order(std::size_t id, std::uint32_t order) {
    auto& unit = units_.at(id);
    if (order != order_stop) return false;
    unit.order_ = order_none;
    unit.batch_active_ = false;
    unit.route_.clear();
    unit.hold_ = 0;
    unit.blocker_ = no_unit;
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
    for (const std::size_t id : sequence_) {
        auto& unit = units_[id];
        auto& s = unit.soft_;
        if (!update) {
            soft_expose(unit);
            continue;
        }
        soft_integrate(unit);
        const bool hold = model_.pathing.enabled && unit.order_ == order_move && route(id);
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
            if (!hold && !less(stop_radius, distance)) {
                unit.order_ = order_none;
                unit.route_.clear();
                steer = true;
            } else {
                F error = angle_to(vector_angle(dx, dy, distance), current);
                if (less(abs(error), turn_epsilon)) error = 0;
                if (!hold && !greater(abs(error), window)) speed = s.speed;
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

// Unit pathing: retail's grid mechanism (docs/footman-v4-model.md#unit-pathing). Grid
// geometry is evaluated in double from the float32 positions with correctly rounded
// +, -, *, / and sqrt only, so every host makes the same discrete choices.
namespace {

P2 p2(Vec2 v) { return {v.x, v.y}; }
double distance(P2 a, P2 b) { return std::sqrt((a.x - b.x) * (a.x - b.x) + (a.y - b.y) * (a.y - b.y)); }
}
Vec2 World::soft_position(const Unit& unit) const {
    if (!model_.soft_float) return unit.position_;
    const auto& s = unit.soft_;
    const sf::F dt = frames_to_seconds(s.integrated_step, steps_);
    const sf::F origin = sf::bits(model_.heading.frame_origin);
    return {sf::value(sf::add(sf::add(s.x, sf::mul(s.vx, dt)), origin)),
            sf::value(sf::add(sf::add(s.y, sf::mul(s.vy, dt)), origin))};
}
// Moving: a nonzero velocity (as floats: -0 is still).
bool World::moving(const Unit& unit) const {
    return (unit.soft_.vx | unit.soft_.vy) & 0x7fffffffu;
}
// Logical updates completed so far.
std::uint64_t World::update_index() const {
    const auto& h = model_.heading;
    return steps_ < h.update_phase_steps ? 0 : (steps_ - h.update_phase_steps) / h.update_period_steps + 1;
}
// Plan a route to the order target with retail's grid A* (0x8bd560). A node is a cell,
// standing for a Footman whose footprint is anchored there; a move is open when the
// cells it newly covers are free of stationary units' footprints. Straight moves cost
// 15, diagonal ones 21, and the heuristic is retail's integer distance estimate; the
// open list is retail's binary heap, which decides between equal paths. If the search
// never met an occupied cell the unit walks straight at the target; otherwise it
// follows the node centres, skipping ahead as it reaches them (route()). An unreachable
// target routes to the first-found node nearest it: a partial route, replanned on arrival.
void World::plan(std::size_t id) {
    auto& unit = units_[id];
    unit.route_.clear();
    unit.route_index_ = 0;
    unit.route_partial_ = false;
    unit.planned_update_ = update_index();
    const P2 p = cell(unit), g = grid(unit.target_);
    const long sx = std::floor(p.x), sy = std::floor(p.y), gx = std::floor(g.x), gy = std::floor(g.y);
    if (sx == gx && sy == gy) {
        unit.route_.push_back(unit.target_);
        return;
    }
    std::vector<std::pair<long, long>> fixed;  // footprint cells of the units the search sees
    for (std::size_t j = 0; j < units_.size(); ++j)
        if (j != id && !moving(units_[j])) {
            const P2 q = cell(units_[j]);
            fixed.push_back({std::floor(q.x), std::floor(q.y)});
        }
    bool touched = false;
    const long size = model_.pathing.grid_cells;
    auto blocked = [&](long x, long y) {
        bool hit = x < 0 || y < 0 || x >= size || y >= size;
        for (const auto& [fx, fy] : fixed) hit = hit || (x >= fx - 1 && x <= fx && y >= fy - 1 && y <= fy);
        touched = touched || hit;
        return hit;
    };
    auto estimate = [&](long x, long y) -> std::uint32_t {
        const std::uint32_t dx = std::abs(x - gx) * 15, dy = std::abs(y - gy) * 15;
        const std::uint32_t lo = std::min(dx, dy), hi = std::max(dx, dy);
        if (lo <= hi >> 2) return hi;
        const std::uint32_t u = lo + (lo >> 1);
        return (u >> 2) + (u >> 7) + hi + (hi >> 6) - (hi >> 4);
    };
    struct Node { long x, y; std::uint32_t g = 0, h = 0, version = 0; long parent = -1; int state = 0; };
    enum { unseen = 0, open = 1, closed = 2 };
    std::vector<Node> nodes;
    std::map<std::pair<long, long>, long> index;
    auto node = [&](long x, long y) {
        const auto [it, fresh] = index.try_emplace({x, y}, static_cast<long>(nodes.size()));
        if (fresh) nodes.push_back({x, y});
        return it->second;
    };
    // 1-based binary heap of (f, node, version); stale versions are skipped.
    struct Entry { std::uint32_t f; long node; std::uint32_t version; };
    std::vector<Entry> heap(1);
    auto push = [&](Entry e) {
        heap.push_back(e);
        std::size_t i = heap.size() - 1;
        for (; i > 1 && !(heap[i / 2].f < e.f); i /= 2) heap[i] = heap[i / 2];
        heap[i] = e;
    };
    auto pop = [&] {
        const Entry top = heap[1], last = heap.back();
        heap.pop_back();
        if (const std::size_t n = heap.size() - 1; n >= 1) {
            std::size_t i = 1;
            for (std::size_t c = 2; i <= n / 2; i = c, c = 2 * i) {
                if (c < n && heap[c + 1].f <= heap[c].f) ++c;
                if (last.f <= heap[c].f) break;
                heap[i] = heap[c];
            }
            heap[i] = last;
        }
        return top;
    };
    const long start = node(sx, sy), goal = node(gx, gy);
    long best = start;
    std::uint64_t best_distance = (sx - gx) * (sx - gx) + (sy - gy) * (sy - gy);
    auto relax = [&](long n, long from, std::uint32_t step) {
        const std::uint32_t cost = nodes[from].g + step, h = estimate(nodes[n].x, nodes[n].y);
        auto& m = nodes[n];
        if (m.state == unseen) {
            const std::uint64_t d = (m.x - gx) * (m.x - gx) + (m.y - gy) * (m.y - gy);
            if (d < best_distance) {
                best_distance = d;
                best = n;
            }
        } else if (m.g <= cost) {
            return;
        }
        m.g = cost;
        m.h = h;
        m.parent = from;
        m.state = open;
        push({cost + h, n, ++m.version});
    };
    nodes[start].h = estimate(sx, sy);
    nodes[start].state = open;
    push({nodes[start].h, start, ++nodes[start].version});
    bool found = false;
    for (std::uint32_t expanded = 0; heap.size() > 1 && expanded < model_.pathing.search_limit; ++expanded) {
        const Entry e = pop();
        if (e.version != nodes[e.node].version) continue;
        ++nodes[e.node].version;
        if (e.node == goal) {
            found = true;
            break;
        }
        const long x = nodes[e.node].x, y = nodes[e.node].y;
        // The 12 cells around the footprint, from the south-west corner anticlockwise;
        // each move needs the ones it newly covers.
        static constexpr int ring[12][2] = {{-2, -2}, {-1, -2}, {0, -2}, {1, -2}, {1, -1}, {1, 0},
                                            {1, 1}, {0, 1}, {-1, 1}, {-2, 1}, {-2, 0}, {-2, -1}};
        unsigned mask = 0;
        for (int b = 0; b < 12; ++b)
            if (blocked(x + ring[b][0], y + ring[b][1])) mask |= 1u << b;
        static constexpr struct { int dx, dy; unsigned needs; std::uint32_t cost; } moves[8] = {
            {-1, -1, 0xc07, 21}, {0, -1, 0x6, 15}, {1, -1, 0x3e, 21}, {-1, 0, 0xc00, 15},
            {1, 0, 0x30, 15}, {-1, 1, 0xf80, 21}, {0, 1, 0x180, 15}, {1, 1, 0x1f0, 21}};
        for (const auto& m : moves)
            if (!(mask & m.needs)) relax(node(x + m.dx, y + m.dy), e.node, m.cost);
        nodes[e.node].state = closed;
    }
    const long end = found ? goal : best;
    const double origin = model_.heading.frame_origin, size_cell = model_.pathing.cell;
    for (long n = end; n != start && n >= 0; n = nodes[n].parent)
        unit.route_.push_back({static_cast<float>((nodes[n].x + 0.5) * size_cell + origin),
                               static_cast<float>((nodes[n].y + 0.5) * size_cell + origin)});
    if (unit.route_.empty() || end == goal) {
        if (unit.route_.empty()) unit.route_.push_back(unit.target_);
        unit.route_.front() = unit.target_;
    }
    unit.route_partial_ = end != goal && end != start;
    if (!touched) unit.route_.erase(unit.route_.begin() + 1, unit.route_.end());
    std::reverse(unit.route_.begin(), unit.route_.end());
}
// Grid position in cells from the map corner.
P2 World::grid(Vec2 v) const {
    const double origin = model_.heading.frame_origin, cell = model_.pathing.cell;
    return {(v.x - origin) / cell, (v.y - origin) / cell};
}
// The grid position a unit occupies: where it was last integrated, so a unit not yet
// processed this update still covers last update's cells.
P2 World::cell(const Unit& unit) const {
    const double cell = model_.pathing.cell;
    return {sf::value(unit.soft_.x) / cell, sf::value(unit.soft_.y) / cell};
}
// Other units whose footprints cover any of the cells a Footman entering cell (x, y)
// from the given octant (retail class-1 walker: 8 west, 2 east, 1 south, 4 north) newly
// covers. A Footman's footprint is the 2x2 cells {fx-1, fx} x {fy-1, fy}, f the cell
// holding it: the walker checks the whole footprint with no cell change, the leading
// edge for a straight one, and the L of the swept box for a diagonal one.
std::vector<std::size_t> World::occupants(std::size_t id, long x, long y, int octant, bool moving_too) const {
    std::vector<std::pair<long, long>> cells;
    auto row = [&](long cx, long cy, int n) { for (int i = 0; i < n; ++i) cells.push_back({cx + i, cy}); };
    auto column = [&](long cx, long cy, int n) { for (int i = 0; i < n; ++i) cells.push_back({cx, cy + i}); };
    switch (octant) {
    case 1: row(x - 1, y - 1, 2); break;
    case 2: column(x, y - 1, 2); break;
    case 4: row(x - 1, y, 2); break;
    case 8: column(x - 1, y - 1, 2); break;
    case 3: row(x - 2, y - 1, 3); column(x, y, 2); break;
    case 6: row(x - 2, y, 3); column(x, y - 2, 2); break;
    case 9: row(x - 1, y - 1, 3); column(x - 1, y, 2); break;
    case 12: row(x - 1, y, 3); column(x - 1, y - 2, 2); break;
    default: row(x - 1, y - 1, 2); row(x - 1, y, 2);
    }
    std::vector<std::size_t> found;
    for (const auto& [cx, cy] : cells)
        for (std::size_t j = 0; j < units_.size(); ++j) {
            const P2 q = cell(units_[j]);
            const long fx = std::floor(q.x), fy = std::floor(q.y);
            if (j == id || cx < fx - 1 || cx > fx || cy < fy - 1 || cy > fy) continue;
            if (!moving_too && moving(units_[j])) continue;
            if (std::find(found.begin(), found.end(), j) == found.end()) found.push_back(j);
        }
    return found;
}
namespace {
int octant(long fx, long fy, long tx, long ty) {
    return (tx < fx ? 8 : tx > fx ? 2 : 0) | (ty < fy ? 1 : ty > fy ? 4 : 0);
}
}
// The units in the way of a step toward the waypoint: the walker for the cell one cell
// ahead (or the waypoint, if nearer).
std::vector<std::size_t> World::probe(std::size_t id, Vec2 waypoint) const {
    const P2 p = cell(units_[id]), w = grid(waypoint);
    double dx = w.x - p.x, dy = w.y - p.y;
    if (const double length = std::sqrt(dx * dx + dy * dy); length > 1) {
        dx /= length;
        dy /= length;
    }
    const long ex = std::floor(p.x + dx), ey = std::floor(p.y + dy);
    return occupants(id, ex, ey, octant(std::floor(p.x), std::floor(p.y), ex, ey), true);
}
// Whether the unit could walk straight to the waypoint: the walker at each whole-cell
// step along the line that enters a new cell. Retail starts the previous cell at the
// grid corner (0, 0), so the first step always checks the north-east L.
bool World::clear(std::size_t id, Vec2 waypoint) const {
    const P2 p = cell(units_[id]), w = grid(waypoint);
    double dx = w.x - p.x, dy = w.y - p.y;
    const double length = std::sqrt(dx * dx + dy * dy);
    if (length > 1) {
        dx /= length;
        dy /= length;
    }
    long px = 0, py = 0;
    for (double t = 1; t < length; t += 1) {
        const long x = std::floor(p.x + dx * t), y = std::floor(p.y + dy * t);
        if ((x != px || y != py) && !occupants(id, x, y, octant(px, py, x, y), false).empty()) return false;
        px = x;
        py = y;
    }
    return true;
}
// Per update, before steering: advance waypoints, probe for units in the way, and
// point the soft-float target at the current waypoint. True holds the unit in place
// this update; it still steers toward the waypoint.
bool World::route(std::size_t id) {
    auto& unit = units_[id];
    auto& s = unit.soft_;
    const auto& P = model_.pathing;
    const sf::F origin = sf::bits(model_.heading.frame_origin);
    auto aim = [&](Vec2 point) {
        s.target_x = sf::sub(sf::bits(point.x), origin);
        s.target_y = sf::sub(sf::bits(point.y), origin);
    };
    // Holding out a wait, or waiting to replan, the unit steers for its order target.
    if (unit.hold_) {
        --unit.hold_;
        aim(unit.target_);
        return true;
    }
    if (unit.route_.empty()) {
        if (update_index() - unit.planned_update_ < P.replan_updates) {
            aim(unit.target_);
            return true;
        }
        plan(id);
    }
    auto point = [&] { return p2(soft_position(unit)); };
    // At the end of a partial route the unit replans at once and holds for this update,
    // already steering toward the new route (MOV-0018-b's u1).
    bool hold = false;
    for (;;) {
        // Reaching a waypoint skips on to the last of the following ones in straight reach.
        if (unit.route_index_ + 1 < unit.route_.size()
            && distance(point(), p2(unit.route_[unit.route_index_])) <= P.waypoint_radius) {
            ++unit.route_index_;
            while (unit.route_index_ + 1 < unit.route_.size() && clear(id, unit.route_[unit.route_index_ + 1]))
                ++unit.route_index_;
        }
        if (hold || !unit.route_partial_ || unit.route_index_ + 1 != unit.route_.size()
            || distance(point(), p2(unit.route_.back())) > P.waypoint_radius)
            break;
        plan(id);
        hold = true;
    }
    const Vec2 waypoint = unit.route_[unit.route_index_];
    aim(waypoint);
    if (hold) return true;
    if (distance(point(), p2(waypoint)) <= model_.stop_radius) return false;  // arrival is the movement code's
    const auto in_way = probe(id, waypoint);
    unit.blocker_ = no_unit;
    if (in_way.empty()) return false;
    // A moving unit that is not itself held for another: wait for it if it is at least
    // as fast (squared speeds, so ulp differences decide equal speeds); a slower one
    // holds for this unit instead. Stationary units are routed around.
    auto squared = [](const Unit& u) { return sf::add(sf::mul(u.soft_.vx, u.soft_.vx), sf::mul(u.soft_.vy, u.soft_.vy)); };
    const sf::F mine = squared(unit);
    for (const std::size_t j : in_way) {
        auto& other = units_[j];
        const sf::F theirs = squared(other);
        if (!theirs || other.blocker_ != no_unit) continue;
        if (!sf::less(theirs, mine)) {
            unit.blocker_ = j;
            unit.hold_ = std::max(unit.hold_, P.wait_updates);
            return true;
        }
        other.blocker_ = id;
        other.hold_ = std::max(other.hold_, P.give_way_updates);
    }
    // Nothing to wait for: drop the route and plan around what is in the way.
    unit.route_.clear();
    aim(unit.target_);
    return true;
}
}
