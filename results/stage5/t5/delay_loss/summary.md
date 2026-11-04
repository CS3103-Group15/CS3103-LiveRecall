# LiveRecall benchmark summary: delay_loss

Independent runs: 3

| Metric | delay_loss_run01.json | delay_loss_run02.json | delay_loss_run03.json | Median |
|---|---:|---:|---:|---:|
| Clients observed (count) | 100 | 100 | 100 | **100** |
| P50 caption age (ms) | 277.81 | 275.36 | 287.27 | **277.81** |
| P95 caption age (ms) | 799.48 | 726.81 | 957.48 | **799.48** |
| P99 caption age (ms) | 1168.05 | 1105.50 | 1291.79 | **1168.05** |
| Fresh Caption Ratio (%) | 88.47 | 89.68 | 80.07 | **88.47** |
| Fresh Final Caption Ratio (%) | 90.78 | 89.65 | 80.88 | **89.65** |
| Final-caption completeness (%) | 100.00 | 100.00 | 100.00 | **100.00** |
| Normal Update Coverage (%) | 100.00 | 99.91 | 99.99 | **99.99** |
| Duplicate messages (count) | 0 | 0 | 0 | **0** |
| Stale messages (count) | 0 | 0 | 0 | **0** |
| Connection errors (count) | 0 | 0 | 0 | **0** |
| Normal-client P95 (ms) | 799.48 | 726.81 | 957.48 | **799.48** |
| Normal-client freshness (%) | 88.47 | 89.68 | 80.07 | **88.47** |
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
