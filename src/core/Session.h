#pragma once
// The command boundary between player input and the World (docs/client-v1.md).
// Live input and replay both schedule commands here, and advance_frame() is the
// only place a command reaches the World. No clock, file, window or renderer APIs.
#include "core/World.h"
#include <cstdint>
#include <string>
#include <string_view>
#include <vector>

namespace wc3 {
struct Command {
    std::uint64_t time_us = 0;   // simulation time; applied before the frame starting here
    std::uint64_t sequence = 0;  // strictly increasing; orders commands at equal times
    std::size_t unit = 0;        // entity ID: index in creation order
    std::uint32_t order = order_none;  // order_move or order_stop
    Vec2 target;                 // order_move only
};
struct Recording {
    std::string scene;
    std::uint32_t seed = 1;
    std::vector<Command> commands;
    std::uint64_t end_us = 0;    // simulation time the session reached
};
// Throws std::invalid_argument for malformed text; serialize(parse(t)) == t.
Recording parse_recording(std::string_view text);
std::string serialize(const Recording& recording);
std::string serialize(const Command& command);

// The flat placeholder scene: footman-v4 Footmen on the 64x64 oracle map.
inline constexpr const char* scene_name = "flat-footmen-3";
inline constexpr float map_extent = 4096.0f;  // targets lie in [-extent, extent]

class Session {
public:
    explicit Session(std::uint32_t seed = 1);
    const World& world() const { return world_; }
    std::uint64_t time_us() const;
    // Frames are the movement exposure period (5 ms for footman-v4); commands
    // apply only between frames, as the scenario runner issues orders.
    std::uint64_t frame_us() const;
    // Live input: stamps the current time and the next sequence, then schedules.
    Command submit(std::size_t unit, std::uint32_t order, Vec2 target = {});
    // Replay or live: queue a command for its time. Times must lie on a frame
    // boundary not yet simulated; sequences must increase. Throws otherwise.
    void schedule(const Command& command);
    // Applies the commands due now in sequence order, then simulates one frame.
    void advance_frame();
    // Commands applied so far, in application order, with the World's acceptance.
    const std::vector<Command>& applied() const { return applied_; }
    const std::vector<bool>& accepted() const { return accepted_; }
    std::size_t pending() const { return pending_.size() - next_; }
    Recording recording() const;
private:
    World world_;
    std::uint32_t seed_;
    std::vector<Command> pending_;  // in (time, sequence) order
    std::size_t next_ = 0;
    std::uint64_t next_sequence_ = 1;
    std::vector<Command> applied_;
    std::vector<bool> accepted_;
};
}
