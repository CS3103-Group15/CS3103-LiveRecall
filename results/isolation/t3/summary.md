# LiveRecall benchmark summary: t3

Independent runs: 3

| Metric | t3_run01.json | t3_run02.json | t3_run03.json | Median |
|---|---:|---:|---:|---:|
| Clients observed (count) | 100 | 100 | 100 | **100** |
| P50 caption age (ms) | 4.55 | 4.66 | 4.58 | **4.58** |
| P95 caption age (ms) | 2257.80 | 2266.34 | 2259.91 | **2259.91** |
| P99 caption age (ms) | 24021.46 | 24033.04 | 24027.21 | **24027.21** |
| Fresh Caption Ratio (%) | 94.65 | 94.65 | 94.65 | **94.65** |
| Fresh Final Caption Ratio (%) | 90.00 | 90.00 | 90.00 | **90.00** |
| Final-caption completeness (%) | 95.13 | 95.13 | 95.13 | **95.13** |
| Normal Update Coverage (%) | 95.18 | 95.18 | 95.18 | **95.18** |
| Duplicate messages (count) | 0 | 0 | 0 | **0** |
| Stale messages (count) | 0 | 0 | 0 | **0** |
| Connection errors (count) | 0 | 0 | 0 | **0** |
| Normal-client P95 (ms) | 5.47 | 5.69 | 5.60 | **5.60** |
| Normal-client freshness (%) | 100.00 | 100.00 | 100.00 | **100.00** |
| Slow-client P95 (ms) | 28082.29 | 28075.86 | 28085.35 | **28082.29** |
| Slow-client freshness (%) | 1.69 | 1.69 | 1.69 | **1.69** |
| Recovery P50 (ms) | — | — | — | **—** |
| Recovery P95 (ms) | — | — | — | **—** |

## Quick checks

- Median final completeness: 95.13%
- Median duplicates: 0
- Median stale messages: 0
- Median connection errors: 0

A dash indicates that the metric does not apply to this workload or was not reported.
