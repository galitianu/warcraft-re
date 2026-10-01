# Canonical comparison

Reference `wc3-1.29.2-9231-x86`; footman-v3, after-due-update.

X/Y 0.001 world unit; circular facing 0.001 degree; current order exact;
clock and action time 0.0000615 s; targets reuse X/Y limits.
Primary callback/unit/action order; no shifts or resampling. Missing CLOCKS: UNOBSERVED.

| Case | Verdict | Records WC3 / C++ | Samples | First divergence |
|---|---|---|---|---|
| MOV-0001 | PASS | 507 / 506 | 251 | — |
| MOV-0002 | FAIL | 760 / 759 | 502 | cb 1 u0 y: 0.014648 → 0 (Δ -0.014648) |
| MOV-0003 | FAIL | 508 / 507 | 251 | cb 4 u0 x: 13.362793 → 13.3642578 (Δ 0.0014648) |
| MOV-0004 | FAIL | 1208 / 1207 | 601 | cb 1 u0 y: 0.007813 → 0 (Δ -0.007813) |
| MOV-0005 | FAIL | 508 / 507 | 251 | cb 1 u0 y: 0.021484 → 0 (Δ -0.021484) |
| MOV-0006 | FAIL | 509 / 508 | 251 | cb 1 u0 y: 0.014648 → 0 (Δ -0.014648) |
| MOV-0007 | FAIL | 509 / 508 | 251 | cb 1 u0 y: 0.014648 → 0 (Δ -0.014648) |
| MOV-0008 | FAIL | 509 / 508 | 251 | cb 1 u0 y: 0.014648 → 0 (Δ -0.014648) |
| MOV-0009 | FAIL | 508 / 507 | 251 | cb 9 u0 y: 1.130371 → 1.13623047 (Δ 0.00585947) |
| MOV-0010 | FAIL | 509 / 508 | 251 | cb 1 u0 y: 0.014648 → 0 (Δ -0.014648) |

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
| x | FAIL | 502 / 163 | cb 88 u0 x: 472.475586 → 472.477051 (Δ 0.001465) | {'u0': 0.01904300000001058, 'u1': 0} | {'u0': 0.01904300000001058, 'u1': 0.0} |
| y | FAIL | 502 / 239 | cb 1 u0 y: 0.014648 → 0 (Δ -0.014648) | {'u0': 0.043945, 'u1': 0} | {'u0': -0.033203, 'u1': 0.0} |
| facing | FAIL | 502 / 250 | cb 1 u0 facing: 0.174245 → 0 (Δ -0.174245) | {'u0': 0.38864300000000185, 'u1': 0} | {'u0': -0.38864300000000185, 'u1': 0.0} |
| order | PASS | 502 / 0 | — | {'u0': 0, 'u1': 0} | {'u0': 0, 'u1': 0} |
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
| x | FAIL | 251 / 247 | cb 4 u0 x: 13.362793 → 13.3642578 (Δ 0.0014648) | {'u0': 0.05957100000000537} | {'u0': 0.05957100000000537} |
| y | FAIL | 251 / 247 | cb 4 u0 y: 13.362793 → 13.3642578 (Δ 0.0014648) | {'u0': 0.05908199999998942} | {'u0': 0.05908199999998942} |
| facing | FAIL | 251 / 92 | cb 8 u0 facing: 45.001221 → 44.9999962 (Δ -0.0012248) | {'u0': 0.001533199999983026} | {'u0': 0.0011862000000064654} |
| order | PASS | 251 / 0 | — | {'u0': 0} | {'u0': 0} |
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
| x | PASS | 601 / 0 | — | {'u0': 1.0000001111620804e-06} | {'u0': 0.0} |
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
| x | FAIL | 251 / 138 | cb 113 u0 x: 899.961914 → 899.963379 (Δ 0.001465) | {'u0': 0.001952999999957683} | {'u0': 0.001952999999957683} |
| y | FAIL | 251 / 242 | cb 1 u0 y: 0.021484 → 0 (Δ -0.021484) | {'u0': 0.065918} | {'u0': -0.001465} |
| facing | FAIL | 251 / 245 | cb 1 u0 facing: 0.124252 → 0 (Δ -0.124252) | {'u0': 0.21939099999997325} | {'u0': 0.21939099999997325} |
| order | PASS | 251 / 0 | — | {'u0': 0} | {'u0': 0} |
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
| x | FAIL | 251 / 180 | cb 54 u0 x: 269.214355 → 269.243652 (Δ 0.029297) | {'u0': 0.043945000000007894} | {'u0': 0.00048800000001847366} |
| y | FAIL | 251 / 249 | cb 1 u0 y: 0.014648 → 0 (Δ -0.014648) | {'u0': 0.043945} | {'u0': 0.026855999999952473} |
| facing | FAIL | 251 / 250 | cb 1 u0 facing: 0.174245 → 0 (Δ -0.174245) | {'u0': 0.4053916000000015} | {'u0': 0.0027845999999840387} |
| order | PASS | 251 / 0 | — | {'u0': 0} | {'u0': 0} |
| t | PASS | 251 / 0 | — | {'u0': 5.900000000003125e-05} | {'u0': 0.0} |
| action.callback | PASS | 2 / 0 | — | {'u0': 0} | {'u0': 0} |
| action.unit | PASS | 2 / 0 | — | {'u0': 0} | {'u0': 0} |
| action.command | PASS | 2 / 0 | — | {'u0': 0} | {'u0': 0} |
| action.accepted | PASS | 2 / 0 | — | {'u0': 0} | {'u0': 0} |
| action.t | PASS | 2 / 0 | — | {'u0': 0} | {'u0': 0.0} |
| action.target_x | PASS | 2 / 0 | — | {'u0': 0} | {'u0': 0.0} |
| action.target_y | FAIL | 2 / 1 | cb 50 u0 target_y: 999.976807 → 1000 (Δ 0.023193) | {'u0': 0.023192999999992026} | {'u0': 0.023192999999992026} |

Structural differences: []
Unobserved: []

## MOV-0007

| Property | Verdict | Observations / failures | First divergence | Max absolute delta by unit | Final signed delta by unit |
|---|---|---|---|---|---|
| x | FAIL | 251 / 183 | cb 58 u0 x: 264.611816 → 264.61377 (Δ 0.001954) | {'u0': 0.046386999999981526} | {'u0': -0.046386999999981526} |
| y | FAIL | 251 / 249 | cb 1 u0 y: 0.014648 → 0 (Δ -0.014648) | {'u0': 0.860107812} | {'u0': 0.0131835938} |
| facing | FAIL | 251 / 248 | cb 1 u0 facing: 0.174245 → 0 (Δ -0.174245) | {'u0': 0.43344099999998775} | {'u0': 0.43344099999998775} |
| order | PASS | 251 / 0 | — | {'u0': 0} | {'u0': 0} |
| t | PASS | 251 / 0 | — | {'u0': 5.900000000003125e-05} | {'u0': 0.0} |
| action.callback | PASS | 2 / 0 | — | {'u0': 0} | {'u0': 0} |
| action.unit | PASS | 2 / 0 | — | {'u0': 0} | {'u0': 0} |
| action.command | PASS | 2 / 0 | — | {'u0': 0} | {'u0': 0} |
| action.accepted | PASS | 2 / 0 | — | {'u0': 0} | {'u0': 0} |
| action.t | PASS | 2 / 0 | — | {'u0': 0} | {'u0': 0.0} |
| action.target_x | PASS | 2 / 0 | — | {'u0': 0} | {'u0': 0.0} |
| action.target_y | FAIL | 2 / 1 | cb 50 u0 target_y: -0.023193 → 0 (Δ 0.023193) | {'u0': 0.023193} | {'u0': 0.023193} |

Structural differences: []
Unobserved: []

## MOV-0008

| Property | Verdict | Observations / failures | First divergence | Max absolute delta by unit | Final signed delta by unit |
|---|---|---|---|---|---|
| x | FAIL | 251 / 160 | cb 91 u0 x: 480.575195 → 480.57666 (Δ 0.001465) | {'u0': 0.0019530000000145264} | {'u0': 0.0019530000000145264} |
| y | FAIL | 251 / 249 | cb 1 u0 y: 0.014648 → 0 (Δ -0.014648) | {'u0': 0.043945} | {'u0': -0.015625} |
| facing | FAIL | 251 / 250 | cb 1 u0 facing: 0.174245 → 0 (Δ -0.174245) | {'u0': 0.3447979999999973} | {'u0': -0.3447979999999973} |
| order | PASS | 251 / 0 | — | {'u0': 0} | {'u0': 0} |
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
| x | FAIL | 251 / 166 | cb 85 u0 x: 423.796875 → 423.79834 (Δ 0.001465) | {'u0': 0.022948999999925945} | {'u0': 0.022948999999925945} |
| y | FAIL | 251 / 241 | cb 9 u0 y: 1.130371 → 1.13623047 (Δ 0.00585947) | {'u0': 0.787598125} | {'u0': 0.0307615938} |
| facing | FAIL | 251 / 226 | cb 25 u0 facing: 0.403869 → 0.675093293 (Δ 0.271224293) | {'u0': 0.32104500000002645} | {'u0': 0.3104849999999715} |
| order | PASS | 251 / 0 | — | {'u0': 0} | {'u0': 0} |
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
| x | PASS | 251 / 0 | — | {'u0': 0.00048800000001847366} | {'u0': 0.0} |
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
