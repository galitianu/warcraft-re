#include "core/World.h"
#include <algorithm>
#include <cmath>
#include <limits>
#include <map>
#include <numbers>
#include <queue>
#include <tuple>

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
World::World(ModelVersion version, std::uint32_t seed) : World(model(version), seed) {}

World::World(const Model& parameters, std::uint32_t seed) : model_(parameters), random_(seed) {
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
    if (model_.pathing.enabled) plan(id);
    return true;
}
bool World::issue_immediate_order(std::size_t id, std::uint32_t order) {
    auto& unit = units_.at(id);
    if (order != order_stop) return false;
    unit.order_ = order_none;
    unit.batch_active_ = false;
    unit.route_.clear();
    unit.waiting_ = false;
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
    for (std::size_t id = 0; id < units_.size(); ++id) {
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
        // Held by unit pathing: the update steers as usual (heading, facing target),
        // then the unit does not move (MOV-0018-c's facing while it waits).
        if (hold) s.vx = s.vy = 0;
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

// Unit pathing (MOV-0018, docs/mov-0018.md). Geometry is evaluated in double from the
// float32 positions with correctly rounded +, -, *, / and sqrt only, so every host
// makes the same discrete choices; the soft-float movement itself is unchanged.
namespace {
struct P2 { double x, y; };
P2 p2(Vec2 v) { return {v.x, v.y}; }
double distance(P2 a, P2 b) { return std::sqrt((a.x - b.x) * (a.x - b.x) + (a.y - b.y) * (a.y - b.y)); }
double segment_distance(P2 p, P2 a, P2 b) {
    const double dx = b.x - a.x, dy = b.y - a.y, d2 = dx * dx + dy * dy;
    double t = d2 == 0 ? 0 : ((p.x - a.x) * dx + (p.y - a.y) * dy) / d2;
    t = t < 0 ? 0 : t > 1 ? 1 : t;
    return distance(p, {a.x + t * dx, a.y + t * dy});
}
// Distance from segment ab to the rectangle [lx, hx] x [ly, hy]; 0 if they meet.
double rectangle_distance(P2 a, P2 b, double lx, double hx, double ly, double hy) {
    auto in = [&](P2 p) { return p.x >= lx && p.x <= hx && p.y >= ly && p.y <= hy; };
    if (in(a) || in(b)) return 0;
    // Liang-Barsky clip: does the segment cross the rectangle?
    double t0 = 0, t1 = 1;
    const double d[2] = {b.x - a.x, b.y - a.y};
    const double lo[2] = {lx - a.x, ly - a.y}, hi[2] = {hx - a.x, hy - a.y};
    bool crosses = true;
    for (int k = 0; k < 2 && crosses; ++k) {
        if (d[k] == 0) { crosses = lo[k] <= 0 && hi[k] >= 0; continue; }
        double u = lo[k] / d[k], v = hi[k] / d[k];
        if (u > v) std::swap(u, v);
        t0 = std::max(t0, u);
        t1 = std::min(t1, v);
        crosses = t0 <= t1;
    }
    if (crosses) return 0;
    auto box = [&](P2 p) {
        const double x = p.x < lx ? lx - p.x : p.x > hx ? p.x - hx : 0;
        const double y = p.y < ly ? ly - p.y : p.y > hy ? p.y - hy : 0;
        return std::sqrt(x * x + y * y);
    };
    return std::min({box(a), box(b), segment_distance({lx, ly}, a, b), segment_distance({lx, hy}, a, b),
                     segment_distance({hx, ly}, a, b), segment_distance({hx, hy}, a, b)});
}
}
Vec2 World::soft_position(const Unit& unit) const {
    if (!model_.soft_float) return unit.position_;
    const auto& s = unit.soft_;
    const sf::F dt = frames_to_seconds(s.integrated_step, steps_);
    const sf::F origin = sf::bits(model_.heading.frame_origin);
    return {sf::value(sf::add(sf::add(s.x, sf::mul(s.vx, dt)), origin)),
            sf::value(sf::add(sf::add(s.y, sf::mul(s.vy, dt)), origin))};
}
// A unit following its route counts as moving even while it turns on the spot.
bool World::moving(const Unit& unit) const {
    return unit.order_ == order_move && !unit.waiting_;
}
// Plan a route from the unit's position to its order target around the other units.
// A clear straight line is taken as it is. Otherwise A* runs over 32-unit cell centres
// (8-connected, no corner cutting); the start cell is dropped, the first step kept, and
// the rest string-pulled. A target covered by a unit ends the route at the last free
// node before it (partial; replanned on arrival). An idle unit standing on the target
// is ignored (MOV-0018-b).
void World::plan(std::size_t id) {
    auto& unit = units_[id];
    const auto& P = model_.pathing;
    unit.route_.clear();
    unit.route_index_ = 0;
    unit.route_partial_ = unit.waiting_ = false;
    const P2 start = p2(soft_position(unit)), goal = p2(unit.target_);
    const double cell = P.cell;
    auto index = [&](double v) { return static_cast<long>(std::floor(v / cell)); };
    auto centre = [&](long i) { return (static_cast<double>(i) + 0.5) * cell; };
    // Each other unit blocks the 3x3 cells around the cell holding its centre.
    struct Block { long x, y; };
    std::vector<Block> blocks;
    for (std::size_t j = 0; j < units_.size(); ++j) {
        if (j == id) continue;
        const P2 q = p2(soft_position(units_[j]));
        if (units_[j].order_ != order_move && distance(q, goal) <= model_.stop_radius) continue;
        blocks.push_back({index(q.x), index(q.y)});
    }
    auto inside = [](const Block& b, long x, long y) { return std::abs(x - b.x) <= 1 && std::abs(y - b.y) <= 1; };
    auto visible = [&](P2 a, P2 b, const std::vector<Block>& set) {
        for (const auto& k : set) {
            const double lx = (k.x - 1) * cell, hx = (k.x + 2) * cell, ly = (k.y - 1) * cell, hy = (k.y + 2) * cell;
            if (rectangle_distance(a, b, lx, hx, ly, hy) < P.line_clearance) return false;
        }
        return true;
    };
    const long sx = index(start.x), sy = index(start.y), gx = index(goal.x), gy = index(goal.y);
    if (visible(start, goal, blocks) || (sx == gx && sy == gy)) {
        unit.route_.push_back(unit.target_);
        return;
    }
    // Units covering the target node are searched through, then cut off (partial route).
    std::vector<Block> covering, others;
    for (const auto& k : blocks) (inside(k, gx, gy) ? covering : others).push_back(k);
    auto free_of = [&](long x, long y, const std::vector<Block>& set) {
        for (const auto& k : set)
            if (inside(k, x, y)) return false;
        return true;
    };
    auto passable = [&](long x, long y) { return (x == sx && y == sy) || free_of(x, y, others); };
    const long margin = 16;
    const long x0 = std::min(sx, gx) - margin, x1 = std::max(sx, gx) + margin;
    const long y0 = std::min(sy, gy) - margin, y1 = std::max(sy, gy) + margin;
    // Octile costs as exact (straight, diagonal) step counts: equal paths tie exactly.
    struct Cost {
        long s = 0, d = 0;
        Cost operator+(Cost o) const { return {s + o.s, d + o.d}; }
        bool operator<(Cost o) const {  // s + d*sqrt(2) < o.s + o.d*sqrt(2)
            const long a = s - o.s, b = o.d - d;  // a < b*sqrt(2)?
            if (b >= 0) return a < 0 || a * a < 2 * b * b;
            return a < 0 && a * a > 2 * b * b;
        }
        bool operator==(Cost o) const { return s == o.s && d == o.d; }
    };
    auto heuristic = [&](long x, long y) {
        const long dx = std::abs(x - gx), dy = std::abs(y - gy);
        return Cost{std::max(dx, dy) - std::min(dx, dy), std::min(dx, dy)};
    };
    using Node = std::pair<long, long>;
    std::map<Node, Cost> cost{{{sx, sy}, Cost{}}};
    struct Entry { Cost f, h; std::uint64_t serial; long x, y; };
    // Ties: lower f, then lower h, then first queued.
    auto later = [](const Entry& a, const Entry& b) {
        if (!(a.f == b.f)) return b.f < a.f;
        if (!(a.h == b.h)) return b.h < a.h;
        return a.serial > b.serial;
    };
    std::priority_queue<Entry, std::vector<Entry>, decltype(later)> open(later);
    std::uint64_t serial = 0;
    open.push({heuristic(sx, sy), heuristic(sx, sy), serial++, sx, sy});
    static constexpr int steps[8][2] = {{1, 0}, {0, -1}, {-1, 0}, {0, 1}, {1, -1}, {-1, -1}, {-1, 1}, {1, 1}};
    bool found = false;
    while (!open.empty()) {
        const Entry e = open.top();
        open.pop();
        const long x = e.x, y = e.y;
        if (cost[{x, y}] + heuristic(x, y) < e.f) continue;  // stale entry
        // Finish every node that can still tie the goal, so equal paths are all seen.
        if (found && cost[{gx, gy}] < e.f) break;
        if (x == gx && y == gy) { found = true; continue; }
        for (const auto& step : steps) {
            const long nx = x + step[0], ny = y + step[1];
            if (nx < x0 || nx > x1 || ny < y0 || ny > y1 || !passable(nx, ny)) continue;
            if (step[0] && step[1] && (!passable(x + step[0], y) || !passable(x, y + step[1]))) continue;
            const Cost next = cost[{x, y}] + (step[0] && step[1] ? Cost{0, 1} : Cost{1, 0});
            const auto known = cost.find({nx, ny});
            if (known != cost.end() && !(next < known->second)) continue;
            cost[{nx, ny}] = next;
            open.push({next + heuristic(nx, ny), heuristic(nx, ny), serial++, nx, ny});
        }
    }
    if (!found) {  // Unreachable: keep walking straight at the target.
        unit.route_.push_back(unit.target_);
        return;
    }
    // Walk back from the goal over equal-cost predecessors: diagonal steps first, each
    // group clockwise from east. Equal paths so take their diagonals as late as possible
    // (MOV-0018-b's (976, -16)), and an exact tie between sides of a blocker on an
    // eastward line passes south (MOV-0018-a/d, one observed tie).
    static constexpr int back[8][2] = {{1, -1}, {-1, -1}, {-1, 1}, {1, 1}, {1, 0}, {0, -1}, {-1, 0}, {0, 1}};
    std::vector<Node> nodes{{gx, gy}};
    while (nodes.back() != Node{sx, sy}) {
        const auto [x, y] = nodes.back();
        const Cost here = cost.at({x, y});
        bool stepped = false;
        for (const auto& step : back) {
            const long px = x + step[0], py = y + step[1];
            const auto known = cost.find({px, py});
            if (known == cost.end() || !passable(px, py)) continue;
            if (step[0] && step[1] && (!passable(px, y) || !passable(x, py))) continue;
            if (!(known->second + (step[0] && step[1] ? Cost{0, 1} : Cost{1, 0}) == here)) continue;
            nodes.push_back({px, py});
            stepped = true;
            break;
        }
        if (!stepped) break;  // cannot happen with exact costs
    }
    std::reverse(nodes.begin(), nodes.end());
    std::vector<P2> raw;
    bool partial = false;
    for (std::size_t i = 1; i < nodes.size(); ++i) {
        if (!free_of(nodes[i].first, nodes[i].second, covering)) { partial = true; break; }
        raw.push_back({centre(nodes[i].first), centre(nodes[i].second)});
    }
    if (raw.empty()) {
        unit.route_.push_back(unit.target_);
        return;
    }
    std::vector<P2> route{raw.front()};
    for (std::size_t i = 0; i + 1 < raw.size();) {
        std::size_t j = raw.size() - 1;
        while (j > i + 1 && !visible(raw[i], raw[j], blocks)) --j;
        route.push_back(raw[j]);
        i = j;
    }
    for (const auto& w : route) unit.route_.push_back({static_cast<float>(w.x), static_cast<float>(w.y)});
    if (!partial) unit.route_.back() = unit.target_;
    unit.route_partial_ = partial;
}
// True when another unit lies within block_radius of the next block_lookahead of the
// path, and is (or, if moving, soon will be) within block_lateral of the path line.
bool World::blocked_by(const Unit& unit, Vec2 direction, std::size_t& blocker) const {
    const auto& P = model_.pathing;
    const P2 p = p2(soft_position(unit));
    const double dx = direction.x, dy = direction.y;
    for (std::size_t j = 0; j < units_.size(); ++j) {
        const auto& other = units_[j];
        if (&other == &unit) continue;
        const P2 q = p2(soft_position(other));
        const double rx = q.x - p.x, ry = q.y - p.y;
        const double along = rx * dx + ry * dy, perp = ry * dx - rx * dy;
        if (along <= 0) continue;
        const double beyond = along > P.block_lookahead ? along - P.block_lookahead : 0;
        if (std::sqrt(beyond * beyond + perp * perp) >= P.block_radius) continue;
        // A moving unit's distance from the path line, the nearer of now and after the
        // time this unit needs to cover the lookahead (0 if it crosses the line by then).
        double lateral = std::abs(perp);
        if (moving(other)) {
            const double vx = sf::value(other.soft_.vx), vy = sf::value(other.soft_.vy);
            const double later = perp + (vy * dx - vx * dy) * P.block_lookahead / sf::value(unit.soft_.speed);
            lateral = (perp > 0) != (later > 0) ? 0 : std::min(lateral, std::abs(later));
        }
        if (lateral < P.block_lateral) {
            blocker = j;
            return true;
        }
    }
    return false;
}
// Per update, before steering: advance waypoints, wait for or route around units in
// the way, and point the soft-float target at the current waypoint. True holds the
// unit in place this update.
bool World::route(std::size_t id) {
    auto& unit = units_[id];
    auto& s = unit.soft_;
    const auto& P = model_.pathing;
    if (unit.route_.empty()) plan(id);
    auto point = [&] { return p2(soft_position(unit)); };
    // At the end of a partial route the unit replans at once and holds for this update,
    // already steering toward the new route (MOV-0018-b's u1).
    bool hold = false;
    for (;;) {
        while (unit.route_index_ + 1 < unit.route_.size()
               && distance(point(), p2(unit.route_[unit.route_index_])) <= P.waypoint_radius)
            ++unit.route_index_;
        if (hold || !unit.route_partial_ || unit.route_index_ + 1 != unit.route_.size()
            || distance(point(), p2(unit.route_.back())) > P.waypoint_radius)
            break;
        plan(id);
        hold = true;
    }
    const Vec2 waypoint = unit.route_[unit.route_index_];
    const sf::F origin = sf::bits(model_.heading.frame_origin);
    s.target_x = sf::sub(sf::bits(waypoint.x), origin);
    s.target_y = sf::sub(sf::bits(waypoint.y), origin);
    if (hold) return true;
    const double to_x = waypoint.x - point().x, to_y = waypoint.y - point().y;
    const double length = std::sqrt(to_x * to_x + to_y * to_y);
    if (length <= model_.stop_radius) return false;  // arrival is the movement code's
    const Vec2 direction{static_cast<float>(to_x / length), static_cast<float>(to_y / length)};
    std::size_t blocker = 0;
    if (unit.waiting_) {
        ++unit.wait_updates_;
        if (!moving(units_[unit.blocker_])) {
            plan(id);  // the unit in the way has stopped: route around it
            return route(id);
        }
        if (unit.wait_updates_ % P.recheck_updates) return true;
        if (blocked_by(unit, direction, blocker)) {
            unit.blocker_ = blocker;
            return true;
        }
        unit.waiting_ = false;
        return false;
    }
    if (blocked_by(unit, direction, blocker)) {
        unit.waiting_ = true;
        unit.wait_updates_ = 0;
        unit.blocker_ = blocker;
        return true;
    }
    return false;
}
}

