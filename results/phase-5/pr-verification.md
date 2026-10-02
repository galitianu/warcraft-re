# Phase 5 PR verification

[Run 36887017447](https://github.com/galitianu/warcraft-re/actions/runs/36887017447), `pull_request` for PR #13 head `ceaf1c70ec7579c5f1b5e0008d7786fac8882b59`, built from the clean PR merge commit `cbf9d0f046a36c045348321137ca9db9efcd9d57`. All five configurations and the aggregate job PASS.

Each configuration passed CTest 3/3 and Python 56/56. All five hard-coded suites and all five scenario suites ran twice each; every scenario migration was EQUIVALENT. Native ARM Release also passed the archival migration. The downloaded artifacts were rechecked locally with `tools/summarize_ci.py`, and the result is identical to this scope report. The earlier [failed run](initial-pr-run.json) is retained.


CI scope gate: **PASS**.

measured artifact-producing configurations of this workflow run only; movement RNG unused; retail RNG/other hosts remain UNKNOWN

Payload hashes exclude build/transport identity; full trace hashes include it.
Cross-configuration byte differences are reported, while each configuration is graded against the same WC3 fixtures.

| Configuration | Host / target | Compiler | Build | CI | v4 compatibility |
|---|---|---|---|---|---|
| mac-arm-release | Darwin arm64 / arm64 | AppleClang 17.0.0.17000013 | Release | PASS | 10/10 PASS |
| mac-arm-debug | Darwin arm64 / arm64 | AppleClang 17.0.0.17000013 | Debug | PASS | 10/10 PASS |
| linux-gcc-release | Linux x86_64 / x86_64 | GNU 13.3.0 | Release | PASS | 10/10 PASS |
| linux-clang-debug | Linux x86_64 / x86_64 | Clang 18.1.3 | Debug | PASS | 10/10 PASS |
| windows-msvc-release | Windows x86_64 / x86_64 | MSVC 19.44.35229.0 | Release | PASS | 10/10 PASS |

| Model | Observation payload equality | Distinct payloads per case | Full trace variants per case | Scenario migration | Scenario inputs |
|---|---|---|---|---|---|
| v1 | DIFFERENT | [1, 1, 1, 1, 1, 1, 2, 1, 1, 1] | [5, 5, 5, 5, 5, 5, 5, 5, 5, 5] | EQUIVALENT | IDENTICAL |
| v2 | DIFFERENT | [1, 1, 1, 1, 1, 1, 2, 1, 1, 1] | [5, 5, 5, 5, 5, 5, 5, 5, 5, 5] | EQUIVALENT | IDENTICAL |
| v2-before | DIFFERENT | [1, 1, 1, 1, 1, 1, 2, 1, 1, 1] | [5, 5, 5, 5, 5, 5, 5, 5, 5, 5] | EQUIVALENT | IDENTICAL |
| v3 | IDENTICAL | [1, 1, 1, 1, 1, 1, 1, 1, 1, 1] | [5, 5, 5, 5, 5, 5, 5, 5, 5, 5] | EQUIVALENT | IDENTICAL |
| v4 | IDENTICAL | [1, 1, 1, 1, 1, 1, 1, 1, 1, 1] | [5, 5, 5, 5, 5, 5, 5, 5, 5, 5] | EQUIVALENT | IDENTICAL |
