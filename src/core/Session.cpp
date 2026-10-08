#include "core/Session.h"
#include <bit>
#include <charconv>
#include <cmath>
#include <cstdio>
#include <stdexcept>

namespace wc3 {
namespace {
constexpr const char* header = "wc3-command-recording 1";
constexpr ModelVersion scene_model = ModelVersion::v4;

std::uint64_t frame_us_of(const Model& model) {
    return std::uint64_t{model.heading.exposure_period_steps} * model.step_us;
}
std::vector<std::string_view> words(std::string_view line) {
    std::vector<std::string_view> out;
    while (!line.empty()) {
        const auto start = line.find_first_not_of(' ');
        if (start == std::string_view::npos) break;
        line.remove_prefix(start);
        const auto end = line.find(' ');
        out.push_back(line.substr(0, end));
        line.remove_prefix(end == std::string_view::npos ? line.size() : end);
    }
    return out;
}
std::uint64_t number(std::string_view text, int base = 10) {
    if (base == 16) {
        if (text.substr(0, 2) != "0x") throw std::invalid_argument("expected 0x float bits");
        text.remove_prefix(2);
    }
    std::uint64_t value = 0;
    const auto [end, error] = std::from_chars(text.data(), text.data() + text.size(), value, base);
    if (error != std::errc() || end != text.data() + text.size() || text.empty() ||
        (base == 10 && text.size() > 1 && text[0] == '0'))
        throw std::invalid_argument("invalid number: " + std::string(text));
    return value;
}
float float_bits(std::string_view text) {
    const auto value = number(text, 16);
    if (text.size() != 10 || value > 0xffffffffu) throw std::invalid_argument("expected 8 hex digits");
    return std::bit_cast<float>(static_cast<std::uint32_t>(value));
}
std::string hex(float value) {
    char buffer[16];
    std::snprintf(buffer, sizeof buffer, "0x%08x", std::bit_cast<std::uint32_t>(value));
    return buffer;
}
}

std::string serialize(const Command& c) {
    std::string out = "command " + std::to_string(c.time_us) + ' ' + std::to_string(c.sequence) +
                      ' ' + std::to_string(c.unit);
    if (c.order == order_stop) return out + " stop";
    char comment[64];
    std::snprintf(comment, sizeof comment, " # %.9g %.9g", c.target.x, c.target.y);
    return out + " move " + hex(c.target.x) + ' ' + hex(c.target.y) + comment;
}
std::string serialize(const Recording& r) {
    const auto model = wc3::model(scene_model);
    std::string out = std::string(header) + "\nscene " + r.scene + "\nmodel " + model.name +
                      "\nseed " + std::to_string(r.seed) + "\nframe_us " +
                      std::to_string(frame_us_of(model)) + '\n';
    for (const auto& c : r.commands) out += serialize(c) + '\n';
    return out + "end " + std::to_string(r.end_us) + '\n';
}
Recording parse_recording(std::string_view text) {
    const auto model = wc3::model(scene_model);
    const auto frame = frame_us_of(model);
    Recording r;
    std::vector<std::string_view> lines;
    while (!text.empty()) {
        const auto end = text.find('\n');
        if (end == std::string_view::npos) throw std::invalid_argument("recording must end with a newline");
        lines.push_back(text.substr(0, end));
        text.remove_prefix(end + 1);
    }
    if (lines.size() < 6 || lines[0] != header) throw std::invalid_argument("not a wc3 command recording");
    const auto field = [&](std::size_t i, std::string_view key) {
        const auto w = words(lines[i]);
        if (w.size() != 2 || w[0] != key) throw std::invalid_argument("expected " + std::string(key));
        return w[1];
    };
    r.scene = field(1, "scene");
    if (r.scene != scene_name) throw std::invalid_argument("unknown scene " + r.scene);
    if (field(2, "model") != model.name) throw std::invalid_argument("recording made with another model");
    const auto seed = number(field(3, "seed"));
    if (seed > 0xffffffffu) throw std::invalid_argument("seed out of range");
    r.seed = static_cast<std::uint32_t>(seed);
    if (number(field(4, "frame_us")) != frame) throw std::invalid_argument("frame period differs");
    for (std::size_t i = 5; i + 1 < lines.size(); ++i) {
        auto line = lines[i];
        line = line.substr(0, line.find('#'));
        const auto w = words(line);
        if (w.size() < 5 || w[0] != "command") throw std::invalid_argument("expected command");
        Command c{number(w[1]), number(w[2]), static_cast<std::size_t>(number(w[3])), order_none, {}};
        if (w[4] == "stop" && w.size() == 5) {
            c.order = order_stop;
        } else if (w[4] == "move" && w.size() == 7) {
            c.order = order_move;
            c.target = {float_bits(w[5]), float_bits(w[6])};
        } else {
            throw std::invalid_argument("expected move X Y or stop");
        }
        r.commands.push_back(c);
    }
    r.end_us = number(field(lines.size() - 1, "end"));
    if (r.end_us % frame) throw std::invalid_argument("end is not on a frame boundary");
    return r;
}

Session::Session(std::uint32_t seed) : world_(scene_model, seed), seed_(seed) {
    // Three Footmen facing north, far enough apart to pick one at a time.
    for (const float x : {-192.0f, 0.0f, 192.0f}) world_.create_footman({x, 0.0f}, 90.0f);
}
std::uint64_t Session::frame_us() const { return frame_us_of(world_.parameters()); }
std::uint64_t Session::time_us() const { return world_.steps() * world_.parameters().step_us; }
Command Session::submit(std::size_t unit, std::uint32_t order, Vec2 target) {
    const Command command{time_us(), next_sequence_, unit, order, order == order_move ? target : Vec2{}};
    schedule(command);
    return command;
}
void Session::schedule(const Command& c) {
    if (c.unit >= world_.unit_count()) throw std::invalid_argument("command for an unknown unit");
    if (c.order != order_move && c.order != order_stop) throw std::invalid_argument("unsupported order");
    if (c.order == order_move && !(std::abs(c.target.x) <= map_extent && std::abs(c.target.y) <= map_extent))
        throw std::invalid_argument("move target outside the map");
    if (c.order == order_stop && (std::bit_cast<std::uint32_t>(c.target.x) | std::bit_cast<std::uint32_t>(c.target.y)))
        throw std::invalid_argument("stop has no target");
    if (c.time_us % frame_us() || c.time_us < time_us())
        throw std::invalid_argument("command time is not a future frame boundary");
    if (c.sequence < next_sequence_) throw std::invalid_argument("command sequence does not increase");
    if (!pending_.empty() && c.time_us < pending_.back().time_us)
        throw std::invalid_argument("command time precedes an already scheduled command");
    pending_.push_back(c);
    next_sequence_ = c.sequence + 1;
}
void Session::advance_frame() {
    const auto now = time_us();
    for (; next_ < pending_.size() && pending_[next_].time_us == now; ++next_) {
        const auto& c = pending_[next_];
        const bool ok = c.order == order_move ? world_.issue_point_order(c.unit, c.order, c.target)
                                              : world_.issue_immediate_order(c.unit, c.order);
        applied_.push_back(c);
        accepted_.push_back(ok);
    }
    const auto steps = world_.parameters().heading.exposure_period_steps;
    for (std::uint32_t i = 0; i < steps; ++i) world_.step();
}
Recording Session::recording() const {
    return {scene_name, seed_, pending_, time_us()};
}
}
