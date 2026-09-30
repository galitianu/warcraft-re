#include "BuildIdentity.h"
#include "Cases.h"
#include "Canonical.h"
#include <charconv>
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

namespace {
void write(const std::filesystem::path& path, const std::string& bytes) {
    std::ofstream file(path, std::ios::binary);
    file.exceptions(std::ios::badbit | std::ios::failbit);
    file << bytes;
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
        auto version = wc3::ModelVersion::v2;
        std::uint32_t seed = 1;
        bool before = false;
        for (int i = 1; i < argc; ++i) {
            const std::string option = argv[i];
            if (option == "--help") {
                std::cout << "wc3test --out DIR [--model v1|v2] [--seed UINT32] "
                             "[--phase after|before]\n";
                return 0;
            }
            if (i + 1 == argc) throw std::invalid_argument("missing option value");
            const std::string value = argv[++i];
            if (option == "--out") output = value;
            else if (option == "--model" && (value == "v1" || value == "v2"))
                version = value == "v1" ? wc3::ModelVersion::v1 : wc3::ModelVersion::v2;
            else if (option == "--phase" && (value == "after" || value == "before"))
                before = value == "before";
            else if (option == "--seed") {
                const auto parsed = std::from_chars(value.data(), value.data() + value.size(), seed);
                if (parsed.ec != std::errc{} || parsed.ptr != value.data() + value.size())
                    throw std::invalid_argument("seed must be a uint32");
            } else throw std::invalid_argument("unknown option or invalid value: " + option);
        }
        if (output.empty()) throw std::invalid_argument("--out DIR is required");
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
            << "  \"observation_phase\": \"" << (before ? "before" : "after") << "-due-update\",\n"
            << "  \"sample_period_us\": " << movement::sample_period_us << ",\n"
            // t is the requested callback time; before-phase state omits the step due then.
            << "  \"state_lag_us\": " << (before ? p.step_us : 0) << ",\n"
            << "  \"parameters\": ";
        std::ostringstream parameters;
        parameters.imbue(std::locale::classic());
        parameters << std::setprecision(std::numeric_limits<float>::max_digits10);
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
        identity << parameters.str() << ",\n  \"cases\": [\n";
        std::vector<movement::Trace> traces;
        for (int number = 1; number <= 10; ++number) {
            const auto name = movement::case_name(number);
            const auto trace = movement::run(number, version, seed, before);
            traces.push_back(trace);
            write(output / (name + ".csv"), movement::samples_csv(trace));
            write(output / (name + "-actions.csv"), movement::actions_csv(trace));
            identity << "    {\"test\": \"" << name << "\", \"callbacks\": "
                << movement::case_callbacks(number) << ", \"units\": " << movement::case_units(number)
                << ", \"samples\": " << trace.samples.size() << "}"
                << (number == 10 ? "\n" : ",\n");
        }
        identity << "  ]\n}\n";
        write(output / "identity.json", identity.str());
        for (int number = 1; number <= 10; ++number)
            write(output / (movement::case_name(number) + ".json"),
                  movement::canonical_json(traces[number - 1], number, identity.str(),
                                           version, seed, before, build_source_sha256, parameters.str()));
        std::cout << p.name << ": wrote ten finite traces to " << output << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "wc3test: " << error.what() << '\n';
        return 2;
    }
}
