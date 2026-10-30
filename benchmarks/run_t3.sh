#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

run_benchmark "t3" "t3" \
    --clients 100 \
    --duration 60 \
    --runs 3 \
    --slow-percent 10 \
    --slow-ms 500
