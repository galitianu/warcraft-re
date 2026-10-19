# MOV-0026 measured results

Twelve fresh WC3 processes; three identical observation payloads within each map.
The comparator and hypothesis rules are unchanged from preregistration.

| Layout | Stop callback | Pre-stop x,y | Next sample x,y | Displacement | Setup | H0 compatibility |
|---|---|---|---|---|---|---|
| MOV-0026-a | 90 | [-30.222656, 0.012695] | [-48.0, 48.0] | 51.174363 | PASS | FAIL |
| MOV-0026-b | 96 | [-30.222656, 0.012695] | [-48.0, 48.0] | 51.174363 | PASS | FAIL |
| MOV-0026-c | 80 | [-70.719727, 0.041992] | [-70.719727, 0.041992] | 0.000000 | PASS | PASS |
| MOV-0026-d | 96 | [-30.421387, 15.998535] | [-30.421387, 15.998535] | 0.000000 | INCONCLUSIVE | FAIL |

| Hypothesis | Overall | MOV-0026-a | MOV-0026-b | MOV-0026-c | MOV-0026-d |
|---|---|---|---|---|---|
| stop_in_place | REFUTED | REFUTED | REFUTED | SURVIVES | INCONCLUSIVE |
| blocked_grid | INCONCLUSIVE | SURVIVES | SURVIVES | SURVIVES | INCONCLUSIVE |
| unconditional_grid | REFUTED | SURVIVES | SURVIVES | REFUTED | INCONCLUSIVE |

| Layout/unit | WC3 / H0 first idle callback | WC3 final x,y,facing,order |
|---|---|---|
| MOV-0026-a/u0 | 91 / 91 | -48.0, 48.0, 359.681061, 0 |
| MOV-0026-a/u1 | 92 / None | 13.997559, -0.019531, 180.371155, 0 |
| MOV-0026-b/u0 | 97 / 97 | -48.0, 48.0, 359.681061, 0 |
| MOV-0026-b/u1 | 98 / None | 13.997559, -0.019531, 180.371155, 0 |
| MOV-0026-c/u0 | 81 / 81 | -70.719727, 0.041992, 359.661438, 0 |
| MOV-0026-c/u1 | 91 / 91 | 13.997559, -0.019531, 180.371155, 0 |
| MOV-0026-d/u0 | 95 / 97 | -30.421387, 15.998535, 0.247019, 0 |
| MOV-0026-d/u1 | 89 / None | 54.296387, 15.981445, 179.681076, 0 |

In a/b/c, u0 first idle follows its explicit stop. In d, u0 idles at 95, before the stop at 96. `None` means no idle sample within 12 s.

| Layout | First canonical divergence | Rating |
|---|---|---|
| MOV-0026-a | callback 91, u0, x, delta 17.7773438 | P3 |
| MOV-0026-b | callback 97, u0, x, delta 17.7773438 | P3 |
| MOV-0026-c | none | none |
| MOV-0026-d | callback 89, u1, order, delta 851986 | P3 |

Full per-unit positions, facing, order, waits, sampled-route descriptions, property failures and
transition measurements are in [reviewed.json](reviewed.json); H0 descriptions and traces remain
in [predictions.json](predictions.json). Rounding above is display only; raw emitted strings and
all comparator deltas are retained unchanged.
