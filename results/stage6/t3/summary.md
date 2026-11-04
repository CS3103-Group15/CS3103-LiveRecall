# LiveRecall benchmark summary: t3

Independent runs: 3

| Metric | t3_run01.json | t3_run02.json | t3_run03.json | Median |
|---|---:|---:|---:|---:|
| Clients observed (count) | 100 | 100 | 100 | **100** |
| P50 caption age (ms) | 37.61 | 37.93 | 37.45 | **37.61** |
| P95 caption age (ms) | 70.62 | 72.32 | 74.01 | **72.32** |
| P99 caption age (ms) | 5489.59 | 5502.02 | 5491.34 | **5491.34** |
| Fresh Caption Ratio (%) | 97.16 | 97.16 | 97.16 | **97.16** |
| Fresh Final Caption Ratio (%) | 94.61 | 94.61 | 94.61 | **94.61** |
| Final-caption completeness (%) | 100.00 | 100.00 | 100.00 | **100.00** |
| Normal Update Coverage (%) | 94.30 | 94.30 | 94.30 | **94.30** |
| Duplicate messages (count) | 0 | 0 | 0 | **0** |
| Stale messages (count) | 0 | 0 | 0 | **0** |
| Connection errors (count) | 0 | 0 | 0 | **0** |
| Normal-client P95 (ms) | 57.70 | 60.26 | 59.94 | **59.94** |
| Normal-client freshness (%) | 100.00 | 100.00 | 100.00 | **100.00** |
| Slow-client P95 (ms) | 7615.48 | 7635.94 | 7628.79 | **7628.79** |
| Slow-client freshness (%) | 37.76 | 37.76 | 37.76 | **37.76** |
| Recovery P50 (ms) | — | — | — | **—** |
| Recovery P95 (ms) | — | — | — | **—** |

## Quick checks

- Median final completeness: 100.00%
- Median duplicates: 0
- Median stale messages: 0
- Median connection errors: 0

A dash indicates that the metric does not apply to this workload or was not reported.
