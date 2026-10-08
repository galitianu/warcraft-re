#include "client/View.h"
#include <algorithm>
#include <bit>
#include <cstdio>
#include <cmath>
#include <numbers>

namespace client {
std::uint64_t Pacer::frames_for(std::uint64_t elapsed_us) {
    // Paused renders, and the resume render's interval (spent paused), are dropped.
    if (paused || resuming) {
        resuming = false;
        return 0;
    }
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

namespace {
Vec3 sub(Vec3 a, Vec3 b) { return {a.x-b.x, a.y-b.y, a.z-b.z}; }
Vec3 mul(Vec3 a, float f) { return {a.x*f, a.y*f, a.z*f}; }
float dot(Vec3 a, Vec3 b) { return a.x*b.x+a.y*b.y+a.z*b.z; }
Vec3 cross(Vec3 a, Vec3 b) { return {a.y*b.z-a.z*b.y, a.z*b.x-a.x*b.z, a.x*b.y-a.y*b.x}; }
Vec3 normal(Vec3 a) { return mul(a, 1/std::sqrt(dot(a,a))); }
Vec3 forward(const Camera& c) { return normal(sub({c.target_x,c.target_y,0},c.eye())); }
}
Ray screen_ray(const Camera& c, ScreenPoint p, float width, float height) {
    const auto f = forward(c), r = normal(cross(f,{0,0,1})), u = cross(r,f);
    const float t = std::tan(c.fov_degrees * std::numbers::pi_v<float> / 360);
    const float x = (2*p.x/width-1)*t*width/height, y = (1-2*p.y/height)*t;
    return {c.eye(), {f.x+r.x*x+u.x*y, f.y+r.y*x+u.y*y, f.z+r.z*x+u.z*y}};
}
ScreenPoint project(const Camera& c, Vec3 p, float width, float height) {
    const auto f = forward(c), r = normal(cross(f,{0,0,1})), u = cross(r,f), v = sub(p,c.eye());
    const float t = std::tan(c.fov_degrees * std::numbers::pi_v<float> / 360), z = dot(v,f);
    return {width/2 + dot(v,r)*height/(2*t*z), height/2-dot(v,u)*height/(2*t*z)};
}
std::vector<std::size_t> box_pick(const wc3::World& world, const Camera& c,
    ScreenPoint a, ScreenPoint b, float width, float height) {
    const float l=std::min(a.x,b.x), r=std::max(a.x,b.x), t=std::min(a.y,b.y), d=std::max(a.y,b.y);
    // Exact sphere versus infinite selection frustum: distance to its interior,
    // face projections, edge rays and apex. This also rejects corner near misses.
    const Vec3 rays[]{screen_ray(c,{l,t},width,height).direction, screen_ray(c,{r,t},width,height).direction,
                      screen_ray(c,{r,d},width,height).direction, screen_ray(c,{l,d},width,height).direction};
    Vec3 planes[4];
    const auto middle=screen_ray(c,{(l+r)/2,(t+d)/2},width,height).direction;
    if (l == r || t == d) return {};
    for (int i=0;i<4;++i) {
        planes[i]=normal(cross(rays[i],rays[(i+1)%4]));
        if (dot(planes[i],middle)<0) planes[i]=mul(planes[i],-1);
    }
    const auto inside=[&](Vec3 v) {
        for (auto n:planes) if (dot(n,v)<-0.0001f) return false;
        return dot(v,middle)>=0;
    };
    std::vector<std::size_t> out;
    for (std::size_t id=0;id<world.unit_count();++id) {
        const auto p=world.unit(id).position();
        const auto v=sub({p.x,p.y,unit_height/2},c.eye());
        float distance=inside(v)?0:dot(v,v);
        for (auto n:planes) {
            const float signed_distance=dot(v,n);
            const auto on_plane=sub(v,mul(n,signed_distance));
            if (inside(on_plane)) distance=std::min(distance,signed_distance*signed_distance);
        }
        for (auto edge:rays) {
            const auto closest=mul(edge,std::max(0.0f,dot(v,edge)/dot(edge,edge)));
            const auto delta=sub(v,closest);
            distance=std::min(distance,dot(delta,delta));
        }
        if (distance<=pick_radius*pick_radius) out.push_back(id);
    }
    return out;
}
bool Controller::contains(std::size_t id) const { return std::binary_search(selected_.begin(),selected_.end(),id); }
void Controller::press(ScreenPoint p, bool shift) { anchor_=pointer_=p; pressed_=true; box_=false; shift_=shift; }
void Controller::motion(ScreenPoint p) {
    pointer_=p;
    if (pressed_ && std::hypot(p.x-anchor_.x,p.y-anchor_.y)>drag_threshold) box_=true;
}
void Controller::release(const wc3::World& world, const Camera& c, ScreenPoint p, float width, float height) {
    if (!pressed_) return;
    motion(p);
    if (box_) {
        const auto hits=box_pick(world,c,anchor_,p,width,height);
        if (!shift_) selected_.clear();
        selected_.insert(selected_.end(),hits.begin(),hits.end());
        std::sort(selected_.begin(),selected_.end());
        selected_.erase(std::unique(selected_.begin(),selected_.end()),selected_.end());
    } else left_click(world,screen_ray(c,p,width,height),shift_);
    pressed_=box_=false;
}
void Controller::left_click(const wc3::World& world, const Ray& ray, bool shift) {
    const auto hit=pick(world,ray);
    if (!shift) selected_.clear();
    if (!hit) return;
    const auto at=std::lower_bound(selected_.begin(),selected_.end(),*hit);
    if (at!=selected_.end() && *at==*hit) selected_.erase(at);
    else selected_.insert(at,*hit);
}
std::vector<wc3::Command> Controller::right_click(wc3::Session& session, const Ray& ray) {
    const auto point=ground(ray);
    std::vector<wc3::Command> commands;
    if (!point || !(std::abs(point->x)<=wc3::map_extent && std::abs(point->y)<=wc3::map_extent)) return commands;
    for (auto id:selected_) commands.push_back(session.submit(id,wc3::order_move,*point));
    return commands;
}
std::vector<wc3::Command> Controller::stop(wc3::Session& session) {
    std::vector<wc3::Command> commands;
    for (auto id:selected_) commands.push_back(session.submit(id,wc3::order_stop));
    return commands;
}

std::vector<UnitView> unit_views(const wc3::Session& session, const Controller& controller) {
    const auto& world = session.world();
    std::vector<UnitView> views;
    for (std::size_t id = 0; id < world.unit_count(); ++id) {
        const auto& unit = world.unit(id);
        UnitView view{id, unit.position(), unit.facing(), controller.contains(id), std::nullopt};
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

namespace {
std::string order_text(std::uint32_t order) {
    return order == wc3::order_move ? "move" : order == wc3::order_stop ? "stop" : "none";
}
std::string seconds(std::uint64_t us) {
    char text[32];
    std::snprintf(text, sizeof text, "%.3f s", us / 1e6);
    return text;
}
}
std::vector<std::string> diagnostics(const wc3::Session& session, const Controller& controller,
                                     const DiagnosticsInput& input) {
    std::vector<std::string> lines{"DIAGNOSTICS (F3 hides)"};
    lines.push_back("sim " + seconds(session.time_us()) + "  frame " + std::to_string(session.time_us() / session.frame_us()) +
                    " (5 ms)  " + (input.paused ? "PAUSED" : "running"));
    lines.push_back("render " + std::to_string(input.render_fps) + " fps (wall time only paces frames)");
    const auto submitted = session.recording().commands.size();
    lines.push_back("commands: submitted " + std::to_string(submitted) + ", applied " +
                    std::to_string(session.applied().size()) + ", pending " + std::to_string(session.pending()));
    lines.push_back("last: " + input.last_command);
    if (controller.selection().empty()) lines.push_back("selected: none");
    for (const auto id : controller.selection()) {
        const auto route = route_view(session, id);
        std::string line = "Footman " + std::to_string(id) + ": order " + order_text(session.world().unit(id).current_order()) +
                           ", route " + route_state_name(route.state);
        if (route.points.size() > 1) line += " (" + std::to_string(route.points.size() - 1) + " waypoints left)";
        if (route.state == RouteState::partial) line += ", ends short";
        if (session.pending_for(id)) line += ", command pending";
        lines.push_back(line);
    }
    lines.push_back("Group orders give every unit the same point: WC3 assignment and");
    lines.push_back("formations are unmeasured (likely P3); no formation compatibility.");
    return lines;
}
std::string pending_summary(const wc3::Session& session) {
    const auto n = session.pending();
    if (n == 0) return "no orders queued";
    return std::to_string(n) + (n == 1 ? " order" : " orders") + " queued; applied on resume";
}
std::string observation(const std::string& name, std::uint64_t render_frame, bool paused,
                        const wc3::Session& session, const std::string& snapshot_sha256) {
    return "observe " + name + ' ' + std::to_string(render_frame) + ' ' + (paused ? "paused" : "running") + ' ' +
           std::to_string(session.time_us()) + ' ' + std::to_string(session.recording().commands.size()) + ' ' +
           std::to_string(session.applied().size()) + ' ' + std::to_string(session.pending()) + ' ' + snapshot_sha256;
}
}
