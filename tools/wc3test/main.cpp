#include "BuildIdentity.h"
#include "Cases.h"
#include "Canonical.h"
#include <algorithm>
#include <charconv>
#include <cstdio>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iomanip>
#include <limits>
#include <locale>
#include <sstream>
#include <string>
#include <stdexcept>
#include <vector>

namespace {
void write(const std::filesystem::path& path, const std::string& bytes) {
    std::ofstream file(path, std::ios::binary);
    file.exceptions(std::ios::badbit | std::ios::failbit);
    file << bytes;
}
std::string json_string(const std::string& text) {
    std::string quoted = "\"";
    for (const char c : text) {
        if (c == '"' || c == '\\') quoted += '\\';
        if (static_cast<unsigned char>(c) < 0x20) {
            char escape[8];
            std::snprintf(escape, sizeof escape, "\\u%04x", static_cast<unsigned>(c));
            quoted += escape;
        } else {
            quoted += c;
        }
    }
    return quoted + '"';
}
struct Input {
    std::string path;  // as named on the command line, '/' separated
    std::string sha256;  // of the exact bytes parsed
    scenario::Scenario description;
};
// Reads and validates every description before any simulation or output.
std::vector<Input> load_scenarios(const std::vector<std::string>& arguments) {
    std::vector<std::filesystem::path> files;
    for (const auto& argument : arguments) {
        const std::filesystem::path path(argument);
        if (std::filesystem::is_directory(path)) {
            std::vector<std::filesystem::path> found;
            for (const auto& entry : std::filesystem::directory_iterator(path))
                if (entry.is_regular_file() && entry.path().extension() == ".yaml") found.push_back(entry.path());
            if (found.empty()) throw std::invalid_argument("no *.yaml scenarios in " + argument);
            std::sort(found.begin(), found.end(), [](const auto& a, const auto& b) {
                return a.filename().generic_string() < b.filename().generic_string();
            });
            files.insert(files.end(), found.begin(), found.end());
        } else if (std::filesystem::is_regular_file(path)) {
            files.push_back(path);
        } else {
            throw std::invalid_argument("scenario not found: " + argument);
        }
    }
    std::vector<Input> inputs;
    for (const auto& file : files) {
        const auto name = file.generic_string();
        std::ifstream stream(file, std::ios::binary);
        std::ostringstream bytes;
        bytes << stream.rdbuf();
        if (!stream) throw std::invalid_argument("cannot read scenario " + name);
        try {
            inputs.push_back({name, scenario::sha256_hex(bytes.str()), scenario::parse(bytes.str())});
        } catch (const scenario::Error& error) {
            throw std::invalid_argument("scenario " + name + ": " + error.what());
        }
        for (std::size_t i = 0; i + 1 < inputs.size(); ++i)
            if (inputs[i].description.experiment == inputs.back().description.experiment)
                throw std::invalid_argument("scenario " + name + ": experiment " +
                    inputs.back().description.experiment + " already declared by " + inputs[i].path);
    }
    return inputs;
}
// JSON has no infinity; an infinite turn limit turns the whole remaining angle.
std::string json_number(float value) {
    if (std::isinf(value)) return "\"unlimited\"";
    std::ostringstream out;
    out.imbue(std::locale::classic());
    out << std::setprecision(std::numeric_limits<float>::max_digits10) << value;
    return out.str();
}
}
int main(int argc, char** argv) {
    try {
        std::filesystem::path output;
        std::vector<std::string> scenarios;
        auto version = wc3::ModelVersion::v2;
        std::uint32_t seed = 1;
        bool before = false;
        for (int i = 1; i < argc; ++i) {
            const std::string option = argv[i];
            if (option == "--help") {
                std::cout << "wc3test --scenario FILE_OR_DIR... --out DIR [--model v1|v2|v3|v4] "
                             "[--seed UINT32] [--phase after|before]\n"
                             "Each --scenario names a v1/v2 scenario file or a directory of *.yaml files\n"
                             "(sorted); the committed MOV-0001..0010 are in scenarios/.\n";
                return 0;
            }
            if (i + 1 == argc) throw std::invalid_argument("missing option value");
            const std::string value = argv[++i];
            if (option == "--out") output = value;
            else if (option == "--scenario") scenarios.push_back(value);
            else if (option == "--model" && (value == "v1" || value == "v2" || value == "v3" || value == "v4"))
                version = value == "v1" ? wc3::ModelVersion::v1
                        : value == "v2" ? wc3::ModelVersion::v2
                        : value == "v3" ? wc3::ModelVersion::v3 : wc3::ModelVersion::v4;
            else if (option == "--phase" && (value == "after" || value == "before"))
                before = value == "before";
            else if (option == "--seed") {
                const auto parsed = std::from_chars(value.data(), value.data() + value.size(), seed);
                if (parsed.ec != std::errc{} || parsed.ptr != value.data() + value.size())
                    throw std::invalid_argument("seed must be a uint32");
            } else throw std::invalid_argument("unknown option or invalid value: " + option);
        }
        if (output.empty()) throw std::invalid_argument("--out DIR is required");
        if (scenarios.empty()) throw std::invalid_argument("--scenario FILE_OR_DIR is required (e.g. scenarios)");
        // Invalid descriptions or unsupported schedules fail before any output exists.
        const auto inputs = load_scenarios(scenarios);
        // A v2 run's timing (start, period, state clock) is part of its run identity,
        // so each v2 scenario runs in its own invocation.
        const bool v2 = std::any_of(inputs.begin(), inputs.end(),
                                    [](const Input& i) { return i.description.version == 2; });
        if (v2 && inputs.size() != 1)
            throw std::invalid_argument("a version 2 scenario must be the only scenario of its run");
        std::vector<movement::Trace> traces;
        for (const auto& input : inputs)
            traces.push_back(movement::run(input.description, version, seed, before));
        std::filesystem::create_directories(output);
        const auto p = wc3::model(version);
        std::ostringstream identity;
        identity.imbue(std::locale::classic());
        identity << "{\n  \"git_commit\": " << build_git_commit_json << ",\n"
            << "  \"git_dirty_at_configure\": " << build_git_dirty_json << ",\n"
            << "  \"source_sha256\": \"" << build_source_sha256 << "\",\n"
            << "  \"compiler\": \"" << build_compiler << "\",\n"
            << "  \"build_type\": \"" << build_type << "\",\n"
            << "  \"architecture\": \"" << build_architecture << "\",\n"
            << "  \"fp_contract\": \"" << build_fp_contract << "\",\n"
            << "  \"model\": \"" << p.name << "\",\n"
            << "  \"time_unit\": \"seconds\",\n  \"step_us\": " << p.step_us << ",\n"
            << "  \"seed\": " << seed << ",\n  \"rng\": \"std::mt19937; unused by movement\",\n"
            << "  \"observation_phase\": \"" << (v2 ? "scheduled-sampler-time" : before ? "before-due-update" : "after-due-update") << "\",\n"
            << "  \"sample_period_us\": " << (v2 ? inputs[0].description.period_us : movement::sample_period_us) << ",\n";
        if (v2)
            identity << "  \"sampler_start_us\": " << inputs[0].description.start_us << ",\n"
                << "  \"state_lag_us\": null,\n";
        else
            // t is the requested callback time; before-phase state omits the step due then.
            identity << "  \"state_lag_us\": " << (before ? p.step_us : 0) << ",\n";
        identity << "  \"parameters\": ";
        std::ostringstream parameters;
        parameters.imbue(std::locale::classic());
        parameters << std::setprecision(std::numeric_limits<float>::max_digits10);
        if (p.soft_float) {
            const auto& h = p.heading;
            parameters << "{\n"
                << "    \"update_period_steps\": " << h.update_period_steps << ",\n"
                << "    \"update_phase_steps\": " << h.update_phase_steps << ",\n"
                << "    \"frame_steps\": " << h.exposure_period_steps << ",\n"
                << "    \"stop_radius\": " << p.stop_radius << ",\n"
                << "    \"default_speed\": " << json_number(p.default_speed) << ", \"speed_clamp\": ["
                << json_number(p.min_speed) << ", " << json_number(p.max_speed) << "],\n"
                << "    \"turn_rate_radians\": \"atof(0.6)\",\n"
                << "    \"propulsion_window_degrees\": " << json_number(h.propulsion_window_degrees) << ",\n"
                << "    \"facing\": \"atof(0.07, 0.2, 0.2, 0.25, 0.001)\",\n"
                << "    \"frame_origin\": " << json_number(h.frame_origin) << ",\n"
                << "    \"clock_start_seconds\": " << json_number(wc3::sf::value(h.clock_start)) << ",\n"
                << (v2 ? "    \"library_clock\": \"sub(1000, floor32(1000 + floor(start, 2^-17) - scheduled)); "
                         "start = scheduled(0) = add(0.5, observe.start); scheduled += period per callback; "
                         "a callback observes every frame with clock <= scheduled\",\n"
                       : "    \"library_clock\": \"sub(1000, sub(add(start, 1000), scheduled)); "
                         "scheduled += 0.02 per callback\",\n")
                << "    \"arithmetic\": \"wc3::sf retail soft-float\"\n  }";
        } else if (p.heading.enabled) {
            const auto& h = p.heading;
            parameters << "{\n"
                << "    \"update_period_steps\": " << h.update_period_steps << ",\n"
                << "    \"update_phase_steps\": " << h.update_phase_steps << ",\n"
                << "    \"exposure_period_steps\": " << h.exposure_period_steps << ",\n"
                << "    \"stop_radius\": " << p.stop_radius << ",\n"
                << "    \"default_speed\": " << json_number(p.default_speed) << ", \"speed_clamp\": ["
                << json_number(p.min_speed) << ", " << json_number(p.max_speed) << "],\n"
                << "    \"turn_rate_radians\": " << json_number(h.turn_rate_radians) << ",\n"
                << "    \"propulsion_window_degrees\": " << json_number(h.propulsion_window_degrees) << ",\n"
                << "    \"facing_acceleration_radians\": " << json_number(h.facing_acceleration_radians) << ",\n"
                << "    \"facing_max_velocity_radians\": " << json_number(h.facing_max_velocity_radians) << ",\n"
                << "    \"facing_snap_radians\": " << json_number(h.facing_snap_radians) << ",\n"
                << "    \"facing_braking\": \"error * (error / max_velocity)^0.25\",\n"
                << "    \"frame_origin\": " << json_number(h.frame_origin) << ",\n"
                << "    \"float_rounding\": \"toward-zero\",\n"
                << "    \"opposite_angle_tie\": {\"turn\": \"counter-clockwise\", \"within_degrees\": 0}\n  }";
        } else {
            parameters << "{\n"
                << "    \"position_period_steps\": " << p.position_period_steps << ",\n"
                << "    \"facing_period_steps\": " << p.facing_period_steps << ",\n"
                << "    \"facing_phase_steps\": " << p.facing_phase_steps << ",\n"
                << "    \"move_delay_steps\": " << p.move_delay_steps << ",\n"
                << "    \"stop_radius\": " << p.stop_radius << ",\n"
                << "    \"default_speed\": " << json_number(p.default_speed) << ", \"speed_clamp\": ["
                << json_number(p.min_speed) << ", " << json_number(p.max_speed) << "],\n"
                << "    \"movement_angle_limit_degrees\": " << json_number(p.movement_angle_limit) << ",\n"
                << "    \"turn_ramp_radians\": [" << json_number(p.turn_ramp_radians[0]) << ", "
                << json_number(p.turn_ramp_radians[1]) << ", " << json_number(p.turn_ramp_radians[2]) << "],\n"
                << "    \"opposite_angle_tie\": {\"turn\": \"clockwise\", \"within_degrees\": "
                << json_number(p.opposite_tie_degrees) << "}\n  }";
        }
        identity << parameters.str() << ",\n  \"cases\": [\n";
        for (std::size_t i = 0; i < inputs.size(); ++i) {
            const auto& d = inputs[i].description;
            identity << "    {\"test\": \"" << d.experiment << "\", \"callbacks\": " << d.callbacks
                << ", \"units\": " << d.units.size() << ", \"samples\": " << traces[i].samples.size()
                << "}" << (i + 1 == inputs.size() ? "\n" : ",\n");
        }
        identity << "  ],\n  \"scenarios\": [\n";
        for (std::size_t i = 0; i < inputs.size(); ++i)
            identity << "    {\"experiment\": \"" << inputs[i].description.experiment
                << "\", \"map_revision\": \"" << inputs[i].description.map_revision
                << "\", \"path\": " << json_string(inputs[i].path)
                << ", \"sha256\": \"" << inputs[i].sha256 << "\"}" << (i + 1 == inputs.size() ? "\n" : ",\n");
        identity << "  ]\n}\n";
        write(output / "identity.json", identity.str());
        for (std::size_t i = 0; i < inputs.size(); ++i) {
            const auto& d = inputs[i].description;
            const auto& trace = traces[i];
            write(output / (d.experiment + ".csv"), movement::samples_csv(trace));
            write(output / (d.experiment + "-actions.csv"), movement::actions_csv(trace));
            const auto provenance = "{\"scenario\":{\"schema\":\"wc3-scenario\",\"version\":"
                + std::to_string(d.version) + ",\"path\":"
                + json_string(inputs[i].path) + ",\"sha256\":\"" + inputs[i].sha256 + "\"}}";
            write(output / (d.experiment + ".json"),
                  movement::canonical_json(trace, {d.experiment, d.map_revision, d.callbacks}, identity.str(),
                                           version, seed, before, build_source_sha256, parameters.str(), provenance));
        }
        std::cout << p.name << ": wrote " << inputs.size() << " finite scenario traces to " << output << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "wc3test: " << error.what() << '\n';
        return 2;
    }
}
