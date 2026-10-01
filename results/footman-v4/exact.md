# footman-v4 exact text comparison

Each C++ float printed as WC3 R2SW(value, 1, 6) and compared as a string with the
canonical fixture: SAMPLE x/y/facing, current order, and the TICK clock.

| Case | x | y | facing | order | clock | Result |
|---|---|---|---|---|---|---|
| MOV-0001 | 251/251 | 251/251 | 251/251 | 251/251 | 251/251 | identical |
| MOV-0002 | 502/502 | 502/502 | 502/502 | 502/502 | 251/251 | identical |
| MOV-0003 | 251/251 | 251/251 | 251/251 | 251/251 | 251/251 | identical |
| MOV-0004 | 601/601 | 601/601 | 601/601 | 601/601 | 601/601 | identical |
| MOV-0005 | 251/251 | 251/251 | 251/251 | 251/251 | 251/251 | identical |
| MOV-0006 | 251/251 | 251/251 | 251/251 | 251/251 | 251/251 | identical |
| MOV-0007 | 251/251 | 251/251 | 251/251 | 251/251 | 251/251 | identical |
| MOV-0008 | 251/251 | 251/251 | 251/251 | 251/251 | 251/251 | identical |
| MOV-0009 | 251/251 | 251/251 | 251/251 | 251/251 | 251/251 | identical |
| MOV-0010 | 251/251 | 251/251 | 251/251 | 251/251 | 251/251 | identical |
