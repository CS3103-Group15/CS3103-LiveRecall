# LiveRecall benchmark summary: delay_loss

Independent runs: 3

| Metric | delay_loss_run01.json | delay_loss_run02.json | delay_loss_run03.json | Median |
|---|---:|---:|---:|---:|
| Clients observed (count) | 100 | 100 | 100 | **100** |
| P50 caption age (ms) | 254.96 | 266.71 | 257.74 | **257.74** |
| P95 caption age (ms) | 695.50 | 796.30 | 752.06 | **752.06** |
| P99 caption age (ms) | 964.07 | 1097.42 | 1122.64 | **1097.42** |
| Fresh Caption Ratio (%) | 86.36 | 84.77 | 88.24 | **86.36** |
| Fresh Final Caption Ratio (%) | 85.88 | 80.18 | 85.29 | **85.29** |
| Final-caption completeness (%) | 100.00 | 100.00 | 100.00 | **100.00** |
| Normal Update Coverage (%) | 99.85 | 99.97 | 100.00 | **99.97** |
| Duplicate messages (count) | 0 | 0 | 0 | **0** |
| Stale messages (count) | 0 | 0 | 0 | **0** |
| Connection errors (count) | 0 | 0 | 0 | **0** |
| Normal-client P95 (ms) | 695.50 | 796.30 | 752.06 | **752.06** |
| Normal-client freshness (%) | 86.36 | 84.77 | 88.24 | **86.36** |
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
