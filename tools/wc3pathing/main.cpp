// Runs one v1 scenario under footman-v4 with candidate unit-pathing parameters, for
// pre-registered predictions (MOV-0019, docs/mov-0019.md). Never a canonical trace:
// each stdin line is one parameter set,
//   "line_clearance waypoint_radius block_radius block_lookahead block_lateral recheck_updates",
// and stdout gets "# set N" followed by that run's samples CSV.
#include "Cases.h"
#include "Scenario.h"
#include <cstdio>
#include <exception>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>

int main(int argc, char** argv) {
    if (argc != 2) {
        std::fprintf(stderr, "wc3pathing SCENARIO < parameter sets\n");
        return 2;
    }
    try {
        std::ifstream stream(argv[1], std::ios::binary);
        if (!stream) throw std::invalid_argument(std::string("cannot read scenario ") + argv[1]);
        std::ostringstream bytes;
        bytes << stream.rdbuf();
        const auto description = scenario::parse(bytes.str());
        std::string line;
        for (int set = 0; std::getline(std::cin, line); ++set) {
            std::istringstream fields(line);
            auto pathing = wc3::model(wc3::ModelVersion::v4).pathing;
            if (!(fields >> pathing.line_clearance >> pathing.waypoint_radius >> pathing.block_radius >>
                  pathing.block_lookahead >> pathing.block_lateral >> pathing.recheck_updates))
                throw std::invalid_argument("bad parameter set: " + line);
            const auto trace = movement::run(description, wc3::ModelVersion::v4, 1, false, &pathing);
            std::cout << "# set " << set << '\n' << movement::samples_csv(trace);
        }
    } catch (const std::exception& error) {
        std::fprintf(stderr, "wc3pathing: %s\n", error.what());
        return 2;
    }
    return 0;
}
