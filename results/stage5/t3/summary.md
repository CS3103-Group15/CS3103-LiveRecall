# LiveRecall benchmark summary: t3

Independent runs: 3

| Metric | t3_run01.json | t3_run02.json | t3_run03.json | Median |
|---|---:|---:|---:|---:|
| Clients observed (count) | 100 | 100 | 100 | **100** |
| P50 caption age (ms) | 38.75 | 38.59 | 39.82 | **38.75** |
| P95 caption age (ms) | 2315.18 | 2315.49 | 2333.24 | **2315.49** |
| P99 caption age (ms) | 24208.54 | 24227.65 | 24200.52 | **24208.54** |
| Fresh Caption Ratio (%) | 94.65 | 94.65 | 94.65 | **94.65** |
| Fresh Final Caption Ratio (%) | 90.00 | 90.00 | 90.00 | **90.00** |
| Final-caption completeness (%) | 95.13 | 95.13 | 95.13 | **95.13** |
| Normal Update Coverage (%) | 95.18 | 95.18 | 95.18 | **95.18** |
| Duplicate messages (count) | 0 | 0 | 0 | **0** |
| Stale messages (count) | 0 | 0 | 0 | **0** |
| Connection errors (count) | 0 | 0 | 0 | **0** |
| Normal-client P95 (ms) | 51.72 | 52.26 | 55.75 | **52.26** |
| Normal-client freshness (%) | 100.00 | 100.00 | 100.00 | **100.00** |
| Slow-client P95 (ms) | 28217.70 | 28298.73 | 28232.66 | **28232.66** |
| Slow-client freshness (%) | 1.69 | 1.69 | 1.69 | **1.69** |
| Recovery P50 (ms) | — | — | — | **—** |
| Recovery P95 (ms) | — | — | — | **—** |

## Quick checks

- Median final completeness: 95.13%
- Median duplicates: 0
- Median stale messages: 0
- Median connection errors: 0

A dash indicates that the metric does not apply to this workload or was not reported.
