# LiveRecall benchmark summary: t4

Independent runs: 3

| Metric | t4_run01.json | t4_run02.json | t4_run03.json | Median |
|---|---:|---:|---:|---:|
| Clients observed (count) | 100 | 100 | 100 | **100** |
| P50 caption age (ms) | 5.21 | 4.91 | 5.09 | **5.09** |
| P95 caption age (ms) | 6.48 | 6.05 | 6.58 | **6.48** |
| P99 caption age (ms) | 7.43 | 6.87 | 7.93 | **7.43** |
| Fresh Caption Ratio (%) | 100.00 | 100.00 | 100.00 | **100.00** |
| Fresh Final Caption Ratio (%) | 98.68 | 98.42 | 98.68 | **98.68** |
| Final-caption completeness (%) | 100.00 | 100.00 | 100.00 | **100.00** |
| Normal Update Coverage (%) | 98.33 | 98.25 | 98.33 | **98.33** |
| Duplicate messages (count) | 0 | 0 | 0 | **0** |
| Stale messages (count) | 0 | 0 | 0 | **0** |
| Connection errors (count) | 0 | 0 | 0 | **0** |
| Normal-client P95 (ms) | 6.48 | 6.05 | 6.58 | **6.48** |
| Normal-client freshness (%) | 100.00 | 100.00 | 100.00 | **100.00** |
| Slow-client P95 (ms) | — | — | — | **—** |
| Slow-client freshness (%) | — | — | — | **—** |
| Recovery P50 (ms) | 2.67 | 3.36 | 3.04 | **3.04** |
| Recovery P95 (ms) | 2.94 | 3.50 | 3.16 | **3.16** |

## Quick checks

- Median final completeness: 100.00%
- Median duplicates: 0
- Median stale messages: 0
- Median connection errors: 0

A dash indicates that the metric does not apply to this workload or was not reported.
