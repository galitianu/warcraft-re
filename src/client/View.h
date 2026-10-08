#pragma once
// Client-side state that never touches the simulation (docs/client-v1.md): wall-time
// pacing, camera, picking and selection. Everything here reads a const World or
// Session; only Session::submit/advance_frame change gameplay. No raylib types,
// so the headless replay check drives exactly this code.
#include "core/Session.h"
#include <cstdint>
#include <optional>
#include <string>
#include <vector>

namespace client {
// Converts elapsed wall time into whole simulation frames. Wall time only decides
// how much work to do now; the simulation clock advances in frames of frame_us.
struct Pacer {
    std::uint64_t frame_us;
    // A stalled render (window drag, breakpoint) simulates at most this many frames
    // and drops the rest of its wall time, so the game slows instead of jumping.
    std::uint64_t max_frames = 20;
    std::uint64_t carry_us = 0;
    std::uint64_t frames_for(std::uint64_t elapsed_us);
};

// Replay checks and the live client record World::snapshot digests at multiples of this.
inline constexpr std::uint64_t checkpoint_us = 1000000;

struct Vec3 { float x = 0, y = 0, z = 0; };  // WC3 axes: x east, y north, z up
struct Ray { Vec3 origin, direction; };

// A WC3-like perspective camera looking north and down at a ground target.
struct Camera {
    float target_x = 0, target_y = 0;
    float distance = 1100;           // eye distance from the target
    float pitch_degrees = 56;        // below the horizon
    float fov_degrees = 70;
    void pan(float dx, float dy);    // world units
    void zoom(float wheel);          // positive zooms in
    Vec3 eye() const;
};

inline constexpr float unit_radius = 16;   // half a Footman's 32-unit footprint
inline constexpr float unit_height = 72;
inline constexpr float pick_radius = 36;   // generous click target around the body

// The nearest unit whose pick volume the ray hits, if any.
std::optional<std::size_t> pick(const wc3::World& world, const Ray& ray);
// Where the ray meets flat ground (z = 0), if it points down.
std::optional<wc3::Vec2> ground(const Ray& ray);

// Single-unit selection and the player's orders. Owns no simulation state.
class Controller {
public:
    std::optional<std::size_t> selected() const { return selected_; }
    void left_click(const wc3::World& world, const Ray& ray);
    // Right-click and stop issue a command for the selected unit, if any.
    std::optional<wc3::Command> right_click(wc3::Session& session, const Ray& ray);
    std::optional<wc3::Command> stop(wc3::Session& session);
private:
    std::optional<std::size_t> selected_;
};

// What the renderer draws for each unit, read from the session after a frame.
struct UnitView {
    std::size_t id;
    wc3::Vec2 position;
    float facing_degrees;
    bool selected;
    std::optional<wc3::Vec2> destination;  // the applied move order still being carried out
};
std::vector<UnitView> unit_views(const wc3::Session& session, const Controller& controller);

// A unit's current computed route (docs/client-route.md), copied from the world's
// existing plan. Building it never plans, steps or changes route state. The plan may
// change as blockers move; it does not promise where the unit will actually walk.
enum class RouteState {
    none,     // no move order being carried out (idle, stopped, arrived)
    pending,  // a command is due but unapplied, or the move has no plan yet
    planned,  // the route reaches the order target
    partial,  // the route ends short of a blocked target, where the plan ends
};
struct RouteView {
    RouteState state = RouteState::none;
    // planned/partial: the unit's displayed position, then the remaining waypoints
    // from the route cursor in traversal order; empty otherwise.
    std::vector<wc3::Vec2> points;
};
RouteView route_view(const wc3::Session& session, std::size_t unit);
// The selected unit's route; none without a selection.
RouteView selected_route(const wc3::Session& session, const Controller& controller);
const char* route_state_name(RouteState state);
// One canonical line, "route TIME_US UNIT STATE N X Y ..." with float32 bits and a
// decimal comment, so a route shown live can be compared exactly with a replay.
std::string serialize(std::uint64_t time_us, std::size_t unit, const RouteView& route);
}
