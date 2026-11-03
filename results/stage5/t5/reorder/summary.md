# LiveRecall benchmark summary: reorder

Independent runs: 3

| Metric | reorder_run01.json | reorder_run02.json | reorder_run03.json | Median |
|---|---:|---:|---:|---:|
| Clients observed (count) | 100 | 100 | 100 | **100** |
| P50 caption age (ms) | 45.59 | 45.76 | 45.57 | **45.59** |
| P95 caption age (ms) | 47.48 | 47.07 | 46.95 | **47.07** |
| P99 caption age (ms) | 49.38 | 48.67 | 48.18 | **48.67** |
| Fresh Caption Ratio (%) | 100.00 | 100.00 | 100.00 | **100.00** |
| Fresh Final Caption Ratio (%) | 100.00 | 100.00 | 100.00 | **100.00** |
| Final-caption completeness (%) | 100.00 | 100.00 | 100.00 | **100.00** |
| Normal Update Coverage (%) | 100.00 | 100.00 | 100.00 | **100.00** |
| Duplicate messages (count) | 0 | 0 | 0 | **0** |
| Stale messages (count) | 0 | 0 | 0 | **0** |
| Connection errors (count) | 0 | 0 | 0 | **0** |
| Normal-client P95 (ms) | 47.48 | 47.07 | 46.95 | **47.07** |
| Normal-client freshness (%) | 100.00 | 100.00 | 100.00 | **100.00** |
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
