# Required deterministic demo and viva checklist

Use the same submitted server/browser and the supplied `caption_source.py`. The mandatory video is 5–7 minutes; optional ASR does not replace it.

1. Start the server and HTTP client server with the README commands. Open two browser clients, then start a 100-segment source.
2. Show gray provisional text changing in place into green final text. A revision must not append duplicate lines.
3. Click “What did I miss?” (default 30 s), then 15 s and 60 s. Recall uses the browser's local finalized history. Give the source enough time to build history.
4. Demonstrate a temporary disconnect and automatic reconnect. With the browser on the Mac, a short VM network disconnect can be used and restored; avoid restarting the caption server because that would erase the history being demonstrated. For a controlled development demonstration, closing only one browser WebSocket and allowing its automatic reconnect is also possible through browser developer tools.
5. Show ordered missed finals merging without duplicate lines, while the other browser continues live.
6. Open a late third browser client and show recent history plus continuing live updates.
7. Briefly show `results/final/SUMMARY.md` and the before/after comparison. Explain completeness vs freshness and why TCP loss increases tails.

Before submission, record the actual video, review the 4–5 page report, complete the agreed team contributions, and check the team's viva booking/attendance. These human deliverables are not completed by automated tests.

Be ready to explain `state.accept_update`, `application.attach_client`, `delivery_hub.publish`, `ClientSession.enqueue`, `sender_loop`, `compact`, the delivery bookmark vs browser checkpoint, all queue/history bounds, pong limitations and the high-RTT batching trade-off. Know what happens after an outage longer than retained history and why public success does not guarantee hidden marks.
