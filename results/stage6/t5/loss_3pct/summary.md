# LiveRecall benchmark summary: loss_3pct

Independent runs: 3

| Metric | loss_3pct_run01.json | loss_3pct_run02.json | loss_3pct_run03.json | Median |
|---|---:|---:|---:|---:|
| Clients observed (count) | 100 | 100 | 100 | **100** |
| P50 caption age (ms) | 32.09 | 32.20 | 33.21 | **32.20** |
| P95 caption age (ms) | 113.27 | 136.44 | 239.52 | **136.44** |
| P99 caption age (ms) | 243.51 | 252.82 | 342.40 | **252.82** |
| Fresh Caption Ratio (%) | 100.00 | 99.96 | 99.98 | **99.98** |
| Fresh Final Caption Ratio (%) | 100.00 | 99.94 | 99.88 | **99.94** |
| Final-caption completeness (%) | 100.00 | 100.00 | 100.00 | **100.00** |
| Normal Update Coverage (%) | 73.50 | 75.36 | 74.59 | **74.59** |
| Duplicate messages (count) | 0 | 0 | 0 | **0** |
| Stale messages (count) | 0 | 0 | 0 | **0** |
| Connection errors (count) | 0 | 0 | 0 | **0** |
| Normal-client P95 (ms) | 113.27 | 136.44 | 239.52 | **136.44** |
| Normal-client freshness (%) | 100.00 | 99.96 | 99.98 | **99.98** |
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
