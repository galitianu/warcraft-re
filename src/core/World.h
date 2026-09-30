#pragma once
#include "core/Random.h"
#include <cstddef>
#include <cstdint>
#include <vector>

namespace wc3 {
inline constexpr std::uint32_t order_none = 0;
inline constexpr std::uint32_t order_move = 851986;
inline constexpr std::uint32_t order_stop = 851972;
struct Vec2 { float x = 0; float y = 0; };
enum class ModelVersion { v1, v2 };
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
};

// Simulation owns state and seeded randomness. No clock, file or renderer APIs.
class World {
public:
    explicit World(ModelVersion version, std::uint32_t seed = 1);
    std::size_t create_footman(Vec2 position, float facing);
    const Unit& unit(std::size_t id) const { return units_.at(id); }
    std::size_t unit_count() const { return units_.size(); }
    void set_move_speed(std::size_t id, float requested);
    bool issue_point_order(std::size_t id, std::uint32_t order, Vec2 target);
    bool issue_immediate_order(std::size_t id, std::uint32_t order);
    void step();
    std::uint64_t steps() const { return steps_; }
    const Model& parameters() const { return model_; }
    Random& random() { return random_; }
private:
    Model model_;
    Random random_;
    std::vector<Unit> units_;
    std::uint64_t steps_ = 0;
};
}
