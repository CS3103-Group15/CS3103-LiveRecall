# LiveRecall benchmark summary: loss_3pct

Independent runs: 3

| Metric | loss_3pct_run01.json | loss_3pct_run02.json | loss_3pct_run03.json | Median |
|---|---:|---:|---:|---:|
| Clients observed (count) | 100 | 100 | 100 | **100** |
| P50 caption age (ms) | 6.47 | 6.57 | 6.38 | **6.47** |
| P95 caption age (ms) | 206.43 | 207.77 | 206.37 | **206.43** |
| P99 caption age (ms) | 212.65 | 215.20 | 212.78 | **212.78** |
| Fresh Caption Ratio (%) | 100.00 | 100.00 | 99.99 | **100.00** |
| Fresh Final Caption Ratio (%) | 99.96 | 99.96 | 99.98 | **99.96** |
| Final-caption completeness (%) | 100.00 | 100.00 | 100.00 | **100.00** |
| Normal Update Coverage (%) | 99.90 | 99.90 | 100.00 | **99.90** |
| Duplicate messages (count) | 0 | 0 | 0 | **0** |
| Stale messages (count) | 0 | 0 | 0 | **0** |
| Connection errors (count) | 0 | 0 | 0 | **0** |
| Normal-client P95 (ms) | 206.43 | 207.77 | 206.37 | **206.43** |
| Normal-client freshness (%) | 100.00 | 100.00 | 99.99 | **100.00** |
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
