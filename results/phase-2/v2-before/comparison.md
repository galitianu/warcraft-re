# footman-v2 — before-due-update

Reference: `wc3-1.29.2-9231-x86`. Delta = actual − reference.

Tolerances: X/Y 0.001 world unit, facing 0.001° circular, order exact;
clock 0.0000615 s. Compare in callback/unit sequence; do not resample.

| Case | Result | Reference / actual samples | First divergence |
|---|---|---|---|
| MOV-0001 | PASS | 251 / 251 | — |
| MOV-0002 | FAIL | 502 / 502 | cb 1 u0 x: 2.699707 → 1.35000002 (Δ -1.34970698) |
| MOV-0003 | FAIL | 251 / 251 | cb 1 u0 x: 1.908691 → 0.954594135 (Δ -0.954096865) |
| MOV-0004 | FAIL | 601 / 601 | cb 1 u0 x: 1.499512 → 0.75 (Δ -0.749512) |
| MOV-0005 | FAIL | 251 / 251 | cb 1 u0 x: 3.999512 → 2 (Δ -1.999512) |
| MOV-0006 | FAIL | 251 / 251 | cb 1 u0 x: 2.699707 → 1.35000002 (Δ -1.34970698) |
| MOV-0007 | FAIL | 251 / 251 | cb 1 u0 x: 2.699707 → 1.35000002 (Δ -1.34970698) |
| MOV-0008 | FAIL | 251 / 251 | cb 1 u0 x: 2.699707 → 1.35000002 (Δ -1.34970698) |
| MOV-0009 | FAIL | 251 / 251 | cb 2 u0 facing: 167.967850 → 175.989288 (Δ 8.021438) |
| MOV-0010 | FAIL | 251 / 251 | cb 1 u0 x: 2.699707 → 1.35000002 (Δ -1.34970698) |

Per-property results continue through the final sample. Final deltas are
listed per unit (the stationary control must not hide u0's endpoint error).

## MOV-0001

| Property | Samples / failing | Max absolute Δ | Final Δ by unit | First divergence |
|---|---|---|---|---|
| x | 251 / 0 | 0 | u0: 0 | — |
| y | 251 / 0 | 0 | u0: 0 | — |
| facing | 251 / 0 | 0 | u0: 0 | — |
| order | 251 / 0 | 0 | u0: 0 | — |
| t | 251 / 0 | 5.9e-05 | u0: 0 | — |

## MOV-0002

| Property | Samples / failing | Max absolute Δ | Final Δ by unit | First divergence |
|---|---|---|---|---|
| x | 502 / 250 | 3.990174 | u0: -3.990174; u1: 0 | cb 1 u0 x: 2.699707 → 1.35000002 (Δ -1.34970698) |
| y | 502 / 239 | 0.043945 | u0: -0.033203; u1: 0 | cb 1 u0 y: 0.014648 → 0 (Δ -0.014648) |
| facing | 502 / 250 | 0.388643 | u0: -0.388643; u1: 0 | cb 1 u0 facing: 0.174245 → 0 (Δ -0.174245) |
| order | 502 / 0 | 0 | u0: 0; u1: 0 | — |
| t | 502 / 0 | 5.9e-05 | u0: 0; u1: 0 | — |

## MOV-0003

| Property | Samples / failing | Max absolute Δ | Final Δ by unit | First divergence |
|---|---|---|---|---|
| x | 251 / 250 | 2.803405 | u0: -2.803405 | cb 1 u0 x: 1.908691 → 0.954594135 (Δ -0.954096865) |
| y | 251 / 250 | 2.803894 | u0: -2.803894 | cb 1 u0 y: 1.908691 → 0.954594135 (Δ -0.954096865) |
| facing | 251 / 92 | 0.001537 | u0: 0.00119 | cb 8 u0 facing: 45.001221 → 45 (Δ -0.001221) |
| order | 251 / 0 | 0 | u0: 0 | — |
| t | 251 / 0 | 5.9e-05 | u0: 0 | — |

## MOV-0004

| Property | Samples / failing | Max absolute Δ | Final Δ by unit | First divergence |
|---|---|---|---|---|
| x | 601 / 600 | 1.393066 | u0: -1.393066 | cb 1 u0 x: 1.499512 → 0.75 (Δ -0.749512) |
| y | 601 / 589 | 0.024414 | u0: 0.018555 | cb 1 u0 y: 0.007813 → 0 (Δ -0.007813) |
| facing | 601 / 600 | 0.362 | u0: 0.362 | cb 1 u0 facing: 0.156594 → 0 (Δ -0.156594) |
| order | 601 / 0 | 0 | u0: 0 | — |
| t | 601 / 53 | 0.000112 | u0: 6.1e-05 | cb 503 u0 t: 10.059937 → 10.060000 (Δ 6.3e-05) |

## MOV-0005

| Property | Samples / failing | Max absolute Δ | Final Δ by unit | First divergence |
|---|---|---|---|---|
| x | 251 / 250 | 11.95752 | u0: -11.95752 | cb 1 u0 x: 3.999512 → 2 (Δ -1.999512) |
| y | 251 / 242 | 0.065918 | u0: -0.001465 | cb 1 u0 y: 0.021484 → 0 (Δ -0.021484) |
| facing | 251 / 245 | 0.219391 | u0: 0.219391 | cb 1 u0 facing: 0.124252 → 0 (Δ -0.124252) |
| order | 251 / 1 | 851986 | u0: 0 | cb 124 u0 order: 851986 → 0 (Δ -851986) |
| t | 251 / 0 | 5.9e-05 | u0: 0 | — |

## MOV-0006

| Property | Samples / failing | Max absolute Δ | Final Δ by unit | First divergence |
|---|---|---|---|---|
| x | 251 / 250 | 2.869385 | u0: -0.022217 | cb 1 u0 x: 2.699707 → 1.35000002 (Δ -1.34970698) |
| y | 251 / 249 | 12.766174 | u0: -3.432068 | cb 1 u0 y: 0.014648 → 0 (Δ -0.014648) |
| facing | 251 / 250 | 11.8645438 | u0: -0.1650926 | cb 1 u0 facing: 0.174245 → 0 (Δ -0.174245) |
| order | 251 / 2 | 851986 | u0: 0 | cb 234 u0 order: 851986 → 0 (Δ -851986) |
| t | 251 / 0 | 5.9e-05 | u0: 0 | — |

## MOV-0007

| Property | Samples / failing | Max absolute Δ | Final Δ by unit | First divergence |
|---|---|---|---|---|
| x | 251 / 250 | 3.949463 | u0: 3.949463 | cb 1 u0 x: 2.699707 → 1.35000002 (Δ -1.34970698) |
| y | 251 / 233 | 1.073242 | u0: 0 | cb 1 u0 y: 0.014648 → 0 (Δ -0.014648) |
| facing | 251 / 250 | 175.10212 | u0: 0.368973 | cb 1 u0 facing: 0.174245 → 0 (Δ -0.174245) |
| order | 251 / 1 | 851986 | u0: 0 | cb 240 u0 order: 851986 → 0 (Δ -851986) |
| t | 251 / 0 | 5.9e-05 | u0: 0 | — |

## MOV-0008

| Property | Samples / failing | Max absolute Δ | Final Δ by unit | First divergence |
|---|---|---|---|---|
| x | 251 / 250 | 4.076325 | u0: -1.323089 | cb 1 u0 x: 2.699707 → 1.35000002 (Δ -1.34970698) |
| y | 251 / 249 | 0.043945 | u0: -0.015625 | cb 1 u0 y: 0.014648 → 0 (Δ -0.014648) |
| facing | 251 / 250 | 0.344798 | u0: -0.344798 | cb 1 u0 facing: 0.174245 → 0 (Δ -0.174245) |
| order | 251 / 0 | 0 | u0: 0 | — |
| t | 251 / 0 | 5.9e-05 | u0: 0 | — |

## MOV-0009

| Property | Samples / failing | Max absolute Δ | Final Δ by unit | First divergence |
|---|---|---|---|---|
| x | 251 / 244 | 3.905213 | u0: -3.905213 | cb 7 u0 x: 2.672852 → 2.70000005 (Δ 0.02714805) |
| y | 251 / 238 | 1.142578 | u0: 0.017578 | cb 7 u0 y: 0.380859 → 0 (Δ -0.380859) |
| facing | 251 / 234 | 11.4592421 | u0: 0.374786 | cb 2 u0 facing: 167.967850 → 175.989288 (Δ 8.021438) |
| order | 251 / 1 | 851986 | u0: 0 | cb 189 u0 order: 851986 → 0 (Δ -851986) |
| t | 251 / 0 | 5.9e-05 | u0: 0 | — |

## MOV-0010

| Property | Samples / failing | Max absolute Δ | Final Δ by unit | First divergence |
|---|---|---|---|---|
| x | 251 / 250 | 1.34970698 | u0: 0.013428 | cb 1 u0 x: 2.699707 → 1.35000002 (Δ -1.34970698) |
| y | 251 / 249 | 0.043945 | u0: 0.023193 | cb 1 u0 y: 0.014648 → 0 (Δ -0.014648) |
| facing | 251 / 250 | 0.329718 | u0: -0.329718 | cb 1 u0 facing: 0.174245 → 0 (Δ -0.174245) |
| order | 251 / 0 | 0 | u0: 0 | — |
| t | 251 / 0 | 5.9e-05 | u0: 0 | — |
