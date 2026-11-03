#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if (( $# > 1 )); then
    echo "Usage: bash benchmarks/run_all_once.sh [result-stage]" >&2
    exit 2
fi

export RUNS=1
# Separate development results from the usual three-run report results.
export RESULT_STAGE="${1:-${RESULT_STAGE:-quick_check}}"
bash "$SCRIPT_DIR/run_all.sh"
