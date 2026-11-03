#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if (( $# > 1 )); then
    echo "Usage: bash benchmarks/run_all.sh [result-stage]" >&2
    exit 2
fi
if (( $# == 1 )); then
    export RESULT_STAGE="$1"
fi

echo "=== Running T1-T4${RESULT_STAGE:+ for stage $RESULT_STAGE} ==="
bash "$SCRIPT_DIR/run_all_local.sh"

echo "=== Running T5 network profiles ==="
bash "$SCRIPT_DIR/run_t5.sh"

echo "=== All LiveRecall public benchmarks completed ==="
