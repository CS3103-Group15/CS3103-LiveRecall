# Final Ubuntu test results

Start here. `medians.csv` contains the headline metrics; `summary.json` includes per-run completeness and isolation/recovery results. Full measurements and logs are in `raw_results.zip`.

| Test | Final completeness, each run | Median completeness | Fresh finals | Revision coverage |
|---|---|---:|---:|---:|
| T1 | 100.00%, 100.00%, 100.00% | 100.00% | 100.00% | 100.00% |
| T2 | 100.00%, 100.00%, 100.00% | 100.00% | 100.00% | 100.00% |
| T3 | 100.00%, 100.00%, 100.00% | 100.00% | 94.47% | 94.34% |
| T4 | 100.00%, 100.00%, 100.00% | 100.00% | 98.42% | 98.33% |
| T5 | 100.00%, 100.00%, 99.90% | 100.00% | 85.80% | 62.30% |
| BANDWIDTH | 99.59%, 100.00%, 100.00% | 100.00% | 27.00% | 74.97% |

T1-T5 use the school public workloads without measurement changes. BANDWIDTH is an additional 512 kbit/s experiment, not a sixth required public test.

Revision suppression under overload and finals recovered after an offline period explain why coverage/freshness need not be 100%. Check normal T1/T2 coverage separately. Public results do not guarantee hidden-test marks.

The before/after comparison uses the earlier sender and the updated sender on the same VM and persistent filesystem with the same T5 settings. See `comparison.csv`.

The archive includes exact commands, hashes, all raw CSV/JSON, network-profile verification, resource samples and check logs. Review `metadata.json` for check return codes. A file-presence check does not establish that team declarations or video/viva work are complete.
