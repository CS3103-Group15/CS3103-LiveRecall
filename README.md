# LiveRecall — CS3103 Group 15

LiveRecall distributes revision-based lecture captions to students. Each browser displays the newest text, keeps recent final captions locally, and reconnects with a final-caption checkpoint to recover missed context.

## Start here

- **Run the application:** the commands below.
- **Read the final measurements:** [results/final/SUMMARY.md](results/final/SUMMARY.md).
- **Technical report:** `report.pdf` is temporarily removed; add the required 4–5-page report before submission.
- **Required demo video (5–7 minutes):** show live provisional/final revision replacement, local 15/30/60-second recall, and disconnect/reconnect recovery using the supplied caption source. Also demonstrate late joining and prepare the code/results for the viva.
- **Team declarations:** [AI_USAGE.md](AI_USAGE.md) and [CONTRIBUTIONS.md](CONTRIBUTIONS.md). Contribution names/percentages must be confirmed by the team before submission.

The current permanent Ubuntu project is `/home/mininet/CS3103-LiveRecall` in the existing VMware Mininet VM. Mininet itself does not have to run: the server and simulated clients run directly inside Ubuntu, and impairment is applied to `lo`.

## Ubuntu setup

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip iproute2
cd ~/CS3103-LiveRecall
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

`requirements.txt` contains the mandatory server dependency only. There are no cloud APIs, databases, model downloads or interactive startup prompts. The supplied school source, runner, clients, analyser and impairment scripts are unchanged.

## Application demo — three terminals inside Ubuntu

Terminal 1:

```bash
cd ~/CS3103-LiveRecall
source .venv/bin/activate
python solution_server.py --port 8765
```

Terminal 2:

```bash
cd ~/CS3103-LiveRecall
source .venv/bin/activate
python -m http.server 8000 --bind 0.0.0.0 --directory client
```

Open two browser tabs at `http://<VM-IP>:8000` from your Mac, or `http://127.0.0.1:8000` from a browser inside Ubuntu. The browser connects to the hostname serving the page on WebSocket port 8765. Find the VM IP with `hostname -I` inside Ubuntu; its current address may change after reboot.

Terminal 3, after the browser tabs have connected:

```bash
cd ~/CS3103-LiveRecall
source .venv/bin/activate
python caption_source.py --uri ws://127.0.0.1:8765 --segments 100
```

Gray italic text is provisional; green text is final. Revisions replace one line. “What did I miss?” opens the local 30-second view; 15- and 60-second buttons change the window. A late join or reconnect receives ordered missed finals before new live updates. Live display uses a 15-second window; local final retention is 70 seconds.

For a repeatable second lecture/demo, restart the server and reload the browser tabs before restarting a source whose segment numbers begin again at 1. The assignment assumes one source/session at a time.

## Reproducible Ubuntu performance experiments

Do not start a separate server for `run_demo.py`; it starts and stops its own server/source/clients. Port 19877 avoids clashes with the visual demo on 8765.

Run all components inside the same Ubuntu VM. Use three independent runs and report their medians. Write new measurements separately from the saved final evidence.

```bash
source .venv/bin/activate
mkdir -p results/recheck
```

Required public workloads:


```bash
python run_demo.py --clients 20 --duration 20 --runs 3 --port 19877 --output-stem results/recheck/t1
python run_demo.py --clients 100 --duration 40 --runs 3 --port 19877 --output-stem results/recheck/t2
python run_demo.py --clients 100 --duration 60 --runs 3 --port 19877 --slow-percent 10 --slow-ms 500 --output-stem results/recheck/t3
python run_demo.py --clients 100 --duration 60 --runs 3 --port 19877 --disconnect-percent 20 --disconnect-at 15 --disconnect-seconds 5 --output-stem results/recheck/t4
sudo bash network_profiles/delay_loss.sh lo
python run_demo.py --clients 100 --duration 40 --runs 3 --port 19877 --output-stem results/recheck/t5
sudo bash network_profiles/reset.sh lo
```

Always reset the profile even if a manual test fails. Saved measurements in `results/final/` are the published snapshot; do not mix them with new runs. The raw archive includes all per-run CSV/JSON, exact commands/hashes, profiles, resource samples and logs. `comparison.csv` compares the earlier sender with the final sender on the same VM/filesystem and T5 settings. Historical development-test logs are evidence of checks already performed; their helper/test source is available in Git history rather than the minimal submission tree.

## Submission check

```bash
python submission_check.py --port 19878
python submission_check.py --final --port 19878
```

The final check requires `report.pdf`, which is temporarily removed. It checks file presence/startup, not the truth of team declarations or completion of the video/viva.

## Code and protocol flow

`solution_server.py` calls `server/application.py::run_server`. The application routes `SOURCE_HELLO` to `source_session.py` and `CLIENT_HELLO` to `client_session.py`.

Accepted source revisions pass through `state.py`. Duplicate/stale revisions and revisions after a final are rejected. Finals are committed to `history.py` before publication. Unrecognized extra source fields are ignored. The implementation does not assume three revisions per segment.

`delivery_hub.py` publishes accepted updates to registered sessions without waiting for sockets. Each session has an independent sender and a bounded provisional queue. Finals exist once in shared history; a per-session `next_final` sequence bookmark tracks the next final to send. Initial `HISTORY`, bookmark capture and registration happen atomically, and history is sent before live work.

`server/delivery_policy.py` separates fixed queue/timeout/congestion settings (`DeliveryPolicy`) from mutable ping/pong batch progress (`FeedbackState`). `ClientSession` keeps 20 direct fields for its connection, queue, bookmark and sender lifecycle. Grouping settings does not remove delivery safeguards; each client has independent feedback state even if it shares an immutable policy.

The browser checkpoint describes the last final the browser actually accepted. It differs from the server delivery bookmark, which tracks sending progress. The checkpoint survives a WebSocket reconnect in the same page; a page reload starts fresh and requests recent history.

### Bounds and overload policy

- Shared final history: 70 seconds, at most 20,000 finals / 32 MiB. It is not an unlimited lecture transcript.
- Per-session provisional queue: at most 256 entries / 1 MiB.
- Pressure signals: queue length/bytes, queued age, send duration, transport write buffer, final lag and delayed feedback relative to the connection's best RTT. Severe lag defaults to 250 ms; two consecutive mild slow-send/feedback observations also confirm pressure, while an isolated short scheduling hiccup does not immediately trigger coalescing.
- Congested queues drop obsolete provisionals, preserve the latest active revision and preserve every retained final. A cadence-aware provisional replacement window (250 ms to 1 s) lets newer work supersede unsent revisions; a 2 s cap on voluntary deferral prevents continuous revisions from starving the latest update once the sender can transmit. Finals wake the sender immediately.
- Ping/pong checkpoints bound transport progress. Fast links retain tight one-message feedback; higher baseline RTTs allow a cadence-aware batch, capped at eight messages, with a 64 KiB byte threshold that triggers a check after the current message (so it can overshoot by one message). Ping/send waits have timeouts and failures close only the affected connection.
- Recovery uses high/low thresholds and a quiet interval. After a large feedback delay, conservative coalescing may continue for up to 60 seconds. This helps avoid repeated overload but can delay restoration of full provisional coverage after a temporary bottleneck.

A pong is transport feedback, not an application/display acknowledgement. Already transmitted revisions cannot be retracted. If a client falls behind the retained history, the connection is closed rather than silently skipping finals or growing memory forever. This bounded-retention limit must be considered when interpreting long outages.

## Interpretation and remaining team work

Completeness and freshness are different: a final may arrive correctly but later than 500 ms. Slow readers, offline periods and packet loss can lower freshness. Under overload, obsolete provisional suppression lowers overall revision coverage intentionally; unconstrained T1/T2 and healthy-client isolation must still be checked. TCP loss causes retransmission/head-of-line delay and finite-window tail misses, not ordinary unordered WebSocket delivery.

Public-test success does not guarantee hidden workload marks. The team must review the report/declarations, agree contribution percentages, record the required 5–7 minute demo and attend the viva. Optional ASR is outside this mandatory implementation.

## Submission checklist

Include the application source (`solution_server.py`, `server/`, `client/`), `requirements.txt`, `README.md`, `AI_USAGE.md`, `CONTRIBUTIONS.md`, and the required `report.pdf`. Keep the supplied deterministic source, transcript, unchanged public test programs and network profiles so the experiments can be reproduced. Saved results support the report and viva. Submit the required video separately as instructed by the course.

Complete the team contribution agreement and restore the report before submission. Exclude `.git`, `.venv`, Python caches and any fresh ad-hoc test files from a submission ZIP. A repository submission should retain its Git history.

### Reproduce the controlled T5 baseline

The raw archive contains `comparison/before_client_session.py`, the exact earlier sender. This is measurement provenance, not an alternative production server. To reconstruct that configuration without editing the submitted source or school programs:

```bash
TASK_ROOT="$PWD"
BEFORE_DIR=$(mktemp -d /tmp/liverecall-before-XXXXXX)
cp solution_server.py run_demo.py load_clients.py analyse_results.py caption_source.py sample_transcript.txt "$BEFORE_DIR/"
cp -R server network_profiles "$BEFORE_DIR/"
python -c 'import zipfile,sys; sys.stdout.buffer.write(zipfile.ZipFile("results/final/raw_results.zip").read("comparison/before_client_session.py"))' > "$BEFORE_DIR/server/client_session.py"
sudo -v
sudo bash network_profiles/delay_loss.sh lo
(cd "$BEFORE_DIR" && "$TASK_ROOT/.venv/bin/python" run_demo.py --clients 100 --duration 40 --runs 3 --port 19877 --quiet-server --output-stem before_t5)
sudo bash network_profiles/reset.sh lo
```

Repeat the same T5 command from the current project for the after configuration, with a fresh scratch output stem. Always reset impairment if interrupted. Report the median of three independent runs on the same VM/filesystem; retain the before/after configuration hashes. Temporary copies are not included in the submission ZIP.
