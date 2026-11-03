# LiveRecall benchmark summary: t4

Independent runs: 3

| Metric | t4_run01.json | t4_run02.json | t4_run03.json | Median |
|---|---:|---:|---:|---:|
| Clients observed (count) | 100 | 100 | 100 | **100** |
| P50 caption age (ms) | 9.82 | 9.71 | 9.84 | **9.82** |
| P95 caption age (ms) | 12.50 | 12.40 | 12.69 | **12.50** |
| P99 caption age (ms) | 14.53 | 14.26 | 13.82 | **14.26** |
| Fresh Caption Ratio (%) | 100.00 | 100.00 | 100.00 | **100.00** |
| Fresh Final Caption Ratio (%) | 98.47 | 98.42 | 98.68 | **98.47** |
| Final-caption completeness (%) | 100.00 | 100.00 | 100.00 | **100.00** |
| Normal Update Coverage (%) | 98.33 | 98.33 | 98.33 | **98.33** |
| Duplicate messages (count) | 0 | 0 | 0 | **0** |
| Stale messages (count) | 0 | 0 | 0 | **0** |
| Connection errors (count) | 0 | 0 | 0 | **0** |
| Normal-client P95 (ms) | 12.50 | 12.40 | 12.69 | **12.50** |
| Normal-client freshness (%) | 100.00 | 100.00 | 100.00 | **100.00** |
| Slow-client P95 (ms) | — | — | — | **—** |
| Slow-client freshness (%) | — | — | — | **—** |
| Recovery P50 (ms) | 4.69 | 3.71 | 3.74 | **3.74** |
| Recovery P95 (ms) | 4.76 | 3.89 | 3.93 | **3.93** |

## Quick checks

- Median final completeness: 100.00%
- Median duplicates: 0
- Median stale messages: 0
- Median connection errors: 0

A dash indicates that the metric does not apply to this workload or was not reported.
