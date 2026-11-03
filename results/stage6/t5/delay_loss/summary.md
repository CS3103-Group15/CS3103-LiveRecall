# LiveRecall benchmark summary: delay_loss

Independent runs: 3

| Metric | delay_loss_run01.json | delay_loss_run02.json | delay_loss_run03.json | Median |
|---|---:|---:|---:|---:|
| Clients observed (count) | 100 | 100 | 100 | **100** |
| P50 caption age (ms) | 265.58 | 267.30 | 265.12 | **265.58** |
| P95 caption age (ms) | 781.80 | 655.03 | 686.42 | **686.42** |
| P99 caption age (ms) | 1084.45 | 889.61 | 962.60 | **962.60** |
| Fresh Caption Ratio (%) | 84.68 | 91.70 | 88.82 | **88.82** |
| Fresh Final Caption Ratio (%) | 84.39 | 89.78 | 88.20 | **88.20** |
| Final-caption completeness (%) | 100.00 | 100.00 | 100.00 | **100.00** |
| Normal Update Coverage (%) | 64.37 | 59.40 | 59.85 | **59.85** |
| Duplicate messages (count) | 0 | 0 | 0 | **0** |
| Stale messages (count) | 0 | 0 | 0 | **0** |
| Connection errors (count) | 0 | 0 | 0 | **0** |
| Normal-client P95 (ms) | 781.80 | 655.03 | 686.42 | **686.42** |
| Normal-client freshness (%) | 84.68 | 91.70 | 88.82 | **88.82** |
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
