# LiveRecall benchmark summary: t4

Independent runs: 3

| Metric | t4_run01.json | t4_run02.json | t4_run03.json | Median |
|---|---:|---:|---:|---:|
| Clients observed (count) | 100 | 100 | 100 | **100** |
| P50 caption age (ms) | 38.16 | 38.44 | 38.91 | **38.44** |
| P95 caption age (ms) | 60.32 | 59.82 | 60.72 | **60.32** |
| P99 caption age (ms) | 75.20 | 72.73 | 75.08 | **75.08** |
| Fresh Caption Ratio (%) | 100.00 | 100.00 | 100.00 | **100.00** |
| Fresh Final Caption Ratio (%) | 98.42 | 98.42 | 98.42 | **98.42** |
| Final-caption completeness (%) | 100.00 | 100.00 | 100.00 | **100.00** |
| Normal Update Coverage (%) | 98.25 | 98.25 | 98.26 | **98.25** |
| Duplicate messages (count) | 0 | 0 | 0 | **0** |
| Stale messages (count) | 0 | 0 | 0 | **0** |
| Connection errors (count) | 0 | 0 | 0 | **0** |
| Normal-client P95 (ms) | 60.32 | 59.82 | 60.72 | **60.32** |
| Normal-client freshness (%) | 100.00 | 100.00 | 100.00 | **100.00** |
| Slow-client P95 (ms) | — | — | — | **—** |
| Slow-client freshness (%) | — | — | — | **—** |
| Recovery P50 (ms) | 53.05 | 97.28 | 60.54 | **60.54** |
| Recovery P95 (ms) | 76.41 | 122.45 | 62.11 | **76.41** |

## Quick checks

- Median final completeness: 100.00%
- Median duplicates: 0
- Median stale messages: 0
- Median connection errors: 0

A dash indicates that the metric does not apply to this workload or was not reported.
