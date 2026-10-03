#pragma once
#include "core/Random.h"
#include "core/SoftFloat.h"
#include <cstddef>
#include <cstdint>
#include <vector>

namespace wc3 {
inline constexpr std::uint32_t order_none = 0;
inline constexpr std::uint32_t order_move = 851986;
inline constexpr std::uint32_t order_stop = 851972;
struct Vec2 { float x = 0; float y = 0; };
enum class ModelVersion { v1, v2, v3, v4 };
// footman-v3 only: hidden movement heading, globally phased logical updates and
// round-toward-zero float32 state. Hypotheses: docs/footman-v3-model.md.
struct HeadingModel {
    bool enabled = false;
    std::uint32_t update_period_steps = 30;
    std::uint32_t update_phase_steps = 10;
    // Reported position moves toward the update's result in equal exposures.
    std::uint32_t exposure_period_steps = 5;
    float turn_rate_radians = 0.6f;
    // Movement waits while the pre-turn heading error exceeds this window.
    float propulsion_window_degrees = 60.0f;
    float facing_acceleration_radians = 0.07f;
    float facing_max_velocity_radians = 0.2f;
    float facing_snap_radians = 0.001f;
    // Positions are stored relative to the map's minimum corner (64x64 oracle map).
    float frame_origin = -4096.0f;
    // footman-v4: movement clock at step 0 (float32 bits, 0.5 s). The fixtures
    // admit roughly 0.496-0.505 s; the clock's binade sets each frame's truncation.
    std::uint32_t clock_start = 0x3f000000;
};
// footman-v4 unit pathing (MOV-0018, docs/mov-0018.md). Distances are world units,
// fitted to four two-Footman captures; see the document for each constant's interval.
struct UnitPathing {
    bool enabled = false;
    float cell = 32.0f;               // planning lattice: cell centres at 16 + 32k; another
                                      // unit blocks the 3x3 cells around the cell it is in
    float line_clearance = 4.0f;      // a direct line or smoothed segment keeps this from blocked cells
    float waypoint_radius = 16.0f;    // advance to the next waypoint within this distance
    float block_radius = 62.0f;       // another unit this close to the path just ahead blocks
    float block_lookahead = 32.0f;    // length of that path segment
    float block_lateral = 40.0f;      // ...if it is, or soon will be, this close to the path line
    std::uint32_t recheck_updates = 5;  // a unit waiting for a moving unit retests this often
    std::uint32_t give_way_updates = 20;  // a unit another routes around holds this long
};
// Every behavioral difference between versions is one of these parameters.
struct Model {
    const char* name;
    std::uint32_t step_us = 1000;
    std::uint32_t position_period_steps;
    std::uint32_t facing_period_steps;
    std::uint32_t facing_phase_steps;
    std::uint32_t move_delay_steps;
    float stop_radius = 16.0f;
    float default_speed = 270.0f;
    float min_speed = 150.0f;
    float max_speed = 400.0f;
    // Movement waits while facing is further than this from travel; 180 never waits.
    float movement_angle_limit = 135.0f;
    // Per facing update: first, second, later. Infinite turns the whole remaining angle.
    float turn_ramp_radians[3] = {0.07f, 0.14f, 0.2f};
    // Directions within this of exactly opposite take the clockwise tie (-180).
    float opposite_tie_degrees = 0.0001f;
    HeadingModel heading;
    // footman-v4: retail soft-float movement (docs/footman-v4-model.md). Uses the
    // heading block's cadence and frame origin; arithmetic is wc3::sf throughout.
    bool soft_float = false;
    UnitPathing pathing;
};
Model model(ModelVersion version);

class World;
class Unit {
public:
    Vec2 position() const { return position_; }
    float facing() const { return facing_; }
    float move_speed() const { return speed_; }
    std::uint32_t current_order() const { return order_; }
private:
    friend class World;
    Vec2 position_;
    Vec2 target_;
    float facing_ = 0;
    float speed_ = 0;
    std::uint32_t order_ = order_none;
    std::uint64_t command_step_ = 0;
    std::uint32_t turn_updates_ = 0;
    // footman-v3: float32 radians in [0, 2pi); velocity is signed radians per update.
    float facing_radians_ = 0;
    float heading_radians_ = 0;
    float facing_velocity_ = 0;
    bool batch_active_ = false;
    std::uint64_t batch_step_ = 0;
    Vec2 batch_start_;
    Vec2 batch_end_;
    // footman-v4 state, float32 bit patterns in the map-corner frame.
    struct Soft {
        sf::F x = 0, y = 0;             // integrated position
        sf::F vx = 0, vy = 0;           // velocity, units per second
        sf::F heading = 0;              // stored heading [0, 2pi), used while not moving
        sf::F facing = 0;               // reported facing, radians
        sf::F facing_velocity = 0;      // radians per update
        sf::F facing_target = 0;
        sf::F target_x = 0, target_y = 0;
        sf::F speed = 0;
        std::uint64_t integrated_step = 0;  // velocity applies from here
        bool settle = false;            // stop processing due at the next update
    } soft_;
    // Unit pathing: the planned route to the order target, followed waypoint by waypoint.
    std::vector<Vec2> route_;
    std::size_t route_index_ = 0;
    bool route_partial_ = false;     // ends short of a blocked target; replan on arrival
    bool waiting_ = false;           // halted by another unit on the path ahead
    bool yielding_ = false;          // held for a moving unit on its left; route around it next
    std::uint32_t given_way_ = 0;    // updates still to hold for a unit routing around it
    std::uint64_t given_way_step_ = 0;  // the step at which that hold was imposed
    std::uint32_t wait_updates_ = 0;
    std::size_t blocker_ = 0;
};

// Simulation owns state and seeded randomness. No clock, file or renderer APIs.
class World {
public:
    explicit World(ModelVersion version, std::uint32_t seed = 1);
    // Explicit parameters, for predictions under candidate values (tools/wc3pathing).
    explicit World(const Model& parameters, std::uint32_t seed = 1);
    std::size_t create_footman(Vec2 position, float facing);
    const Unit& unit(std::size_t id) const { return units_.at(id); }
    std::size_t unit_count() const { return units_.size(); }
    void set_move_speed(std::size_t id, float requested);
    bool issue_point_order(std::size_t id, std::uint32_t order, Vec2 target);
    bool issue_immediate_order(std::size_t id, std::uint32_t order);
    void step();
    std::uint64_t steps() const { return steps_; }
    const Model& parameters() const { return model_; }
    // footman-v4: the movement clock at a 5 ms frame (frame 0 is clock_start).
    sf::F frame_clock(std::uint64_t frame) const { return clock_at(frame); }
    Random& random() { return random_; }
private:
    void step_heading();
    void step_soft();
    void soft_integrate(Unit& unit) const;
    void soft_expose(Unit& unit) const;
    void soft_halt(Unit& unit) const;
    Vec2 soft_position(const Unit& unit) const;
    bool moving(const Unit& unit) const;
    void plan(std::size_t id);
    bool route(std::size_t id);
    bool blocked_by(const Unit& unit, Vec2 direction, std::size_t& blocker) const;
    sf::F clock_at(std::uint64_t frame) const;
    sf::F frames_to_seconds(std::uint64_t from_step, std::uint64_t to_step) const;
    mutable std::vector<sf::F> clock_;
    Model model_;
    Random random_;
    std::vector<Unit> units_;
    std::uint64_t steps_ = 0;
};
}
