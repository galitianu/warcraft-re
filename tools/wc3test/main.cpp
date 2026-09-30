#include "BuildIdentity.h"
#include "Cases.h"
#include <charconv>
#include <filesystem>
#include <fstream>
#include <iostream>
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
        identity << "{\n  \"git_commit\": \"" << build_git_commit << "\",\n"
            << "  \"git_dirty_at_configure\": " << (build_git_dirty ? "true" : "false") << ",\n"
            << "  \"source_sha256\": \"" << build_source_sha256 << "\",\n"
            << "  \"compiler\": \"" << build_compiler << "\",\n"
            << "  \"build_type\": \"" << build_type << "\",\n"
            << "  \"architecture\": \"" << build_architecture << "\",\n"
            << "  \"fp_contract\": \"off\",\n  \"model\": \"" << p.name << "\",\n"
            << "  \"time_unit\": \"seconds\",\n  \"step_us\": " << p.step_us << ",\n"
            << "  \"seed\": " << seed << ",\n  \"rng\": \"std::mt19937; unused by movement\",\n"
            << "  \"observation_phase\": \"" << (before ? "before" : "after") << "-due-update\",\n"
            << "  \"sample_period_us\": 20000,\n  \"parameters\": {\n"
            << "    \"position_period_steps\": " << p.position_period_steps << ",\n"
            << "    \"facing_period_steps\": " << p.facing_period_steps << ",\n"
            << "    \"facing_phase_steps\": " << p.facing_phase_steps << ",\n"
            << "    \"move_delay_steps\": " << p.move_delay_steps << ",\n"
            << "    \"stop_radius\": " << p.stop_radius << ",\n"
            << "    \"default_speed\": 270, \"speed_clamp\": [150, 400],\n"
            << "    \"movement_angle_limit_degrees_v2\": " << p.movement_angle_limit << ",\n"
            << "    \"turn_ramp_radians_v2\": [0.07, 0.14, 0.2],\n"
            << "    \"opposite_angle_tie_v2\": \"clockwise\"\n  },\n  \"cases\": [\n";
        for (int number = 1; number <= 10; ++number) {
            const auto name = movement::case_name(number);
            const auto trace = movement::run(number, version, seed, before);
            write(output / (name + ".csv"), movement::samples_csv(trace));
            write(output / (name + "-actions.csv"), movement::actions_csv(trace));
            identity << "    {\"test\": \"" << name << "\", \"callbacks\": "
                << (number == 4 ? 600 : 250) << ", \"units\": " << (number == 2 ? 2 : 1)
                << ", \"samples\": " << trace.samples.size() << "}"
                << (number == 10 ? "\n" : ",\n");
        }
        identity << "  ]\n}\n";
        write(output / "identity.json", identity.str());
        std::cout << p.name << ": wrote ten finite traces to " << output << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "wc3test: " << error.what() << '\n';
        return 2;
    }
}
