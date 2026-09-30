# Canonical trace v1

Defined for Phase 3 / issue #5 before changing either producer. This is a trace
contract for the existing manual experiments, not a declarative scenario language.
`tools/trace_contract.py` is the executable validator; Python standard library only.

Every JSON document has `schema: "wc3-trace"`, integer `version: 1`, `scenario`,
`identity`, `units`, `time`, `records`, `completion`, and `provenance`.

- `scenario`: experiment ID, separate map revision, requested period as a decimal
  seconds string, and last callback. The validator knows the 15 retained setups
  independently; a producer cannot redefine the expected sample shape.
- `identity`: `engine` (`wc3` or `cpp`), exact `build`, `source`, `environment`,
  `seed` status/value/retail equivalence, and `model` (null for WC3). WC3 sources
  bind map, library and case paths/hashes; environment binds its recorded JSON.
  C++ source/build/model parameters describe the binary actually used. It has no
  WC3 map dependency. WC3 seed is unset/unobserved; C++ seed is not a retail seed.
- `units`: creation/watch order, names, observed type, speed and default speed.
  Speed strings retain emitted precision. World positions use world units and
  facing uses degrees; orders are unsigned integer strings.
- `time`: seconds, world units, degrees, numeric format, clock duration (WC3's
  1000-second elapsed timer), step size (C++ only), observation phase, and state
  lag. WC3's relative position in a due movement update is unknown. C++ declares
  before/after-due-update. Before samples omit one 1000-microsecond step except
  callback 0; actions execute after the due step in both phases.
- `records`: one contiguous zero-based global `seq`, covering BEGIN/SETUP/WATCH/
  RUN/TICK/SAMPLE/ACTION/EVENT/END. Control records carry `fields` string arrays;
  they are producer evidence, not fields that must be equal between engines.
  Timed records carry callback and `time`: `requested` decimal seconds,
  `reported` WC3 elapsed-clock string or null, and `state_us` explicit C++ state
  time or null. TICK precedes samples in watch order; actions/events follow all
  samples. Callback 0 samples precede initial orders and callback 50 samples
  precede replacement/stop. No sorting, resampling, dropped rows or phase shifts.
- SAMPLE: unit, `values` containing x/y/facing/order strings. ACTION: unit,
  command name, accepted boolean, target {x,y} strings or null for immediate
  orders. EVENT: name and string-valued `values` (including CLOCKS nine-decimal
  evidence). WC3 records retain `source: {seq, payload}` linking every canonical
  record to its exact raw @O record; C++ source is null. Sequence numbers between
  producers need not match. Printed WC3 decimals do not establish float bits;
  C++ max_digits10 strings round-trip its float state. Nothing rounds references.
- `completion`: complete boolean and exact record/tick/sample/action/event counts.
  END and counts are checked independently. Finite complete output is required.
- `provenance`: WC3 representative fixture names every retained run, manifest
  path/hash, raw path/hash, observation payload hash, generated preload entries
  with their raw insertion positions, and footer. These are transport evidence,
  never gameplay events. Normalize each run and verify payload equality before
  choosing run-01. Build/transport metadata is excluded from observation payload
  repeatability. C++ payload hash is computed from scenario/units/time/records/
  completion; build revision is separate.

All real values are lossless emitted strings. Comparison uses finite binary64
values bounded to prevent overflow; exact integral fields are bounded uint32
(or small declared callback/count ranges). Requested time is derived using exact
Decimal multiplication, labelled as requested, never observed. `state_us` is an
integer microsecond counter (one million per second), never derived from a WC3
reading. Numeric overflow, nonfinite values, duplicate JSON keys, unsupported
versions, missing fields, bad source mapping, sequence gaps, wrong identities,
units, truncated callbacks and false completion are input errors (CLI exit 2).

## Comparison and verdict

Primary alignment is callback/unit and ordered actions/events, independent of raw
instrumentation sequence. `tools/trace_contract.py:TOLERANCES` is the sole tolerance
source: X/Y 0.001 world unit, circular facing 0.001 degree, exact current order,
clock 0.0000615 seconds. Action targets reuse X/Y limits; action time reuses the
clock limit; unit type, command order/name/unit and acceptance are exact. Both
relative redirect targets remain each engine's own computed coordinates; report
signed target deltas. Sample and action differences accumulate over the whole
trace, with first divergence, maximum error per unit and final deltas. Structural
unit/action/event differences are separate completed incompatibilities (exit 1).
Unsupported or invalid inputs are never gameplay failures. Exit 0 means completed
compatibility under the named observed scope; missing C++ CLOCKS properties are
UNOBSERVED, never PASS. No general JASS or RNG verdict is inferred.

Before-update output is a separately labelled diagnostic against the same fixture.
Neither a better phase result nor clock quantization suppresses primary failures.
Approximately 5 ms position and 30 ms facing changes are observed cadences, not a
measured simulation quantum. MOV-0004's long-clock discrepancy remains graded.

## Repeatability

Vocabulary: DETERMINISTIC, RNG-DETERMINISTIC-WITH-SEED, NONDETERMINISTIC, UNKNOWN.
Three identical retained WC3 observation payloads per map are DETERMINISTIC **only
under that recorded map/build/VM/fresh-process procedure**, with run counts and
hashes. Raw/footer variability is reported separately. Seed effects and other
machines are UNKNOWN. Repeated C++ payloads with a fixed seed/build are
RNG-DETERMINISTIC-WITH-SEED at that scope; movement does not draw RNG and this says
nothing about retail RNG equivalence. The historical twenty-run example creates
no new capture requirement.
