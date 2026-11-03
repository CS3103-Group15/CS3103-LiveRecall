#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

run_benchmark "t1" "t1" \
    --clients 20 \
    --duration 20 \
    --runs "$RUNS"
