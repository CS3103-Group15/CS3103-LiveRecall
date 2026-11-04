# LiveRecall benchmark summary: delay_loss

Independent runs: 3

| Metric | delay_loss_run01.json | delay_loss_run02.json | delay_loss_run03.json | Median |
|---|---:|---:|---:|---:|
| Clients observed (count) | 100 | 100 | 100 | **100** |
| P50 caption age (ms) | 294.23 | 294.72 | 288.45 | **294.23** |
| P95 caption age (ms) | 884.95 | 1022.61 | 961.98 | **961.98** |
| P99 caption age (ms) | 1236.57 | 1377.09 | 1249.81 | **1249.81** |
| Fresh Caption Ratio (%) | 81.71 | 79.34 | 82.24 | **81.71** |
| Fresh Final Caption Ratio (%) | 82.67 | 78.67 | 81.76 | **81.76** |
| Final-caption completeness (%) | 100.00 | 100.00 | 100.00 | **100.00** |
| Normal Update Coverage (%) | 59.66 | 58.01 | 58.12 | **58.12** |
| Duplicate messages (count) | 0 | 0 | 0 | **0** |
| Stale messages (count) | 0 | 0 | 0 | **0** |
| Connection errors (count) | 0 | 0 | 0 | **0** |
| Normal-client P95 (ms) | 884.95 | 1022.61 | 961.98 | **961.98** |
| Normal-client freshness (%) | 81.71 | 79.34 | 82.24 | **81.71** |
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
