# Current cleanup code — Mininet Ubuntu rerun

T1–T4 each ran three times with the unchanged school harness. T5 was not rerun. Raw data, source hashes and commands are in the evidence archive.

| Test | Final completeness in each run | Median fresh finals | Median revision coverage |
|---|---|---:|---:|
| T1 | 100.00%, 100.00%, 100.00% | 100.00% | 100.00% |
| T2 | 100.00%, 100.00%, 100.00% | 100.00% | 100.00% |
| T3 | 100.00%, 100.00%, 100.00% | 94.34% | 94.34% |
| T4 | 100.00%, 100.00%, 100.00% | 98.68% | 98.33% |

Freshness and revision coverage need not be 100% for slow/offline populations. Normal-client results and errors are retained in summary.json. Public tests do not guarantee hidden-test results.

Verification: all 12 saved run summaries were recomputed exactly from their raw CSVs with the school analyser. All source hashes matched the Mac/VM snapshot. No duplicate captions, stale captions or connection errors were observed. T1/T2 had 100% freshness and revision coverage in every run; T3 healthy-client freshness was 100% in every run. The required server startup check passed.
