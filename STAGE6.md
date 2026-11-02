# Stage 6 semantic backpressure

Stage 6 builds on stage 5's independent client senders. A healthy client receives
all accepted revisions. A congested client skips obsolete unsent provisionals,
receives every retained final in order, and retains the newest provisional for an
unfinished segment. Each client chooses its own mode.

## Congestion signals

Default entry signals are any of:

- 32 pending provisionals, including a new offered message;
- 128 KiB of pending provisional payload, including a new message;
- oldest queued provisional age of 250 ms;
- current or completed send taking at least 100 ms;
- WebSocket transport write buffer reaching 32 KiB;
- four outstanding final entries behind the shared-history head.

Queue thresholds are clamped to configured hard limits. These are initial tuning
values, not claims of optimal hidden-test performance. Time measurements use the
server's monotonic clock, independently of source timestamps.

## What changes during congestion

The sender removes pending provisionals for finalized segments, and collapses the
remaining revisions of each unfinished segment to its latest accepted revision.
When a final arrives, its unsent provisionals are removed. Final delivery still
uses the shared-history cursor, which is advanced only after sending that final.
The sender delivers older finals before a later active segment. No final is
removed by coalescing, and HISTORY still precedes live delivery.

Coalescing happens before capacity failure. A single newest provisional that exceeds
the hard byte limit still fails explicitly instead of using unbounded memory.
The assignment source completes one segment before starting the next; the policy
and the existing finalized-segment high-water mark rely on that assumption.

An in-progress send cannot be retracted. Neither can data already accepted by
WebSocket/TCP/network buffers. Thus a slow application reader can accumulate delay
before the server sees pressure. This implementation does not infer browser
processing from successful sends and does not add a client acknowledgement protocol.

## Returning to normal

After at least 500 ms without pressure, full revision delivery resumes when no final
backlog remains, pending work is at most four messages and 32 KiB, the transport
buffer is at most 8 KiB, and no send is active. Checks happen on new offers and
sender-loop progress; an idle connection needs no periodic polling. Distinct high
and low thresholds plus a quiet interval prevent rapid mode switching.

## Limits and diagnostics

Stage 5's queue/history caps, send timeout, expired-history detection and cleanup
remain in place. A client unable to receive even the final stream can still time out
or fall outside retained history; unlimited final delivery is not promised.
Disconnect logs include congestion entries, recoveries, coalesced provisional count
and failure reason. Queued payload counts exclude one in-flight message; history
byte limits count serialized payload rather than all Python/transport overhead.

## Verification and comparison

```bash
python -m unittest discover -s tests -v
python submission_check.py
python benchmarks/semantic_backpressure.py --output results/stage6/controlled_comparison.json
```

The controlled benchmark holds a client through 40 segments, then releases a
byte-paced fake socket. It compares the stage 5 policy with stage 6 using the same
workload and asserts all 40 finals are delivered in order. It is not a TCP/netem
experiment or a substitute for the required three-run Ubuntu measurements.

For a manually orchestrated real-network before/after experiment, start the same
server with either:

```bash
python solution_server.py --port 8765 --disable-backpressure
python solution_server.py --port 8765
```

Run one at a time with identical source/client/network settings. The disable flag
keeps independent senders but turns off semantic congestion handling; it is useful
for isolating the policy's effect. The supplied run_demo.py starts its own server
and does not pass this flag. Instructor test programs are unchanged.

Local normal, reconnect/late-join and slow-reader checks are saved in
results/stage6/. Normal update coverage should be checked on the normal workload;
offline/late clients necessarily miss live provisional updates. Required Ubuntu
bandwidth/delay/loss experiments and threshold tuning remain stage 7 work.

This implementation was AI-assisted. Include the reviewed changes, tests and
limitations in the team's final AI_USAGE.md and contribution statement; existing
team declarations were not replaced. One rejected shortcut was always discarding
provisionals: it would break normal update coverage. Discarding only after a real
congestion signal preserves the normal revision stream.

## Team module naming

The sender and congestion policy now live in server/client_session.py as
ClientSession. Its outgoing_queue contains pending provisionals; completed captions
remain in shared FinalHistory. DeliveryHub publishes to sessions, and
LiveRecallApplication owns shared state and history/live registration transactions.
The CLI, wire protocol, limits and policy are unchanged by this reorganisation.
