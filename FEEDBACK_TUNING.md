# Slow-reader delivery tuning

## What changed

`server/client_session.py` now uses a WebSocket ping/pong checkpoint after each
outgoing caption/history message. A successful `send()` can mean only that bytes
entered a network buffer. Waiting for a pong limits how far each independent
sender gets ahead of transport progress. The caption protocol and school clients
are unchanged. Other clients and the source never wait for this checkpoint.

Each connection remembers its best round-trip time. A pending or completed probe
that exceeds both 100 ms and four times that baseline activates the existing
congestion policy. Delayed probes keep that mode active for 16 times the measured
round-trip time, capped at 60 seconds, so one fast pong does not immediately
restart full revision traffic. This deliberately conservative cooldown may
keep an affected connection in coalescing mode for up to 60 seconds after a
large delay; latest state/finals continue, but full revision coverage can resume
late after a temporary bottleneck. This is a trade-off to measure in further
Ubuntu catch-up experiments, not a claim that all hidden scenarios are solved.

While congested, the latest provisional also gets a 250 ms replacement window.
A newer provisional restarts that window. An arriving final removes its queued
provisionals and wakes the sender immediately. If no newer update arrives, the
latest provisional is sent when the window expires. Normal clients have no such
wait and retain every revision. Finals still come from the bounded shared
history through the existing per-client bookmark; compaction never skips them.

Disabling semantic backpressure also disables the extra feedback checkpoints.
Disconnect logs include `feedback_checks` and `feedback_delays` for diagnosis.

## Tests and limitations

`tests/test_feedback.py` covers normal full revision delivery, steady transport
delay, delayed feedback, mode recovery, ordered final delivery, provisional
replacement waits, no-final delivery, cancellation and timeout cleanup.

A pong acknowledges WebSocket transport processing, not application consumption
or browser rendering. Python clients pause socket reads when their frame queue
fills, making delayed feedback useful in the public slow-reader workload. A
browser may answer pings while its UI is busy; the same detection is not
promised for UI-only stalls. Already transmitted obsolete captions cannot be
retracted. The extra control frames and round-trip waits cost bandwidth and can
reduce throughput on high-latency connections. Ubuntu impairment/hidden tests
still need separate validation; a local completeness result is not a guarantee
of a grade or of 99% under every workload.

No changes were made to `run_demo.py`, `load_clients.py`, `caption_source.py`,
`analyse_results.py`, test durations, expected counts or the caption protocol.

The tuning experiments use the existing project virtual environment on macOS.
The report alongside the final result files records the measured results.

## Measured slow-reader result

Same public T3 workload: 100 clients, 60 seconds, three independent runs,
10% slow readers, 500 ms read delay, 76 source segments. Port 19877 avoided an
existing service on 8765; it does not change the workload.

| Metric (median) | Before | Tuned |
| --- | ---: | ---: |
| Final completeness | 95.13% | 100.00% |
| Normal-client P95 age | 9.80 ms | 6.90 ms |
| Slow-client P95 age | 28064.54 ms | 7506.71 ms |
| Fresh final ratio | 90.00% | 94.74% |

All three tuned runs delivered 7600/7600 finals. No duplicate/stale messages,
connection errors or reconnect-based recovery were observed in these T3 runs.
Healthy clients received all 20520 expected revisions in each run. The overall
revision-coverage field decreased from 95.18% to 94.30% because more obsolete
slow-client provisional revisions were coalesced. That is the intended overload
trade-off, not loss of normal-client coverage.

`results/feedback_tuning/comparison.json` records the exact command, school-file
hashes, environment, baseline paths and final validated result paths. Only files
named `validated_*` belong to the final validation. Other candidate files are
exploratory and must not be combined into a reported median; the early
`final_t3_*` files include a policy iteration during the experiment.

The normal 100-client, 40-second regression run (one run, not the required
three-run report) achieved 100% final completeness, 100% revision coverage,
100% fresh captions and no duplicate/stale messages.

Reproduce the main measurement from the project directory with the virtual
environment activated:

```bash
python run_demo.py --clients 100 --duration 60 --runs 3 --port 19877 --slow-percent 10 --slow-ms 500 --output-stem results/feedback_tuning/recheck
```

The reconnect regression (one run, 100 clients, 20% disconnected for five
seconds) delivered 7600/7600 finals, recovered 120 history items across 20
reconnects, with no duplicate/stale messages. Recovery P95 was 6.23 ms.
All 34 unit tests passed on the final code.
