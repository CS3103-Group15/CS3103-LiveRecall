#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if (( $# > 1 )); then
    echo "Usage: bash benchmarks/run_all_local.sh [result-stage]" >&2
    exit 2
fi
if (( $# == 1 )); then
    export RESULT_STAGE="$1"
fi

# T5 is intentionally separate because it changes the host's traffic-control
# configuration and requires sudo privileges.
bash "$SCRIPT_DIR/run_t1.sh"
bash "$SCRIPT_DIR/run_t2.sh"
bash "$SCRIPT_DIR/run_t3.sh"
bash "$SCRIPT_DIR/run_t4.sh"
