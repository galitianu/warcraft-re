# MOV-0022 two Footmen with unit pathing

Gate: **PASS** (P3 failures and comparator differences equal the reviewed lists).

C++ footman-v4 with unit pathing runs the same v1 scenario bytes. Canonical comparison uses the
unchanged tolerances.

| Variant | Canonical | Failing properties (failures, largest difference) | Side | Arrival WC3 / C++ | P3 acceptance | Open differences (rating) |
|---|---|---|---|---|---|---|
| MOV-0022-a | PASS | none | u0 left, u1 left | u0 182/182, u1 217/217 | PASS | — |
| MOV-0022-b | PASS | none | u0 right, u1 right | u0 214/214, u1 176/176 | PASS | — |
| MOV-0022-c | PASS | none | u0 left, u1 left | u0 179/179, u1 214/214 | PASS | — |
| MOV-0022-d | PASS | none | u0 left, u1 left | u0 188/188, u1 278/278 | PASS | — |
| MOV-0022-e | PASS | none | u0 left | u0 265/265 | PASS | — |
| MOV-0022-f | PASS | none | u0 right, u1 left | u0 175/175, u1 301/301 | PASS | — |
