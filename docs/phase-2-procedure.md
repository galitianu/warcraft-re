# Build and reproduce Phase 2

Requires CMake ≥3.20, the system C++20 compiler and Python 3 (standard library only).
No game installation, window, renderer, package download or third-party checkout
is needed. On the native ARM Mac, from the repository root:

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_COMPILER=/usr/bin/clang++
cmake --build build -j 4
ctest --test-dir build --output-on-failure
python3 -m unittest discover -s tools -p 'test_*.py' -v
python3 tools/run_phase2.py --runner build/wc3test --out build/phase2 --reports build/phase2-reports
```

`wc3world` is the standalone simulation library; `movement_cases` owns the ten
hard-coded experiment setups and CSV formatting; `wc3test` owns file output.
No simulation code reads reference files. Models are documented in
[phase-2-model.md](phase-2-model.md).

The final command runs v1, v2 and the v2 before-update diagnostic, each with seed 1.
Each output directory has ten sample CSVs, ten action CSVs and `identity.json`.
Each report directory has a numerical report in JSON and Markdown, plus SHA-256
hashes of all 21 output files. All units are sampled in creation order; callback-0
and callback-50 actions follow sampling. Requests are at multiples of 0.02 seconds;
the integration step is a declared 0.001 seconds.

Identity includes the compiler, architecture, build type, configured Git revision
and dirty flag, source digest, model, step, seed, parameters and observation phase.
Run configure explicitly after changing Git revisions; source changes trigger
reconfiguration automatically. The source digest hashes the ordered list of build,
core and runner files in `CMakeLists.txt` (path, colon, file SHA-256, newline), then
SHA-256 hashes that string. It distinguishes dirty source builds without relying
on the revision alone. Default compilation disables floating-point contraction;
no fast-math is requested. Cross-compiler byte parity is unestablished.

To compare an individual model's suite and obtain a compatibility exit status:

```sh
python3 tools/compare_movement.py --actual build/phase2/v2 \
  --json build/v2-comparison.json --markdown build/v2-comparison.md
```

The comparator returns **0** for ten passes, **1** for numerical divergence and
**2** for malformed/missing inputs. It checks complete, ordered callback/unit rows,
finite values and monotonic time; it retains equal-time row order. Tolerances live
only in `tools/compare_movement.py`. Reports include first mismatch and full-run
sample counts, failing counts, maximum absolute deltas and signed final deltas per
unit for X, Y, circular facing, exact order and an auxiliary clock check. No rows
are resampled, discarded or substituted by the before-update diagnostic.

`run_phase2.py` returns 0 when all reports were produced, including honest FAIL
results. It first re-parses three raw runs per movement case and three timing
variants (39 files), checks within-map payload identity and exact derived CSV
string equality for samples/events, and emits `raw-verification.json`. The
evidence manifest binds reference CSVs, raw capture identities, map/JASS,
environment and comparison tools to hashes. It never rewrites oracle artifacts.

Committed results are under [results/phase-2](../results/phase-2/); the C++ CSVs
are reproducible rather than duplicated in Git. Check regenerated sample/action
hashes against `trace-hashes.json`. The identity hash matches only when Git/build
metadata also matches; the CSV hashes do not contain revision or machine paths.
To refresh evidence deliberately, set `--reports results/phase-2`, review the
entire diff, and explain model or environment changes. References and tolerances
must not be changed merely to make a failing model pass.

CTest checks RNG seeding, stationary invariance, finite/circular state and repeat
bytes for every case under both models. Python tests verify comparison integrity
and the existing capture parser. Neither suite is a gameplay compatibility pass.
