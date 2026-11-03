#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# By default, run every supplied impairment profile. Override with, for example:
# PROFILE=bandwidth_2mbit bash benchmarks/run_t5.sh
PROFILE="${PROFILE:-all}"
INTERFACE="${INTERFACE:-lo}"
RESET_SCRIPT="$ROOT_DIR/network_profiles/reset.sh"
ALL_PROFILES=(delay_100ms loss_3pct delay_loss bandwidth_2mbit reorder)

if [[ "$PROFILE" == "all" ]]; then
    PROFILES=("${ALL_PROFILES[@]}")
else
    PROFILES=("$PROFILE")
fi

for profile in "${PROFILES[@]}"; do
    if [[ ! -f "$ROOT_DIR/network_profiles/$profile.sh" ]]; then
        echo "Unknown network profile: $profile" >&2
        echo "Available profiles: all ${ALL_PROFILES[*]}" >&2
        exit 2
    fi
done

profile_active=false

cleanup() {
    if [[ "$profile_active" == true ]]; then
        echo "Resetting network profile on $INTERFACE"
        bash "$RESET_SCRIPT" "$INTERFACE" || true
        profile_active=false
    fi
}
trap cleanup EXIT

for profile in "${PROFILES[@]}"; do
    echo "=== T5 profile: $profile ==="
    profile_active=true
    bash "$ROOT_DIR/network_profiles/$profile.sh" "$INTERFACE"

    run_benchmark "t5/$profile" "$profile" \
        --clients 100 \
        --duration 40 \
        --runs "$RUNS"

    cleanup
done
