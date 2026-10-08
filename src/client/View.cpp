#include "client/View.h"
#include <algorithm>
#include <bit>
#include <cstdio>
#include <cmath>
#include <numbers>

namespace client {
std::uint64_t Pacer::frames_for(std::uint64_t elapsed_us) {
    carry_us += elapsed_us;
    const auto frames = std::min(carry_us / frame_us, max_frames);
    carry_us = frames == max_frames ? 0 : carry_us - frames * frame_us;
    return frames;
}

void Camera::pan(float dx, float dy) {
    target_x = std::clamp(target_x + dx, -wc3::map_extent, wc3::map_extent);
    target_y = std::clamp(target_y + dy, -wc3::map_extent, wc3::map_extent);
}
void Camera::zoom(float wheel) {
    distance = std::clamp(distance * std::pow(0.9f, wheel), 400.0f, 4000.0f);
}
Vec3 Camera::eye() const {
    const float pitch = pitch_degrees * std::numbers::pi_v<float> / 180;
    return {target_x, target_y - distance * std::cos(pitch), distance * std::sin(pitch)};
}

std::optional<std::size_t> pick(const wc3::World& world, const Ray& ray) {
    std::optional<std::size_t> best;
    float nearest = INFINITY;
    const auto& d = ray.direction;
    const float dd = d.x * d.x + d.y * d.y + d.z * d.z;
    for (std::size_t id = 0; id < world.unit_count(); ++id) {
        const auto p = world.unit(id).position();
        // Sphere at the body's centre: |o + t d - c|^2 = r^2.
        const Vec3 m{ray.origin.x - p.x, ray.origin.y - p.y, ray.origin.z - unit_height / 2};
        const float b = m.x * d.x + m.y * d.y + m.z * d.z;
        const float c = m.x * m.x + m.y * m.y + m.z * m.z - pick_radius * pick_radius;
        const float disc = b * b - dd * c;
        if (disc < 0) continue;
        const float t = (-b - std::sqrt(disc)) / dd;
        if (t >= 0 && t < nearest) nearest = t, best = id;
    }
    return best;
}
std::optional<wc3::Vec2> ground(const Ray& ray) {
    if (!(ray.direction.z < 0)) return std::nullopt;
    const float t = -ray.origin.z / ray.direction.z;
    return wc3::Vec2{ray.origin.x + t * ray.direction.x, ray.origin.y + t * ray.direction.y};
}

void Controller::left_click(const wc3::World& world, const Ray& ray) {
    selected_ = pick(world, ray);  // empty ground clears the selection
}
std::optional<wc3::Command> Controller::right_click(wc3::Session& session, const Ray& ray) {
    const auto point = ground(ray);
    if (!selected_ || !point || !(std::abs(point->x) <= wc3::map_extent && std::abs(point->y) <= wc3::map_extent))
        return std::nullopt;
    return session.submit(*selected_, wc3::order_move, *point);
}
std::optional<wc3::Command> Controller::stop(wc3::Session& session) {
    if (!selected_) return std::nullopt;
    return session.submit(*selected_, wc3::order_stop);
}

std::vector<UnitView> unit_views(const wc3::Session& session, const Controller& controller) {
    const auto& world = session.world();
    std::vector<UnitView> views;
    for (std::size_t id = 0; id < world.unit_count(); ++id) {
        const auto& unit = world.unit(id);
        UnitView view{id, unit.position(), unit.facing(), controller.selected() == id, std::nullopt};
        if (unit.current_order() == wc3::order_move) {
            const auto& applied = session.applied();
            for (auto c = applied.rbegin(); c != applied.rend(); ++c)
                if (c->unit == id) {
                    if (c->order == wc3::order_move) view.destination = c->target;
                    break;
                }
        }
        views.push_back(view);
    }
    return views;
}

RouteView route_view(const wc3::Session& session, std::size_t id) {
    const auto& unit = session.world().unit(id);
    // An unapplied command makes any current plan stale; a move not yet planned
    // (the plan comes at the unit's next update) has no computed path to show.
    if (session.pending_for(id)) return {RouteState::pending, {}};
    if (unit.current_order() != wc3::order_move) return {};
    const auto& route = unit.route();
    if (unit.route_index() >= route.size()) return {RouteState::pending, {}};
    RouteView view{unit.route_partial() ? RouteState::partial : RouteState::planned, {unit.position()}};
    view.points.insert(view.points.end(), route.begin() + static_cast<std::ptrdiff_t>(unit.route_index()), route.end());
    return view;
}
RouteView selected_route(const wc3::Session& session, const Controller& controller) {
    return controller.selected() ? route_view(session, *controller.selected()) : RouteView{};
}
const char* route_state_name(RouteState state) {
    switch (state) {
    case RouteState::pending: return "pending";
    case RouteState::planned: return "planned";
    case RouteState::partial: return "partial";
    default: return "none";
    }
}
std::string serialize(std::uint64_t time_us, std::size_t unit, const RouteView& route) {
    std::string out = "route " + std::to_string(time_us) + ' ' + std::to_string(unit) + ' ' +
                      route_state_name(route.state) + ' ' + std::to_string(route.points.size());
    std::string comment;
    for (const auto& p : route.points) {
        char text[64];
        std::snprintf(text, sizeof text, " 0x%08x 0x%08x", std::bit_cast<std::uint32_t>(p.x), std::bit_cast<std::uint32_t>(p.y));
        out += text;
        std::snprintf(text, sizeof text, " (%.9g, %.9g)", p.x, p.y);
        comment += text;
    }
    return comment.empty() ? out : out + " #" + comment;
}
}
