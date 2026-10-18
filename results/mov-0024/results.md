# MOV-0024 measured results

Three fresh WC3 processes per layout. Canonical verdicts use unchanged tolerances.

| Layout/unit | WC3 / H0 / C96 idle callback | WC3 final x,y,facing,order |
|---|---|---|
| MOV-0024-a/u0 | 98 / None / 88 | -48.0,48.0,359.681061,0 |
| MOV-0024-a/u1 | 115 / None / 89 | 13.997559,-0.019531,180.371155,0 |
| MOV-0024-b/u0 | 118 / None / 83 | 7.17041,47.531738,261.421448,0 |
| MOV-0024-b/u1 | 91 / 91 / 91 | 0.0,-14.011475,89.999992,0 |
| MOV-0024-c/u0 | 94 / None / 85 | -10.729492,7.070313,326.613129,0 |
| MOV-0024-c/u1 | 184 / None / None | 985.967773,0.144531,359.301605,0 |
| MOV-0024-c/u2 | not ordered / not ordered / not ordered | -16.0,-48.0,0.0,0 |
| MOV-0024-d/u0 | 86 / None / 85 | -56.653076,15.90918,344.313751,0 |
| MOV-0024-d/u1 | not ordered / not ordered / not ordered | 0.0,0.0,0.0,0 |
| MOV-0024-d/u2 | not ordered / not ordered / not ordered | -16.0,-48.0,0.0,0 |
| MOV-0024-e/u0 | 85 / None / 82 | 0.0,62.594727,270.0,0 |
| MOV-0024-e/u1 | 100 / None / 82 | -13.488525,-24.776855,61.436554,0 |
| MOV-0024-e/u2 | 116 / None / 83 | 54.496094,-0.027588,179.664871,0 |
| MOV-0024-f/u0 | 97 / 97 / 88 | -48.0,16.0,359.681061,0 |
| MOV-0024-f/u1 | 107 / None / 89 | 13.997559,-0.019531,180.371155,0 |
| MOV-0024-f/u2 | 130 / None / 94 | 12.066895,59.13916,234.427109,0 |

`None` means no idle transition within the 12-second window. `not ordered` means a stationary control.

| Layout | H0 first divergence | C96 first divergence | Intervention |
|---|---|---|---|
| MOV-0024-a | 98/u0/x delta 17.7773438 | 88/u0/facing delta 0.2990855190000161 | PASS |
| MOV-0024-b | 118/u0/order delta 851986 | 83/u0/facing delta -0.2978719999999839 | PASS |
| MOV-0024-c | 0/u2/x delta 16.0 | 0/u2/x delta 16.0 | INCONCLUSIVE |
| MOV-0024-d | 0/u2/x delta 16.0 | 0/u2/x delta 16.0 | INCONCLUSIVE |
| MOV-0024-e | 85/u0/order delta 851986 | 82/u0/order delta -851986 | PASS |
| MOV-0024-f | 97/u0/x delta 17.7773438 | 88/u0/facing delta 0.2990855190000161 | INCONCLUSIVE |
