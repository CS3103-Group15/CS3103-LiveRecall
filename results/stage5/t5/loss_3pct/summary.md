# LiveRecall benchmark summary: loss_3pct

Independent runs: 3

| Metric | loss_3pct_run01.json | loss_3pct_run02.json | loss_3pct_run03.json | Median |
|---|---:|---:|---:|---:|
| Clients observed (count) | 100 | 100 | 100 | **100** |
| P50 caption age (ms) | 43.26 | 41.17 | 40.90 | **41.17** |
| P95 caption age (ms) | 238.39 | 108.89 | 84.88 | **108.89** |
| P99 caption age (ms) | 263.28 | 261.83 | 256.08 | **261.83** |
| Fresh Caption Ratio (%) | 99.97 | 100.00 | 99.99 | **99.99** |
| Fresh Final Caption Ratio (%) | 99.90 | 100.00 | 99.98 | **99.98** |
| Final-caption completeness (%) | 100.00 | 100.00 | 100.00 | **100.00** |
| Normal Update Coverage (%) | 99.91 | 99.93 | 99.94 | **99.93** |
| Duplicate messages (count) | 0 | 0 | 0 | **0** |
| Stale messages (count) | 0 | 0 | 0 | **0** |
| Connection errors (count) | 0 | 0 | 0 | **0** |
| Normal-client P95 (ms) | 238.39 | 108.89 | 84.88 | **108.89** |
| Normal-client freshness (%) | 99.97 | 100.00 | 99.99 | **99.99** |
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
