#include "Canonical.h"
#include <iomanip>
#include <limits>
#include <locale>
#include <sstream>
#include <stdexcept>

namespace movement {
namespace {
std::string value(float f) {
    std::ostringstream s;
    s.imbue(std::locale::classic());
    s << std::setprecision(std::numeric_limits<float>::max_digits10) << f;
    return s.str();
}
std::string time_string(std::uint64_t us) {
    std::ostringstream s;
    s.imbue(std::locale::classic());
    s << std::fixed << std::setprecision(6) << static_cast<double>(us) / 1000000;
    return s.str();
}
}
std::string canonical_json(const Trace& trace, const CaseIdentity& scenario, const std::string& build_json,
                           wc3::ModelVersion version, std::uint32_t seed, bool before,
                           const std::string& source_sha256, const std::string& parameters,
                           const std::string& provenance) {
    const auto p = wc3::model(version);
    // v2: a callback observes the frames whose clock is at most its float32
    // scheduled time; the requested time no longer fixes a state lag.
    const bool scheduled = trace.version == 2;
    const auto phase = scheduled ? "scheduled-sampler-time" : before ? "before-due-update" : "after-due-update";
    std::ostringstream out;
    out.imbue(std::locale::classic());
    out << "{\"schema\":\"wc3-trace\",\"version\":1,\"scenario\":{\"experiment\":\"" << scenario.experiment
        << "\",\"map_revision\":\"" << scenario.map_revision
        << "\",\"callbacks\":" << scenario.callbacks << ",\"requested_period\":\""
        << time_string(trace.period_us) << "\"},"
        << "\"identity\":{\"engine\":\"cpp\",\"build\":" << build_json
        << ",\"source\":{\"sha256\":\"" << source_sha256 << "\"},\"environment\":null,"
        << "\"seed\":{\"status\":\"explicit-cpp-only\",\"value\":" << seed << ",\"retail_equivalent\":false},"
        << "\"model\":{\"name\":\"" << p.name << "\",\"parameters\":" << parameters << "}},\"units\":[";
    for (std::size_t id = 0; id < trace.speeds.size(); ++id) {
        if (id) out << ',';
        out << "{\"name\":\"" << trace.names.at(id) << "\",\"type\":\"footman\",\"speed\":\"" << value(trace.speeds[id])
            << "\",\"default_speed\":\"" << value(p.default_speed) << "\"}";
    }
    out << "],\"time\":{\"unit\":\"seconds\",\"position_unit\":\"world-units\",\"facing_unit\":\"degrees\","
        << "\"numeric_format\":\"float-max_digits10\",\"clock_duration\":null,\"step_us\":" << p.step_us
        << ",\"observation_phase\":\"" << phase << "\",\"state_lag_us\":";
    if (scheduled) out << "null";
    else out << (before ? p.step_us : 0);
    out << "},\"records\":[\n";
    std::size_t seq = 0;
    auto header = [&](const char* kind, std::size_t recorded_seq) {
        if (recorded_seq != seq) throw std::runtime_error("trace sequence discontinuity");
        if (seq) out << ",\n";
        out << "{\"seq\":" << seq++ << ",\"kind\":\"" << kind << "\",\"source\":null";
    };
    auto control = [&](const char* kind) {
        header(kind, seq);
        out << ",\"fields\":[]}";
    };
    auto timing = [&](int cb, std::uint64_t state_us) {
        out << ",\"callback\":" << cb << ",\"time\":{\"requested\":\""
            << time_string(cb * trace.period_us) << "\",\"reported\":";
        if (trace.reported_time.empty()) out << "null";
        else out << '"' << value(trace.reported_time.at(cb)) << '"';
        out << ",\"state_us\":" << state_us << '}';
    };
    control("BEGIN");
    for (std::size_t id = 0; id < trace.speeds.size(); ++id) control("WATCH");
    control("RUN");
    std::size_t sample_index = 0, action_index = 0, event_index = 0;
    const std::string clock_key = trace.state_clock ? "c" + std::to_string(*trace.state_clock) + "_9" : "";
    for (int cb = 0; cb <= scenario.callbacks; ++cb) {
        header("TICK", trace.tick_sequences.at(cb));
        timing(cb, trace.samples.at(sample_index).state_us);
        out << '}';
        for (std::size_t id = 0; id < trace.speeds.size(); ++id) {
            const auto& s = trace.samples.at(sample_index++);
            header("SAMPLE", s.seq);
            timing(cb, s.state_us);
            out << ",\"unit\":\"" << trace.names.at(s.unit) << "\",\"values\":{\"x\":\"" << value(s.position.x)
                << "\",\"y\":\"" << value(s.position.y) << "\",\"facing\":\"" << value(s.facing)
                << "\",\"order\":\"" << s.order << "\"}}";
        }
        while (action_index < trace.actions.size() && trace.actions[action_index].callback == cb) {
            const auto& a = trace.actions[action_index++];
            header("ACTION", a.seq);
            timing(cb, a.state_us);
            out << ",\"unit\":\"" << trace.names.at(a.unit) << "\",\"command\":\"" << (a.order == wc3::order_move ? "move" : "stop")
                << "\",\"accepted\":" << (a.accepted ? "true" : "false") << ",\"target\":";
            if (a.order == wc3::order_move)
                out << "{\"x\":\"" << value(a.target.x) << "\",\"y\":\"" << value(a.target.y) << "\"}";
            else out << "null";
            out << '}';
        }
        while (event_index < trace.events.size() && trace.events[event_index].callback == cb) {
            const auto& e = trace.events[event_index++];
            header("EVENT", e.seq);
            timing(cb, e.state_us);
            out << ",\"name\":\"STATE\",\"values\":{\"" << clock_key << "\":\"" << value(e.clock)
                << "\",\"x_9\":\"" << value(e.position.x) << "\",\"y_9\":\"" << value(e.position.y)
                << "\",\"facing_9\":\"" << value(e.facing) << "\"}}";
        }
    }
    control("END");
    out << "],\"completion\":{\"complete\":true,\"records\":" << seq
        << ",\"ticks\":" << trace.tick_sequences.size() << ",\"samples\":" << trace.samples.size()
        << ",\"actions\":" << trace.actions.size() << ",\"events\":" << trace.events.size()
        << "},\"provenance\":" << provenance << "}\n";
    return out.str();
}
}
