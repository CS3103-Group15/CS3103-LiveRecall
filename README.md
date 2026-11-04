# LiveRecall — CS3103 Assignment 4, Group 15

LiveRecall displays live lecture captions and lets students review recent completed sentences. The deterministic caption source sends revisions to a WebSocket server, which delivers them to browser clients. Each browser replaces older revisions, stores recent finals locally and recovers missing recent finals after reconnecting.

## 1. Environment and dependencies

Use Ubuntu for networking/performance experiments. A full Ubuntu VM, including the Mininet lab VM, is suitable; Mininet itself does not need to run. Run the server, caption source and simulated clients inside the same Ubuntu environment. Network impairment is applied to its loopback interface (`lo`).

Tested environment: Ubuntu 24.04, Python 3.12, ARM64 VMware VM with 4 vCPUs and 4 GiB RAM. Python's `venv` and `iproute2` are needed. The only mandatory third-party Python dependency is `websockets`, as declared in `requirements.txt`. Server startup needs no cloud services, database, credentials, model downloads or interactive input.

From the submitted project's root directory:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip iproute2
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

For the team's existing Mininet VM, the project is at `/home/mininet/CS3103-LiveRecall`. After logging in, use:

```bash
cd ~/CS3103-LiveRecall
source .venv/bin/activate
```

Activate `.venv` in every terminal used below.

## 2. Run the application

### Terminal 1: caption server

```bash
source .venv/bin/activate
python solution_server.py --port 8765
```

The required evaluation entry point is `python solution_server.py --port <port>`. The server listens on the specified port and binds to `0.0.0.0` so browsers on the host computer can reach a VM.

### Terminal 2: website server

```bash
source .venv/bin/activate
python -m http.server 8000 --bind 0.0.0.0 --directory client
```

Open `http://127.0.0.1:8000` in a browser on the same machine. If the servers run inside Ubuntu and the browser runs on your Mac/Windows host, find the VM's IP using `hostname -I`, then open `http://<VM-IP>:8000` instead.

Port 8000 serves the website; port 8765 carries caption WebSocket connections. Do not open port 8765 as a normal webpage. Each browser tab is an independent client. The browser connects to the hostname serving its page on port 8765; if changing the caption server's port for an interactive demo, also change `WS_URL` in `client/app.js`. Automated clients use the port passed to the test runner.

### Terminal 3: deterministic caption source

Open the browser tabs first, then run:

```bash
source .venv/bin/activate
python caption_source.py --uri ws://127.0.0.1:8765 --segments 100
```

For a slower, easier-to-follow visual demonstration:

```bash
python caption_source.py --uri ws://127.0.0.1:8765 --segments 40 --revision-delay 1 --segment-gap 1
```

These are interactive demo settings only; use the unchanged public workloads below for reported performance results.

### Browser behavior and demo checks

- Provisional captions are gray/italic; finals are green. New revisions update the same segment's row.
- “What did I miss?” displays the previous 30 seconds of finalized captions. The 15- and 60-second buttons select those windows. Normal recall reads browser-local history without a server request.
- Each tab keeps 70 seconds of local finals, while the live area displays a 15-second window.
- To demonstrate recovery, temporarily disconnect one tab using the browser developer tools' Network “Offline” setting, wait a few seconds while another tab continues receiving captions, then return it to “Online”. Keep the page open. Its status changes and it reconnects automatically, reporting its last accepted final checkpoint.
- Open another tab after the source has been running to demonstrate late joining. Recent recovered finals can appear in live display if sufficiently recent, and in recall if inside its selected window.
- Refreshing or closing a tab clears its in-memory caption history/checkpoint. A fresh tab requests recent context from the server.

Stop terminal processes with Ctrl+C. Before repeating a lecture whose segment numbers restart at 1, restart the caption server and reload browser tabs. The mandatory path supports one active source and session `L1`.

If a browser shows an older version of the page after switching project copies, use a hard refresh. Browser caches are shared by pages using the same host and port.

## 3. Reproduce the public experiments

Do not launch a separate caption server or source for these commands: `run_demo.py` manages both and the simulated clients. Run one workload at a time inside Ubuntu, using an unused port. Each command performs three independent runs and prints medians. The supplied source, load clients, runner and analyser are unchanged.

```bash
source .venv/bin/activate
mkdir -p results/manual
```

### T1: basic correctness, 20 clients

```bash
python run_demo.py --clients 20 --duration 20 --runs 3 --port 19877 --output-stem results/manual/t1
```

### T2: normal operation, 100 clients

```bash
python run_demo.py --clients 100 --duration 40 --runs 3 --port 19877 --output-stem results/manual/t2
```

### T3: slow-reader isolation

```bash
python run_demo.py --clients 100 --duration 60 --runs 3 --port 19877 --slow-percent 10 --slow-ms 500 --output-stem results/manual/t3
```

### T4: disconnect/reconnect recovery

```bash
python run_demo.py --clients 100 --duration 60 --runs 3 --port 19877 --disconnect-percent 20 --disconnect-at 15 --disconnect-seconds 5 --output-stem results/manual/t4
```

### T5: Ubuntu delay, jitter and packet loss

The supplied profile applies 120 ms delay, 30 ms jitter and 3% packet loss. The following subshell resets the profile on exit, including after a test failure:

```bash
sudo -v
(
    set -e
    trap 'sudo bash network_profiles/reset.sh lo' EXIT
    sudo bash network_profiles/delay_loss.sh lo
    python run_demo.py --clients 100 --duration 40 --runs 3 --port 19877 --output-stem results/manual/t5
)
```

If a terminal is forcibly closed during impairment testing, explicitly reset the interface before other tests:

```bash
sudo bash network_profiles/reset.sh lo
```

For each workload, files such as `t1_run01.csv` and `t1_run01.json` are written under the chosen output directory. Use a separate output stem/directory for subsequent experiments so saved evidence is not overwritten. The runner prints the per-run results and median summary.

### Understanding the results

| Metric | Meaning |
|---|---|
| Caption Age | Client receive time minus the caption's source timestamp. |
| P50 / P95 / P99 age | Median, tail and extreme-tail delivery latency. |
| Final completeness | Unique required finals received divided by finals expected across clients. |
| Fresh Caption Ratio | Fraction of received updates arriving within 500 ms by default. |
| Fresh Final Caption Ratio | Fraction of generated required finals received within that threshold. |
| Normal Update Coverage | Fraction of generated live revisions received; unconstrained clients should receive all revisions. |
| Recovery time | Reconnect-to-HISTORY response timing; check completeness too, because an empty response can be fast. |
| Slow-reader isolation | Healthy-client latency/freshness while another population reads slowly. |

A delivered final can be complete but late. Slow/offline populations can lower freshness; suppression of obsolete provisionals can lower overall revision coverage. Inspect healthy clients separately in T3. WebSocket uses TCP, so packet loss usually adds retransmission/head-of-line delay rather than exposing unordered or missing TCP bytes to the application. Report medians across independent runs, and retain individual runs so a median does not hide misses.

The group also provides optional benchmark wrappers and result consolidation under [benchmarks/README.md](benchmarks/README.md). These invoke the same school runner; the direct commands above remain available.

## 4. Saved evidence and before/after comparison

- [Latest cleanup-code Ubuntu rerun: T1–T4](results/cleanup_recheck_20261103/SUMMARY.md): three runs each, all with 100% final completeness. T1/T2 also achieved 100% freshness and revision coverage; healthy-client freshness in T3 was 100%.
- [Earlier full Ubuntu experiment snapshot](results/final/SUMMARY.md): T1–T5, an additional bandwidth stress experiment, and the controlled T5 optimization comparison. T5 was not rerun during the latest four-test check.
- Each snapshot has `summary.json`, `metadata.json` and `raw_results.zip`. The archives preserve per-run CSV/JSON, commands and logs; metadata identifies the measured source by hash. Later comment-only edits do not represent new performance measurements.
- [Earlier T5 comparison](results/final/comparison.csv): the same VM and workload were used for three runs of each sender version. Median fresh-final ratio improved from 76.00% to 85.80%, coverage from 50.44% to 62.30%, and P95 age from 941.41 ms to 763.92 ms. Median completeness was 100% for both versions. These are historical measured results, not a claim that every metric is always 100%.

### Reproduce the earlier configuration

Use the complete historical server snapshot at commit `fb3e54b`. Do not swap only its `client_session.py` into the current server: helper interfaces changed during cleanup.

For a Git checkout with that commit available, install Git if needed (`sudo apt install -y git`), then run from the project root:

```bash
PROJECT_ROOT="$PWD"
PROJECT_PYTHON="$PWD/.venv/bin/python"
BEFORE_DIR=$(mktemp -d /tmp/liverecall-before-XXXXXX)
git archive fb3e54b solution_server.py requirements.txt server caption_source.py sample_transcript.txt run_demo.py load_clients.py analyse_results.py network_profiles | tar -x -C "$BEFORE_DIR"
mkdir -p results/manual
sudo -v
(
    set -e
    trap 'sudo bash "$PROJECT_ROOT/network_profiles/reset.sh" lo' EXIT
    sudo bash network_profiles/delay_loss.sh lo
    "$PROJECT_PYTHON" "$BEFORE_DIR/run_demo.py" --clients 100 --duration 40 --runs 3 --port 19877 --output-stem "$PROJECT_ROOT/results/manual/before_t5"
    python run_demo.py --clients 100 --duration 40 --runs 3 --port 19877 --output-stem results/manual/after_t5
)
```

For a ZIP without Git history, obtain the earlier snapshot from the [group repository](https://github.com/CS3103-Group15/CS3103-LiveRecall) at that commit first. Keep dependencies, machine and workload settings identical for both configurations. New results may differ from historical results because scheduling and loss are variable; preserve the new raw measurements rather than substituting old numbers.

## 5. Implementation and limits

| File | Responsibility |
|---|---|
| `solution_server.py` | Required CLI; starts the application on the selected port. |
| `server/application.py` | Shared application state, connection routing, caption processing and atomic client attachment. |
| `server/source_session.py` | Reads source messages and delegates accepted-update processing. |
| `server/state.py` | Validates fields/session, rejects stale/duplicate updates and protects finalized segments. |
| `server/history.py` | Shared bounded final history, recovery selection and sequence-based bookmark lookup. |
| `server/delivery_hub.py` | Registers sessions and publishes work without awaiting client sockets. |
| `server/client_session.py` | Independent sender, provisional queue, ordered finals, compaction, feedback and cleanup. |
| `server/delivery_policy.py` | Fixed delivery settings and per-client mutable ping/pong progress. |
| `server/protocol.py` | Required message type definitions. |
| `client/index.html`, `client/app.js` | Caption display, local recall, checkpoint reporting and automatic reconnect. |

The initial `SOURCE_HELLO`/`CLIENT_HELLO` identifies the connection. Accepted source updates are published only after state/history processing. Extra source fields are ignored; no fixed revision count is assumed. Initial `HISTORY`, bookmark capture and registration are prepared together, and the sender sends history before live updates.

Each client queues only provisionals. Finals remain once in shared history and are read through that client's `next_final` bookmark. It advances after successful sending; it is separate from the browser checkpoint, which records the last final actually accepted by the browser.

| Resource / behavior | Default limit or policy |
|---|---|
| Server final history | 70 seconds after storage; at most 20,000 finals / 32 MiB of serialized payload. |
| Per-client provisional queue | At most 256 entries / 1 MiB of queued payload. |
| Congestion handling | Compact superseded provisionals; retain the latest queued unfinished revision. Finals are not discarded to make room for provisionals. |
| Provisional deferral during congestion | Cadence-based quiet window, normally 250 ms–1 s; voluntary deferral capped at 2 s. Network stalls can add delay. |
| Feedback pipeline | Adaptive batch of 1–8 messages, with a 64 KiB byte threshold checked after each message. |
| Caption send / ping write / pong wait | 10-second timeout per awaited operation. |
| Congestion recovery | Requires drained work, low buffer pressure and a quiet period; confirmed slow feedback can hold coalescing for up to 60 s. |

Pressure checks consider queue entries/bytes/age, send duration, transport buffers, final lag and feedback RTT relative to the connection's baseline. Ping/pong confirms transport progress, not browser rendering or application acceptance. Already transmitted messages cannot be removed by queue compaction. Conservative recovery can delay restoration of full provisional coverage after a temporary bottleneck.

Expired history is not an unlimited recovery guarantee. If a connected sender falls behind retained finals, the connection closes rather than silently skipping them; a reconnect can request remaining recent context. If history hits its item/byte cap before entries can expire, the source connection is closed explicitly rather than silently discarding finals inside the retention window. Capacity must be sufficient for the intended 60-second workload.

Optional ASR, multiple concurrent sessions, authentication and production TLS termination are outside this implementation. Public-test results do not guarantee hidden-test marks.

## 6. Submission checks and deliverables

Check the mandatory entry point:

```bash
python submission_check.py --port 19878
```

When all required documents are present:

```bash
python submission_check.py --final --port 19878
```

The checker validates required filenames and startup, not full protocol/performance correctness or the content of declarations.

Required submission contents are the application source (`solution_server.py`, `server/`, `client/`), `requirements.txt`, this README, [AI_USAGE.md](AI_USAGE.md), [CONTRIBUTIONS.md](CONTRIBUTIONS.md), and `report.pdf` (4–5 pages excluding references/appendices). Keep the supplied deterministic source, transcript, unchanged test programs and network profiles for reproduction. Retain the group Git history and experiment evidence for the report/viva. Exclude generated virtual environments, Python caches and model weights from the submission ZIP.

Current outstanding submission items:

- `report.pdf` was deliberately removed during cleanup and must be restored before submission. It must cover architecture/protocol, revision/recovery, overload policy, repeated public experiments, a before/after comparison, required metrics, failures/trade-offs, limitations and future work.
- `CONTRIBUTIONS.md` is still a draft: the team must agree named responsibilities and percentages totaling 100%. Review `AI_USAGE.md` as a team too.
- Submit the required 5–7-minute deterministic-source demo video and attend the individual technical viva as instructed by the course. Their completion is separate from the code and file-presence checks.
