#!/usr/bin/env python3
"""
Run Experiment 1 and Experiment 2 only. Assumes local registry (:6900) and
50-agent ecosystem (:8000) are already running.

Usage (from NEST root):
  python experiments/run_exp1_exp2_only.py
  python experiments/run_exp1_exp2_only.py --quick   # Exp1 sweep 5,10
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser(description="Run Exp 1 & 2 (registry + ecosystem must be running)")
    ap.add_argument("--quick", action="store_true", help="Exp1 sweep 5,10 instead of 50,200")
    args = ap.parse_args()
    sweep = "5,10" if args.quick else "50,200"

    exp1_dir = ROOT / "experiments" / "exp1_discovery_efficiency"
    exp1_out = exp1_dir / "results"
    exp1_out.mkdir(parents=True, exist_ok=True)
    r1 = subprocess.run(
        [
            sys.executable, "experiments/exp1_discovery_efficiency/run.py",
            "--sweep", sweep,
            "--config", str(exp1_dir / "config_ecosystem_50_local.json"),
            "--out-dir", str(exp1_out),
        ],
        cwd=ROOT,
    )
    if r1.returncode != 0:
        print("[run_exp1_exp2] Exp 1 failed")
        return 1
    print("[run_exp1_exp2] Exp 1 done ->", exp1_out)

    exp2_dir = ROOT / "experiments" / "exp2_freshness_correctness"
    exp2_out = exp2_dir / "results"
    exp2_out.mkdir(parents=True, exist_ok=True)
    r2 = subprocess.run(
        [
            sys.executable, "experiments/exp2_freshness_correctness/run.py",
            "--config", str(exp2_dir / "config.json"),
            "--out-dir", str(exp2_out),
        ],
        cwd=ROOT,
    )
    if r2.returncode != 0:
        print("[run_exp1_exp2] Exp 2 failed")
        return 1
    print("[run_exp1_exp2] Exp 2 done ->", exp2_out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
