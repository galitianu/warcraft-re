// Prints footman-v4's state after every 1 ms step for one Footman and one move
// order issued at step 0 (or ORDER_STEP), as float32 bit patterns: "step x y facing".
// The 1 ms oracle captures (JASS-0001-p001, MOV-0012) read these through
// tools/compare_states.py; MOV-0013 analysis uses ORDER_STEP.
#include "core/World.h"
#include <bit>
#include <cstdio>
#include <exception>
#include <string>

int main(int argc, char** argv) {
    if (argc != 7 && argc != 8) {
        std::fprintf(stderr, "wc3states START_X START_Y FACING TARGET_X TARGET_Y STEPS [ORDER_STEP]\n");
        return 2;
    }
    try {
        const auto number = [&](int i) { return std::stof(argv[i]); };
        wc3::World world(wc3::ModelVersion::v4, 1);
        const auto id = world.create_footman({number(1), number(2)}, number(3));
        const unsigned long steps = std::stoul(argv[6]), order = argc == 8 ? std::stoul(argv[7]) : 0;
        for (unsigned long step = 0; step <= steps; ++step) {
            if (step) world.step();
            if (step == order) world.issue_point_order(id, wc3::order_move, {number(4), number(5)});
            const auto& unit = world.unit(id);
            std::printf("%lu %08x %08x %08x\n", step, std::bit_cast<std::uint32_t>(unit.position().x),
                        std::bit_cast<std::uint32_t>(unit.position().y),
                        std::bit_cast<std::uint32_t>(unit.facing()));
        }
    } catch (const std::exception& error) {
        std::fprintf(stderr, "wc3states: %s\n", error.what());
        return 2;
    }
    return 0;
}
