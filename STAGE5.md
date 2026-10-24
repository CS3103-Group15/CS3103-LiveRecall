# Stage 5 client delivery

Each connection owns a ClientDelivery sender task. The source validates updates,
stores finals and offers work without awaiting client sends. The source yields
between updates so sender tasks can run even during a buffered source burst.

## Ordering and shared history

FinalHistory stores each final once, with a monotonically increasing internal
sequence number. Each sender tracks its next final sequence. These sequences are
internal bookmarks, not protocol segment IDs or acknowledgements of browser
processing. A bounded deque holds provisional updates. The sender compares segment
IDs to deliver same-segment provisionals before their final and finals before the
next segment. This relies on the assignment's sequential source.

On connection, history selection, bookmark capture and registration happen without
an await. The new sender sends HISTORY before live updates. No network send holds a
shared lock. A HISTORY snapshot is bounded by the shared history limits and released
after its send finishes.

## Limits and failure policy

- Pending provisionals: at most 256 queued messages and 1 MiB of serialized data per
  client, plus at most one message currently being sent.
- Finals: shared 70-second history, at most 20,000 entries and 32 MiB of serialized
  caption data. Python objects and transport buffers add overhead beyond these
  payload byte limits.
- Each send has a 10-second timeout. Server close timeout is 2 seconds.
- Queue overflow, a send failure/timeout or an expired final bookmark closes only
  that client (1013). The existing browser can reconnect using its actual final
  checkpoint. No queued final is silently skipped.
- If shared history cannot accept a final, final state isn't committed and the
  source connection closes explicitly. The source would need to retry after
  capacity is available; automatic source retry is not implemented.

This is a stage 5 infrastructure policy, not the finished semantic overload design.
An indefinitely slow client cannot be guaranteed every final beyond retained history.
Stage 6 should coalesce obsolete provisionals, prioritize useful state and tune
congestion/recovery behaviour to reduce disconnects while preserving final order.
Normal mode currently preserves every accepted revision.

## Verification

Run from the repository root with the virtual environment activated:

```bash
python -m unittest discover -s tests -v
python submission_check.py
```

The focused tests exercise blocked-client isolation, shared final bookmarks, full
revision ordering, HISTORY-before-live ordering, message/byte limits, send timeout,
expired history, sender cleanup and failure-safe final storage. Test harness files
are unchanged.

Short local normal, recovery/late-join and 100-client slow-reader results are saved
under results/stage5/implemented_*. These are development checks, not the required
three-run Ubuntu experiments or proof of sustained memory usage under stress.

Record this AI-assisted implementation and the reviewed overload limitations in the
final AI_USAGE.md and contribution statement. Existing team declarations have not
been replaced.
