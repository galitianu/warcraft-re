# MOV-0023 measured results

All four frozen predictions **FAIL** compatibility. Three fresh WC3 processes per layout reproduce exactly; this is a completed negative evidence experiment, not a three-unit gameplay pass.

| Layout/unit | WC3 / predicted idle callback | WC3 final X,Y / order | Predicted final X,Y / order | WC3 / predicted peak lateral offset |
|---|---|---|---|---|
| MOV-0023-a/u0 | 101 / None | -28.675781,14.20752 / 0 | -21.4182129,10.6113281 / 851986 | 14.20752 / 14.20752 |
| MOV-0023-a/u1 | 131 / None | 51.453613,7.478516 / 0 | 51.4536133,7.47851562 / 851986 | -7.478516 / -7.478516 |
| MOV-0023-a/u2 | 172 / None | 24.009766,-46.875488 / 0 | 24.0097656,-46.8754883 / 851986 | -111.821289 / -111.821289 |
| MOV-0023-b/u0 | 101 / None | -28.675781,14.20752 / 0 | -21.4182129,10.6113281 / 851986 | 14.20752 / 14.20752 |
| MOV-0023-b/u1 | 131 / None | 51.453613,7.478516 / 0 | 51.4536133,7.47851562 / 851986 | -7.478516 / -7.478516 |
| MOV-0023-b/u2 | 160 / None | 24.144043,78.91748 / 0 | 24.144043,78.9174805 / 851986 | -111.98291 / -111.98291 |
| MOV-0023-c/u0 | 172 / None | 24.009766,-46.875488 / 0 | 24.0097656,-46.8754883 / 851986 | -111.821289 / -111.821289 |
| MOV-0023-c/u1 | 101 / None | -28.675781,14.20752 / 0 | -21.4182129,10.6113281 / 851986 | 14.20752 / 14.20752 |
| MOV-0023-c/u2 | 131 / None | 51.453613,7.478516 / 0 | 51.4536133,7.47851562 / 851986 | -7.478516 / -7.478516 |
| MOV-0023-d/u0 | 202 / 214 | 988.127441,-0.009277 / 0 | 988.12793,-0.0212402344 / 0 | 0.043945 / 0.043945 |
| MOV-0023-d/u1 | 187 / 196 | 9.346191,-36.706055 / 0 | 10.8603516,-36.166748 / 0 | 15.632813 / 47.685791 |
| MOV-0023-d/u2 | 197 / 187 | 7.089355,38.168945 / 0 | 8.07080078,32.2866211 / 0 | -47.789551 / -26.937012 |

`None` means no idle transition within 12 seconds. Orders are exact: 0 idle, 851986 move. Lateral offset is signed relative to the initial start→target line. The complete JSON includes waits and relative side/closest approach for **both** other units; side at closest approach does not imply the central units passed each other.

| Layout | First divergence (callback/unit/property) | Canonical failures x / y / facing / order | Largest x / y / facing difference |
|---|---|---|---|
| MOV-0023-a | 94/u0/x, delta 2.4191892000000017 | 507 / 507 / 921 / 1399 | 7.2575681 / 3.596191900000001 / 2.1234130000000278 |
| MOV-0023-b | 94/u0/x, delta 2.4191892000000017 | 507 / 507 / 498 / 1411 | 7.2575681 / 3.596191900000001 / 0.0017399999999838656 |
| MOV-0023-c | 94/u1/x, delta 2.4191892000000017 | 507 / 507 / 921 / 1399 | 7.2575681 / 3.596191900000001 / 2.1234130000000278 |
| MOV-0023-d | 1/u0/x, delta 2.69970703 | 1240 / 1612 / 1628 / 31 | 64.79394600000006 / 47.212890800000004 / 54.154358 |

No reported-clock, ordered-action/target or structural comparison fails. Tolerances are unchanged.

Ratings: central final move/idle outcomes are **P3**; central several-unit position offsets and a/c south-facing drift (2.123413°) are **P2**. The central west unit's approximately 0.001740° facing difference is **P1**, retained and pinned without investigation. d's route offsets (up to 64.794 X / 47.213 Y), wait pattern and 9–12 callback arrival changes are **P3**; its first 2.700-unit reading alone is **P2**. Smaller d final offsets/facing are recorded in JSON and not fitted separately.

All full per-property counts, first/per-unit divergence and maxima are pinned in `reviewed.json`. The evidence regression returns PASS only for the exact retained verdicts and unchanged predicted payloads; each compatibility verdict remains FAIL.
