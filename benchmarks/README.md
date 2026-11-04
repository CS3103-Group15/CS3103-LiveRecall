# Benchmark runners

Run these scripts from Ubuntu after installing `requirements.txt`. They resolve
the repository root automatically, so they may be invoked from any directory.

```bash
bash benchmarks/run_t1.sh
bash benchmarks/run_t2.sh
bash benchmarks/run_t3.sh
bash benchmarks/run_t4.sh
```

To run T1-T4 sequentially:

```bash
bash benchmarks/run_all_local.sh
```

To run T1-T5, including every supplied network profile:

```bash
bash benchmarks/run_all.sh
```

## Workloads

The runners use these fixed public workloads:

| Test | Workload |
| --- | --- |
| T1 | 20 clients for 20 seconds |
| T2 | 100 clients for 40 seconds |
| T3 | 100 clients for 60 seconds; 10% are slow readers with a 500 ms read delay |
| T4 | 100 clients for 60 seconds; 20% disconnect at 15 seconds and reconnect after 5 seconds |
| T5 | 100 clients for 40 seconds under each selected network profile |

Every runner defaults to three independent runs. The server is restarted for
each run by `run_demo.py`.

For a development check, run T1-T4 and each T5 profile once:

```bash
bash benchmarks/run_all_once.sh
bash benchmarks/run_all_once.sh my_single_run
```

The helper defaults to `results/quick_check/`, or uses the supplied stage name.
It includes T5, which requires Ubuntu and sudo for `tc/netem`. Existing runners
still default to three runs for report measurements. Individual scripts also
accept a run count, for example `RUNS=1 RESULT_STAGE=quick_check bash benchmarks/run_t3.sh`.
Single-run outputs use `t3.csv` and `t3.json` (without `_run01`); summaries support
both single-run and repeated-run output.

Give the complete run a stage name to keep results from different
implementations separate:

```bash
bash benchmarks/run_all.sh isolation_v1
```

This writes to `results/isolation_v1/t1`, `results/isolation_v1/t2`, and so on.
The local-only runner also accepts a stage argument:

```bash
bash benchmarks/run_all_local.sh isolation_v1
```

For an individual benchmark, set `RESULT_STAGE`:

```bash
RESULT_STAGE=isolation_v1 bash benchmarks/run_t3.sh
RESULT_STAGE=isolation_v1 bash benchmarks/run_t5.sh
```



The full runner requests sudo when it reaches T5 because Linux traffic control
changes the loopback interface. It stops on the first failed test and T5 still
resets the active network profile through its exit trap.

T5 requests sudo through the network-profile scripts and runs all supplied
profiles by default. It resets the interface between profiles
and again on exit if a benchmark fails:

```bash
bash benchmarks/run_t5.sh
```

The supplied profiles are:

| Profile | Traffic-control settings |
| --- | --- |
| `delay_100ms` | 100 ms delay with 20 ms normally distributed jitter |
| `loss_3pct` | 3% IP packet loss |
| `delay_loss` | 120 ms delay, 30 ms normally distributed jitter, and 3% IP packet loss |
| `bandwidth_2mbit` | Shared 2 Mbit/s rate limit, 32 Kbit burst, and 400 ms latency |
| `reorder` | 20 ms delay and 20% IP packet reordering with 50% correlation |



Run only one supplied profile, or select another interface, with environment
variables:

```bash
PROFILE=bandwidth_2mbit INTERFACE=lo bash benchmarks/run_t5.sh
```

Use a different Python executable if necessary:

```bash
PYTHON_BIN=python bash benchmarks/run_t1.sh
```

Outputs are grouped by test:

```text
results/
  t1/
    benchmark.log
    summary.md
    summary.json
    t1_run01.csv
    t1_run01.json
    ...
  t2/
  t3/
  t4/
  t5/
    delay_100ms/
      ...
    loss_3pct/
      ...
    delay_loss/
      benchmark.log
      summary.md
      summary.json
      delay_loss_run01.csv
      delay_loss_run01.json
      ...
    bandwidth_2mbit/
      ...
    reorder/
      ...
```

`summary.md` contains a per-run comparison and median table suitable for
reading or copying into the report. `summary.json` contains the same aggregate
data in a machine-readable form. To regenerate either file from existing runs:

```bash
python3 consolidate_results.py results/t3 --stem t3
```

The default expects three files named `t3_run01.json`, `t3_run02.json`, and
`t3_run03.json`. For a single-run result, whose input is named `t3.json`, pass
the expected run count explicitly:

```bash
python3 consolidate_results.py results/quick_check/t3 --stem t3 --expected-runs 1
```

See the main [README](../README.md#understanding-the-results) for metric
definitions and [selected group benchmark results](../README.md#selected-group-benchmark-results).
