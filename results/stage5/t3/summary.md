# LiveRecall benchmark summary: t3

Independent runs: 3

| Metric | t3_run01.json | t3_run02.json | t3_run03.json | Median |
|---|---:|---:|---:|---:|
| Clients observed (count) | 100 | 100 | 100 | **100** |
| P50 caption age (ms) | 6.25 | 6.20 | 6.33 | **6.25** |
| P95 caption age (ms) | 2258.74 | 2253.13 | 2255.62 | **2255.62** |
| P99 caption age (ms) | 24013.62 | 24021.83 | 24007.07 | **24013.62** |
| Fresh Caption Ratio (%) | 94.65 | 94.65 | 94.65 | **94.65** |
| Fresh Final Caption Ratio (%) | 90.00 | 90.00 | 90.00 | **90.00** |
| Final-caption completeness (%) | 95.13 | 95.13 | 95.13 | **95.13** |
| Normal Update Coverage (%) | 95.18 | 95.18 | 95.18 | **95.18** |
| Duplicate messages (count) | 0 | 0 | 0 | **0** |
| Stale messages (count) | 0 | 0 | 0 | **0** |
| Connection errors (count) | 0 | 0 | 0 | **0** |
| Normal-client P95 (ms) | 8.18 | 7.99 | 8.58 | **8.18** |
| Normal-client freshness (%) | 100.00 | 100.00 | 100.00 | **100.00** |
| Slow-client P95 (ms) | 28061.30 | 28074.80 | 28058.04 | **28061.30** |
| Slow-client freshness (%) | 1.69 | 1.69 | 1.69 | **1.69** |
| Recovery P50 (ms) | — | — | — | **—** |
| Recovery P95 (ms) | — | — | — | **—** |

## Quick checks

- Median final completeness: 95.13%
- Median duplicates: 0
- Median stale messages: 0
- Median connection errors: 0

A dash indicates that the metric does not apply to this workload or was not reported.
