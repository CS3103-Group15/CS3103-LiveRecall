# AI / coding-assistant usage

## Tools and scope

OpenAI ChatGPT/Codex was used to explain the assignment and code, develop/refactor independent client delivery and semantic overload handling, investigate timing/performance, add regression tests, orchestrate the unchanged school workloads, organize result files and draft setup/report documentation. The assistant used local files, Python/Node test tools, SSH into the team's Ubuntu VM and browser automation for validation. The team must review these declarations before submission; other members should add any additional AI tools they used.

## Useful suggestion and verification

Independent client sender tasks prevent one blocked socket from holding up publication to healthy clients. Shared final history with a per-client bookmark avoids copying a final backlog into every provisional queue. Tests exercise ordering, history/live boundaries, bounded queues, final protection, cancellation and isolation. Ubuntu T1–T5 runs and memory observations provide measurement evidence; see `results/final/`.

## Generated suggestion/code that required modification

The initial feedback implementation effectively did this after every caption:

```python
await websocket.send(raw)
pong = await websocket.ping()
await pong
```

This detects transport stalls earlier than relying only on `send()`, but it creates stop-and-wait throughput on high-RTT links: even a healthy receiver can be limited to about one message per RTT. It also does not prove that the application consumed or displayed the caption. The corrected policy measures baseline RTT and accepted source cadence, allows a small bounded batch on longer-RTT links, and keeps byte/message limits and timeout cleanup. Fast links retain tight feedback. The before/after T5 experiment uses the same Ubuntu VM/filesystem and unchanged public workload. Unit tests cover full revision delivery, pipeline caps, byte limits, final ordering, delayed feedback and cancellation.

A separate investigation found missing tail finals caused by delayed timers in the earlier QEMU environment: increasing the test window was used only as a labelled diagnostic, never substituted for a standard public score. Final validation uses the existing VMware Ubuntu VM and the school's original timings/counts/analyser.

## Limitations and responsibility

Generated claims are not evidence on their own. Experimental results come from the saved raw files. Random packet loss and hidden workloads prevent a promise of a particular grade or universal 100% completeness. The conservative post-congestion cooldown remains a trade-off described in the report. Each team member must understand the code they claim, review the final declarations/results and be able to explain or modify the implementation during the viva.
