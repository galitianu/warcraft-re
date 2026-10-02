#include "Scenario.h"
#include <cmath>
#include <cstdio>
#include <utility>

namespace scenario {
namespace {
[[noreturn]] void fail(int line, const std::string& message) {
    throw Error(line > 0 ? "line " + std::to_string(line) + ": " + message : message);
}

// The accepted YAML subset (docs/scenario-v1.md): printable ASCII, LF lines,
// space indentation, block mappings/sequences, one-line flow sequences of
// scalars, plain or simply quoted scalars, comments, and a required '...' end.
// Anchors, aliases, tags, flow mappings, block scalars and escapes are rejected.
struct Entry;
struct Node {
    enum class Kind { scalar, sequence, mapping } kind = Kind::scalar;
    int line = 0;
    std::string text;
    bool quoted = false;
    std::vector<Node> items;
    std::vector<Entry> entries;
};
struct Entry {
    std::string key;
    int line;
    Node value;
};
struct Line {
    int number;
    std::size_t indent;
    std::string text;
};
constexpr std::size_t max_bytes = 65536, max_depth = 8, max_items = 1000;

bool lower(char c) { return c >= 'a' && c <= 'z'; }
bool digit(char c) { return c >= '0' && c <= '9'; }
bool plain(char c) {
    return lower(c) || digit(c) || (c >= 'A' && c <= 'Z') || c == '_' || c == '.' || c == '-' || c == '+';
}

std::vector<Line> split(std::string_view text) {
    if (text.size() > max_bytes) fail(0, "scenario exceeds 65536 bytes");
    if (text.empty() || text.back() != '\n') fail(0, "scenario must end with a newline (truncated?)");
    std::vector<Line> lines;
    int number = 0;
    bool ended = false;
    for (std::size_t start = 0; start < text.size();) {
        const auto end = text.find('\n', start);
        std::string_view content = text.substr(start, end - start);
        start = end + 1;
        ++number;
        for (const char raw : content) {
            const auto c = static_cast<unsigned char>(raw);
            if (c == '\t') fail(number, "tabs are not allowed; indent with spaces");
            if (c == '\r') fail(number, "carriage return; use LF line endings");
            if (c < 0x20 || c > 0x7e) fail(number, "only printable ASCII is allowed");
        }
        const auto indent = content.find_first_not_of(' ');
        if (indent == std::string_view::npos || content[indent] == '#') continue;
        content.remove_prefix(indent);
        if (const auto comment = content.find(" #"); comment != std::string_view::npos)
            content = content.substr(0, comment);
        while (content.back() == ' ') content.remove_suffix(1);
        if (ended) fail(number, "content after the document end marker '...'");
        if (content == "...") {
            if (indent) fail(number, "the document end marker must not be indented");
            ended = true;
            continue;
        }
        if (content.substr(0, 3) == "---") fail(number, "document start markers and multiple documents are unsupported");
        lines.push_back({number, indent, std::string(content)});
    }
    if (!ended) fail(number, "missing document end marker '...' (truncated?)");
    if (lines.empty()) fail(0, "empty scenario");
    return lines;
}

Node scalar(std::string_view text, int line) {
    Node node;
    node.line = line;
    if (text.front() == '"') {
        if (text.size() < 2 || text.back() != '"') fail(line, "unterminated quoted scalar");
        node.quoted = true;
        text = text.substr(1, text.size() - 2);
    }
    if (text.empty()) fail(line, "empty scalar");
    for (const char c : text)
        if (!plain(c))
            fail(line, std::string("unsupported character '") + c + "' (outside the v1 YAML subset: "
                 "no anchors, aliases, tags, flow mappings, block scalars, escapes or spaces in scalars)");
    node.text = text;
    return node;
}

Node inline_value(std::string_view text, int line) {
    if (text.front() != '[') return scalar(text, line);
    if (text.back() != ']') fail(line, "unterminated flow sequence");
    Node node;
    node.kind = Node::Kind::sequence;
    node.line = line;
    const auto body = text.substr(1, text.size() - 2);
    if (body.find_first_not_of(' ') == std::string_view::npos) return node;
    for (std::size_t start = 0;;) {
        const auto comma = body.find(',', start);
        auto part = body.substr(start, comma == std::string_view::npos ? std::string_view::npos : comma - start);
        while (!part.empty() && part.front() == ' ') part.remove_prefix(1);
        while (!part.empty() && part.back() == ' ') part.remove_suffix(1);
        if (part.empty()) fail(line, "empty flow sequence item");
        node.items.push_back(scalar(part, line));
        if (comma == std::string_view::npos) break;
        start = comma + 1;
    }
    return node;
}

class Parser {
public:
    explicit Parser(std::vector<Line> lines) : lines_(std::move(lines)) {}
    Node document() {
        if (lines_[0].indent != 0) fail(lines_[0].number, "the top level must not be indented");
        Node root = block(0, 0);
        if (root.kind != Node::Kind::mapping) fail(root.line, "the top level must be a mapping");
        if (i_ != lines_.size()) fail(lines_[i_].number, "unexpected indentation");
        return root;
    }
private:
    static bool item(const std::string& text) { return text == "-" || text.rfind("- ", 0) == 0; }
    bool more(std::size_t indent) const { return i_ < lines_.size() && lines_[i_].indent == indent; }
    void no_deeper(std::size_t indent) const {
        if (i_ < lines_.size() && lines_[i_].indent > indent) fail(lines_[i_].number, "unexpected indentation");
    }
    Node block(std::size_t indent, std::size_t depth) {
        if (depth > max_depth) fail(lines_[i_].number, "nesting deeper than 8 levels");
        return item(lines_[i_].text) ? sequence(indent, depth) : mapping(indent, depth);
    }
    // A nested block is indented further than the line that opens it, except that
    // a mapping key's sequence may also start at the key's own indentation.
    Node child(const Line& parent, std::size_t indent, std::size_t depth, const std::string& what,
               bool key = false) {
        const bool same = key && more(indent) && item(lines_[i_].text);
        if (!same && (i_ == lines_.size() || lines_[i_].indent <= indent)) fail(parent.number, what);
        return block(lines_[i_].indent, depth + 1);
    }
    Node mapping(std::size_t indent, std::size_t depth) {
        Node node;
        node.kind = Node::Kind::mapping;
        node.line = lines_[i_].number;
        while (more(indent)) {
            const Line line = lines_[i_++];
            if (item(line.text)) fail(line.number, "sequence item where a mapping key was expected");
            const auto colon = line.text.find(':');
            if (colon == std::string::npos) fail(line.number, "expected 'key: value'");
            const std::string key = line.text.substr(0, colon);
            if (key.empty() || key.size() > 32 || !lower(key[0]))
                fail(line.number, "invalid key '" + key + "'");
            for (const char c : key)
                if (!lower(c) && !digit(c) && c != '_') fail(line.number, "invalid key '" + key + "'");
            for (const auto& entry : node.entries)
                if (entry.key == key) fail(line.number, "duplicate key '" + key + "'");
            const std::string_view rest = std::string_view(line.text).substr(colon + 1);
            if (!rest.empty() && rest.front() != ' ') fail(line.number, "expected a space after ':'");
            const auto first = rest.find_first_not_of(' ');
            Node value = first == std::string_view::npos
                ? child(line, indent, depth, "missing value for '" + key + "'", true)
                : inline_value(rest.substr(first), line.number);
            node.entries.push_back({key, line.number, std::move(value)});
        }
        no_deeper(indent);
        return node;
    }
    Node sequence(std::size_t indent, std::size_t depth) {
        Node node;
        node.kind = Node::Kind::sequence;
        node.line = lines_[i_].number;
        while (more(indent) && item(lines_[i_].text)) {
            if (node.items.size() == max_items) fail(lines_[i_].number, "more than 1000 sequence items");
            Line& line = lines_[i_];
            const std::string rest = line.text.substr(1);
            const auto first = rest.find_first_not_of(' ');
            if (first == std::string::npos) {
                const Line opener = lines_[i_++];
                node.items.push_back(child(opener, indent, depth, "empty sequence item"));
            } else if (rest.find(':') != std::string::npos) {
                // "- key: value" opens a mapping whose keys align after the dash.
                line.indent = indent + 1 + first;
                line.text = rest.substr(first);
                node.items.push_back(mapping(line.indent, depth + 1));
            } else {
                node.items.push_back(inline_value(std::string_view(rest).substr(first), line.number));
                ++i_;
            }
        }
        no_deeper(indent);
        return node;
    }
    std::vector<Line> lines_;
    std::size_t i_ = 0;
};

// ---- Semantic layer: typed fields with line-numbered errors.

const char* kind_name(Node::Kind kind) {
    return kind == Node::Kind::scalar ? "a scalar" : kind == Node::Kind::sequence ? "a sequence" : "a mapping";
}
void expect(const Node& node, Node::Kind kind, const std::string& what) {
    if (node.kind != kind) fail(node.line, what + " must be " + kind_name(kind));
}
const Node* find(const Node& map, std::string_view key) {
    for (const auto& entry : map.entries)
        if (entry.key == key) return &entry.value;
    return nullptr;
}
const Node& get(const Node& map, std::string_view key) { return *find(map, key); }
void fields(const Node& node, std::initializer_list<std::string_view> required,
            std::initializer_list<std::string_view> optional, const std::string& what) {
    expect(node, Node::Kind::mapping, what);
    for (const auto& entry : node.entries) {
        bool known = false;
        for (const auto key : required) known |= key == entry.key;
        for (const auto key : optional) known |= key == entry.key;
        if (!known) fail(entry.line, "unsupported field '" + entry.key + "' in " + what);
    }
    for (const auto key : required)
        if (!find(node, key)) fail(node.line, "missing field '" + std::string(key) + "' in " + what);
}
std::string word(const Node& node, const std::string& what) {
    expect(node, Node::Kind::scalar, what);
    if (!node.quoted) {
        std::string folded;
        for (const char c : node.text) folded += c >= 'A' && c <= 'Z' ? static_cast<char>(c - 'A' + 'a') : c;
        // YAML 1.1 reads these unquoted words as booleans/null; require quotes.
        for (const char* ambiguous : {"y", "n", "yes", "no", "true", "false", "on", "off", "null"})
            if (folded == ambiguous)
                fail(node.line, what + " '" + node.text + "' is a YAML boolean or null unless quoted");
    }
    return node.text;
}
bool matches(std::string_view text, std::size_t min, std::size_t max, bool (*ok)(char)) {
    if (text.size() < min || text.size() > max) return false;
    for (const char c : text)
        if (!ok(c)) return false;
    return true;
}

// Exact unsigned decimal: mantissa / 10^scale, sign kept separately.
struct Decimal {
    bool negative = false;
    std::uint64_t mantissa = 0;
    int scale = 0;
    int integer_digits = 0;
};
std::optional<Decimal> decimal(std::string_view text) {
    Decimal d;
    if (!text.empty() && text.front() == '-') {
        d.negative = true;
        text.remove_prefix(1);
    }
    const auto dot = text.find('.');
    const auto whole = text.substr(0, dot);
    if (whole.empty() || !matches(whole, 1, 64, digit) || (whole.size() > 1 && whole[0] == '0'))
        return std::nullopt;
    std::string_view fraction;
    if (dot != std::string_view::npos) {
        fraction = text.substr(dot + 1);
        if (!matches(fraction, 1, 64, digit)) return std::nullopt;
    }
    d.integer_digits = static_cast<int>(whole.size());
    d.scale = static_cast<int>(fraction.size());
    if (d.integer_digits > 6 || d.scale > 9) {
        d.mantissa = UINT64_MAX; // Reported by callers as out of range/precision.
        return d;
    }
    for (const char c : whole) d.mantissa = d.mantissa * 10 + static_cast<std::uint64_t>(c - '0');
    for (const char c : fraction) d.mantissa = d.mantissa * 10 + static_cast<std::uint64_t>(c - '0');
    return d;
}
// Nearest float32 to mantissa / 10^scale with ties to even, in exact integer
// arithmetic. Bounded inputs (< 10^6, <= 9 fractional digits) fit in 64 bits.
float to_float(const Decimal& d) {
    if (d.mantissa == 0) return d.negative ? -0.0f : 0.0f;
    std::uint64_t power = 1;
    for (int i = 0; i < d.scale; ++i) power *= 10;
    const auto bits = [](std::uint64_t v) { int n = 0; for (; v; v >>= 1) ++n; return n; };
    int shift = 24 + bits(power) - bits(d.mantissa);
    std::uint64_t quotient = 0, remainder = 0, divisor = 0;
    for (;;) {
        const std::uint64_t numerator = shift >= 0 ? d.mantissa << shift : d.mantissa;
        divisor = shift >= 0 ? power : power << -shift;
        quotient = numerator / divisor;
        remainder = numerator % divisor;
        if (quotient >= (1u << 24)) --shift;
        else if (quotient < (1u << 23)) ++shift;
        else break;
    }
    if (2 * remainder > divisor || (2 * remainder == divisor && (quotient & 1))) ++quotient;
    const float magnitude = std::ldexp(static_cast<float>(quotient), -shift);
    return d.negative ? -magnitude : magnitude;
}
float real(const Node& node, const std::string& what, float lo, float hi) {
    expect(node, Node::Kind::scalar, what);
    const auto d = node.quoted ? std::nullopt : decimal(node.text);
    if (!d) fail(node.line, what + " must be an unquoted decimal like -12.5 (no exponent, sign '+', inf or nan)");
    if (d->integer_digits > 6) fail(node.line, what + " is out of range");
    if (d->scale > 9) fail(node.line, what + " has more than 9 fractional digits");
    const float value = to_float(*d);
    if (!(value >= lo && value <= hi)) fail(node.line, what + " is outside its supported range");
    return value;
}
std::uint64_t microseconds(const Node& node, const std::string& what) {
    expect(node, Node::Kind::scalar, what);
    const auto d = node.quoted ? std::nullopt : decimal(node.text);
    if (!d || d->negative) fail(node.line, what + " must be an unquoted non-negative decimal of seconds");
    if (d->integer_digits > 6) fail(node.line, what + " is out of range");
    if (d->scale > 6) fail(node.line, what + " is not a whole number of microseconds; it is never rounded");
    std::uint64_t us = d->mantissa;
    for (int i = d->scale; i < 6; ++i) us *= 10;
    return us;
}
long integer(const Node& node, const std::string& what, long lo, long hi) {
    expect(node, Node::Kind::scalar, what);
    if (node.quoted || !matches(node.text, 1, 9, digit) || (node.text.size() > 1 && node.text[0] == '0'))
        fail(node.line, what + " must be an unquoted integer");
    const long value = std::stol(node.text);
    if (value < lo || value > hi)
        fail(node.line, what + " must be in [" + std::to_string(lo) + ", " + std::to_string(hi) + "]");
    return value;
}
wc3::Vec2 pair(const Node& node, const std::string& what, float limit) {
    expect(node, Node::Kind::sequence, what);
    if (node.items.size() != 2) fail(node.line, what + " must be [x, y]");
    return {real(node.items[0], what + " x", -limit, limit), real(node.items[1], what + " y", -limit, limit)};
}
bool identifier_char(char c) { return lower(c) || digit(c) || c == '_'; }
bool revision_char(char c) { return lower(c) || digit(c) || c == '-'; }
}

float decimal_to_float(std::string_view text) {
    const auto d = decimal(text);
    if (!d || d->integer_digits > 6 || d->scale > 9) throw Error("unsupported decimal");
    return to_float(*d);
}

Scenario parse(std::string_view text) {
    const Node root = Parser(split(text)).document();
    // Identify the schema before anything else so a newer version fails clearly.
    const Node* schema = find(root, "schema");
    const Node* version = find(root, "version");
    if (!schema || word(*schema, "schema") != "wc3-scenario")
        fail(schema ? schema->line : root.line, "not a wc3-scenario document");
    if (!version) fail(root.line, "missing field 'version'");
    if (integer(*version, "version", 0, 999999) != 1)
        fail(version->line, "unsupported scenario version " + version->text + "; this runner reads version 1");
    fields(root, {"schema", "version", "experiment", "map_revision", "units", "observe", "actions"}, {}, "scenario");

    Scenario s;
    const Node& experiment = get(root, "experiment");
    s.experiment = word(experiment, "experiment");
    const auto dash = s.experiment.find('-');
    if (dash < 2 || dash > 5 || s.experiment.size() != dash + 5
        || !matches(s.experiment.substr(0, dash), 2, 5, [](char c) { return c >= 'A' && c <= 'Z'; })
        || !matches(std::string_view(s.experiment).substr(dash + 1), 4, 4, digit))
        fail(experiment.line, "experiment must be a permanent ID like MOV-0001");
    const Node& revision = get(root, "map_revision");
    s.map_revision = word(revision, "map_revision");
    const auto suffix = std::string_view(s.map_revision).substr(std::min(s.experiment.size(), s.map_revision.size()));
    if (s.map_revision.size() > 64 || s.map_revision.compare(0, s.experiment.size(), s.experiment) != 0
        || !matches(suffix, 0, 64, revision_char) || (!suffix.empty() && (suffix.front() != '-' || suffix.back() == '-'))
        || suffix.find("--") != std::string_view::npos)
        fail(revision.line, "map_revision must be the experiment ID with optional -suffixes, like MOV-0002-r2");

    const Node& units = get(root, "units");
    expect(units, Node::Kind::sequence, "units");
    if (units.items.empty() || units.items.size() > 8) fail(units.line, "units must declare 1 to 8 units");
    for (const auto& node : units.items) {
        fields(node, {"name", "type", "position", "facing"}, {"move_speed"}, "unit");
        Unit unit;
        const Node& name = get(node, "name");
        unit.name = word(name, "unit name");
        if (!matches(unit.name, 1, 16, identifier_char) || !lower(unit.name[0]))
            fail(name.line, "unit name must match [a-z][a-z0-9_]{0,15}");
        for (const auto& other : s.units)
            if (other.name == unit.name) fail(name.line, "duplicate unit name '" + unit.name + "'");
        const Node& type = get(node, "type");
        unit.type = word(type, "unit type");
        if (unit.type != "hfoo") fail(type.line, "unsupported unit type '" + unit.type + "'; v1 supports hfoo");
        // The 64x64 oracle map spans [-4096, 4096]; WC3's own clamping is unobserved.
        unit.position = pair(get(node, "position"), "position", 4096);
        unit.facing = real(get(node, "facing"), "facing", 0, 360);
        if (unit.facing == 360) fail(get(node, "facing").line, "facing must be in [0, 360) degrees");
        if (const Node* speed = find(node, "move_speed")) {
            unit.move_speed = real(*speed, "move_speed", 0, 10000);
            if (*unit.move_speed == 0) fail(speed->line, "move_speed must be positive");
        }
        s.units.push_back(std::move(unit));
    }

    const Node& observe = get(root, "observe");
    fields(observe, {"period", "callbacks", "properties"}, {}, "observe");
    const Node& period = get(observe, "period");
    s.period_us = microseconds(period, "period");
    if (s.period_us == 0 || s.period_us > 10000000) fail(period.line, "period must be in (0, 10] seconds");
    s.callbacks = static_cast<int>(integer(get(observe, "callbacks"), "callbacks", 1, 10000));
    const Node& properties = get(observe, "properties");
    expect(properties, Node::Kind::sequence, "properties");
    std::vector<std::string> names;
    for (const auto& property : properties.items) names.push_back(word(property, "property"));
    if (names != std::vector<std::string>{"x", "y", "facing", "order"})
        fail(properties.line, "v1 observes exactly [x, \"y\", facing, order] for every unit, in that order");

    const Node& actions = get(root, "actions");
    expect(actions, Node::Kind::sequence, "actions");
    for (const auto& node : actions.items) {
        fields(node, {"at", "unit", "order"}, {"target", "offset"}, "action");
        Action action;
        action.line = node.line;
        const Node& at = get(node, "at");
        action.at_us = microseconds(at, "at");
        if (action.at_us % s.period_us != 0)
            fail(at.line, "action time is not a callback time (a multiple of the period)");
        if (action.at_us / s.period_us > static_cast<std::uint64_t>(s.callbacks))
            fail(at.line, "action time is after the last callback");
        if (!s.actions.empty() && action.at_us < s.actions.back().at_us)
            fail(at.line, "actions must be listed in non-decreasing time; equal times run in file order");
        const Node& unit = get(node, "unit");
        const auto name = word(unit, "action unit");
        action.unit = s.units.size();
        for (std::size_t id = 0; id < s.units.size(); ++id)
            if (s.units[id].name == name) action.unit = id;
        if (action.unit == s.units.size()) fail(unit.line, "unknown unit '" + name + "'");
        const Node& order = get(node, "order");
        const auto command = word(order, "order");
        const Node* target = find(node, "target");
        const Node* offset = find(node, "offset");
        if (command == "move") {
            if (!target == !offset) fail(node.line, "move needs exactly one of target or offset");
            action.order = Order::move;
            action.relative = offset != nullptr;
            action.point = target ? pair(*target, "target", 4096) : pair(*offset, "offset", 8192);
        } else if (command == "stop") {
            if (target || offset) fail(node.line, "stop takes no target or offset");
            action.order = Order::stop;
        } else {
            fail(order.line, "unsupported order '" + command + "'; v1 supports move and stop");
        }
        s.actions.push_back(action);
    }
    return s;
}

std::string sha256_hex(std::string_view bytes) {
    static constexpr std::uint32_t k[64] = {
        0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
        0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
        0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
        0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
        0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
        0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
        0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
        0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2};
    std::uint32_t h[8] = {0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
                          0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19};
    std::string message(bytes);
    const std::uint64_t length = static_cast<std::uint64_t>(bytes.size()) * 8;
    message.push_back(static_cast<char>(0x80));
    while (message.size() % 64 != 56) message.push_back('\0');
    for (int i = 7; i >= 0; --i) message.push_back(static_cast<char>((length >> (8 * i)) & 0xff));
    const auto rotr = [](std::uint32_t x, int n) { return (x >> n) | (x << (32 - n)); };
    for (std::size_t chunk = 0; chunk < message.size(); chunk += 64) {
        std::uint32_t w[64];
        for (int i = 0; i < 16; ++i) {
            w[i] = 0;
            for (int b = 0; b < 4; ++b)
                w[i] = (w[i] << 8) | static_cast<unsigned char>(message[chunk + 4 * i + b]);
        }
        for (int i = 16; i < 64; ++i) {
            const auto s0 = rotr(w[i - 15], 7) ^ rotr(w[i - 15], 18) ^ (w[i - 15] >> 3);
            const auto s1 = rotr(w[i - 2], 17) ^ rotr(w[i - 2], 19) ^ (w[i - 2] >> 10);
            w[i] = w[i - 16] + s0 + w[i - 7] + s1;
        }
        auto a = h[0], b = h[1], c = h[2], d = h[3], e = h[4], f = h[5], g = h[6], hh = h[7];
        for (int i = 0; i < 64; ++i) {
            const auto t1 = hh + (rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25)) + ((e & f) ^ (~e & g)) + k[i] + w[i];
            const auto t2 = (rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22)) + ((a & b) ^ (a & c) ^ (b & c));
            hh = g; g = f; f = e; e = d + t1; d = c; c = b; b = a; a = t1 + t2;
        }
        h[0] += a; h[1] += b; h[2] += c; h[3] += d; h[4] += e; h[5] += f; h[6] += g; h[7] += hh;
    }
    std::string hex;
    char buffer[9];
    for (const auto word : h) {
        std::snprintf(buffer, sizeof buffer, "%08x", static_cast<unsigned>(word));
        hex += buffer;
    }
    return hex;
}
}
