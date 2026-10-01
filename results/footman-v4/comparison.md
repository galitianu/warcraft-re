# Canonical comparison

Reference `wc3-1.29.2-9231-x86`; footman-v4, after-due-update.

X/Y 0.001 world unit; circular facing 0.001 degree; current order exact;
clock and action time 0.0000615 s; targets reuse X/Y limits.
Primary callback/unit/action order; no shifts or resampling. Missing CLOCKS: UNOBSERVED.

| Case | Verdict | Records WC3 / C++ | Samples | First divergence |
|---|---|---|---|---|
| MOV-0001 | PASS | 507 / 506 | 251 | — |
| MOV-0002 | PASS | 760 / 759 | 502 | — |
| MOV-0003 | PASS | 508 / 507 | 251 | — |
| MOV-0004 | PASS | 1208 / 1207 | 601 | — |
| MOV-0005 | PASS | 508 / 507 | 251 | — |
| MOV-0006 | PASS | 509 / 508 | 251 | — |
| MOV-0007 | PASS | 509 / 508 | 251 | — |
| MOV-0008 | PASS | 509 / 508 | 251 | — |
| MOV-0009 | PASS | 508 / 507 | 251 | — |
| MOV-0010 | PASS | 509 / 508 | 251 | — |

## MOV-0001

| Property | Verdict | Observations / failures | First divergence | Max absolute delta by unit | Final signed delta by unit |
|---|---|---|---|---|---|
| x | PASS | 251 / 0 | — | {'u0': 0} | {'u0': 0.0} |
| y | PASS | 251 / 0 | — | {'u0': 0} | {'u0': 0.0} |
| facing | PASS | 251 / 0 | — | {'u0': 0} | {'u0': 0.0} |
| order | PASS | 251 / 0 | — | {'u0': 0} | {'u0': 0} |
| t | PASS | 251 / 0 | — | {'u0': 5.000000005139782e-07} | {'u0': 0.0} |
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
| x | PASS | 502 / 0 | — | {'u0': 1.0000001111620804e-06, 'u1': 0} | {'u0': 0.0, 'u1': 0.0} |
| y | PASS | 502 / 0 | — | {'u0': 5.000000000005e-07, 'u1': 0} | {'u0': 1.2499999999665556e-07, 'u1': 0.0} |
| facing | PASS | 502 / 0 | — | {'u0': 4.960000126175146e-07, 'u1': 0} | {'u0': 1.7499999671599653e-07, 'u1': 0.0} |
| order | PASS | 502 / 0 | — | {'u0': 0, 'u1': 0} | {'u0': 0, 'u1': 0} |
| t | PASS | 502 / 0 | — | {'u0': 5.000000005139782e-07, 'u1': 5.000000005139782e-07} | {'u0': 0.0, 'u1': 0.0} |
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
| x | PASS | 251 / 0 | — | {'u0': 1.0000001111620804e-06} | {'u0': 0.0} |
| y | PASS | 251 / 0 | — | {'u0': 9.999999974752427e-07} | {'u0': 0.0} |
| facing | PASS | 251 / 0 | — | {'u0': 4.0000000467443897e-07} | {'u0': -1.9999998812636477e-07} |
| order | PASS | 251 / 0 | — | {'u0': 0} | {'u0': 0} |
| t | PASS | 251 / 0 | — | {'u0': 5.000000005139782e-07} | {'u0': 0.0} |
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
| y | PASS | 601 / 0 | — | {'u0': 5.000000000005e-07} | {'u0': 3.124999999985778e-07} |
| facing | PASS | 601 / 0 | — | {'u0': 4.885000066678913e-07} | {'u0': 0.0} |
| order | PASS | 601 / 0 | — | {'u0': 0} | {'u0': 0} |
| t | PASS | 601 / 0 | — | {'u0': 5.000000005139782e-07} | {'u0': 0.0} |
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
| x | PASS | 251 / 0 | — | {'u0': 1.0000001111620804e-06} | {'u0': 0.0} |
| y | PASS | 251 / 0 | — | {'u0': 5.000000000005e-07} | {'u0': -1.5624999999993942e-07} |
| facing | PASS | 251 / 0 | — | {'u0': 9.999999974752427e-07} | {'u0': 0.0} |
| order | PASS | 251 / 0 | — | {'u0': 0} | {'u0': 0} |
| t | PASS | 251 / 0 | — | {'u0': 5.000000005139782e-07} | {'u0': 0.0} |
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
| x | PASS | 251 / 0 | — | {'u0': 9.999999974752427e-07} | {'u0': 0.0} |
| y | PASS | 251 / 0 | — | {'u0': 1.0000001111620804e-06} | {'u0': 0.0} |
| facing | PASS | 251 / 0 | — | {'u0': 4.999999987376214e-07} | {'u0': -1.9999998812636477e-07} |
| order | PASS | 251 / 0 | — | {'u0': 0} | {'u0': 0} |
| t | PASS | 251 / 0 | — | {'u0': 5.000000005139782e-07} | {'u0': 0.0} |
| action.callback | PASS | 2 / 0 | — | {'u0': 0} | {'u0': 0} |
| action.unit | PASS | 2 / 0 | — | {'u0': 0} | {'u0': 0} |
| action.command | PASS | 2 / 0 | — | {'u0': 0} | {'u0': 0} |
| action.accepted | PASS | 2 / 0 | — | {'u0': 0} | {'u0': 0} |
| action.t | PASS | 2 / 0 | — | {'u0': 0} | {'u0': 0.0} |
| action.target_x | PASS | 2 / 0 | — | {'u0': 0} | {'u0': 0.0} |
| action.target_y | PASS | 2 / 0 | — | {'u0': 0} | {'u0': 0.0} |

Structural differences: []
Unobserved: []

## MOV-0007

| Property | Verdict | Observations / failures | First divergence | Max absolute delta by unit | Final signed delta by unit |
|---|---|---|---|---|---|
| x | PASS | 251 / 0 | — | {'u0': 1.0000001111620804e-06} | {'u0': 0.0} |
| y | PASS | 251 / 0 | — | {'u0': 5.000000000005e-07} | {'u0': 0.0} |
| facing | PASS | 251 / 0 | — | {'u0': 9.999999974752427e-07} | {'u0': 0.0} |
| order | PASS | 251 / 0 | — | {'u0': 0} | {'u0': 0} |
| t | PASS | 251 / 0 | — | {'u0': 5.000000005139782e-07} | {'u0': 0.0} |
| action.callback | PASS | 2 / 0 | — | {'u0': 0} | {'u0': 0} |
| action.unit | PASS | 2 / 0 | — | {'u0': 0} | {'u0': 0} |
| action.command | PASS | 2 / 0 | — | {'u0': 0} | {'u0': 0} |
| action.accepted | PASS | 2 / 0 | — | {'u0': 0} | {'u0': 0} |
| action.t | PASS | 2 / 0 | — | {'u0': 0} | {'u0': 0.0} |
| action.target_x | PASS | 2 / 0 | — | {'u0': 0} | {'u0': 0.0} |
| action.target_y | PASS | 2 / 0 | — | {'u0': 3.594000000002595e-07} | {'u0': -3.594000000002595e-07} |

Structural differences: []
Unobserved: []

## MOV-0008

| Property | Verdict | Observations / failures | First divergence | Max absolute delta by unit | Final signed delta by unit |
|---|---|---|---|---|---|
| x | PASS | 251 / 0 | — | {'u0': 9.999999974752427e-07} | {'u0': 0.0} |
| y | PASS | 251 / 0 | — | {'u0': 5.000000000005e-07} | {'u0': 0.0} |
| facing | PASS | 251 / 0 | — | {'u0': 4.960000126175146e-07} | {'u0': -1.500000053056283e-07} |
| order | PASS | 251 / 0 | — | {'u0': 0} | {'u0': 0} |
| t | PASS | 251 / 0 | — | {'u0': 5.000000005139782e-07} | {'u0': 0.0} |
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
| x | PASS | 251 / 0 | — | {'u0': 1.0000001111620804e-06} | {'u0': 0.0} |
| y | PASS | 251 / 0 | — | {'u0': 5.00000000069889e-07} | {'u0': -1.25000000000125e-07} |
| facing | PASS | 251 / 0 | — | {'u0': 4.919999980756984e-07} | {'u0': 0.0} |
| order | PASS | 251 / 0 | — | {'u0': 0} | {'u0': 0} |
| t | PASS | 251 / 0 | — | {'u0': 5.000000005139782e-07} | {'u0': 0.0} |
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
| x | PASS | 251 / 0 | — | {'u0': 5.000000058430487e-07} | {'u0': 0.0} |
| y | PASS | 251 / 0 | — | {'u0': 5.000000000005e-07} | {'u0': -3.594000000002595e-07} |
| facing | PASS | 251 / 0 | — | {'u0': 4.960000126175146e-07} | {'u0': -9.600000794307562e-08} |
| order | PASS | 251 / 0 | — | {'u0': 0} | {'u0': 0} |
| t | PASS | 251 / 0 | — | {'u0': 5.000000005139782e-07} | {'u0': 0.0} |
| action.callback | PASS | 2 / 0 | — | {'u0': 0} | {'u0': 0} |
| action.unit | PASS | 2 / 0 | — | {'u0': 0} | {'u0': 0} |
| action.command | PASS | 2 / 0 | — | {'u0': 0} | {'u0': 0} |
| action.accepted | PASS | 2 / 0 | — | {'u0': 0} | {'u0': 0} |
| action.t | PASS | 2 / 0 | — | {'u0': 0} | {'u0': 0.0} |
| action.target_x | PASS | 1 / 0 | — | {'u0': 0} | {'u0': 0.0} |
| action.target_y | PASS | 1 / 0 | — | {'u0': 0} | {'u0': 0.0} |

Structural differences: []
Unobserved: []
