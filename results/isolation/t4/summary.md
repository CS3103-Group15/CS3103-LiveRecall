# LiveRecall benchmark summary: t4

Independent runs: 3

| Metric | t4_run01.json | t4_run02.json | t4_run03.json | Median |
|---|---:|---:|---:|---:|
| Clients observed (count) | 100 | 100 | 100 | **100** |
| P50 caption age (ms) | 4.69 | 4.62 | 4.56 | **4.62** |
| P95 caption age (ms) | 5.96 | 5.80 | 5.64 | **5.80** |
| P99 caption age (ms) | 8.29 | 6.74 | 6.10 | **6.74** |
| Fresh Caption Ratio (%) | 100.00 | 100.00 | 100.00 | **100.00** |
| Fresh Final Caption Ratio (%) | 98.49 | 98.68 | 98.68 | **98.68** |
| Final-caption completeness (%) | 100.00 | 100.00 | 100.00 | **100.00** |
| Normal Update Coverage (%) | 98.42 | 98.42 | 98.42 | **98.42** |
| Duplicate messages (count) | 0 | 0 | 0 | **0** |
| Stale messages (count) | 0 | 0 | 0 | **0** |
| Connection errors (count) | 0 | 0 | 0 | **0** |
| Normal-client P95 (ms) | 5.96 | 5.80 | 5.64 | **5.80** |
| Normal-client freshness (%) | 100.00 | 100.00 | 100.00 | **100.00** |
| Slow-client P95 (ms) | — | — | — | **—** |
| Slow-client freshness (%) | — | — | — | **—** |
| Recovery P50 (ms) | 7.08 | 7.96 | 7.13 | **7.13** |
| Recovery P95 (ms) | 8.96 | 8.18 | 7.84 | **8.18** |

## Quick checks

- Median final completeness: 100.00%
- Median duplicates: 0
- Median stale messages: 0
- Median connection errors: 0

A dash indicates that the metric does not apply to this workload or was not reported.
