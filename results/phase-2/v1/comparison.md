# footman-v1 — after-due-update

Reference: `wc3-1.29.2-9231-x86`. Delta = actual − reference.

Tolerances: X/Y 0.001 world unit, facing 0.001° circular, order exact;
clock 0.0000615 s. Compare in callback/unit sequence; do not resample.

| Case | Result | Reference / actual samples | First divergence |
|---|---|---|---|
| MOV-0001 | PASS | 251 / 251 | — |
| MOV-0002 | FAIL | 502 / 502 | cb 1 u0 x: 2.699707 → 5.4000001 (Δ 2.7002931) |
| MOV-0003 | FAIL | 251 / 251 | cb 1 u0 x: 1.908691 → 3.81837726 (Δ 1.90968626) |
| MOV-0004 | FAIL | 601 / 601 | cb 1 u0 x: 1.499512 → 3.00000048 (Δ 1.50048848) |
| MOV-0005 | FAIL | 251 / 251 | cb 1 u0 x: 3.999512 → 8.00000095 (Δ 4.00048895) |
| MOV-0006 | FAIL | 251 / 251 | cb 1 u0 x: 2.699707 → 5.4000001 (Δ 2.7002931) |
| MOV-0007 | FAIL | 251 / 251 | cb 1 u0 x: 2.699707 → 5.4000001 (Δ 2.7002931) |
| MOV-0008 | FAIL | 251 / 251 | cb 1 u0 x: 2.699707 → 5.4000001 (Δ 2.7002931) |
| MOV-0009 | FAIL | 251 / 251 | cb 1 u0 x: 0.000000 → 5.4000001 (Δ 5.4000001) |
| MOV-0010 | FAIL | 251 / 251 | cb 1 u0 x: 2.699707 → 5.4000001 (Δ 2.7002931) |

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
| x | 502 / 250 | 3.958252 | u0: -3.958252; u1: 0 | cb 1 u0 x: 2.699707 → 5.4000001 (Δ 2.7002931) |
| y | 502 / 239 | 0.043945 | u0: -0.033203; u1: 0 | cb 1 u0 y: 0.014648 → 0 (Δ -0.014648) |
| facing | 502 / 250 | 0.388643 | u0: -0.388643; u1: 0 | cb 1 u0 facing: 0.174245 → 0 (Δ -0.174245) |
| order | 502 / 1 | 851986 | u0: 0; u1: 0 | cb 183 u0 order: 851986 → 0 (Δ -851986) |
| t | 502 / 0 | 5.9e-05 | u0: 0; u1: 0 | — |

## MOV-0003

| Property | Samples / failing | Max absolute Δ | Final Δ by unit | First divergence |
|---|---|---|---|---|
| x | 251 / 250 | 2.804077 | u0: -2.804077 | cb 1 u0 x: 1.908691 → 3.81837726 (Δ 1.90968626) |
| y | 251 / 250 | 2.804566 | u0: -2.804566 | cb 1 u0 y: 1.908691 → 3.81837726 (Δ 1.90968626) |
| facing | 251 / 92 | 0.001537 | u0: 0.00119 | cb 8 u0 facing: 45.001221 → 45 (Δ -0.001221) |
| order | 251 / 1 | 851986 | u0: 0 | cb 183 u0 order: 851986 → 0 (Δ -851986) |
| t | 251 / 0 | 5.9e-05 | u0: 0 | — |

## MOV-0004

| Property | Samples / failing | Max absolute Δ | Final Δ by unit | First divergence |
|---|---|---|---|---|
| x | 601 / 600 | 1.669068 | u0: -1.330932 | cb 1 u0 x: 1.499512 → 3.00000048 (Δ 1.50048848) |
| y | 601 / 589 | 0.024414 | u0: 0.018555 | cb 1 u0 y: 0.007813 → 0 (Δ -0.007813) |
| facing | 601 / 600 | 0.362 | u0: 0.362 | cb 1 u0 facing: 0.156594 → 0 (Δ -0.156594) |
| order | 601 / 0 | 0 | u0: 0 | — |
| t | 601 / 53 | 0.000112 | u0: 6.1e-05 | cb 503 u0 t: 10.059937 → 10.060000 (Δ 6.3e-05) |

## MOV-0005

| Property | Samples / failing | Max absolute Δ | Final Δ by unit | First divergence |
|---|---|---|---|---|
| x | 251 / 250 | 11.934266 | u0: -11.934266 | cb 1 u0 x: 3.999512 → 8.00000095 (Δ 4.00048895) |
| y | 251 / 242 | 0.065918 | u0: -0.001465 | cb 1 u0 y: 0.021484 → 0 (Δ -0.021484) |
| facing | 251 / 245 | 0.219391 | u0: 0.219391 | cb 1 u0 facing: 0.124252 → 0 (Δ -0.124252) |
| order | 251 / 1 | 851986 | u0: 0 | cb 124 u0 order: 851986 → 0 (Δ -851986) |
| t | 251 / 0 | 5.9e-05 | u0: 0 | — |

## MOV-0006

| Property | Samples / failing | Max absolute Δ | Final Δ by unit | First divergence |
|---|---|---|---|---|
| x | 251 / 250 | 2.713897 | u0: 2.678009 | cb 1 u0 x: 2.699707 → 5.4000001 (Δ 2.7002931) |
| y | 251 / 249 | 16.847412 | u0: -3.400146 | cb 1 u0 y: 0.014648 → 0 (Δ -0.014648) |
| facing | 251 / 250 | 89.86241 | u0: -0.165085 | cb 1 u0 facing: 0.174245 → 0 (Δ -0.174245) |
| order | 251 / 3 | 851986 | u0: 0 | cb 233 u0 order: 851986 → 0 (Δ -851986) |
| t | 251 / 0 | 5.9e-05 | u0: 0 | — |

## MOV-0007

| Property | Samples / failing | Max absolute Δ | Final Δ by unit | First divergence |
|---|---|---|---|---|
| x | 251 / 250 | 37.904297 | u0: 6.641845 | cb 1 u0 x: 2.699707 → 5.4000001 (Δ 2.7002931) |
| y | 251 / 233 | 1.073242 | u0: 0 | cb 1 u0 y: 0.014648 → 0 (Δ -0.014648) |
| facing | 251 / 250 | 179.862395 | u0: 0.368973 | cb 1 u0 facing: 0.174245 → 0 (Δ -0.174245) |
| order | 251 / 8 | 851986 | u0: 0 | cb 233 u0 order: 851986 → 0 (Δ -851986) |
| t | 251 / 0 | 5.9e-05 | u0: 0 | — |

## MOV-0008

| Property | Samples / failing | Max absolute Δ | Final Δ by unit | First divergence |
|---|---|---|---|---|
| x | 251 / 250 | 10.815948 | u0: -1.872558 | cb 1 u0 x: 2.699707 → 5.4000001 (Δ 2.7002931) |
| y | 251 / 249 | 0.043945 | u0: -0.015625 | cb 1 u0 y: 0.014648 → 0 (Δ -0.014648) |
| facing | 251 / 250 | 0.344798 | u0: -0.344798 | cb 1 u0 facing: 0.174245 → 0 (Δ -0.174245) |
| order | 251 / 2 | 851986 | u0: 0 | cb 90 u0 order: 851986 → 0 (Δ -851986) |
| t | 251 / 0 | 5.9e-05 | u0: 0 | — |

## MOV-0009

| Property | Samples / failing | Max absolute Δ | Final Δ by unit | First divergence |
|---|---|---|---|---|
| x | 251 / 250 | 35.272217 | u0: -3.873291 | cb 1 u0 x: 0.000000 → 5.4000001 (Δ 5.4000001) |
| y | 251 / 238 | 1.142578 | u0: 0.017578 | cb 7 u0 y: 0.380859 → 0 (Δ -0.380859) |
| facing | 251 / 250 | 175.989273 | u0: 0.374786 | cb 1 u0 facing: 175.989273 → 0 (Δ -175.989273) |
| order | 251 / 7 | 851986 | u0: 0 | cb 183 u0 order: 851986 → 0 (Δ -851986) |
| t | 251 / 0 | 5.9e-05 | u0: 0 | — |

## MOV-0010

| Property | Samples / failing | Max absolute Δ | Final Δ by unit | First divergence |
|---|---|---|---|---|
| x | 251 / 250 | 2.713897 | u0: 2.713654 | cb 1 u0 x: 2.699707 → 5.4000001 (Δ 2.7002931) |
| y | 251 / 249 | 0.043945 | u0: 0.023193 | cb 1 u0 y: 0.014648 → 0 (Δ -0.014648) |
| facing | 251 / 250 | 0.329718 | u0: -0.329718 | cb 1 u0 facing: 0.174245 → 0 (Δ -0.174245) |
| order | 251 / 0 | 0 | u0: 0 | — |
| t | 251 / 0 | 5.9e-05 | u0: 0 | — |
