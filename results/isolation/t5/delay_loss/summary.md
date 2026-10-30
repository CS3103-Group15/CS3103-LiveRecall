# LiveRecall benchmark summary: delay_loss

Independent runs: 3

| Metric | delay_loss_run01.json | delay_loss_run02.json | delay_loss_run03.json | Median |
|---|---:|---:|---:|---:|
| Clients observed (count) | 100 | 100 | 100 | **100** |
| P50 caption age (ms) | 253.10 | 253.86 | 258.07 | **253.86** |
| P95 caption age (ms) | 642.02 | 690.90 | 794.25 | **690.90** |
| P99 caption age (ms) | 893.27 | 1092.65 | 1142.05 | **1092.65** |
| Fresh Caption Ratio (%) | 92.07 | 89.81 | 87.36 | **89.81** |
| Fresh Final Caption Ratio (%) | 92.41 | 90.86 | 89.76 | **90.86** |
| Final-caption completeness (%) | 99.98 | 100.00 | 100.00 | **100.00** |
| Normal Update Coverage (%) | 99.99 | 99.97 | 99.95 | **99.97** |
| Duplicate messages (count) | 0 | 0 | 0 | **0** |
| Stale messages (count) | 0 | 0 | 0 | **0** |
| Connection errors (count) | 0 | 0 | 0 | **0** |
| Normal-client P95 (ms) | 642.02 | 690.90 | 794.25 | **690.90** |
| Normal-client freshness (%) | 92.07 | 89.81 | 87.36 | **89.81** |
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
