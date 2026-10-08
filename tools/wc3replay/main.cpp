// Replays a command recording headlessly and under named render schedules, and
// compares exact world state at identical simulation checkpoints (docs/client-v1.md).
// Usage: wc3replay RECORDING [--live CHECKPOINTS] [--routes ROUTES] [--json REPORT]
// Exit 0: every schedule (and the live client's checkpoints and displayed routes,
// when given) matches the headless replay; 1: a difference; 2: invalid input.
#include "Scenario.h"
#include "client/View.h"
#include <fstream>
#include <functional>
#include <iostream>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
using Checkpoints = std::map<std::uint64_t, std::string>;  // time_us -> sha256 of World::snapshot
std::string read(const std::string& path) {
    std::ifstream file(path, std::ios::binary);
    std::ostringstream bytes;
    bytes << file.rdbuf();
    if (!file) throw std::invalid_argument("cannot read " + path);
    return bytes.str();
}
std::string digest(const wc3::Session& session) { return scenario::sha256_hex(session.world().snapshot()); }
struct Run {
    std::string name;
    std::string description;
    Checkpoints checkpoints;
    std::uint64_t render_frames = 0;
    std::uint64_t sim_frames = 0;
    std::uint64_t presentation_checks = 0;
    std::map<client::RouteState, std::uint64_t> route_views;  // per unit per render frame
    std::vector<wc3::Command> applied;
    std::vector<bool> accepted;
};
// Simulates one frame through the shared session path and records checkpoints.
void frame(wc3::Session& session, Run& run) {
    session.advance_frame();
    ++run.sim_frames;
    if (session.time_us() % client::checkpoint_us == 0) run.checkpoints[session.time_us()] = digest(session);
}
wc3::Session start(const wc3::Recording& recording, Run& run) {
    wc3::Session session(recording.seed);
    for (const auto& c : recording.commands) session.schedule(c);
    run.checkpoints[0] = digest(session);
    return session;
}
void finish(const wc3::Session& session, Run& run, const wc3::Recording& recording) {
    run.checkpoints[recording.end_us] = digest(session);
    run.applied = session.applied();
    run.accepted = session.accepted();
}
// Routes the live client logged with its screenshots: time_us -> canonical lines.
using Routes = std::multimap<std::uint64_t, std::string>;
struct RouteCheck {
    std::uint64_t compared = 0;
    std::string first_mismatch;  // empty when every line matched
};
// Compares the logged route lines due now with the headless session's route views.
void check_routes(const wc3::Session& session, const Routes& routes, RouteCheck& check) {
    const auto [begin, end] = routes.equal_range(session.time_us());
    for (auto it = begin; it != end; ++it) {
        std::istringstream fields(it->second);
        std::string key;
        std::uint64_t time;
        std::size_t unit;
        fields >> key >> time >> unit;
        const auto line = client::serialize(time, unit, client::route_view(session, unit));
        ++check.compared;
        if (line != it->second && check.first_mismatch.empty()) check.first_mismatch = "live: " + it->second + "\nreplay: " + line;
    }
}
Run headless(const wc3::Recording& recording, const Routes& routes, RouteCheck& route_check) {
    Run run;
    run.name = "headless";
    run.description = "no renderer: frames back to back until the recorded end";
    auto session = start(recording, run);
    check_routes(session, routes, route_check);
    while (session.time_us() < recording.end_us) {
        frame(session, run);
        check_routes(session, routes, route_check);
    }
    finish(session, run, recording);
    return run;
}
// A route view must copy the world's plan: the displayed position, then the waypoints
// from the cursor, in order. Pending/none views show no path.
void check_route(const wc3::Session& session, std::size_t id, const client::RouteView& view, const std::string& name) {
    const auto& unit = session.world().unit(id);
    const auto& route = unit.route();
    bool ok = view.points.empty();
    if (view.state == client::RouteState::planned || view.state == client::RouteState::partial) {
        ok = unit.current_order() == wc3::order_move && unit.route_index() < route.size() &&
             view.points.size() == route.size() - unit.route_index() + 1 &&
             view.points[0].x == unit.position().x && view.points[0].y == unit.position().y &&
             (view.state == client::RouteState::partial) == unit.route_partial();
        for (std::size_t i = 1; ok && i < view.points.size(); ++i) {
            const auto& w = route[unit.route_index() + i - 1];
            ok = view.points[i].x == w.x && view.points[i].y == w.y;
        }
    } else if (view.state == client::RouteState::none) {
        ok = ok && unit.current_order() != wc3::order_move;
    }
    if (!ok) throw std::logic_error(name + ": route view does not copy unit " + std::to_string(id) + "'s plan");
}
// A render loop as the client runs it: wall time -> Pacer -> frames, then camera,
// picking/selection and the draw list read the world. Presentation must not change
// the snapshot; any change fails the run.
Run rendered(const wc3::Recording& recording, std::string name, std::string description,
             const std::function<std::uint64_t(std::uint64_t)>& wall_us) {
    Run run;
    run.name = std::move(name);
    run.description = std::move(description);
    auto session = start(recording, run);
    client::Pacer pacer{session.frame_us()};
    client::Camera camera;
    client::Controller controller;
    while (session.time_us() < recording.end_us) {
        const auto frames = pacer.frames_for(wall_us(run.render_frames));
        for (std::uint64_t i = 0; i < frames && session.time_us() < recording.end_us; ++i) frame(session, run);
        const auto before = session.world().snapshot();
        // Exercise every presentation path: pan/zoom, picking each unit, selection.
        const auto n = run.render_frames;
        camera.pan(n % 7 == 0 ? 3.0f : -1.0f, n % 5 == 0 ? -2.0f : 1.0f);
        camera.zoom(n % 11 == 0 ? 1.0f : n % 13 == 0 ? -1.0f : 0.0f);
        const auto eye = camera.eye();
        const auto target = session.world().unit(n % session.world().unit_count()).position();
        const client::Ray ray{eye, {target.x - eye.x, target.y - eye.y, client::unit_height / 2 - eye.z}};
        controller.left_click(session.world(), ray);
        client::ground(ray);
        const auto views = client::unit_views(session, controller);
        // Route views for every unit and the selection, built twice: reading must not plan.
        for (int pass = 0; pass < 2; ++pass) {
            for (std::size_t id = 0; id < session.world().unit_count(); ++id) {
                const auto route = client::route_view(session, id);
                check_route(session, id, route, run.name);
                if (pass == 0) ++run.route_views[route.state];
            }
            client::selected_route(session, controller);
        }
        if (session.world().snapshot() != before || views.size() != session.world().unit_count())
            throw std::logic_error(run.name + ": presentation changed the world");
        ++run.presentation_checks;
        ++run.render_frames;
    }
    finish(session, run, recording);
    return run;
}
Checkpoints read_live(const std::string& text) {
    std::istringstream in(text);
    std::string line;
    if (!std::getline(in, line) || line != "wc3-checkpoints 2")
        throw std::invalid_argument("expected wc3-checkpoints 2 (portable RNG snapshots); legacy v1 needs verified migration");
    Checkpoints out;
    while (std::getline(in, line)) {
        std::istringstream fields(line);
        std::string key, hash;
        std::uint64_t time;
        if (!(fields >> key >> time >> hash) || key != "checkpoint" || hash.size() != 64)
            throw std::invalid_argument("invalid checkpoint line: " + line);
        out[time] = hash;
    }
    return out;
}
Routes read_routes(const std::string& text) {
    std::istringstream in(text);
    std::string line;
    if (!std::getline(in, line) || line != "wc3-routes 1") throw std::invalid_argument("expected wc3-routes 1");
    Routes out;
    while (std::getline(in, line)) {
        if (line.rfind('#', 0) == 0) continue;  // the screenshot each route was shown with
        std::istringstream fields(line);
        std::string key;
        std::uint64_t time;
        std::size_t unit;
        if (!(fields >> key >> time >> unit) || key != "route") throw std::invalid_argument("invalid route line: " + line);
        out.emplace(time, line);
    }
    return out;
}
bool same_commands(const std::vector<wc3::Command>& a, const std::vector<wc3::Command>& b) {
    if (a.size() != b.size()) return false;
    for (std::size_t i = 0; i < a.size(); ++i)
        if (wc3::serialize(a[i]) != wc3::serialize(b[i])) return false;
    return true;
}
std::string json(const std::string& s) { return '"' + s + '"'; }
}

int main(int argc, char** argv) {
    std::string recording_path, live_path, routes_path, json_path;
    const char* usage = "usage: wc3replay RECORDING [--live CHECKPOINTS] [--routes ROUTES] [--json REPORT]\n";
    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        if (arg == "--live" && i + 1 < argc) live_path = argv[++i];
        else if (arg == "--routes" && i + 1 < argc) routes_path = argv[++i];
        else if (arg == "--json" && i + 1 < argc) json_path = argv[++i];
        else if (recording_path.empty() && arg.rfind("--", 0) != 0) recording_path = arg;
        else { std::cerr << usage; return 2; }
    }
    if (recording_path.empty()) { std::cerr << usage; return 2; }
    try {
        const auto bytes = read(recording_path);
        const auto recording = wc3::parse_recording(bytes);
        if (wc3::serialize(recording) != bytes) throw std::invalid_argument("recording is not in canonical form");
        Routes routes;
        if (!routes_path.empty()) routes = read_routes(read(routes_path));
        RouteCheck route_check;
        const auto reference = headless(recording, routes, route_check);
        // Irregular: a fixed, repeating mix of short, long, zero and capped stalls (wall µs).
        const std::vector<std::uint64_t> irregular{7000, 41000, 16667, 1000, 0, 250000, 3000, 25000, 9999, 33334, 4999, 5001};
        std::vector<Run> runs;
        runs.push_back(rendered(recording, "render-30hz", "33333/33333/33334 us render intervals",
                                [](std::uint64_t n) { return n % 3 == 2 ? 33334 : 33333; }));
        runs.push_back(rendered(recording, "render-60hz", "16666/16667/16667 us render intervals",
                                [](std::uint64_t n) { return n % 3 == 0 ? 16666 : 16667; }));
        runs.push_back(rendered(recording, "render-irregular",
                                "repeating 7000,41000,16667,1000,0,250000,3000,25000,9999,33334,4999,5001 us",
                                [&](std::uint64_t n) { return irregular[n % irregular.size()]; }));
        bool pass = true;
        std::ostringstream report;
        report << "{\n  \"recording\": " << json(recording_path) << ",\n  \"recording_sha256\": "
               << json(scenario::sha256_hex(bytes)) << ",\n  \"scene\": " << json(recording.scene)
               << ",\n  \"model\": " << json(wc3::model(wc3::ModelVersion::v4).name)
               << ",\n  \"seed\": " << recording.seed << ",\n  \"frame_us\": " << wc3::Session(recording.seed).frame_us()
               << ",\n  \"commands\": " << recording.commands.size() << ",\n  \"end_us\": " << recording.end_us;
        std::map<std::uint64_t, int> per_time;
        for (const auto& c : recording.commands) ++per_time[c.time_us];
        int shared = 0;
        for (const auto& [time, count] : per_time) shared += count > 1 ? count : 0;
        report << ",\n  \"commands_sharing_a_time\": " << shared << ",\n  \"checkpoint_us\": " << client::checkpoint_us
               << ",\n  \"headless\": {\"sim_frames\": " << reference.sim_frames << ", \"checkpoints\": [";
        bool first = true;
        for (const auto& [time, hash] : reference.checkpoints) {
            report << (first ? "" : ", ") << "{\"time_us\": " << time << ", \"sha256\": " << json(hash) << "}";
            first = false;
        }
        report << "]},\n  \"comparisons\": [";
        const auto compare = [&](const std::string& name, const std::string& description, const Checkpoints& checkpoints,
                                 const Run* run) {
            std::string divergence = "null";
            for (const auto& [time, hash] : reference.checkpoints) {
                const auto found = checkpoints.find(time);
                if (found == checkpoints.end() || found->second != hash) { divergence = std::to_string(time); break; }
            }
            if (checkpoints.size() != reference.checkpoints.size() && divergence == "null") divergence = "\"extra checkpoints\"";
            if (run && divergence == "null" &&
                (!same_commands(run->applied, reference.applied) || run->accepted != reference.accepted))
                divergence = "\"applied commands differ\"";
            const bool same = divergence == "null";
            pass &= same;
            report << (name == "render-30hz" ? "\n    " : ",\n    ") << "{\"name\": " << json(name) << ", \"schedule\": "
                   << json(description) << ", \"checkpoints_compared\": " << reference.checkpoints.size();
            if (run) {
                report << ", \"render_frames\": " << run->render_frames << ", \"sim_frames\": " << run->sim_frames
                       << ", \"presentation_checks\": " << run->presentation_checks << ", \"route_views\": {";
                for (auto s : {client::RouteState::none, client::RouteState::pending, client::RouteState::planned,
                               client::RouteState::partial})
                    report << (s == client::RouteState::none ? "" : ", ") << json(client::route_state_name(s)) << ": "
                           << (run->route_views.count(s) ? run->route_views.at(s) : 0);
                report << "}";
            }
            report << ", \"identical\": " << (same ? "true" : "false") << ", \"first_divergence_us\": " << divergence << "}";
            std::cout << name << ": " << (same ? "IDENTICAL" : "DIFFERS at " + divergence) << " ("
                      << reference.checkpoints.size() << " checkpoints)\n";
        };
        for (const auto& run : runs) compare(run.name, run.description, run.checkpoints, &run);
        if (!live_path.empty()) compare("live-client", "checkpoints the live client recorded while playing",
                                        read_live(read(live_path)), nullptr);
        report << "\n  ]";
        if (!routes_path.empty()) {
            const bool same = route_check.compared == routes.size() && route_check.first_mismatch.empty();
            pass &= same;
            report << ",\n  \"live_routes\": {\"lines\": " << routes.size() << ", \"compared\": "
                   << route_check.compared << ", \"identical\": " << (same ? "true" : "false") << "}";
            std::cout << "live-routes: " << (same ? "IDENTICAL" : "DIFFERS") << " (" << route_check.compared << " of "
                      << routes.size() << " displayed routes)\n";
            if (!route_check.first_mismatch.empty()) std::cout << route_check.first_mismatch << '\n';
        }
        report << ",\n  \"status\": " << json(pass ? "PASS" : "FAIL") << "\n}\n";
        if (!json_path.empty()) {
            std::ofstream out(json_path, std::ios::binary);
            out << report.str();
            if (!out) throw std::runtime_error("cannot write " + json_path);
        }
        std::cout << (pass ? "PASS" : "FAIL") << ": " << recording.commands.size() << " commands, end "
                  << recording.end_us << " us\n";
        return pass ? 0 : 1;
    } catch (const std::invalid_argument& error) {
        std::cerr << "wc3replay: " << error.what() << '\n';
        return 2;
    } catch (const std::exception& error) {
        std::cerr << "wc3replay: " << error.what() << '\n';
        return 1;
    }
}
