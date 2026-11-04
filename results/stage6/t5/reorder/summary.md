# LiveRecall benchmark summary: reorder

Independent runs: 3

| Metric | reorder_run01.json | reorder_run02.json | reorder_run03.json | Median |
|---|---:|---:|---:|---:|
| Clients observed (count) | 100 | 100 | 100 | **100** |
| P50 caption age (ms) | 88.62 | 87.19 | 86.75 | **87.19** |
| P95 caption age (ms) | 114.81 | 110.82 | 112.65 | **112.65** |
| P99 caption age (ms) | 137.86 | 134.68 | 142.32 | **137.86** |
| Fresh Caption Ratio (%) | 100.00 | 100.00 | 100.00 | **100.00** |
| Fresh Final Caption Ratio (%) | 100.00 | 100.00 | 100.00 | **100.00** |
| Final-caption completeness (%) | 100.00 | 100.00 | 100.00 | **100.00** |
| Normal Update Coverage (%) | 100.00 | 100.00 | 99.76 | **100.00** |
| Duplicate messages (count) | 0 | 0 | 0 | **0** |
| Stale messages (count) | 0 | 0 | 0 | **0** |
| Connection errors (count) | 0 | 0 | 0 | **0** |
| Normal-client P95 (ms) | 114.81 | 110.82 | 112.65 | **112.65** |
| Normal-client freshness (%) | 100.00 | 100.00 | 100.00 | **100.00** |
| Slow-client P95 (ms) | — | — | — | **—** |
| Slow-client freshness (%) | — | — | — | **—** |
| Recovery P50 (ms) | — | — | — | **—** |
| Recovery P95 (ms) | — | — | — | **—** |

## Quick checks

- Median final completeness: 100.00%
- Median duplicates: 0
- Median stale messages: 0
- Median connection errors: 0

A dash indicates that the metric does not apply to this workload or was not reported.
