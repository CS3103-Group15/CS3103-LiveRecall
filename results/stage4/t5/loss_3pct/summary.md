# LiveRecall benchmark summary: loss_3pct

Independent runs: 3

| Metric | loss_3pct_run01.json | loss_3pct_run02.json | loss_3pct_run03.json | Median |
|---|---:|---:|---:|---:|
| Clients observed (count) | 100 | 100 | 100 | **100** |
| P50 caption age (ms) | 5.25 | 5.28 | 5.44 | **5.28** |
| P95 caption age (ms) | 206.79 | 206.05 | 206.21 | **206.21** |
| P99 caption age (ms) | 216.68 | 214.57 | 213.37 | **214.57** |
| Fresh Caption Ratio (%) | 99.98 | 99.99 | 99.96 | **99.98** |
| Fresh Final Caption Ratio (%) | 100.00 | 99.98 | 99.96 | **99.98** |
| Final-caption completeness (%) | 100.00 | 100.00 | 100.00 | **100.00** |
| Normal Update Coverage (%) | 99.95 | 99.97 | 99.96 | **99.96** |
| Duplicate messages (count) | 0 | 0 | 0 | **0** |
| Stale messages (count) | 0 | 0 | 0 | **0** |
| Connection errors (count) | 0 | 0 | 0 | **0** |
| Normal-client P95 (ms) | 206.79 | 206.05 | 206.21 | **206.21** |
| Normal-client freshness (%) | 99.98 | 99.99 | 99.96 | **99.98** |
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
