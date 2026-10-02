// Scenario v1/v2 parsing, exact numeric conversion, the committed scenarios and
// equal-time ordering. Usage: scenario_tests SCENARIO_DIR (the committed scenarios/).
#include "Cases.h"
#include "Scenario.h"
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <sstream>
#include <stdexcept>
#include <string>

namespace {
void check(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error(message);
}
std::string read(const std::filesystem::path& path) {
    std::ifstream file(path, std::ios::binary);
    std::ostringstream bytes;
    bytes << file.rdbuf();
    check(static_cast<bool>(file), "cannot read " + path.string());
    return bytes.str();
}
std::string rejected(const std::string& text) {
    try {
        scenario::parse(text);
    } catch (const scenario::Error& error) {
        return error.what();
    }
    throw std::runtime_error("accepted invalid scenario:\n" + text);
}
bool rejected_run(const scenario::Scenario& description, wc3::ModelVersion version, bool before = false) {
    try {
        movement::run(description, version, 1, before);
    } catch (const std::invalid_argument&) {
        return true;
    }
    return false;
}
const std::string flow = R"(schema: wc3-scenario
version: 1
experiment: ORD-9001
map_revision: ORD-9001-t1
units:
  - name: u0
    type: hfoo
    position: [0, 0]
    facing: 0
observe:
  period: 0.02
  callbacks: 10
  properties: [x, "y", facing, order]
actions:
  - at: 0.02
    unit: u0
    order: move
    target: [707.106781, -0.5]
...
)";
// The same document using block sequences, comments and quoted words.
const std::string block = R"(# comment
schema: "wc3-scenario"   # trailing comment
version: 1
experiment: ORD-9001
map_revision: ORD-9001-t1
units:
  -
    name: "u0"
    type: hfoo
    position:
      - 0
      - 0
    facing: 0.0
observe:
  callbacks: 10
  period: 0.020
  properties:
    - x
    - "y"
    - facing
    - order
actions:
- at: 0.02
  unit: u0
  order: move
  target: [707.106781, -0.500]
...
# trailing comment after the end marker
)";
}

int main(int argc, char** argv) {
    try {
        check(argc == 2, "usage: scenario_tests SCENARIO_DIR");
        using scenario::sha256_hex;
        check(sha256_hex("") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", "sha256 empty");
        check(sha256_hex("abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad", "sha256 abc");
        check(sha256_hex("abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq") ==
              "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1", "sha256 two blocks");
        check(sha256_hex("abcdefghbcdefghicdefghijdefghijkefghijklfghijklmghijklmnhijklmnoijklmnopjklmnopq"
                         "klmnopqrlmnopqrsmnopqrstnopqrstu") ==
              "cf5b16a778af8380036ce59e7b0492370b249b11e8f07a51afac45037afee9d1", "sha256 896 bits");
        check(sha256_hex(std::string(55, 'a')) == "9f4390f8d30c2dd92ec9f095b65e2b9ae9b0a925a5258e241c9f1e910f734318", "sha256 55");
        check(sha256_hex(std::string(64, 'a')) == "ffe054fe7ae0cb6dc65c3af9b61d5209f439851db43d0ba5997337df154668eb", "sha256 64");

        // Exact decimal conversion equals the compiler's correctly rounded literals,
        // including exact float midpoints (ties to even).
        using scenario::decimal_to_float;
        const std::pair<const char*, float> literals[] = {
            {"707.106781", 707.106781f}, {"866.025391", 866.025391f}, {"0.001953125", 0.001953125f},
            {"1000.001953125", 1000.001953125f}, {"0.1", 0.1f}, {"0.02", 0.02f}, {"-1000", -1000.0f},
            {"4095.999999999", 4095.999999999f}, {"524288.03125", 524288.03125f},
            {"524288.09375", 524288.09375f}, {"524288.031250001", 524288.031250001f},
            {"999999.999999999", 999999.999999999f}, {"0.000000001", 0.000000001f},
            {"999999", 999999.0f}, {"3.4", 3.4f}, {"45", 45.0f}, {"123456.789", 123456.789f}};
        for (const auto& [text, value] : literals)
            check(decimal_to_float(text) == value, std::string("decimal conversion ") + text);
        check(std::signbit(decimal_to_float("-0")) && decimal_to_float("-0") == 0, "negative zero");

        const auto a = scenario::parse(flow), b = scenario::parse(block);
        check(a.experiment == b.experiment && a.map_revision == b.map_revision && a.period_us == 20000 &&
              b.period_us == 20000 && a.callbacks == b.callbacks && a.units.size() == 1 && b.units.size() == 1 &&
              a.actions.size() == 1 && b.actions.size() == 1 && a.actions[0].at_us == 20000 &&
              b.actions[0].at_us == 20000 && a.actions[0].point.x == b.actions[0].point.x &&
              a.actions[0].point.x == 707.106781f && b.actions[0].point.y == -0.5f,
              "flow and block spellings differ");

        // Each rejection names its reason; nothing is rounded, snapped or guessed.
        const auto replace = [](std::string text, const std::string& from, const std::string& to) {
            const auto at = text.find(from);
            check(at != std::string::npos, "test fixture lacks " + from);
            return text.replace(at, from.size(), to);
        };
        const std::pair<std::string, std::string> invalid[] = {
            {replace(flow, "version: 1", "version: 3"), "unsupported scenario version 3"},
            {replace(flow, "  callbacks: 10\n", "  callbacks: 10\n  start: 0.02\n"), "unsupported field 'start'"},
            {replace(flow, "schema: wc3-scenario", "schema: wc3-trace"), "not a wc3-scenario"},
            {replace(flow, "  callbacks: 10\n", "  callbacks: 10\n  seed: 1\n"), "unsupported field 'seed'"},
            {replace(flow, "    facing: 0\n", ""), "missing field 'facing'"},
            {replace(flow, "type: hfoo", "type: hpea"), "unsupported unit type"},
            {replace(flow, "order: move", "order: attack"), "unsupported order"},
            {replace(flow, "unit: u0", "unit: u9"), "unknown unit 'u9'"},
            {replace(flow, "    facing: 0\n", "    facing: 0\n  - name: u0\n    type: hfoo\n    position: [1, 1]\n    facing: 0\n"),
             "duplicate unit name"},
            {replace(flow, "version: 1\n", "version: 1\nversion: 1\n"), "duplicate key 'version'"},
            {flow.substr(0, flow.size() - 4), "missing document end marker"},
            {flow.substr(0, flow.size() - 1), "must end with a newline"},
            {flow.substr(0, flow.find("    target")), "missing document end marker"},
            {replace(flow, "[707.106781, -0.5]", "[707.106781, -0.5"), "unterminated flow sequence"},
            {replace(flow, "[707.106781, -0.5]", "[1e3, 0]"), "unquoted decimal"},
            {replace(flow, "[707.106781, -0.5]", "[inf, 0]"), "unquoted decimal"},
            {replace(flow, "[707.106781, -0.5]", "[nan, 0]"), "unquoted decimal"},
            {replace(flow, "[707.106781, -0.5]", "[99999999999999999999, 0]"), "out of range"},
            {replace(flow, "[707.106781, -0.5]", "[5000, 0]"), "outside its supported range"},
            {replace(flow, "[707.106781, -0.5]", "[0.0000000001, 0]"), "more than 9 fractional digits"},
            {replace(flow, "[707.106781, -0.5]", "[1, 2, 3]"), "must be [x, y]"},
            {replace(flow, "facing: 0", "facing: 360"), "facing must be in [0, 360)"},
            {replace(flow, "period: 0.02", "period: 0"), "period must be in (0, 10]"},
            {replace(flow, "period: 0.02", "period: 0.0200001"), "whole number of microseconds"},
            {replace(flow, "period: 0.02", "period: -0.02"), "non-negative decimal"},
            {replace(flow, "callbacks: 10", "callbacks: 0"), "callbacks must be in [1, 10000]"},
            {replace(flow, "callbacks: 10", "callbacks: 1.5"), "unquoted integer"},
            {replace(flow, "at: 0.02", "at: 0.03"), "not a callback time"},
            {replace(flow, "at: 0.02", "at: 0.22"), "after the last callback"},
            {replace(flow, "target: [707.106781, -0.5]", "target: [1, 1]\n    offset: [1, 1]"), "exactly one of target or offset"},
            {replace(flow, "order: move\n    target: [707.106781, -0.5]", "order: stop\n    target: [1, 1]"), "stop takes no target"},
            {replace(flow, "\"y\"", "y"), "YAML boolean or null unless quoted"},
            {replace(flow, "[x, \"y\", facing, order]", "[x, \"y\", facing]"), "observes exactly"},
            {replace(flow, "  - at: 0.02", "  - at: 0.04\n    unit: u0\n    order: stop\n  - at: 0.02"), "non-decreasing time"},
            {replace(flow, "experiment: ORD-9001", "experiment: ord-9001"), "permanent ID"},
            {replace(flow, "map_revision: ORD-9001-t1", "map_revision: MOV-0001"), "map_revision must be"},
            {replace(flow, "name: u0", "name: &a u0"), "unsupported character '&'"},
            {replace(flow, "type: hfoo", "type: !!str hfoo"), "unsupported character '!'"},
            {replace(flow, "position: [0, 0]", "position: {x: 0, y: 0}"), "unsupported character '{'"},
            {replace(flow, "    type: hfoo", "\ttype: hfoo"), "tabs are not allowed"},
            {replace(flow, "version: 1\n", "version: 1\r\n"), "carriage return"},
            {replace(flow, "schema: wc3-scenario\n", "---\nschema: wc3-scenario\n"), "document start markers"},
            {flow + "extra: 1\n", "content after the document end marker"},
            {replace(flow, "  period: 0.02", "    period: 0.02"), "unexpected indentation"},
            {replace(flow, "units:\n", "units:\n\n"), ""},  // A blank line is still valid; see below.
        };
        for (const auto& [text, reason] : invalid) {
            if (reason.empty()) {
                scenario::parse(text);
                continue;
            }
            const auto message = rejected(text);
            check(message.find(reason) != std::string::npos, "expected '" + reason + "', got: " + message);
        }
        check(rejected(replace(flow, "callbacks: 10", "callbacks: 0")).rfind("line 12:", 0) == 0,
              "errors carry their line");

        // Every committed scenario parses, is named after its experiment, and runs to a
        // complete schedule under every model and phase. Behavior against WC3 is graded
        // by the comparator and footman_v4_wc3; Phase 5 retained byte equivalence with
        // the former hard-coded cases (docs/phase-5-scenarios.md).
        const std::filesystem::path directory(argv[1]);
        int compared = 0;
        for (const auto& entry : std::filesystem::directory_iterator(directory)) {
            if (entry.path().extension() != ".yaml") continue;
            const auto description = scenario::parse(read(entry.path()));
            check(entry.path().stem().string() == description.experiment, description.experiment + " file name");
            for (auto version : {wc3::ModelVersion::v1, wc3::ModelVersion::v2, wc3::ModelVersion::v3,
                                 wc3::ModelVersion::v4}) {
                for (const bool before : {false, true}) {
                    const auto trace = movement::run(description, version, 1, before);
                    check(trace.samples.size() == (description.callbacks + 1u) * description.units.size() &&
                          trace.actions.size() == description.actions.size() &&
                          trace.tick_sequences.size() == description.callbacks + 1u,
                          description.experiment + " incomplete schedule");
                    ++compared;
                }
            }
        }
        check(compared >= 80, "expected at least the ten committed MOV scenarios");

        // Scenario v2 (docs/scenario-v2.md): MOV-0013/0014's start and STATE event, v4/after only.
        for (const auto* experiment : {"MOV-0013", "MOV-0014"})
        for (const auto& entry : std::filesystem::directory_iterator(directory / experiment)) {
            const auto description = scenario::parse(read(entry.path()));
            check(description.version == 2 && description.state_clock == 10 && description.period_us == 1000,
                  entry.path().stem().string() + " v2 fields");
            const auto trace = movement::run(description, wc3::ModelVersion::v4, 1, false);
            check(trace.events.size() == description.callbacks + 1u &&
                  trace.samples.size() == description.callbacks + 1u, description.map_revision + " incomplete v2 schedule");
            for (auto version : {wc3::ModelVersion::v1, wc3::ModelVersion::v2, wc3::ModelVersion::v3})
                check(rejected_run(description, version), description.map_revision + " ran v2 outside footman-v4");
            check(rejected_run(description, wc3::ModelVersion::v4, true), description.map_revision + " ran v2 before-phase");
        }

        // Equal-time actions execute in file order after the callback's samples;
        // relative targets read this world's position at execution.
        const auto ordered = scenario::parse(R"(schema: wc3-scenario
version: 1
experiment: ORD-9002
map_revision: ORD-9002
units:
  - name: u0
    type: hfoo
    position: [0, 0]
    facing: 0
  - name: u1
    type: hfoo
    position: [0, 384]
    facing: 90
    move_speed: 100
observe:
  period: 0.02
  callbacks: 60
  properties: [x, "y", facing, order]
actions:
  - at: 0
    unit: u0
    order: move
    target: [1000, 0]
  - at: 1
    unit: u1
    order: move
    offset: [0, 100]
  - at: 1
    unit: u0
    order: stop
  - at: 1
    unit: u0
    order: move
    offset: [-0.5, 2.25]
...
)");
        const auto trace = movement::run(ordered, wc3::ModelVersion::v4);
        check(trace.speeds.at(1) == 150, "setter clamp observed by the world");
        check(trace.actions.size() == 4 && trace.actions[1].unit == 1 && trace.actions[2].unit == 0 &&
              trace.actions[2].order == wc3::order_stop && trace.actions[3].order == wc3::order_move,
              "equal-time action order");
        check(trace.actions[1].seq + 1 == trace.actions[2].seq && trace.actions[2].seq + 1 == trace.actions[3].seq &&
              trace.actions[1].seq > trace.samples.at(2 * 50 + 1).seq, "actions follow the callback's samples");
        const auto u0 = trace.samples.at(2 * 50).position, u1 = trace.samples.at(2 * 50 + 1).position;
        check(u0.x > 0 && trace.actions[3].target.x == u0.x + -0.5f && trace.actions[3].target.y == u0.y + 2.25f,
              "relative target from the executing unit's position");
        check(trace.actions[1].target.x == u1.x && trace.actions[1].target.y == u1.y + 100.0f,
              "zero offset component copies the coordinate");
        bool unsupported = false;
        try {
            movement::run(scenario::parse(replace(flow, "period: 0.02", "period: 0.01")), wc3::ModelVersion::v4);
        } catch (const std::invalid_argument&) {
            unsupported = true;
        }
        check(unsupported, "runner accepted an unsupported period");

        std::cout << "scenario v1: SHA-256 vectors, exact decimals, " << std::size(invalid)
                  << " syntax/validation cases, " << compared
                  << " complete committed-scenario model/phase runs and equal-time ordering passed.\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
