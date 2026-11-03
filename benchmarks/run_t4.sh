#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

run_benchmark "t4" "t4" \
    --clients 100 \
    --duration 60 \
    --runs "$RUNS" \
    --disconnect-percent 20 \
    --disconnect-at 15 \
    --disconnect-seconds 5
