// wc3client: the first interactive client (docs/client-v1.md). Placeholder geometry
// on flat ground establishes interaction, not Warcraft III visual fidelity.
// raylib stays in this file: input becomes Session commands, wall time becomes a
// frame count through client::Pacer (which also holds pause), and drawing reads
// client::unit_views, client::selected_route and client::diagnostics.
#include "Scenario.h"
#include "client/SmokeInput.h"
#include "client/View.h"
#include "raylib.h"
#include "rlgl.h"
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <deque>
#include <filesystem>
#include <fstream>
#include <functional>
#include <iostream>
#include <map>
#include <optional>
#include <sstream>
#include <string>
#include <vector>

#ifndef __APPLE__
namespace client::smoke {
bool available() { return false; }
void focus(void*) {}
void mouse_move(void*, float, float) {}
void mouse_button(void*, bool, bool, float, float) {}
void key(void*, Key, bool) {}
void scroll(void*, float, float, float) {}
}
#endif

namespace {
// raylib's default far plane is 1000 render units; draw WC3 units at 1/100.
constexpr float scale = 0.01f;
Vector3 render(float x, float y, float z = 0) { return {x * scale, z * scale, -y * scale}; }
client::Ray world_ray(const ::Ray& r) {
    return {{r.position.x / scale, -r.position.z / scale, r.position.y / scale},
            {r.direction.x, -r.direction.z, r.direction.y}};
}
Camera3D raylib_camera(const client::Camera& c) {
    const auto eye = c.eye();
    return {render(eye.x, eye.y, eye.z), render(c.target_x, c.target_y), {0, 1, 0}, c.fov_degrees, CAMERA_PERSPECTIVE};
}
void write_file(const std::filesystem::path& path, const std::string& text) {
    if (path.has_parent_path()) std::filesystem::create_directories(path.parent_path());
    const auto temporary = path.string() + ".tmp";
    {
        std::ofstream out(temporary, std::ios::binary);
        out << text;
        if (!out) throw std::runtime_error("cannot write " + temporary);
    }
    std::filesystem::rename(temporary, path);
}
// Draws the pending 2D batch (HUD text) first, so captures show the whole frame.
Image capture() {
    rlDrawRenderBatchActive();
    return LoadImageFromScreen();
}
std::string order_name(std::uint32_t order) {
    return order == wc3::order_move ? "move" : order == wc3::order_stop ? "stop" : "none";
}
void draw_right(const std::string& text, int right, int y, int size, Color color) {
    DrawText(text.c_str(), right - MeasureText(text.c_str(), size), y, size, color);
}

// A smoke script: one action per line, run in order; "wait N" pauses N render frames.
// Targets are "@ID" (a unit's body on screen) or "ground X Y" (world units), resolved
// against the current camera like a player aiming. Releases follow one frame later
// (or after "key NAME FRAMES") so raylib sees each press.
struct Smoke {
    std::deque<std::vector<std::string>> lines;
    int waiting = 0;
    std::vector<std::pair<int, std::function<void()>>> release;  // frames left, action
};
Smoke load_smoke(const std::string& path) {
    std::ifstream in(path);
    if (!in) throw std::runtime_error("cannot read smoke script " + path);
    Smoke smoke;
    std::string line;
    while (std::getline(in, line)) {
        line = line.substr(0, line.find('#'));
        std::istringstream words(line);
        std::vector<std::string> w;
        for (std::string word; words >> word;) w.push_back(word);
        if (!w.empty()) smoke.lines.push_back(w);
    }
    return smoke;
}
}

int main(int argc, char** argv) {
    std::string record = "wc3client-session", smoke_path, shots, frames_dir;
    std::uint32_t seed = 1;
    int width = 1280, height = 720;
    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        const bool value = i + 1 < argc;
        if (arg == "--record" && value) record = argv[++i];
        else if (arg == "--seed" && value) seed = static_cast<std::uint32_t>(std::stoul(argv[++i]));
        else if (arg == "--smoke" && value) smoke_path = argv[++i];
        else if (arg == "--screenshots" && value) shots = argv[++i];
        else if (arg == "--frames" && value) frames_dir = argv[++i];
        else if (arg == "--window" && value && std::sscanf(argv[++i], "%dx%d", &width, &height) == 2 &&
                 width >= 640 && height >= 360) {}
        else {
            std::cerr << "usage: wc3client [--record BASE] [--seed N] [--screenshots DIR]\n"
                         "                 [--smoke SCRIPT] [--frames DIR] [--window WxH]\n"
                         "Writes BASE.rec (commands), BASE.checkpoints (state digests),\n"
                         "BASE.routes (the selected route displayed with each screenshot) and\n"
                         "BASE.observations (smoke 'observe' lines: time, counts, digest).\n";
            return 2;
        }
    }
    try {
        std::optional<Smoke> smoke;
        if (!smoke_path.empty()) {
            if (!client::smoke::available()) throw std::runtime_error("--smoke needs macOS");
            smoke = load_smoke(smoke_path);
        }
        wc3::Session session(seed);
        client::Pacer pacer{session.frame_us()};
        client::Camera camera;
        client::Controller controller;
        // The selected route as displayed with each screenshot, for wc3replay --routes.
        std::string routes_log = "wc3-routes 1\n";
        // Smoke "observe" lines: frozen time, counts and digest, for wc3replay --observations.
        std::string observations_log = "wc3-pause-observations 1\n";
        std::map<std::uint64_t, std::string> checkpoints{{0, scenario::sha256_hex(session.world().snapshot())}};
        const auto save = [&] {
            write_file(record + ".rec", wc3::serialize(session.recording()));
            std::string text = "wc3-checkpoints 2\n";
            auto all = checkpoints;
            all[session.time_us()] = scenario::sha256_hex(session.world().snapshot());
            for (const auto& [time, hash] : all) text += "checkpoint " + std::to_string(time) + ' ' + hash + '\n';
            write_file(record + ".checkpoints", text);
            write_file(record + ".routes", routes_log);
            write_file(record + ".observations", observations_log);
        };
        std::string last_command = "-";
        const auto issued = [&](const std::vector<wc3::Command>& commands) {
            for (const auto& c : commands) {
                last_command = wc3::serialize(c);
                std::cout << last_command << '\n';
            }
            if (!commands.empty()) save();
        };

        SetTraceLogLevel(std::getenv("WC3CLIENT_LOG") ? LOG_INFO : LOG_WARNING);
        SetConfigFlags(FLAG_MSAA_4X_HINT | FLAG_VSYNC_HINT);
        InitWindow(width, height, "wc3client - placeholder Footmen (interaction only)");
        SetExitKey(KEY_ESCAPE);
        void* window = GetWindowHandle();
        if (smoke) client::smoke::focus(window);
        std::uint64_t render_frame = 0;
        bool quit = false, show_diagnostics = false;
        while (!quit && !WindowShouldClose()) {
            const auto cam3d = raylib_camera(camera);
            // Player input first, in a fixed order: left button, right click, S, Space
            // (pause), F3, camera. Commands are stamped with the current simulation time
            // and apply before the next frame is simulated; while paused that is the
            // first resumed frame. Pause/resume take effect at this render's pacing step.
            const auto mouse = GetMousePosition();
            if (IsMouseButtonPressed(MOUSE_BUTTON_LEFT))
                controller.press({mouse.x, mouse.y}, IsKeyDown(KEY_LEFT_SHIFT) || IsKeyDown(KEY_RIGHT_SHIFT));
            controller.motion({mouse.x, mouse.y});
            if (IsMouseButtonReleased(MOUSE_BUTTON_LEFT))
                controller.release(session.world(), camera, {mouse.x, mouse.y}, GetScreenWidth(), GetScreenHeight());
            if (IsMouseButtonPressed(MOUSE_BUTTON_RIGHT))
                issued(controller.right_click(session, world_ray(GetScreenToWorldRay(GetMousePosition(), cam3d))));
            if (IsKeyPressed(KEY_S)) issued(controller.stop(session));
            if (IsKeyPressed(KEY_SPACE)) pacer.toggle();
            if (IsKeyPressed(KEY_F3)) show_diagnostics = !show_diagnostics;
            const float dt = GetFrameTime();
            const float pan = camera.distance * 0.8f * dt;
            if (IsKeyDown(KEY_LEFT)) camera.pan(-pan, 0);
            if (IsKeyDown(KEY_RIGHT)) camera.pan(pan, 0);
            if (IsKeyDown(KEY_UP)) camera.pan(0, pan);
            if (IsKeyDown(KEY_DOWN)) camera.pan(0, -pan);
            if (IsMouseButtonDown(MOUSE_BUTTON_MIDDLE)) {
                const auto d = GetMouseDelta();
                camera.pan(-d.x * camera.distance * 0.0012f, d.y * camera.distance * 0.0012f);
            }
            camera.zoom(GetMouseWheelMove() + (IsKeyPressed(KEY_EQUAL) ? 1.0f : 0) - (IsKeyPressed(KEY_MINUS) ? 1.0f : 0));

            // Wall time decides how many whole frames to simulate; never simulation state.
            // Paused renders and the resume render simulate nothing and drop their time.
            const auto frames = pacer.frames_for(static_cast<std::uint64_t>(std::llround(dt * 1e6)));
            for (std::uint64_t i = 0; i < frames; ++i) {
                session.advance_frame();
                if (session.time_us() % client::checkpoint_us == 0)
                    checkpoints[session.time_us()] = scenario::sha256_hex(session.world().snapshot());
            }

            const auto views = client::unit_views(session, controller);
            const auto route = client::selected_route(session, controller);
            const auto route_unit = controller.selected();  // as drawn, before smoke actions
            // Later render frames may submit commands at this same simulation time; the
            // count lets the replay rebuild exactly the commands known when it was drawn.
            const auto log_route = [&, now = session.time_us(), submitted = session.recording().commands.size()](
                                       const std::string& shot) {
                routes_log += "screenshot " + shot + ' ' + std::to_string(submitted) + '\n';
                if (route_unit) routes_log += client::serialize(now, *route_unit, route) + '\n';
            };
            const auto cam = raylib_camera(camera);
            BeginDrawing();
            ClearBackground({24, 28, 34, 255});
            BeginMode3D(cam);
            DrawPlane(render(0, 0), {2 * wc3::map_extent * scale, 2 * wc3::map_extent * scale}, {58, 92, 52, 255});
            for (float g = -2048; g <= 2048; g += 128) {
                const Color line = g == 0 ? Color{110, 140, 100, 255} : Color{70, 104, 62, 255};
                DrawLine3D(render(g, -2048, 0.5f), render(g, 2048, 0.5f), line);
                DrawLine3D(render(-2048, g, 0.5f), render(2048, g, 0.5f), line);
            }
            for (const auto& v : views) {
                const auto base = render(v.position.x, v.position.y);
                if (v.selected) {
                    DrawCircle3D(render(v.position.x, v.position.y, 1), (client::unit_radius + 10) * scale,
                                 {1, 0, 0}, 90, {80, 255, 80, 255});
                    DrawCircle3D(render(v.position.x, v.position.y, 1.5f), (client::unit_radius + 12) * scale,
                                 {1, 0, 0}, 90, {80, 255, 80, 255});
                }
                if (v.destination && v.selected) {
                    const auto d = *v.destination;
                    DrawLine3D(render(d.x - 14, d.y - 14, 1), render(d.x + 14, d.y + 14, 1), {80, 255, 80, 255});
                    DrawLine3D(render(d.x - 14, d.y + 14, 1), render(d.x + 14, d.y - 14, 1), {80, 255, 80, 255});
                }
                // The current computed route, not a line to the destination. A partial
                // route stops where the plan ends (orange ring); pending shows no path.
                if (route_unit == v.id && route.points.size() > 1) {
                    const Color path{90, 210, 255, 255};
                    for (std::size_t i = 1; i < route.points.size(); ++i) {
                        const auto a = route.points[i - 1], b = route.points[i];
                        DrawLine3D(render(a.x, a.y, 2), render(b.x, b.y, 2), path);
                        DrawLine3D(render(a.x, a.y + 1.5f, 2), render(b.x, b.y + 1.5f, 2), path);
                        DrawSphere(render(b.x, b.y, 2), 3.5f * scale, path);
                    }
                    if (route.state == client::RouteState::partial) {
                        const auto e = route.points.back();
                        DrawCircle3D(render(e.x, e.y, 2), 12 * scale, {1, 0, 0}, 90, ORANGE);
                        DrawCircle3D(render(e.x, e.y, 2.5f), 14 * scale, {1, 0, 0}, 90, ORANGE);
                    }
                }
                const Color body = v.selected ? Color{90, 150, 255, 255} : Color{50, 90, 190, 255};
                DrawCylinder(base, client::unit_radius * scale, client::unit_radius * scale,
                             client::unit_height * scale, 14, body);
                DrawCylinderWires(base, client::unit_radius * scale, client::unit_radius * scale,
                                  client::unit_height * scale, 14, {20, 30, 60, 255});
                const float a = v.facing_degrees * PI / 180;
                const float top = client::unit_height + 2;
                DrawLine3D(render(v.position.x, v.position.y, top),
                           render(v.position.x + 34 * std::cos(a), v.position.y + 34 * std::sin(a), top),
                           {255, 220, 90, 255});
                DrawSphere(render(v.position.x + 34 * std::cos(a), v.position.y + 34 * std::sin(a), top),
                           3 * scale, {255, 220, 90, 255});
            }
            EndMode3D();
            const auto& world = session.world();
            const int screen_w = GetScreenWidth(), screen_h = GetScreenHeight();
            // Player HUD, always shown: selection with each unit's order, the focus
            // route, the shared-target limitation, pause state and controls.
            std::string selection = "selected: none";
            if (!controller.selection().empty()) {
                selection = "selected:";
                for (auto id : controller.selection())
                    selection += " Footman " + std::to_string(id) + " (" + order_name(world.unit(id).current_order()) +
                                 (session.pending_for(id) ? ", queued)" : ")");
            }
            DrawText(selection.c_str(), 12, 10, 18, {150, 255, 150, 255});
            if (controller.selected()) {
                std::string text = "route Footman " + std::to_string(*controller.selected()) + ": " + client::route_state_name(route.state);
                if (route.points.size() > 1) text += ", " + std::to_string(route.points.size() - 1) + " waypoints left";
                if (route.state == client::RouteState::partial) text += " (ends short of the destination)";
                if (route.state == client::RouteState::pending) text += " (no computed path yet)";
                DrawText(text.c_str(), 12, 34, 18, {90, 210, 255, 255});
            }
            if (controller.selection().size() > 1)
                DrawText("Same target for every unit: WC3 formation unmeasured (likely P3)", 12, 58, 16, ORANGE);
            if (pacer.paused) {
                const auto queued = client::pending_summary(session);
                const int box_w = std::max(MeasureText("PAUSED", 36), MeasureText(queued.c_str(), 18)) + 24;
                DrawRectangle(screen_w - box_w - 12, 84, box_w, 76, {0, 0, 0, 170});
                draw_right("PAUSED", screen_w - 24, 92, 36, {255, 210, 80, 255});
                draw_right(queued, screen_w - 24, 132, 18, RAYWHITE);
            }
            if (show_diagnostics) {
                const auto lines = client::diagnostics(session, controller, {pacer.paused, GetFPS(), last_command});
                // Bottom-left above the controls, compact in small windows, to keep units visible.
                const int size = screen_w < 1100 ? 14 : 16, step = size + 4;
                const int top = screen_h - 60 - static_cast<int>(lines.size()) * step;
                int panel_w = 0;
                for (const auto& line : lines) panel_w = std::max(panel_w, MeasureText(line.c_str(), size));
                DrawRectangle(6, top - 4, panel_w + 16, static_cast<int>(lines.size()) * step + 8, {0, 0, 0, 170});
                for (std::size_t i = 0; i < lines.size(); ++i)
                    DrawText(lines[i].c_str(), 14, top + static_cast<int>(i) * step, size,
                             i == 0 ? Color{255, 210, 80, 255} : i + 2 >= lines.size() ? ORANGE : RAYWHITE);
            }
            if (controller.dragging()) {
                const auto a = controller.anchor(), b = controller.pointer();
                DrawRectangleLinesEx({std::min(a.x,b.x),std::min(a.y,b.y),std::abs(a.x-b.x),std::abs(a.y-b.y)},2,{80,255,80,255});
            }
            DrawText("click / drag select | Shift toggle / add | right-click move | S stop", 12, screen_h - 46, 16, LIGHTGRAY);
            DrawText((std::string(pacer.paused ? "Space resume" : "Space pause") + " | F3 diagnostics | arrows pan | wheel zoom | Esc quit").c_str(),
                     12, screen_h - 24, 16, LIGHTGRAY);
            if (smoke) draw_right("SMOKE RUN: scripted Cocoa input events", screen_w - 12, screen_h - 72, 18, ORANGE);

            // Smoke script: release last frame's presses, then run actions until a wait.
            if (smoke) {
                std::erase_if(smoke->release, [](auto& r) { return --r.first == 0 && (r.second(), true); });
                if (smoke->waiting > 0) --smoke->waiting;
                while (smoke->waiting == 0 && !smoke->lines.empty()) {
                    const auto w = smoke->lines.front();
                    smoke->lines.pop_front();
                    const auto aim = [&](std::size_t i) {
                        if (w.at(i)[0] == '@') {
                            const auto p = world.unit(std::stoul(w[i].substr(1))).position();
                            return GetWorldToScreen(render(p.x, p.y, client::unit_height / 2), cam);
                        }
                        if (w.at(i) != "ground") throw std::runtime_error("smoke target: " + w[i]);
                        return GetWorldToScreen(render(std::stof(w.at(i + 1)), std::stof(w.at(i + 2))), cam);
                    };
                    const auto& op = w[0];
                    if (op == "wait") smoke->waiting = std::stoi(w.at(1));
                    else if (op == "point") { const auto p = aim(1); client::smoke::mouse_move(window, p.x, p.y); }
                    else if (op == "down" || op == "up" || op == "drag") {
                        const auto p = aim(1);
                        client::smoke::mouse_move(window,p.x,p.y);
                        if (op != "drag") client::smoke::mouse_button(window,false,op == "down",p.x,p.y);
                    } else if (op == "left" || op == "right") {
                        const auto p = aim(1);
                        const bool right = op == "right";
                        client::smoke::mouse_move(window, p.x, p.y);
                        client::smoke::mouse_button(window, right, true, p.x, p.y);
                        smoke->release.emplace_back(1, [=] { client::smoke::mouse_button(window, right, false, p.x, p.y); });
                    } else if (op == "key") {
                        const std::map<std::string, client::smoke::Key> keys{
                            {"s", client::smoke::Key::s}, {"shift", client::smoke::Key::shift}, {"left", client::smoke::Key::left},
                            {"right", client::smoke::Key::right}, {"up", client::smoke::Key::up},
                            {"down", client::smoke::Key::down}, {"plus", client::smoke::Key::plus},
                            {"minus", client::smoke::Key::minus}, {"space", client::smoke::Key::space},
                            {"f3", client::smoke::Key::f3}};
                        const auto k = keys.at(w.at(1));
                        const int hold = w.size() > 2 ? std::stoi(w[2]) : 1;
                        client::smoke::key(window, k, true);
                        smoke->release.emplace_back(hold, [=] { client::smoke::key(window, k, false); });
                    } else if (op == "scroll") {
                        client::smoke::scroll(window, std::stof(w.at(1)), GetScreenWidth() / 2.0f, GetScreenHeight() / 2.0f);
                    } else if (op == "screenshot" && !shots.empty()) {
                        log_route(w.at(1));
                        std::filesystem::create_directories(shots);
                        Image image = capture();
                        ExportImage(image, (std::filesystem::path(shots) / (w.at(1) + ".png")).string().c_str());
                        UnloadImage(image);
                    } else if (op == "observe") {
                        // Pacing already ran this render: the state as drawn.
                        observations_log += client::observation(w.at(1), render_frame, pacer.paused, session,
                                                                scenario::sha256_hex(world.snapshot())) + '\n';
                    } else if (op == "quit") {
                        quit = true;
                        break;
                    } else if (op != "screenshot") {
                        throw std::runtime_error("unknown smoke action " + op);
                    }
                }
            }
            if (!frames_dir.empty() && render_frame % 2 == 0) {
                std::filesystem::create_directories(frames_dir);
                char name[32];
                std::snprintf(name, sizeof name, "frame-%05llu.png", static_cast<unsigned long long>(render_frame / 2));
                Image image = capture();
                ExportImage(image, (std::filesystem::path(frames_dir) / name).string().c_str());
                UnloadImage(image);
            }
            if (!shots.empty() && IsKeyPressed(KEY_F12)) {
                const auto name = "manual-" + std::to_string(session.time_us());
                log_route(name);
                std::filesystem::create_directories(shots);
                Image image = capture();
                ExportImage(image, (std::filesystem::path(shots) / (name + ".png")).string().c_str());
                UnloadImage(image);
            }
            EndDrawing();
            ++render_frame;
        }
        CloseWindow();
        save();
        std::cout << "recorded " << session.recording().commands.size() << " commands to " << record
                  << ".rec; ended at " << session.time_us() << " us\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "wc3client: " << error.what() << '\n';
        return 1;
    }
}
