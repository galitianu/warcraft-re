// One-time v1 -> v2 evidence migration on the original macOS/libc++ scope.
// Reconstruct the legacy bytes, require EVERY original live hash to match, then
// emit the portable digest of that same world. No new live capture is claimed.
// See results/client-v1/README.md for the command and retained migration reports.
#include "Scenario.h"
#include "core/Session.h"
#include <fstream>
#include <iostream>
#include <map>
#include <random>
#include <sstream>
#include <stdexcept>

std::string read(const char* path) {
    std::ifstream in(path, std::ios::binary);
    if (!in) throw std::runtime_error("cannot open input");
    std::ostringstream out;
    out << in.rdbuf();
    return out.str();
}

int main(int argc, char** argv) {
    try {
        if (argc != 4) throw std::runtime_error("usage: migrate RECORDING LEGACY_CHECKPOINTS OUTPUT");
        const auto recording_bytes = read(argv[1]);
        const auto legacy_bytes = read(argv[2]);
        const auto recording = wc3::parse_recording(recording_bytes);
        std::istringstream input(legacy_bytes);
        std::string header;
        std::getline(input, header);
        if (header != "wc3-checkpoints 1") throw std::runtime_error("expected legacy v1");
        std::map<std::uint64_t, std::string> expected;
        std::string key, hash;
        std::uint64_t time;
        while (input >> key >> time >> hash) {
            if (key != "checkpoint" || hash.size() != 64 || !expected.emplace(time, hash).second)
                throw std::runtime_error("invalid legacy checkpoint");
        }
        if (!input.eof() || expected.empty() || !expected.count(0) || !expected.count(recording.end_us))
            throw std::runtime_error("incomplete legacy checkpoints");

        // No gameplay path in this scene consumes RNG. The original library's
        // engine insertion is used only here to reconstruct its retained bytes.
        std::ostringstream engine;
        engine << std::mt19937(recording.seed);
        wc3::Random random(recording.seed);
        const auto suffix = random.state();
        const std::string prefix = "wc3-world-snapshot 2\n";
        wc3::Session session(recording.seed);
        for (const auto& command : recording.commands) session.schedule(command);
        std::ostringstream portable, report;
        portable << "wc3-checkpoints 2\n";
        report << "{\n  \"recording_sha256\": \"" << scenario::sha256_hex(recording_bytes)
               << "\",\n  \"legacy_file_sha256\": \"" << scenario::sha256_hex(legacy_bytes)
               << "\",\n  \"checkpoints\": [";
        bool first = true;
        for (const auto& [checkpoint, old_hash] : expected) {
            if (checkpoint % session.frame_us() || checkpoint > recording.end_us)
                throw std::runtime_error("invalid checkpoint time");
            while (session.time_us() < checkpoint) session.advance_frame();
            const auto current = session.world().snapshot();
            if (current.substr(0, prefix.size()) != prefix ||
                current.substr(current.size() - suffix.size()) != suffix)
                throw std::runtime_error("unexpected snapshot schema or consumed RNG");
            auto legacy = current.substr(prefix.size(), current.size() - prefix.size() - suffix.size());
            legacy += engine.str();
            if (scenario::sha256_hex(legacy) != old_hash)
                throw std::runtime_error("original live hash differs at " + std::to_string(checkpoint));
            const auto new_hash = scenario::sha256_hex(current);
            portable << "checkpoint " << checkpoint << ' ' << new_hash << '\n';
            report << (first ? "\n    " : ",\n    ") << "{\"time_us\": " << checkpoint
                   << ", \"legacy_sha256\": \"" << old_hash << "\", \"verified\": true, \"portable_sha256\": \""
                   << new_hash << "\"}";
            first = false;
        }
        report << "\n  ],\n  \"portable_file_sha256\": \"" << scenario::sha256_hex(portable.str())
               << "\",\n  \"status\": \"PASS\"\n}\n";
        // Write only after all original live checkpoints have been verified.
        std::ofstream out(argv[3], std::ios::binary);
        out << portable.str();
        if (!out) throw std::runtime_error("cannot write output");
        std::cout << report.str();
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "migration: " << error.what() << '\n';
        return 1;
    }
}
