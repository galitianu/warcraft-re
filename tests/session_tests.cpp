// Command/session boundary (docs/client-v1.md): equal-time ordering, live versus
// replay equivalence, validation, pacing and presentation isolation.
#include "client/View.h"
#include <cmath>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
void check(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error(message);
}
template <class F> void rejects(F&& f, const std::string& message) {
    try {
        f();
    } catch (const std::invalid_argument&) {
        return;
    }
    throw std::runtime_error("accepted: " + message);
}
void advance(wc3::Session& s, int frames) {
    for (int i = 0; i < frames; ++i) s.advance_frame();
}
bool same(wc3::Vec2 a, wc3::Vec2 b) { return a.x == b.x && a.y == b.y; }
using client::RouteState;
// A route view must be the unit's position followed by the world's waypoints from the cursor.
void copies_plan(const wc3::Session& s, std::size_t id, const client::RouteView& v, const std::string& what) {
    const auto& u = s.world().unit(id);
    check(v.state == RouteState::planned || v.state == RouteState::partial, what + ": not a computed route");
    check(v.points.size() == u.route().size() - u.route_index() + 1 && same(v.points[0], u.position()),
          what + ": route view does not start at the unit");
    for (std::size_t i = 1; i < v.points.size(); ++i)
        check(same(v.points[i], u.route()[u.route_index() + i - 1]), what + ": waypoint order");
}
// Advances until the unit's route view leaves `state`, at most `limit` frames.
client::RouteView advance_while(wc3::Session& s, std::size_t id, RouteState state, int limit) {
    for (int i = 0; i < limit; ++i) {
        s.advance_frame();
        if (const auto v = client::route_view(s, id); v.state != state) return v;
    }
    throw std::runtime_error("route state did not change");
}
client::Ray ray_at(const client::Camera& camera, wc3::Vec2 p, float z) {
    const auto eye = camera.eye();
    return {eye, {p.x - eye.x, p.y - eye.y, z - eye.z}};
}
}

int main() {
    try {
        // Portable full RNG identity, including a consumed stream and copies.
        // Pin the standard mt19937 outputs; snapshots must detect RNG draws even
        // when no unit state changes.
        {
            wc3::Random random(1);
            check(random.state() == "mt19937 seed=1 draws=0", "initial RNG identity");
            check(random.next() == 1791095845u, "mt19937 first output");
            check(random.state() == "mt19937 seed=1 draws=1", "consumed RNG identity");
            auto copy = random;
            check(copy.next() == random.next() && random.next() == 3093770124u, "copied RNG stream");
            check(copy.state() == "mt19937 seed=1 draws=2", "independent copy draw count");
            wc3::World world(wc3::ModelVersion::v4, 1);
            const auto before = world.snapshot();
            world.random().next();
            check(world.snapshot() != before, "snapshot ignores RNG consumption");
        }
        // Equal time: the later sequence wins. Move then stop leaves the unit idle where it stood.
        {
            wc3::Session s;
            const auto start = s.world().unit(1).position();
            advance(s, 10);
            const auto move = s.submit(1, wc3::order_move, {0, 600});
            const auto stop = s.submit(1, wc3::order_stop);
            check(move.time_us == stop.time_us && move.time_us == 50000, "equal-time stamps");
            check(stop.sequence == move.sequence + 1, "sequence order");
            advance(s, 400);
            check(s.applied().size() == 2 && s.accepted() == std::vector<bool>{true, true}, "both applied");
            check(s.applied()[0].sequence == move.sequence, "move applied first");
            check(s.world().unit(1).current_order() == wc3::order_none, "move+stop ends idle");
            check(same(s.world().unit(1).position(), start), "move+stop did not move");
        }
        // Stop then move at the same time: the unit leaves.
        {
            wc3::Session s;
            advance(s, 10);
            s.submit(1, wc3::order_stop);
            s.submit(1, wc3::order_move, {0, 600});
            advance(s, 200);
            check(s.world().unit(1).current_order() == wc3::order_move, "stop+move still moving at 1 s");
            check(s.world().unit(1).position().y > 100, "stop+move moved north");
        }
        // Live submission and replay of its recording reach identical snapshots every frame.
        {
            wc3::Session live;
            std::vector<std::string> snapshots{live.world().snapshot()};
            for (int frame = 0; frame < 700; ++frame) {
                if (frame == 3) live.submit(0, wc3::order_move, {-192, 400});
                if (frame == 3) live.submit(2, wc3::order_move, {-192, 400});
                if (frame == 90) live.submit(0, wc3::order_stop);
                if (frame == 140) {
                    live.submit(2, wc3::order_move, {300.5f, -250.25f});
                    live.submit(2, wc3::order_stop);
                    live.submit(1, wc3::order_stop);
                    live.submit(1, wc3::order_move, {-400, -400});
                }
                live.advance_frame();
                snapshots.push_back(live.world().snapshot());
            }
            const auto recording = live.recording();
            const auto text = wc3::serialize(recording);
            check(wc3::serialize(wc3::parse_recording(text)) == text, "recording round trip");
            check(recording.end_us == 700 * live.frame_us() && recording.commands.size() == 7, "recording contents");
            wc3::Session replay(recording.seed);
            for (const auto& c : wc3::parse_recording(text).commands) replay.schedule(c);
            check(replay.world().snapshot() == snapshots[0], "initial snapshot");
            for (std::size_t frame = 1; frame < snapshots.size(); ++frame) {
                replay.advance_frame();
                check(replay.world().snapshot() == snapshots[frame], "replay diverged at frame " + std::to_string(frame));
            }
            check(replay.accepted() == live.accepted(), "acceptance differs");
            check(live.world().unit(2).current_order() == wc3::order_none, "equal-time move+stop idle");
            check(live.world().unit(1).current_order() == wc3::order_move ||
                  !same(live.world().unit(1).position(), {0, 0}), "equal-time stop+move moved");
            check(snapshots[0] != snapshots.back(), "snapshot ignores motion");
        }
        // Validation: only future frame boundaries, increasing sequences, known units, on-map moves.
        {
            wc3::Session s;
            advance(s, 2);
            rejects([&] { s.schedule({5000, 1, 0, wc3::order_stop, {}}); }, "past time");
            rejects([&] { s.schedule({12000, 1, 0, wc3::order_stop, {}}); }, "mid-frame time");
            rejects([&] { s.schedule({10000, 1, 3, wc3::order_stop, {}}); }, "unknown unit");
            rejects([&] { s.schedule({10000, 1, 0, wc3::order_move, {5000, 0}}); }, "off-map target");
            rejects([&] { s.schedule({10000, 1, 0, wc3::order_stop, {1, 0}}); }, "stop with target");
            rejects([&] { s.schedule({10000, 1, 0, 1234, {}}); }, "unknown order");
            s.schedule({20000, 5, 0, wc3::order_stop, {}});
            rejects([&] { s.schedule({25000, 5, 0, wc3::order_stop, {}}); }, "repeated sequence");
            rejects([&] { s.schedule({15000, 6, 0, wc3::order_stop, {}}); }, "time before a scheduled command");
            check(s.pending() == 1, "pending count");
            rejects([] { wc3::parse_recording("wc3-command-recording 1\nscene other\n"); }, "unknown scene");
            rejects([] { wc3::parse_recording("wc3-command-recording 1\nscene flat-footmen-3\nmodel footman-v4\n"
                                              "seed 1\nframe_us 5000\ncommand 0 1 0 move 0x0 0x0\nend 0\n"); },
                    "short float bits");
            rejects([] { wc3::parse_recording("wc3-command-recording 1\nscene flat-footmen-3\nmodel footman-v4\n"
                                              "seed 1\nframe_us 5000\nend 7\n"); }, "end off a frame");
        }
        // Pacing: whole frames, remainder carried, stalls capped and dropped.
        {
            client::Pacer p{5000};
            check(p.frames_for(4999) == 0 && p.frames_for(1) == 1 && p.carry_us == 0, "carry");
            check(p.frames_for(16667) == 3 && p.carry_us == 1667, "60 Hz");
            check(p.frames_for(1000000) == 20 && p.carry_us == 0, "stall cap");
        }
        // Presentation reads: camera, picking, selection and views leave the world unchanged.
        {
            wc3::Session s;
            client::Camera camera;
            client::Controller controller;
            const auto before = s.world().snapshot();
            const auto eye = camera.eye();
            const client::Ray at_unit2{eye, {192 - eye.x, 0 - eye.y, client::unit_height / 2 - eye.z}};
            controller.left_click(s.world(), at_unit2);
            check(controller.selected() == std::size_t{2}, "picked unit 2");
            camera.pan(500, 0);
            camera.zoom(3);
            check(client::unit_views(s, controller)[2].selected, "selection view");
            const client::Ray at_ground{eye, {600 - eye.x, 300 - eye.y, -eye.z}};
            controller.left_click(s.world(), at_ground);
            check(!controller.selected(), "ground click clears selection");
            check(!controller.right_click(s, at_ground) && !controller.stop(s), "no selection, no command");
            check(s.world().snapshot() == before && s.pending() == 0, "presentation mutated the world");
            controller.left_click(s.world(), at_unit2);
            const auto c = controller.right_click(s, at_ground);
            check(c && c->unit == 2 && c->order == wc3::order_move && std::abs(c->target.x - 600) < 0.1f &&
                  std::abs(c->target.y - 300) < 0.1f, "right-click moves the selected unit to the ground point");
        }
        // Route views (docs/client-route.md): idle and pending states show no path.
        {
            wc3::Session s;
            for (std::size_t id = 0; id < 3; ++id)
                check(client::route_view(s, id).state == RouteState::none && client::route_view(s, id).points.empty(),
                      "idle units have no route");
            advance(s, 10);
            s.submit(0, wc3::order_move, {96, 0});
            check(client::route_view(s, 0).state == RouteState::pending && client::route_view(s, 0).points.empty(),
                  "an unapplied move is pending, not a path");
            check(client::route_view(s, 1).state == RouteState::none, "pending is per unit");
            s.advance_frame();
            check(s.world().unit(0).current_order() == wc3::order_move && s.world().unit(0).route().empty() &&
                  client::route_view(s, 0).state == RouteState::pending, "an applied move awaiting its plan is pending");
            // A detour around the idle Footman 1 at the origin, ending at the target (Footman 2 idles at x = 192).
            const auto v = advance_while(s, 0, RouteState::pending, 20);
            copies_plan(s, 0, v, "detour");
            check(v.state == RouteState::planned && same(v.points.back(), {96, 0}) && v.points.size() > 3,
                  "detour reaches the target through waypoints");
            for (std::size_t i = 1; i + 1 < v.points.size(); ++i)
                check(std::hypot(v.points[i].x, v.points[i].y) >= 32, "detour waypoint inside the blocker");
            // Repeated construction reads only.
            const auto before = s.world().snapshot();
            for (int i = 0; i < 100; ++i) client::route_view(s, i % 3);
            check(s.world().snapshot() == before, "route view construction changed the world");
            // While the plan stands, the remaining waypoints only shrink from the front.
            auto previous = v;
            int advanced = 0;
            for (int frame = 0; frame < 60; ++frame) {
                s.advance_frame();
                const auto now = client::route_view(s, 0);
                if (now.state != RouteState::planned) break;
                copies_plan(s, 0, now, "detour frame " + std::to_string(frame));
                const auto offset = previous.points.size() - now.points.size();
                check(now.points.size() <= previous.points.size(), "remaining waypoints grew without a replan");
                for (std::size_t i = 1; i < now.points.size(); ++i)
                    check(same(now.points[i], previous.points[i + offset]), "remaining waypoints reordered");
                advanced += offset > 0;
                previous = now;
            }
            check(advanced > 0, "the route cursor never advanced");
            // A redirect never shows the stale route: pending until the new plan, which ends at the new target.
            s.submit(0, wc3::order_move, {-100, 400});
            check(client::route_view(s, 0).state == RouteState::pending, "redirect is pending before it applies");
            const auto redirected = advance_while(s, 0, RouteState::pending, 20);
            copies_plan(s, 0, redirected, "redirect");
            check(same(redirected.points.back(), {-100, 400}), "redirected route ends at the new target");
            // A stop clears it: pending until applied, then no route.
            s.submit(0, wc3::order_stop);
            check(client::route_view(s, 0).state == RouteState::pending, "unapplied stop hides the route");
            s.advance_frame();
            check(client::route_view(s, 0).state == RouteState::none && client::route_view(s, 0).points.empty(),
                  "stop clears the route");
        }
        // Arrival clears the route; deselection clears the selected-unit feedback while moving.
        {
            wc3::Session s;
            client::Camera camera;
            client::Controller controller;
            controller.left_click(s.world(), ray_at(camera, {192, 0}, client::unit_height / 2));
            check(controller.selected() == std::size_t{2}, "picked unit 2");
            s.submit(2, wc3::order_move, {450, 300});
            const auto straight = advance_while(s, 2, RouteState::pending, 20);
            check(straight.state == RouteState::planned && straight.points.size() == 2 &&
                  same(straight.points.back(), {450, 300}), "unobstructed move is a straight planned route");
            check(client::selected_route(s, controller).points.size() == 2, "selected route");
            controller.left_click(s.world(), ray_at(camera, {600, -300}, 0));
            check(!controller.selected() && client::selected_route(s, controller).state == RouteState::none,
                  "deselection clears route feedback");
            check(client::route_view(s, 2).state == RouteState::planned, "the unit still has its plan");
            const auto arrived = advance_while(s, 2, RouteState::planned, 1000);
            check(arrived.state == RouteState::none && s.world().unit(2).current_order() == wc3::order_none,
                  "arrival clears the route");
        }
        // A blocked target: the route is partial and ends where the plan ends, short of the target.
        {
            wc3::Session s;
            s.submit(0, wc3::order_move, {0, 0});  // onto the idle Footman 1
            const auto v = advance_while(s, 0, RouteState::pending, 20);
            copies_plan(s, 0, v, "partial");
            check(v.state == RouteState::partial && s.world().unit(0).route_partial(), "blocked target routes partially");
            check(!same(v.points.back(), {0, 0}) && std::hypot(v.points.back().x, v.points.back().y) >= 32,
                  "partial route ends short of the target");
            const auto line = client::serialize(s.time_us(), 0, v);
            check(line.rfind("route " + std::to_string(s.time_us()) + " 0 partial " + std::to_string(v.points.size()) + " 0x", 0) == 0,
                  "route line format");
        }
        std::cout << "session tests passed\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "session test failed: " << error.what() << '\n';
        return 1;
    }
}
