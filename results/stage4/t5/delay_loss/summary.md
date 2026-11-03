# LiveRecall benchmark summary: delay_loss

Independent runs: 3

| Metric | delay_loss_run01.json | delay_loss_run02.json | delay_loss_run03.json | Median |
|---|---:|---:|---:|---:|
| Clients observed (count) | 100 | 100 | 100 | **100** |
| P50 caption age (ms) | 255.37 | 258.56 | 249.19 | **255.37** |
| P95 caption age (ms) | 671.22 | 678.33 | 557.26 | **671.22** |
| P99 caption age (ms) | 953.45 | 891.35 | 937.76 | **937.76** |
| Fresh Caption Ratio (%) | 90.87 | 88.49 | 93.74 | **90.87** |
| Fresh Final Caption Ratio (%) | 88.22 | 88.78 | 92.80 | **88.78** |
| Final-caption completeness (%) | 100.00 | 100.00 | 100.00 | **100.00** |
| Normal Update Coverage (%) | 99.90 | 99.93 | 99.90 | **99.90** |
| Duplicate messages (count) | 0 | 0 | 0 | **0** |
| Stale messages (count) | 0 | 0 | 0 | **0** |
| Connection errors (count) | 0 | 0 | 0 | **0** |
| Normal-client P95 (ms) | 671.22 | 678.33 | 557.26 | **671.22** |
| Normal-client freshness (%) | 90.87 | 88.49 | 93.74 | **90.87** |
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
