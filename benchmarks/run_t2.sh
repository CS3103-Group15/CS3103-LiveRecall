#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

run_benchmark "t2" "t2" \
    --clients 100 \
    --duration 40 \
    --runs 3
