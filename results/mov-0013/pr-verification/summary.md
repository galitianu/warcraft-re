# Measured build scope

CI scope gate: **PASS**.

measured artifact-producing configurations of this workflow run only; movement RNG unused; retail RNG/other hosts remain UNKNOWN

Payload hashes exclude build/transport identity; full trace hashes include it.
Cross-configuration byte differences are reported, while each configuration is graded against the same WC3 fixtures.

Oracle generation: **IDENTICAL** across 5 configurations.

Generated-map capture/comparison: **PASS** across 5 configurations.

MOV-0013 reviewed differences, regraded: **PASS** across 5 configurations.

| Configuration | Host / target | Compiler | Build | CI | v4 compatibility |
|---|---|---|---|---|---|
| mac-arm-release | Darwin arm64 / arm64 | AppleClang 17.0.0.17000013 | Release | PASS | 10/10 PASS |
| mac-arm-debug | Darwin arm64 / arm64 | AppleClang 17.0.0.17000013 | Debug | PASS | 10/10 PASS |
| linux-gcc-release | Linux x86_64 / x86_64 | GNU 13.3.0 | Release | PASS | 10/10 PASS |
| linux-clang-debug | Linux x86_64 / x86_64 | Clang 18.1.3 | Debug | PASS | 10/10 PASS |
| windows-msvc-release | Windows x86_64 / x86_64 | MSVC 19.44.35229.0 | Release | PASS | 10/10 PASS |

| Model | Observation payload equality | Distinct payloads per case | Full trace variants per case | Scenario inputs |
|---|---|---|---|---|
| v1 | DIFFERENT | [1, 1, 1, 1, 1, 1, 2, 1, 1, 1] | [5, 5, 5, 5, 5, 5, 5, 5, 5, 5] | IDENTICAL |
| v2 | DIFFERENT | [1, 1, 1, 1, 1, 1, 2, 1, 1, 1] | [5, 5, 5, 5, 5, 5, 5, 5, 5, 5] | IDENTICAL |
| v2-before | DIFFERENT | [1, 1, 1, 1, 1, 1, 2, 1, 1, 1] | [5, 5, 5, 5, 5, 5, 5, 5, 5, 5] | IDENTICAL |
| v3 | IDENTICAL | [1, 1, 1, 1, 1, 1, 1, 1, 1, 1] | [5, 5, 5, 5, 5, 5, 5, 5, 5, 5] | IDENTICAL |
| v4 | IDENTICAL | [1, 1, 1, 1, 1, 1, 1, 1, 1, 1] | [5, 5, 5, 5, 5, 5, 5, 5, 5, 5] | IDENTICAL |
