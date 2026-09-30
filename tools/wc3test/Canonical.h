#pragma once
#include "Cases.h"

namespace movement {
std::string canonical_json(const Trace& trace, int number, const std::string& build_json,
                           wc3::ModelVersion version, std::uint32_t seed, bool before,
                           const std::string& source_sha256, const std::string& parameters);
}
