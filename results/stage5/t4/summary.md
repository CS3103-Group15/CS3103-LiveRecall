# LiveRecall benchmark summary: t4

Independent runs: 3

| Metric | t4_run01.json | t4_run02.json | t4_run03.json | Median |
|---|---:|---:|---:|---:|
| Clients observed (count) | 100 | 100 | 100 | **100** |
| P50 caption age (ms) | 6.62 | 6.19 | 6.27 | **6.27** |
| P95 caption age (ms) | 11.29 | 8.26 | 8.19 | **8.26** |
| P99 caption age (ms) | 16.50 | 9.85 | 9.43 | **9.85** |
| Fresh Caption Ratio (%) | 100.00 | 100.00 | 100.00 | **100.00** |
| Fresh Final Caption Ratio (%) | 98.42 | 98.42 | 98.42 | **98.42** |
| Final-caption completeness (%) | 100.00 | 100.00 | 100.00 | **100.00** |
| Normal Update Coverage (%) | 98.33 | 98.25 | 98.25 | **98.25** |
| Duplicate messages (count) | 0 | 0 | 0 | **0** |
| Stale messages (count) | 0 | 0 | 0 | **0** |
| Connection errors (count) | 0 | 0 | 0 | **0** |
| Normal-client P95 (ms) | 11.29 | 8.26 | 8.19 | **8.26** |
| Normal-client freshness (%) | 100.00 | 100.00 | 100.00 | **100.00** |
| Slow-client P95 (ms) | — | — | — | **—** |
| Slow-client freshness (%) | — | — | — | **—** |
| Recovery P50 (ms) | 2.90 | 1.90 | 3.92 | **2.90** |
| Recovery P95 (ms) | 3.92 | 4.59 | 5.91 | **4.59** |

## Quick checks

- Median final completeness: 100.00%
- Median duplicates: 0
- Median stale messages: 0
- Median connection errors: 0

A dash indicates that the metric does not apply to this workload or was not reported.
