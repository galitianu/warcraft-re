# Canonical comparison

Reference `wc3-1.29.2-9231-x86`; footman-v1, after-due-update.

X/Y 0.001 world unit; circular facing 0.001 degree; current order exact;
clock and action time 0.0000615 s; targets reuse X/Y limits.
Primary callback/unit/action order; no shifts or resampling. Missing CLOCKS: UNOBSERVED.

| Case | Verdict | Records WC3 / C++ | Samples | First divergence |
|---|---|---|---|---|
| MOV-0001 | PASS | 507 / 506 | 251 | — |
| MOV-0002 | FAIL | 760 / 759 | 502 | cb 1 u0 x: 2.699707 → 5.4000001 (Δ 2.7002931) |
| MOV-0003 | FAIL | 508 / 507 | 251 | cb 1 u0 x: 1.908691 → 3.81837726 (Δ 1.90968626) |
| MOV-0004 | FAIL | 1208 / 1207 | 601 | cb 1 u0 x: 1.499512 → 3.00000048 (Δ 1.50048848) |
| MOV-0005 | FAIL | 508 / 507 | 251 | cb 1 u0 x: 3.999512 → 8.00000095 (Δ 4.00048895) |
| MOV-0006 | FAIL | 509 / 508 | 251 | cb 1 u0 x: 2.699707 → 5.4000001 (Δ 2.7002931) |
| MOV-0007 | FAIL | 509 / 508 | 251 | cb 1 u0 x: 2.699707 → 5.4000001 (Δ 2.7002931) |
| MOV-0008 | FAIL | 509 / 508 | 251 | cb 1 u0 x: 2.699707 → 5.4000001 (Δ 2.7002931) |
| MOV-0009 | FAIL | 508 / 507 | 251 | cb 1 u0 x: 0.000000 → 5.4000001 (Δ 5.4000001) |
| MOV-0010 | FAIL | 509 / 508 | 251 | cb 1 u0 x: 2.699707 → 5.4000001 (Δ 2.7002931) |

## MOV-0001

| Property | Verdict | Observations / failures | First divergence | Max absolute delta by unit | Final signed delta by unit |
|---|---|---|---|---|---|
| x | PASS | 251 / 0 | — | {'u0': 0} | {'u0': 0.0} |
| y | PASS | 251 / 0 | — | {'u0': 0} | {'u0': 0.0} |
| facing | PASS | 251 / 0 | — | {'u0': 0} | {'u0': 0.0} |
| order | PASS | 251 / 0 | — | {'u0': 0} | {'u0': 0} |
| t | PASS | 251 / 0 | — | {'u0': 5.900000000003125e-05} | {'u0': 0.0} |
| action.callback | NOT-APPLICABLE | 0 / 0 | — | {} | {} |
| action.unit | NOT-APPLICABLE | 0 / 0 | — | {} | {} |
| action.command | NOT-APPLICABLE | 0 / 0 | — | {} | {} |
| action.accepted | NOT-APPLICABLE | 0 / 0 | — | {} | {} |
| action.t | NOT-APPLICABLE | 0 / 0 | — | {} | {} |
| action.target_x | NOT-APPLICABLE | 0 / 0 | — | {} | {} |
| action.target_y | NOT-APPLICABLE | 0 / 0 | — | {} | {} |

Structural differences: []
Unobserved: []

## MOV-0002

| Property | Verdict | Observations / failures | First divergence | Max absolute delta by unit | Final signed delta by unit |
|---|---|---|---|---|---|
| x | FAIL | 502 / 250 | cb 1 u0 x: 2.699707 → 5.4000001 (Δ 2.7002931) | {'u0': 3.958252000000016, 'u1': 0} | {'u0': -3.958252000000016, 'u1': 0.0} |
| y | FAIL | 502 / 239 | cb 1 u0 y: 0.014648 → 0 (Δ -0.014648) | {'u0': 0.043945, 'u1': 0} | {'u0': -0.033203, 'u1': 0.0} |
| facing | FAIL | 502 / 250 | cb 1 u0 facing: 0.174245 → 0 (Δ -0.174245) | {'u0': 0.38864300000000185, 'u1': 0} | {'u0': -0.38864300000000185, 'u1': 0.0} |
| order | FAIL | 502 / 1 | cb 183 u0 order: 851986 → 0 (Δ -851986) | {'u0': 851986, 'u1': 0} | {'u0': 0, 'u1': 0} |
| t | PASS | 502 / 0 | — | {'u0': 5.900000000003125e-05, 'u1': 5.900000000003125e-05} | {'u0': 0.0, 'u1': 0.0} |
| action.callback | PASS | 1 / 0 | — | {'u0': 0} | {'u0': 0} |
| action.unit | PASS | 1 / 0 | — | {'u0': 0} | {'u0': 0} |
| action.command | PASS | 1 / 0 | — | {'u0': 0} | {'u0': 0} |
| action.accepted | PASS | 1 / 0 | — | {'u0': 0} | {'u0': 0} |
| action.t | PASS | 1 / 0 | — | {'u0': 0} | {'u0': 0.0} |
| action.target_x | PASS | 1 / 0 | — | {'u0': 0} | {'u0': 0.0} |
| action.target_y | PASS | 1 / 0 | — | {'u0': 0} | {'u0': 0.0} |

Structural differences: []
Unobserved: []

## MOV-0003

| Property | Verdict | Observations / failures | First divergence | Max absolute delta by unit | Final signed delta by unit |
|---|---|---|---|---|---|
| x | FAIL | 251 / 250 | cb 1 u0 x: 1.908691 → 3.81837726 (Δ 1.90968626) | {'u0': 2.8040770000000066} | {'u0': -2.8040770000000066} |
| y | FAIL | 251 / 250 | cb 1 u0 y: 1.908691 → 3.81837726 (Δ 1.90968626) | {'u0': 2.8045660000000225} | {'u0': -2.8045660000000225} |
| facing | FAIL | 251 / 92 | cb 8 u0 facing: 45.001221 → 45 (Δ -0.001221) | {'u0': 0.0015369999999848005} | {'u0': 0.00119000000000824} |
| order | FAIL | 251 / 1 | cb 183 u0 order: 851986 → 0 (Δ -851986) | {'u0': 851986} | {'u0': 0} |
| t | PASS | 251 / 0 | — | {'u0': 5.900000000003125e-05} | {'u0': 0.0} |
| action.callback | PASS | 1 / 0 | — | {'u0': 0} | {'u0': 0} |
| action.unit | PASS | 1 / 0 | — | {'u0': 0} | {'u0': 0} |
| action.command | PASS | 1 / 0 | — | {'u0': 0} | {'u0': 0} |
| action.accepted | PASS | 1 / 0 | — | {'u0': 0} | {'u0': 0} |
| action.t | PASS | 1 / 0 | — | {'u0': 0} | {'u0': 0.0} |
| action.target_x | PASS | 1 / 0 | — | {'u0': 0} | {'u0': 0.0} |
| action.target_y | PASS | 1 / 0 | — | {'u0': 0} | {'u0': 0.0} |

Structural differences: []
Unobserved: []

## MOV-0004

| Property | Verdict | Observations / failures | First divergence | Max absolute delta by unit | Final signed delta by unit |
|---|---|---|---|---|---|
| x | FAIL | 601 / 600 | cb 1 u0 x: 1.499512 → 3.00000048 (Δ 1.50048848) | {'u0': 1.6690680000000384} | {'u0': -1.3309319999999616} |
| y | FAIL | 601 / 589 | cb 1 u0 y: 0.007813 → 0 (Δ -0.007813) | {'u0': 0.024414} | {'u0': 0.018555} |
| facing | FAIL | 601 / 600 | cb 1 u0 facing: 0.156594 → 0 (Δ -0.156594) | {'u0': 0.3620000000000232} | {'u0': 0.3620000000000232} |
| order | PASS | 601 / 0 | — | {'u0': 0} | {'u0': 0} |
| t | FAIL | 601 / 53 | cb 503 u0 t: 10.059937 → 10.060000 (Δ 6.3e-05) | {'u0': 0.00011199999999966792} | {'u0': 6.100000000053285e-05} |
| action.callback | PASS | 1 / 0 | — | {'u0': 0} | {'u0': 0} |
| action.unit | PASS | 1 / 0 | — | {'u0': 0} | {'u0': 0} |
| action.command | PASS | 1 / 0 | — | {'u0': 0} | {'u0': 0} |
| action.accepted | PASS | 1 / 0 | — | {'u0': 0} | {'u0': 0} |
| action.t | PASS | 1 / 0 | — | {'u0': 0} | {'u0': 0.0} |
| action.target_x | PASS | 1 / 0 | — | {'u0': 0} | {'u0': 0.0} |
| action.target_y | PASS | 1 / 0 | — | {'u0': 0} | {'u0': 0.0} |

Structural differences: []
Unobserved: []

## MOV-0005

| Property | Verdict | Observations / failures | First divergence | Max absolute delta by unit | Final signed delta by unit |
|---|---|---|---|---|---|
| x | FAIL | 251 / 250 | cb 1 u0 x: 3.999512 → 8.00000095 (Δ 4.00048895) | {'u0': 11.934266000000093} | {'u0': -11.934266000000093} |
| y | FAIL | 251 / 242 | cb 1 u0 y: 0.021484 → 0 (Δ -0.021484) | {'u0': 0.065918} | {'u0': -0.001465} |
| facing | FAIL | 251 / 245 | cb 1 u0 facing: 0.124252 → 0 (Δ -0.124252) | {'u0': 0.21939099999997325} | {'u0': 0.21939099999997325} |
| order | FAIL | 251 / 1 | cb 124 u0 order: 851986 → 0 (Δ -851986) | {'u0': 851986} | {'u0': 0} |
| t | PASS | 251 / 0 | — | {'u0': 5.900000000003125e-05} | {'u0': 0.0} |
| action.callback | PASS | 1 / 0 | — | {'u0': 0} | {'u0': 0} |
| action.unit | PASS | 1 / 0 | — | {'u0': 0} | {'u0': 0} |
| action.command | PASS | 1 / 0 | — | {'u0': 0} | {'u0': 0} |
| action.accepted | PASS | 1 / 0 | — | {'u0': 0} | {'u0': 0} |
| action.t | PASS | 1 / 0 | — | {'u0': 0} | {'u0': 0.0} |
| action.target_x | PASS | 1 / 0 | — | {'u0': 0} | {'u0': 0.0} |
| action.target_y | PASS | 1 / 0 | — | {'u0': 0} | {'u0': 0.0} |

Structural differences: []
Unobserved: []

## MOV-0006

| Property | Verdict | Observations / failures | First divergence | Max absolute delta by unit | Final signed delta by unit |
|---|---|---|---|---|---|
| x | FAIL | 251 / 250 | cb 1 u0 x: 2.699707 → 5.4000001 (Δ 2.7002931) | {'u0': 2.7138970000000313} | {'u0': 2.6780090000000314} |
| y | FAIL | 251 / 249 | cb 1 u0 y: 0.014648 → 0 (Δ -0.014648) | {'u0': 16.847412000000077} | {'u0': -3.4001460000000634} |
| facing | FAIL | 251 / 250 | cb 1 u0 facing: 0.174245 → 0 (Δ -0.174245) | {'u0': 89.86241000000001} | {'u0': -0.1650850000000048} |
| order | FAIL | 251 / 3 | cb 233 u0 order: 851986 → 0 (Δ -851986) | {'u0': 851986} | {'u0': 0} |
| t | PASS | 251 / 0 | — | {'u0': 5.900000000003125e-05} | {'u0': 0.0} |
| action.callback | PASS | 2 / 0 | — | {'u0': 0} | {'u0': 0} |
| action.unit | PASS | 2 / 0 | — | {'u0': 0} | {'u0': 0} |
| action.command | PASS | 2 / 0 | — | {'u0': 0} | {'u0': 0} |
| action.accepted | PASS | 2 / 0 | — | {'u0': 0} | {'u0': 0} |
| action.t | PASS | 2 / 0 | — | {'u0': 0} | {'u0': 0.0} |
| action.target_x | FAIL | 2 / 1 | cb 50 u0 target_x: 267.287109 → 270.000763 (Δ 2.713654) | {'u0': 2.7136540000000196} | {'u0': 2.7136540000000196} |
| action.target_y | FAIL | 2 / 1 | cb 50 u0 target_y: 999.976807 → 1000 (Δ 0.023193) | {'u0': 0.023192999999992026} | {'u0': 0.023192999999992026} |

Structural differences: []
Unobserved: []

## MOV-0007

| Property | Verdict | Observations / failures | First divergence | Max absolute delta by unit | Final signed delta by unit |
|---|---|---|---|---|---|
| x | FAIL | 251 / 250 | cb 1 u0 x: 2.699707 → 5.4000001 (Δ 2.7002931) | {'u0': 37.90429700000004} | {'u0': 6.641844999999989} |
| y | FAIL | 251 / 233 | cb 1 u0 y: 0.014648 → 0 (Δ -0.014648) | {'u0': 1.073242} | {'u0': 0.0} |
| facing | FAIL | 251 / 250 | cb 1 u0 facing: 0.174245 → 0 (Δ -0.174245) | {'u0': 179.862395} | {'u0': 0.3689730000000111} |
| order | FAIL | 251 / 8 | cb 233 u0 order: 851986 → 0 (Δ -851986) | {'u0': 851986} | {'u0': 0} |
| t | PASS | 251 / 0 | — | {'u0': 5.900000000003125e-05} | {'u0': 0.0} |
| action.callback | PASS | 2 / 0 | — | {'u0': 0} | {'u0': 0} |
| action.unit | PASS | 2 / 0 | — | {'u0': 0} | {'u0': 0} |
| action.command | PASS | 2 / 0 | — | {'u0': 0} | {'u0': 0} |
| action.accepted | PASS | 2 / 0 | — | {'u0': 0} | {'u0': 0} |
| action.t | PASS | 2 / 0 | — | {'u0': 0} | {'u0': 0.0} |
| action.target_x | FAIL | 2 / 1 | cb 50 u0 target_x: -732.712891 → -729.999268 (Δ 2.713623) | {'u0': 2.713622999999984} | {'u0': 2.713622999999984} |
| action.target_y | FAIL | 2 / 1 | cb 50 u0 target_y: -0.023193 → 0 (Δ 0.023193) | {'u0': 0.023193} | {'u0': 0.023193} |

Structural differences: []
Unobserved: []

## MOV-0008

| Property | Verdict | Observations / failures | First divergence | Max absolute delta by unit | Final signed delta by unit |
|---|---|---|---|---|---|
| x | FAIL | 251 / 250 | cb 1 u0 x: 2.699707 → 5.4000001 (Δ 2.7002931) | {'u0': 10.815947999999992} | {'u0': -1.8725579999999695} |
| y | FAIL | 251 / 249 | cb 1 u0 y: 0.014648 → 0 (Δ -0.014648) | {'u0': 0.043945} | {'u0': -0.015625} |
| facing | FAIL | 251 / 250 | cb 1 u0 facing: 0.174245 → 0 (Δ -0.174245) | {'u0': 0.3447979999999973} | {'u0': -0.3447979999999973} |
| order | FAIL | 251 / 2 | cb 90 u0 order: 851986 → 0 (Δ -851986) | {'u0': 851986} | {'u0': 0} |
| t | PASS | 251 / 0 | — | {'u0': 5.900000000003125e-05} | {'u0': 0.0} |
| action.callback | PASS | 2 / 0 | — | {'u0': 0} | {'u0': 0} |
| action.unit | PASS | 2 / 0 | — | {'u0': 0} | {'u0': 0} |
| action.command | PASS | 2 / 0 | — | {'u0': 0} | {'u0': 0} |
| action.accepted | PASS | 2 / 0 | — | {'u0': 0} | {'u0': 0} |
| action.t | PASS | 2 / 0 | — | {'u0': 0} | {'u0': 0.0} |
| action.target_x | PASS | 2 / 0 | — | {'u0': 0} | {'u0': 0.0} |
| action.target_y | PASS | 2 / 0 | — | {'u0': 0} | {'u0': 0.0} |

Structural differences: []
Unobserved: []

## MOV-0009

| Property | Verdict | Observations / failures | First divergence | Max absolute delta by unit | Final signed delta by unit |
|---|---|---|---|---|---|
| x | FAIL | 251 / 250 | cb 1 u0 x: 0.000000 → 5.4000001 (Δ 5.4000001) | {'u0': 35.27221700000007} | {'u0': -3.8732910000001084} |
| y | FAIL | 251 / 238 | cb 7 u0 y: 0.380859 → 0 (Δ -0.380859) | {'u0': 1.142578} | {'u0': 0.017578} |
| facing | FAIL | 251 / 250 | cb 1 u0 facing: 175.989273 → 0 (Δ -175.989273) | {'u0': 175.989273} | {'u0': 0.37478599999997186} |
| order | FAIL | 251 / 7 | cb 183 u0 order: 851986 → 0 (Δ -851986) | {'u0': 851986} | {'u0': 0} |
| t | PASS | 251 / 0 | — | {'u0': 5.900000000003125e-05} | {'u0': 0.0} |
| action.callback | PASS | 1 / 0 | — | {'u0': 0} | {'u0': 0} |
| action.unit | PASS | 1 / 0 | — | {'u0': 0} | {'u0': 0} |
| action.command | PASS | 1 / 0 | — | {'u0': 0} | {'u0': 0} |
| action.accepted | PASS | 1 / 0 | — | {'u0': 0} | {'u0': 0} |
| action.t | PASS | 1 / 0 | — | {'u0': 0} | {'u0': 0.0} |
| action.target_x | PASS | 1 / 0 | — | {'u0': 0} | {'u0': 0.0} |
| action.target_y | PASS | 1 / 0 | — | {'u0': 0} | {'u0': 0.0} |

Structural differences: []
Unobserved: []

## MOV-0010

| Property | Verdict | Observations / failures | First divergence | Max absolute delta by unit | Final signed delta by unit |
|---|---|---|---|---|---|
| x | FAIL | 251 / 250 | cb 1 u0 x: 2.699707 → 5.4000001 (Δ 2.7002931) | {'u0': 2.7138970000000313} | {'u0': 2.7136540000000196} |
| y | FAIL | 251 / 249 | cb 1 u0 y: 0.014648 → 0 (Δ -0.014648) | {'u0': 0.043945} | {'u0': 0.023193} |
| facing | FAIL | 251 / 250 | cb 1 u0 facing: 0.174245 → 0 (Δ -0.174245) | {'u0': 0.32971800000001394} | {'u0': -0.32971800000001394} |
| order | PASS | 251 / 0 | — | {'u0': 0} | {'u0': 0} |
| t | PASS | 251 / 0 | — | {'u0': 5.900000000003125e-05} | {'u0': 0.0} |
| action.callback | PASS | 2 / 0 | — | {'u0': 0} | {'u0': 0} |
| action.unit | PASS | 2 / 0 | — | {'u0': 0} | {'u0': 0} |
| action.command | PASS | 2 / 0 | — | {'u0': 0} | {'u0': 0} |
| action.accepted | PASS | 2 / 0 | — | {'u0': 0} | {'u0': 0} |
| action.t | PASS | 2 / 0 | — | {'u0': 0} | {'u0': 0.0} |
| action.target_x | PASS | 1 / 0 | — | {'u0': 0} | {'u0': 0.0} |
| action.target_y | PASS | 1 / 0 | — | {'u0': 0} | {'u0': 0.0} |

Structural differences: []
Unobserved: []
