# footman-v4 results

Completed 1 October 2026 on branch `mov-0012`. **footman-v4 passes all ten movement
fixtures, and the match is exact.** Under the unchanged Phase 3 comparator,
MOV-0001–MOV-0010 all PASS (footman-v3: 1/10). The stricter check prints each C++ value
as WC3's `R2SW(value, 1, 6)` would. All 3,111 sample rows match WC3's text exactly
in X, Y, facing and order, as do all 2,860 clock readings. Rules:
[footman-v4-model.md](footman-v4-model.md). New capture: [MOV-0012](mov-0012.md).

Source/build tested: `624710760d26859dc68c67967882ebbb01ccf15b`, clean detached ARM Mac
checkout (`git_dirty_at_configure: false`); AppleClang 21.0.0.21000334, Release, arm64,
FP contraction off; build source SHA-256
`d6598f438586f82e328168b996e2d4ed9c55e37092d7ed0fbac2ed10d64df0b7`. A Debug (-O0) build
of the same checkout produced identical trace records and state dumps. References
are the unchanged [canonical fixtures](../oracle/canonical/wc3-1.29.2-9231-x86/) and
retained captures of WC3 1.29.2 (9231), x86 32-bit, `wc3-1.29.2-9231-x86`. No fixture,
capture or tolerance was changed.

Reports: [canonical comparison](../results/footman-v4/comparison.md),
[exact text](../results/footman-v4/exact.md),
[state captures](../results/footman-v4/states.md),
[trace hashes](../results/footman-v4/trace-hashes.json); JSON accompanies each.

## Reproduction

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_COMPILER=/usr/bin/clang++
cmake --build build -j 4
ctest --test-dir build --output-on-failure        # world_invariants, footman_v4_wc3
python3 -m unittest discover -s tools -p 'test_*.py' -v
python3 tools/run_footman_v4.py --runner build/wc3test --states build/wc3states \
  --out build/v4 --reports build/footman-v4
```

`run_footman_v4.py` runs v4 twice in separate processes and requires identical bytes.
It then runs [compare_traces.py](../tools/compare_traces.py),
[compare_exact.py](../tools/compare_exact.py) and
[compare_states.py](../tools/compare_states.py). It exits 0 only if every comparison is
identical except the listed [sampling-order](#sampling-order) callbacks. CTest runs it as
`footman_v4_wc3`. `run_phase3.py` and `run_footman_v3.py` still reproduce every v1/v2/v3
statistic and CSV hash. Only the build identity differs.

## How each failure was resolved

Each rule below came from the retail update code. Each was kept only when it removed the
first exact-text divergence and introduced no new one.

| Step | Effect on the first divergences |
|---|---|
| v3's rules in retail soft-float (heading noise = `acos` of a sqrt-biased cosine) | MOV-0001 exact. X/Y exact throughout MOV-0003/4/5/8/9. Remaining: facing from each arrival callback; MOV-0002 Y from callback 53 (one 1/4096 unit); MOV-0006/7 after the redirect; MOV-0010 facing after the stop |
| Heading re-derived from the velocity each update | MOV-0002/3/4/5/8/9 exact (callback 53's sine changes bucket; arrival facing targets `Angle(vel)`) |
| A stop stores the moving direction | MOV-0010 exact (residual facing settles on 0.329718°) |
| A new move order does the same | MOV-0006/7 exact |
| Library clock `sub(1000, sub(add(0.5, 1000), t))`, with `t += 0.02f` | MOV-0004's clock exact from callback 503 (10.059937, not 10.06). Start 0.5 is the only tested start that reproduces all 15 fixtures' clocks |

## State captures

[compare_states.py](../tools/compare_states.py) checks 31 traces. The first 27 are 1 ms runs:
3 of JASS-0001-p001 and 24 of MOV-0012. These compare R2SW_9 X/Y/facing and every timer
field. The other four are the canonical JASS-0001 p010/p020/p025/p050 traces (R2SW_6).

- Clock and timer strings: 26,581 and 33,042 compared, **all identical**.
- X/Y: identical except 135 callbacks (5 per 1 ms run). Facing: identical except 25
  callbacks (p010: 10, p025: 15).
- Every recorded state is one that v4 produces. The differences concern only which
  frame, or which side of an update, a callback reads.

### Sampling order

| Sampling | Rule used | Exceptions |
|---|---|---|
| 20 ms (15 fixtures), 50 ms | Callback k reads frame 4k (10k), after that frame's update | none |
| 1 ms (27 runs) | Callback k reads frame ⌊(k − 1)/5⌋ | k = 15, 20, 25, 30, 35 read frame k/5, in every run |
| 10 ms, 25 ms | Callback k reads frame t/5 after its update | p010 callbacks 352–379 (every third) and p025 64–148 (every sixth) read X/Y of that frame but the facing from before its update |

[MOV-0013](mov-0013.md) moved the sampler start and the order separately. The 1 ms
exceptions follow the sampler, not the order, the update grid or absolute time.
[MOV-0014](mov-0014.md) then refuted the callback-index reading. Every exception so
far is a callback less than 8 × 2⁻²⁴ s before a frame, and it shows that frame's X/Y.
At an update frame, though, it shows the facing from before the update, as in the
10/25 ms cases. [MOV-0015](mov-0015.md) pre-registered this as T7. It held in three of
four new maps. In the fourth, the sampler started one ulp later than modelled, and T7
fits once that is allowed for. The rounded start is post hoc, so this is still a
candidate, and the mechanism is still **not explained**. Comparing each sampler's float32 scheduled time
with the modelled frame clock reproduces the 1 ms rule except at exactly those five
callbacks. One candidate, not implemented, covers the 10/25 ms
cases. It treats the unit update as a 30 ms event, `u += 0.03f` from 0.51 s,
scheduled with the sampler, so that a sampler due earlier runs first. Written exactly
as MOV-0015's FU (facing from before the update while the callback is earlier than the
event), it predicts every retained facing, including the 10–50 ms JASS-0001 traces and
MOV-0013/0014. It predicted MOV-0015-c's five facings past 2 s, all of which the frame
clock missed. MOV-0015-a's callback 10 fits only from that map's later start. It does not explain the 1 ms X/Y exceptions.

## Limits

- **Scope:** one moving Footman on the 64×64 oracle map. MOV-0002's second
  Footman is stationary. Collision, pathing, terrain, other unit types and multiple
  movers are untested. One build, one VM, one seed setting.
- **Stop radius 16:** chosen, not read from game data. Every arrival agrees exactly.
- **Redirect targets** (MOV-0006/7, `GetUnitX/Y ± 1000`) use host float addition in
  the runner. They match, but JASS real arithmetic is not modelled.
- **Determinism:** Release and Debug AppleClang builds are byte-identical. Other
  compilers and platforms are untested. Table generation uses host `libm` in double
  precision, with the margins recorded in [SoftFloat.cpp](../src/core/SoftFloat.cpp).
- The sampling-order exceptions above are listed in the gate, not modelled.

## Next

Phase 4: run `ctest` (including `footman_v4_wc3`) in CI on every commit (done). The
dedicated sampling-order capture is [MOV-0013](mov-0013.md); its next experiments
are listed there.
