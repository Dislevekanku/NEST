#!/usr/bin/env python3
"""
Run 50-agent ecosystem locally (no deploy), then Experiment 1 and Experiment 2.
Redoes results: table, plot, summary (Exp 1); stale-vs-detected table, plot, interpretation (Exp 2).

Usage (from NEST root):
  python experiments/run_local_experiments.py
  python experiments/run_local_experiments.py --quick   # Exp1 sweep 5,10 (faster)

What runs:
  1. Local registry (Flask :6900) — in-memory /register, /list.
  2. Ecosystem (MultiDatasetServer :8000 + 50-agent registration).
  3. Exp 1: sweep N=50,200 (or 5,10 with --quick), config_ecosystem_50_local.
  4. Exp 2: freshness correctness (simulated).
  5. Stops registry and ecosystem.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REGISTRY_PORT = 6900
DATA_PORT = 8000


def wait_for(url: str, timeout: float = 60.0) -> bool:
    import urllib.request
    import urllib.error
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description="Run 50-agent ecosystem + Exp 1 & 2 locally")
    ap.add_argument("--quick", action="store_true", help="Exp1 sweep 5,10 instead of 50,200")
    args = ap.parse_args()
    sweep = "5,10" if args.quick else "50,200"

    os.chdir(ROOT)

    registry_proc = subprocess.Popen(
        [sys.executable, "experiments/local_registry.py"],
        env={**os.environ, "LOCAL_REGISTRY_PORT": str(REGISTRY_PORT)},
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        if not wait_for(f"http://127.0.0.1:{REGISTRY_PORT}/health", timeout=15.0):
            print("[run_local] local registry did not become ready")
            return 1
        print("[run_local] local registry ready")
    except Exception as e:
        registry_proc.terminate()
        registry_proc.wait(timeout=5)
        print(f"[run_local] registry failed: {e}")
        return 1

    eco_env = {
        **os.environ,
        "REGISTRY_URL": f"http://localhost:{REGISTRY_PORT}",
        "PUBLIC_URL": f"http://localhost:{DATA_PORT}",
        "DATA_SERVER_PORT": str(DATA_PORT),
        "CONFIG_PATH": str(ROOT / "experiments" / "ecosystem" / "config_50_agents.json"),
    }
    ecosystem_proc = subprocess.Popen(
        [sys.executable, "experiments/ecosystem/run_ecosystem.py"],
        env=eco_env,
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        if not wait_for(f"http://127.0.0.1:{DATA_PORT}/health", timeout=45.0):
            print("[run_local] ecosystem did not become ready")
            return 1
        print("[run_local] 50-agent ecosystem ready")
    except Exception as e:
        ecosystem_proc.terminate()
        try:
            ecosystem_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            ecosystem_proc.kill()
        print(f"[run_local] ecosystem failed: {e}")
        registry_proc.terminate()
        registry_proc.wait(timeout=5)
        return 1

    # Exp 1
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
        print("[run_local] Exp 1 failed")
    else:
        print("[run_local] Exp 1 done; results in", exp1_out)

    # Exp 2
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
        print("[run_local] Exp 2 failed")
    else:
        print("[run_local] Exp 2 done; results in", exp2_out)

    ecosystem_proc.terminate()
    try:
        ecosystem_proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        ecosystem_proc.kill()
    registry_proc.terminate()
    try:
        registry_proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        registry_proc.kill()

    print("[run_local] Stopped ecosystem and registry.")
    return 0 if (r1.returncode == 0 and r2.returncode == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
