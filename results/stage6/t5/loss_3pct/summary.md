# LiveRecall benchmark summary: loss_3pct

Independent runs: 3

| Metric | loss_3pct_run01.json | loss_3pct_run02.json | loss_3pct_run03.json | Median |
|---|---:|---:|---:|---:|
| Clients observed (count) | 100 | 100 | 100 | **100** |
| P50 caption age (ms) | 8.76 | 8.80 | 8.51 | **8.76** |
| P95 caption age (ms) | 35.52 | 21.83 | 207.77 | **35.52** |
| P99 caption age (ms) | 226.75 | 219.63 | 257.61 | **226.75** |
| Fresh Caption Ratio (%) | 99.99 | 100.00 | 99.99 | **99.99** |
| Fresh Final Caption Ratio (%) | 99.98 | 100.00 | 99.98 | **99.98** |
| Final-caption completeness (%) | 100.00 | 100.00 | 100.00 | **100.00** |
| Normal Update Coverage (%) | 81.10 | 79.29 | 78.76 | **79.29** |
| Duplicate messages (count) | 0 | 0 | 0 | **0** |
| Stale messages (count) | 0 | 0 | 0 | **0** |
| Connection errors (count) | 0 | 0 | 0 | **0** |
| Normal-client P95 (ms) | 35.52 | 21.83 | 207.77 | **35.52** |
| Normal-client freshness (%) | 99.99 | 100.00 | 99.99 | **99.99** |
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
