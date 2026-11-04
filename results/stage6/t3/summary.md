# LiveRecall benchmark summary: t3

Independent runs: 3

| Metric | t3_run01.json | t3_run02.json | t3_run03.json | Median |
|---|---:|---:|---:|---:|
| Clients observed (count) | 100 | 100 | 100 | **100** |
| P50 caption age (ms) | 9.18 | 9.32 | 8.96 | **9.18** |
| P95 caption age (ms) | 12.80 | 12.99 | 12.79 | **12.80** |
| P99 caption age (ms) | 5837.15 | 5858.74 | 5819.21 | **5837.15** |
| Fresh Caption Ratio (%) | 97.02 | 97.02 | 97.04 | **97.02** |
| Fresh Final Caption Ratio (%) | 94.34 | 94.34 | 94.37 | **94.34** |
| Final-caption completeness (%) | 100.00 | 100.00 | 100.00 | **100.00** |
| Normal Update Coverage (%) | 94.34 | 94.34 | 94.34 | **94.34** |
| Duplicate messages (count) | 0 | 0 | 0 | **0** |
| Stale messages (count) | 0 | 0 | 0 | **0** |
| Connection errors (count) | 0 | 0 | 0 | **0** |
| Normal-client P95 (ms) | 11.81 | 12.08 | 11.61 | **11.81** |
| Normal-client freshness (%) | 100.00 | 100.00 | 100.00 | **100.00** |
| Slow-client P95 (ms) | 7835.20 | 7872.79 | 7824.50 | **7835.20** |
| Slow-client freshness (%) | 35.35 | 35.35 | 35.59 | **35.35** |
| Recovery P50 (ms) | — | — | — | **—** |
| Recovery P95 (ms) | — | — | — | **—** |

## Quick checks

- Median final completeness: 100.00%
- Median duplicates: 0
- Median stale messages: 0
- Median connection errors: 0

A dash indicates that the metric does not apply to this workload or was not reported.
