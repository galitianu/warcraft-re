// Replays a command recording headlessly and under named render schedules, and
// compares exact world state at identical simulation checkpoints (docs/client-v1.md).
// Usage: wc3replay RECORDING [--live CHECKPOINTS] [--json REPORT]
// Exit 0: every schedule (and the live client's checkpoints, when given) matches
// the headless replay; 1: a difference; 2: invalid input.
#include "Scenario.h"
#include "client/View.h"
#include <fstream>
#include <functional>
#include <iostream>
#include <map>
#include <sstream>
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
Run headless(const wc3::Recording& recording) {
    Run run;
    run.name = "headless";
    run.description = "no renderer: frames back to back until the recorded end";
    auto session = start(recording, run);
    while (session.time_us() < recording.end_us) frame(session, run);
    finish(session, run, recording);
    return run;
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
    if (!std::getline(in, line) || line != "wc3-checkpoints 1") throw std::invalid_argument("not a checkpoint file");
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
bool same_commands(const std::vector<wc3::Command>& a, const std::vector<wc3::Command>& b) {
    if (a.size() != b.size()) return false;
    for (std::size_t i = 0; i < a.size(); ++i)
        if (wc3::serialize(a[i]) != wc3::serialize(b[i])) return false;
    return true;
}
std::string json(const std::string& s) { return '"' + s + '"'; }
}

int main(int argc, char** argv) {
    std::string recording_path, live_path, json_path;
    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        if ((arg == "--live" || arg == "--json") && i + 1 < argc) (arg == "--live" ? live_path : json_path) = argv[++i];
        else if (recording_path.empty() && arg.rfind("--", 0) != 0) recording_path = arg;
        else { std::cerr << "usage: wc3replay RECORDING [--live CHECKPOINTS] [--json REPORT]\n"; return 2; }
    }
    if (recording_path.empty()) { std::cerr << "usage: wc3replay RECORDING [--live CHECKPOINTS] [--json REPORT]\n"; return 2; }
    try {
        const auto bytes = read(recording_path);
        const auto recording = wc3::parse_recording(bytes);
        if (wc3::serialize(recording) != bytes) throw std::invalid_argument("recording is not in canonical form");
        const auto reference = headless(recording);
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
            if (run) report << ", \"render_frames\": " << run->render_frames << ", \"sim_frames\": " << run->sim_frames
                            << ", \"presentation_checks\": " << run->presentation_checks;
            report << ", \"identical\": " << (same ? "true" : "false") << ", \"first_divergence_us\": " << divergence << "}";
            std::cout << name << ": " << (same ? "IDENTICAL" : "DIFFERS at " + divergence) << " ("
                      << reference.checkpoints.size() << " checkpoints)\n";
        };
        for (const auto& run : runs) compare(run.name, run.description, run.checkpoints, &run);
        if (!live_path.empty()) compare("live-client", "checkpoints the live client recorded while playing",
                                        read_live(read(live_path)), nullptr);
        report << "\n  ],\n  \"status\": " << json(pass ? "PASS" : "FAIL") << "\n}\n";
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
