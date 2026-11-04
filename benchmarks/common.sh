#!/usr/bin/env bash

# Shared setup for the public LiveRecall benchmark scripts.
set -euo pipefail

BENCHMARK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$BENCHMARK_DIR/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
RUNS="${RUNS:-3}"
RESULT_STAGE="${RESULT_STAGE:-}"

if [[ ! "$RUNS" =~ ^[1-9][0-9]*$ ]]; then
    echo "RUNS must be a positive integer." >&2
    return 2 2>/dev/null || exit 2
fi

if [[ -n "$RESULT_STAGE" ]]; then
    if [[ ! "$RESULT_STAGE" =~ ^[A-Za-z0-9._-]+$ ]] \
        || [[ "$RESULT_STAGE" == "." ]] \
        || [[ "$RESULT_STAGE" == ".." ]]; then
        echo "Invalid RESULT_STAGE: $RESULT_STAGE" >&2
        echo "Use letters, numbers, dots, underscores, or hyphens." >&2
        return 2 2>/dev/null || exit 2
    fi
    RESULTS_ROOT="results/$RESULT_STAGE"
else
    RESULTS_ROOT="results"
fi

cd "$ROOT_DIR"

run_benchmark() {
    local result_folder="$1"
    local output_name="$2"
    shift 2

    local output_dir="$RESULTS_ROOT/$result_folder"
    mkdir -p "$output_dir"

    echo "Results: $ROOT_DIR/$output_dir"
    "$PYTHON_BIN" run_demo.py \
        --quiet-server \
        "$@" \
        --output-stem "$output_dir/$output_name" \
        2>&1 | tee "$output_dir/benchmark.log"

    "$PYTHON_BIN" consolidate_results.py "$output_dir" \
        --stem "$output_name" \
        --expected-runs "$RUNS" \
        2>&1 | tee -a "$output_dir/benchmark.log"
}
