# Model revision: footman-v1 → footman-v2

Both use the same setups and tolerances. First divergence is compared per
case/property; later does not mean passing. Before-phase is diagnostic only.

| Case | Property | v1 first callback | v2 first callback | Change |
|---|---|---|---|---|
| MOV-0001 | overall | — | — | unchanged |
| MOV-0001 | x | — | — | unchanged |
| MOV-0001 | y | — | — | unchanged |
| MOV-0001 | facing | — | — | unchanged |
| MOV-0001 | order | — | — | unchanged |
| MOV-0002 | overall | 1 | 1 | unchanged |
| MOV-0002 | x | 1 | 4 | later |
| MOV-0002 | y | 1 | 1 | unchanged |
| MOV-0002 | facing | 1 | 1 | unchanged |
| MOV-0002 | order | 183 | 183 | unchanged |
| MOV-0003 | overall | 1 | 3 | later |
| MOV-0003 | x | 1 | 3 | later |
| MOV-0003 | y | 1 | 3 | later |
| MOV-0003 | facing | 8 | 8 | unchanged |
| MOV-0003 | order | 183 | 183 | unchanged |
| MOV-0004 | overall | 1 | 1 | unchanged |
| MOV-0004 | x | 1 | 4 | later |
| MOV-0004 | y | 1 | 1 | unchanged |
| MOV-0004 | facing | 1 | 1 | unchanged |
| MOV-0004 | order | — | — | unchanged |
| MOV-0005 | overall | 1 | 1 | unchanged |
| MOV-0005 | x | 1 | 4 | later |
| MOV-0005 | y | 1 | 1 | unchanged |
| MOV-0005 | facing | 1 | 1 | unchanged |
| MOV-0005 | order | 124 | 124 | unchanged |
| MOV-0006 | overall | 1 | 1 | unchanged |
| MOV-0006 | x | 1 | 4 | later |
| MOV-0006 | y | 1 | 1 | unchanged |
| MOV-0006 | facing | 1 | 1 | unchanged |
| MOV-0006 | order | 233 | 233 | unchanged |
| MOV-0007 | overall | 1 | 1 | unchanged |
| MOV-0007 | x | 1 | 4 | later |
| MOV-0007 | y | 1 | 1 | unchanged |
| MOV-0007 | facing | 1 | 1 | unchanged |
| MOV-0007 | order | 233 | 240 | later |
| MOV-0008 | overall | 1 | 1 | unchanged |
| MOV-0008 | x | 1 | 4 | later |
| MOV-0008 | y | 1 | 1 | unchanged |
| MOV-0008 | facing | 1 | 1 | unchanged |
| MOV-0008 | order | 90 | 91 | later |
| MOV-0009 | overall | 1 | 7 | later |
| MOV-0009 | x | 1 | 7 | later |
| MOV-0009 | y | 7 | 7 | unchanged |
| MOV-0009 | facing | 1 | 25 | later |
| MOV-0009 | order | 183 | 189 | later |
| MOV-0010 | overall | 1 | 1 | unchanged |
| MOV-0010 | x | 1 | 4 | later |
| MOV-0010 | y | 1 | 1 | unchanged |
| MOV-0010 | facing | 1 | 1 | unchanged |
| MOV-0010 | order | — | — | unchanged |

## Observation-phase sensitivity (v2 only)

Rows count differing primary/diagnostic samples, while each phase is still
graded independently against WC3. No shifted matching or tolerance changes.

| Case | Samples changed by phase | After first divergence | Before first divergence |
|---|---|---|---|
| MOV-0001 | 0 | — | — |
| MOV-0002 | 183 | cb 1 u0 y: 0.014648 → 0 (Δ -0.014648) | cb 1 u0 x: 2.699707 → 1.35000002 (Δ -1.34970698) |
| MOV-0003 | 183 | cb 3 u0 x: 9.544922 → 9.54594231 (Δ 0.00102031) | cb 1 u0 x: 1.908691 → 0.954594135 (Δ -0.954096865) |
| MOV-0004 | 328 | cb 1 u0 y: 0.007813 → 0 (Δ -0.007813) | cb 1 u0 x: 1.499512 → 0.75 (Δ -0.749512) |
| MOV-0005 | 123 | cb 1 u0 y: 0.021484 → 0 (Δ -0.021484) | cb 1 u0 x: 3.999512 → 2 (Δ -1.999512) |
| MOV-0006 | 233 | cb 1 u0 y: 0.014648 → 0 (Δ -0.014648) | cb 1 u0 x: 2.699707 → 1.35000002 (Δ -1.34970698) |
| MOV-0007 | 234 | cb 1 u0 y: 0.014648 → 0 (Δ -0.014648) | cb 1 u0 x: 2.699707 → 1.35000002 (Δ -1.34970698) |
| MOV-0008 | 91 | cb 1 u0 y: 0.014648 → 0 (Δ -0.014648) | cb 1 u0 x: 2.699707 → 1.35000002 (Δ -1.34970698) |
| MOV-0009 | 184 | cb 7 u0 x: 2.672852 → 4.05000019 (Δ 1.37714819) | cb 2 u0 facing: 167.967850 → 175.989288 (Δ 8.021438) |
| MOV-0010 | 50 | cb 1 u0 y: 0.014648 → 0 (Δ -0.014648) | cb 1 u0 x: 2.699707 → 1.35000002 (Δ -1.34970698) |
