#include "Cases.h"
#include <cmath>
#include <iostream>
#include <stdexcept>

namespace {
void check(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}
}
int main() {
    try {
        wc3::Random a(12345), b(12345), c(54321);
        bool distinct = false;
        for (int i = 0; i < 10000; ++i) {
            const auto draw = a.next();
            check(draw == b.next(), "same RNG seed diverged");
            distinct |= draw != c.next();
        }
        check(distinct, "different RNG seeds produced identical streams");
        for (auto version : {wc3::ModelVersion::v1, wc3::ModelVersion::v2}) {
            wc3::World world(version, 13);
            wc3::Random unused(13);
            const auto id = world.create_footman({-123.25f, 384.5f}, 45);
            for (int i = 0; i < 12000; ++i) {
                world.step();
                const auto& unit = world.unit(id);
                check(unit.position().x == -123.25f && unit.position().y == 384.5f &&
                      unit.facing() == 45 && unit.current_order() == wc3::order_none,
                      "stationary unit changed");
            }
            check(world.random().next() == unused.next(), "stationary simulation consumed RNG");
            for (int number = 1; number <= 10; ++number) {
                const auto first = movement::run(number, version, 13);
                const auto second = movement::run(number, version, 13);
                check(movement::samples_csv(first) == movement::samples_csv(second),
                      "repeated sample bytes differ");
                check(movement::actions_csv(first) == movement::actions_csv(second),
                      "repeated action bytes differ");
                for (const auto& sample : first.samples) {
                    check(std::isfinite(sample.position.x) && std::isfinite(sample.position.y),
                          "nonfinite position");
                    check(sample.facing >= 0 && sample.facing < 360,
                          "facing outside circular range");
                }
            }
        }
        // A reversal turns clockwise even when float headings sit a few ULPs off 180.
        for (float facing : {0.0f, 0.00002f, 359.99998f}) {
            wc3::World world(wc3::ModelVersion::v2);
            const auto id = world.create_footman({0, 0}, facing);
            world.issue_point_order(id, wc3::order_move, {-1000, 0});
            while (world.steps() < world.parameters().facing_phase_steps) world.step();
            const float turned = world.unit(id).facing();
            check(turned > 350 && turned < 356, "opposite target did not turn clockwise");
        }
        std::cout << "RNG, stationary state, repeated ten-case bytes (both models) and "
                     "opposite-direction tie passed.\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
