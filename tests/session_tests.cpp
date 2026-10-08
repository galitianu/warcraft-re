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
        std::cout << "session tests passed\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "session test failed: " << error.what() << '\n';
        return 1;
    }
}
