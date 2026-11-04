#!/usr/bin/env python3
"""Consolidate independent LiveRecall run summaries into one readable report."""

from __future__ import annotations

import argparse
import json
import re
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# Label, dotted JSON path, unit, displayed decimal places.
METRICS = [
    ("Clients observed", "clients", "count", 0),
    ("P50 caption age", "p50_ms", "ms", 2),
    ("P95 caption age", "p95_ms", "ms", 2),
    ("P99 caption age", "p99_ms", "ms", 2),
    ("Fresh Caption Ratio", "fresh_pct", "%", 2),
    ("Fresh Final Caption Ratio", "fresh_final_pct", "%", 2),
    ("Final-caption completeness", "final_completeness_pct", "%", 2),
    ("Normal Update Coverage", "normal_update_coverage_pct", "%", 2),
    ("Duplicate messages", "duplicates", "count", 0),
    ("Stale messages", "stale", "count", 0),
    ("Connection errors", "connection_errors", "count", 0),
    ("Normal-client P95", "normal_clients.p95_ms", "ms", 2),
    ("Normal-client freshness", "normal_clients.fresh_pct", "%", 2),
    ("Slow-client P95", "slow_clients.p95_ms", "ms", 2),
    ("Slow-client freshness", "slow_clients.fresh_pct", "%", 2),
    ("Recovery P50", "recovery_p50_ms", "ms", 2),
    ("Recovery P95", "recovery_p95_ms", "ms", 2),
]


def nested_value(data: dict[str, Any], path: str) -> int | float | None:
    current: Any = data
    for key in path.split("."):
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]

    if isinstance(current, bool) or not isinstance(current, (int, float)):
        return None
    return current


def display(value: int | float | None, decimals: int) -> str:
    if value is None:
        return "—"
    if decimals == 0:
        return f"{value:.0f}"
    return f"{value:.{decimals}f}"


def consolidate(files: list[Path]) -> dict[str, Any]:
    runs = []
    for path in files:
        with path.open(encoding="utf-8") as stream:
            runs.append({"file": path.name, "summary": json.load(stream)})

    metrics: dict[str, Any] = {}
    for label, path, unit, decimals in METRICS:
        values = [nested_value(run["summary"], path) for run in runs]
        observed = [float(value) for value in values if value is not None]
        median = statistics.median(observed) if observed else None
        metrics[path] = {
            "label": label,
            "unit": unit,
            "values": values,
            "observed_runs": len(observed),
            "median": median,
            "decimals": decimals,
        }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_count": len(runs),
        "run_files": [run["file"] for run in runs],
        "metrics": metrics,
    }


def markdown_report(name: str, consolidated: dict[str, Any]) -> str:
    run_files = consolidated["run_files"]
    metrics = consolidated["metrics"]

    lines = [
        f"# LiveRecall benchmark summary: {name}",
        "",
        f"Independent runs: {consolidated['run_count']}",
        "",
        "| Metric | " + " | ".join(run_files) + " | Median |",
        "|---|" + "---:|" * (len(run_files) + 1),
    ]

    for metric in metrics.values():
        values = [display(value, metric["decimals"]) for value in metric["values"]]
        median = display(metric["median"], metric["decimals"])
        label = f"{metric['label']} ({metric['unit']})"
        lines.append(f"| {label} | " + " | ".join(values) + f" | **{median}** |")

    lines.extend(["", "## Quick checks", ""])
    checks = [
        ("Final completeness", "final_completeness_pct", "%"),
        ("Duplicates", "duplicates", ""),
        ("Stale messages", "stale", ""),
        ("Connection errors", "connection_errors", ""),
    ]
    for label, path, suffix in checks:
        metric = metrics[path]
        value = display(metric["median"], metric["decimals"])
        lines.append(f"- Median {label.lower()}: {value}{suffix}")

    lines.extend([
        "",
        "A dash indicates that the metric does not apply to this workload or was not reported.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("result_dir", type=Path)
    parser.add_argument("--stem", required=True,
                        help="Run filename stem, for example t3 or delay_loss")
    parser.add_argument("--expected-runs", type=int, default=3)
    parser.add_argument("--output-name", default="summary")
    args = parser.parse_args()

    run_name = re.compile(rf"{re.escape(args.stem)}_run\d+\.json")
    files = sorted(
        path
        for path in args.result_dir.glob("*.json")
        if run_name.fullmatch(path.name)
    )
    # run_demo.py omits the _runNN suffix when only one run is requested.
    single_run = args.result_dir / f"{args.stem}.json"
    if args.expected_runs == 1 and single_run.is_file():
        files = [single_run]
    if len(files) != args.expected_runs:
        raise SystemExit(
            f"Expected {args.expected_runs} JSON runs matching "
            f"{args.stem}_run*.json in {args.result_dir}, found {len(files)}"
        )

    consolidated = consolidate(files)
    json_path = args.result_dir / f"{args.output_name}.json"
    markdown_path = args.result_dir / f"{args.output_name}.md"

    json_path.write_text(json.dumps(consolidated, indent=2), encoding="utf-8")
    markdown_path.write_text(
        markdown_report(args.stem, consolidated), encoding="utf-8"
    )

    print(f"Consolidated JSON: {json_path}")
    print(f"Readable summary:  {markdown_path}")


if __name__ == "__main__":
    main()