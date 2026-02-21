#!/usr/bin/env python3
"""
Experiment 3: Trust / Integrity

Goal: show integrity failures are detectable only with Data Facts (checksum).

Two modes:
  - Without Data Facts: no checksum, corruption is silent.
  - With Data Facts: SHA256 validation; corruption is caught when checksum mismatches.

Outputs:
  - JSON results
  - Detection vs silent-failure table (Markdown)
  - Bar chart: detection rates with vs without Data Facts
  - Security relevance paragraph
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIR = Path(__file__).resolve().parent
for p in (ROOT, DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from injector import (
    Trial,
    detect_with_data_facts,
    detect_without_data_facts,
    generate_trials,
)


@dataclass
class DetectionStats:
    total: int = 0
    corrupted: int = 0
    detected_with_df: int = 0
    detected_without_df: int = 0

    @property
    def detection_rate_with_df(self) -> float:
        return (self.detected_with_df / self.corrupted) if self.corrupted else 0.0

    @property
    def detection_rate_without_df(self) -> float:
        return (self.detected_without_df / self.corrupted) if self.corrupted else 0.0

    @property
    def silent_failure_rate_with_df(self) -> float:
        return 1.0 - self.detection_rate_with_df if self.corrupted else 0.0

    @property
    def silent_failure_rate_without_df(self) -> float:
        return 1.0 - self.detection_rate_without_df if self.corrupted else 0.0


def run_trials(trials: list[Trial]) -> DetectionStats:
    stats = DetectionStats(total=len(trials))
    for t in trials:
        if t.corrupted:
            stats.corrupted += 1
            if detect_with_data_facts(t):
                stats.detected_with_df += 1
            if detect_without_data_facts(t):
                stats.detected_without_df += 1
    return stats


def load_config(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    ap = argparse.ArgumentParser(description="Experiment 3: Trust / Integrity")
    ap.add_argument("--config", type=Path, default=Path(__file__).parent / "config.json")
    ap.add_argument("--out-dir", type=Path, default=Path(__file__).parent / "results")
    args = ap.parse_args()

    cfg = load_config(args.config)
    corruption_percents = cfg["corruption_percents"]
    n_trials = cfg["n_trials_per_level"]
    payload_len = cfg["payload_bytes"]
    seed = cfg.get("rng_seed")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_tag = f"exp3_{ts}"

    results: list[dict] = []
    for pct in corruption_percents:
        trials = generate_trials(n_trials, pct, payload_len, seed)
        stats = run_trials(trials)
        results.append(
            {
                "corruption_percent": pct,
                "n_trials": n_trials,
                "payload_bytes": payload_len,
                "corrupted_trials": stats.corrupted,
                "detected_with_data_facts": stats.detected_with_df,
                "detected_without_data_facts": stats.detected_without_df,
                "detection_rate_with_data_facts": round(stats.detection_rate_with_df, 4),
                "detection_rate_without_data_facts": round(stats.detection_rate_without_df, 4),
                "silent_failure_rate_with_data_facts": round(stats.silent_failure_rate_with_df, 4),
                "silent_failure_rate_without_data_facts": round(stats.silent_failure_rate_without_df, 4),
            }
        )
        print(
            f"[exp3] corruption={pct:.1f}% | with DF detect={stats.detection_rate_with_df:.3f} "
            f"| without DF detect={stats.detection_rate_without_df:.3f} "
            f"| silent (no DF)={stats.silent_failure_rate_without_df:.3f}"
        )

    # Structured log
    log_path = args.out_dir / f"{run_tag}_results.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "run_tag": run_tag,
                "config": cfg,
                "results": results,
            },
            f,
            indent=2,
        )
    print(f"[exp3] Wrote {log_path}")

    # Table (Markdown)
    table_lines = [
        "| Corruption % | Trials | Detection w/ Data Facts | Detection w/o Data Facts | Silent failure w/ DF | Silent failure w/o DF |",
        "|--------------|--------|-------------------------|--------------------------|----------------------|-----------------------|",
    ]
    for r in results:
        table_lines.append(
            f"| {r['corruption_percent']} | {r['n_trials']} | "
            f"{r['detection_rate_with_data_facts']:.1%} | "
            f"{r['detection_rate_without_data_facts']:.1%} | "
            f"{r['silent_failure_rate_with_data_facts']:.1%} | "
            f"{r['silent_failure_rate_without_data_facts']:.1%} |"
        )
    table_md = "\n".join(table_lines)
    table_path = args.out_dir / f"{run_tag}_detection_table.md"
    with open(table_path, "w", encoding="utf-8") as f:
        f.write("## Experiment 3: Integrity detection vs silent failure\n\n")
        f.write(table_md)
    print(f"[exp3] Wrote {table_path}")

    # Plot
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("[exp3] matplotlib not installed, skipping plot")
    else:
        pct_labels = [str(r["corruption_percent"]) for r in results]
        x = range(len(results))
        w = 0.35
        det_yes = [r["detection_rate_with_data_facts"] for r in results]
        det_no = [r["detection_rate_without_data_facts"] for r in results]
        fig, ax = plt.subplots()
        ax.bar([i - w / 2 for i in x], det_no, width=w, label="Without Data Facts", color="#e67e22")
        ax.bar([i + w / 2 for i in x], det_yes, width=w, label="With Data Facts", color="#2980b9")
        ax.set_xticks(list(x))
        ax.set_xticklabels(pct_labels)
        ax.set_ylim(0, 1.05)
        ax.set_ylabel("Detection rate (corrupted trials)")
        ax.set_xlabel("Corruption percentage of payload")
        ax.set_title("Experiment 3: Integrity detection with vs without Data Facts")
        ax.legend()
        fig.tight_layout()
        plot_path = args.out_dir / f"{run_tag}_detection_bar.png"
        fig.savefig(plot_path, dpi=120)
        plt.close()
        print(f"[exp3] Wrote {plot_path}")

    # Security relevance paragraph
    summary = [
        "With Data Facts (checksum), integrity violations are caught deterministically: every checksum mismatch flags tampering.",
        "Without Data Facts, the same corrupt payloads sail through silently; detection depends on luck or downstream failures.",
        "For regulated domains like finance (market data feeds) and healthcare (EHR lab results), silent corruption can trigger bad trades or clinical decisions.",
        "Checksum enforcement via Data Facts converts silent integrity risk into observable, actionable failures.",
    ]
    summary_path = args.out_dir / f"{run_tag}_security_relevance.md"
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("# Experiment 3: Security relevance\n\n")
        for p in summary:
            f.write(p + "\n\n")
    print(f"[exp3] Wrote {summary_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
