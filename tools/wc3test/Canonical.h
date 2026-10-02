#pragma once
#include "Cases.h"

namespace movement {
// provenance is a JSON object: "{}" for the hard-coded cases, or the scenario's
// path and SHA-256 when the schedule came from a description.
std::string canonical_json(const Trace& trace, const CaseIdentity& scenario, const std::string& build_json,
                           wc3::ModelVersion version, std::uint32_t seed, bool before,
                           const std::string& source_sha256, const std::string& parameters,
                           const std::string& provenance = "{}");
}
