// World invariants. Usage: world_tests SCENARIO_DIR (the committed scenarios/).
#include "Cases.h"
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>

namespace {
void check(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}
scenario::Scenario load(const std::filesystem::path& directory, int number) {
    std::ostringstream name;
    name << "MOV-" << std::setw(4) << std::setfill('0') << number << ".yaml";
    std::ifstream file(directory / name.str(), std::ios::binary);
    std::ostringstream bytes;
    bytes << file.rdbuf();
    if (!file) throw std::runtime_error("cannot read " + name.str());
    return scenario::parse(bytes.str());
}
}
int main(int argc, char** argv) {
    try {
        check(argc == 2, "usage: world_tests SCENARIO_DIR");
        const std::filesystem::path scenarios(argv[1]);
        wc3::Random a(12345), b(12345), c(54321);
        bool distinct = false;
        for (int i = 0; i < 10000; ++i) {
            const auto draw = a.next();
            check(draw == b.next(), "same RNG seed diverged");
            distinct |= draw != c.next();
        }
        check(distinct, "different RNG seeds produced identical streams");
        for (auto version : {wc3::ModelVersion::v1, wc3::ModelVersion::v2, wc3::ModelVersion::v3,
                             wc3::ModelVersion::v4}) {
            wc3::World world(version, 13);
            wc3::Random unused(13);
            const auto id = world.create_footman({-123.25f, 384.5f}, 45);
            const float facing = world.unit(id).facing();
            // v3 stores truncated float32 radians; 45 reads one float below. v4 reads
            // 45 * (pi/180) * (180/pi) with truncating soft-float multiplies.
            const float expected = version == wc3::ModelVersion::v3 ? std::nextafter(45.0f, 0.0f)
                : version == wc3::ModelVersion::v4 ? wc3::sf::value(0x4233ffff) : 45.0f;
            check(facing == expected, "initial facing reading");
            for (int i = 0; i < 12000; ++i) {
                world.step();
                const auto& unit = world.unit(id);
                check(unit.position().x == -123.25f && unit.position().y == 384.5f &&
                      unit.facing() == facing && unit.current_order() == wc3::order_none,
                      "stationary unit changed");
            }
            check(world.random().next() == unused.next(), "stationary simulation consumed RNG");
            for (int number = 1; number <= 10; ++number) {
                const auto description = load(scenarios, number);
                const auto first = movement::run(description, version, 13);
                const auto second = movement::run(description, version, 13);
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
        {
            // footman-v4 soft-float: fixed vectors from the reconstruction
            // (docs/footman-v4-model.md), guarding the formula-generated tables.
            namespace sf = wc3::sf;
            const std::pair<sf::F, sf::F> vectors[] = {
                {sf::sqrt(sf::bits(2.0f)), 0x3fb504f3}, {sf::sin(sf::one), 0x3f576ad1},
                {sf::cos(sf::one), 0x3f0a50f7}, {sf::acos(sf::bits(0.5f)), 0x3f860a91},
                {sf::acos(0x3f7fff07), 0x3bb2dd2f}, {sf::recip(sf::bits(3.0f)), 0x3eaaaaab},
                {sf::pow(sf::bits(0.5f), sf::atof("0.25")), 0x3f574500},
                {sf::atof("0.6"), 0x3f19999a}, {sf::exp(sf::one), 0x402df853},
                {sf::log(sf::bits(10.0f)), 0x40135d8d}, {sf::wrap_angle(sf::bits(-0.1f)), 0x40c5dca7},
                {sf::angle_to(0x40c8e323, 0x3b70844c), 0xbc159200},
                // Alignment rounds toward minus infinity: 4096 + 13/2048 - 0.0441940 -> -156/4096.
                {sf::add(0x4580000d, sf::mul(0xbfbc8fa0, 0x3cf5c280)), 0x457fff64}};
            for (const auto& [got, want] : vectors) check(got == want, "soft-float vector");
            // MOV-0002 callback 53: the heading is re-derived from the velocity each
            // update, which keeps this batch's Y at -155/4096 as in WC3.
            wc3::World world(wc3::ModelVersion::v4);
            const auto id = world.create_footman({0, 0}, 0);
            world.issue_point_order(id, wc3::order_move, {1000, 0});
            while (world.steps() < 1060) world.step();
            check(world.unit(id).position().y == -155.0f / 4096, "footman-v4 MOV-0002 callback 53");
            // The library clock: MOV-0004 callback 503 reads 10.059937, not 10.06.
            const auto trace = movement::run(load(scenarios, 4), wc3::ModelVersion::v4);
            check(trace.reported_time.at(503) == sf::value(0x4120f580), "footman-v4 library clock");
            check(movement::run(load(scenarios, 1), wc3::ModelVersion::v3).reported_time.empty(),
                  "only footman-v4 models the library clock");
        }
        std::cout << "RNG, stationary state, repeated ten-case bytes (four models), "
                     "opposite-direction tie, footman-v3 rules and footman-v4 vectors passed.\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
