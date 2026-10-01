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
        for (auto version : {wc3::ModelVersion::v1, wc3::ModelVersion::v2, wc3::ModelVersion::v3}) {
            wc3::World world(version, 13);
            wc3::Random unused(13);
            const auto id = world.create_footman({-123.25f, 384.5f}, 45);
            // v3 stores truncated float32 radians; 45 reads one float below.
            const float facing = world.unit(id).facing();
            check(facing == (version == wc3::ModelVersion::v3 ? std::nextafter(45.0f, 0.0f) : 45.0f),
                  "initial facing reading");
            for (int i = 0; i < 12000; ++i) {
                world.step();
                const auto& unit = world.unit(id);
                check(unit.position().x == -123.25f && unit.position().y == 384.5f &&
                      unit.facing() == facing && unit.current_order() == wc3::order_none,
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
        // footman-v3: 30 ms batches truncated in the map-corner frame, shown every 5 ms.
        {
            wc3::World world(wc3::ModelVersion::v3);
            const auto id = world.create_footman({0, 0}, 0);
            world.issue_point_order(id, wc3::order_move, {1000, 0});
            while (world.steps() < 15) world.step();
            check(world.unit(id).position().x == 5528.0f / 4096, "first exposure");
            while (world.steps() < 39) world.step();
            check(world.unit(id).position().x == 27646.0f / 4096, "fifth exposure");
            world.step();
            check(world.unit(id).position().x == 33176.0f / 4096 && world.unit(id).position().y == 0,
                  "batch end on the 1/2048 grid");
        }
        {
            // West of the frame origin's 4096 boundary the grid is 1/4096 and truncation
            // lengthens the step; 180 degrees reads one float below and needs no turn.
            wc3::World world(wc3::ModelVersion::v3);
            const auto id = world.create_footman({0, 0}, 180);
            check(world.unit(id).facing() == std::nextafter(180.0f, 0.0f), "180 reading");
            world.issue_point_order(id, wc3::order_move, {-1000, 0});
            while (world.steps() < 40) world.step();
            check(world.unit(id).position().x == -33178.0f / 4096, "westward batch");
        }
        {
            // Reported facing ramps 0.07 then 0.14 rad while the hidden heading turns
            // 0.6 rad; the pre-turn 90 degree error blocks movement at the first update.
            wc3::World world(wc3::ModelVersion::v3);
            const auto id = world.create_footman({0, 0}, 0);
            world.issue_point_order(id, wc3::order_move, {0, 1000});
            while (world.steps() < 10) world.step();
            check(std::abs(world.unit(id).facing() - 4.0107045f) < 1e-5f, "first facing ramp");
            while (world.steps() < 40) world.step();
            check(std::abs(world.unit(id).facing() - 12.0321136f) < 1e-5f, "second facing ramp");
            check(world.unit(id).position().x == 0 && world.unit(id).position().y == 0,
                  "propulsion window allowed movement");
            while (world.steps() < 75) world.step();
            check(world.unit(id).position().y > 0, "movement after the turn entered the window");
        }
        {
            // An exact reversal turns counter-clockwise; a stop freezes position at once.
            wc3::World world(wc3::ModelVersion::v3);
            const auto id = world.create_footman({0, 0}, 0);
            world.issue_point_order(id, wc3::order_move, {-1000, 0});
            while (world.steps() < 10) world.step();
            check(world.unit(id).facing() > 3 && world.unit(id).facing() < 5, "reversal direction");
            world.issue_point_order(id, wc3::order_move, {1000, 0});
            while (world.steps() < 100) world.step();
            const auto stopped = world.unit(id).position();
            world.issue_immediate_order(id, wc3::order_stop);
            while (world.steps() < 400) world.step();
            check(world.unit(id).position().x == stopped.x && world.unit(id).current_order() == 0,
                  "stop did not freeze position");
        }
        std::cout << "RNG, stationary state, repeated ten-case bytes (three models), "
                     "opposite-direction tie and footman-v3 rules passed.\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
