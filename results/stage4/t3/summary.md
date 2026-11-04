# LiveRecall benchmark summary: t3

Independent runs: 3

| Metric | t3_run01.json | t3_run02.json | t3_run03.json | Median |
|---|---:|---:|---:|---:|
| Clients observed (count) | 100 | 100 | 100 | **100** |
| P50 caption age (ms) | 4.88 | 5.13 | 4.99 | **4.99** |
| P95 caption age (ms) | 2253.34 | 2247.87 | 2254.65 | **2253.34** |
| P99 caption age (ms) | 24015.32 | 24014.20 | 24017.52 | **24015.32** |
| Fresh Caption Ratio (%) | 94.65 | 94.65 | 94.65 | **94.65** |
| Fresh Final Caption Ratio (%) | 90.00 | 90.00 | 90.00 | **90.00** |
| Final-caption completeness (%) | 95.13 | 95.13 | 95.13 | **95.13** |
| Normal Update Coverage (%) | 95.18 | 95.18 | 95.18 | **95.18** |
| Duplicate messages (count) | 0 | 0 | 0 | **0** |
| Stale messages (count) | 0 | 0 | 0 | **0** |
| Connection errors (count) | 0 | 0 | 0 | **0** |
| Normal-client P95 (ms) | 5.86 | 6.53 | 6.41 | **6.41** |
| Normal-client freshness (%) | 100.00 | 100.00 | 100.00 | **100.00** |
| Slow-client P95 (ms) | 28068.38 | 28070.34 | 28074.05 | **28070.34** |
| Slow-client freshness (%) | 1.69 | 1.69 | 1.69 | **1.69** |
| Recovery P50 (ms) | — | — | — | **—** |
| Recovery P95 (ms) | — | — | — | **—** |

## Quick checks

- Median final completeness: 95.13%
- Median duplicates: 0
- Median stale messages: 0
- Median connection errors: 0

A dash indicates that the metric does not apply to this workload or was not reported.
