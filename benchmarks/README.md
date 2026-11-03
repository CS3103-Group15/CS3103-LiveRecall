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

Stage names may contain letters, numbers, dots, underscores, and hyphens.

The full runner requests sudo when it reaches T5 because `tc/netem` changes the
loopback interface. It stops on the first failed test and T5 still resets the
active network profile through its exit trap.

T5 uses `tc/netem`, requests sudo through the network-profile scripts, and runs
all supplied profiles by default. It resets the interface between profiles and
again on exit if a benchmark fails:

```bash
bash benchmarks/run_t5.sh
```

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
    delay_loss/
      benchmark.log
      summary.md
      summary.json
      delay_loss_run01.csv
      delay_loss_run01.json
      ...
```

`summary.md` contains a per-run comparison and median table suitable for
reading or copying into the report. `summary.json` contains the same aggregate
data in a machine-readable form. To regenerate either file from existing runs:

```bash
python3 consolidate_results.py results/t3 --stem t3
```
