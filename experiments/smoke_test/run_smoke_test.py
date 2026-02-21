#!/usr/bin/env python3
"""
Smoke test: each agent does 2 discovery requests. 5-minute cap.

Safety controls:
  - Jitter: 0–1500ms random start delay per agent
  - Per-agent: max 2–3 concurrent queries
  - Global: max 25 in-flight

Logging: run_tag, agent_id, mode, step, latency_ms, status
Output: results/week5/exp1/smoke_<run_tag>.json, smoke_test_summary.md
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import os
import random
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import requests

from nanda_core.dataset.client import (
    discover_datasets,
    fetch_data_facts,
    fetch_dataset,
    check_freshness,
    verify_checksum,
)


@dataclass
class LogEntry:
    run_tag: str
    agent_id: str
    mode: str
    step: str
    latency_ms: float
    status: str
    error: str | None = None


# Global concurrency: max 25 in-flight
GLOBAL_SEMAPHORE = threading.Semaphore(25)
# Per-agent: max 3 concurrent
AGENT_SEMAPHORES: dict[str, threading.Semaphore] = {}
AGENT_SEMAPHORE_LOCK = threading.Lock()


def get_agent_semaphore(agent_id: str) -> threading.Semaphore:
    with AGENT_SEMAPHORE_LOCK:
        if agent_id not in AGENT_SEMAPHORES:
            AGENT_SEMAPHORES[agent_id] = threading.Semaphore(3)
        return AGENT_SEMAPHORES[agent_id]


def do_one_discovery(
    agent_id: str,
    registry_url: str,
    run_tag: str,
    logs: list,
    logs_lock: threading.Lock,
) -> tuple[str, float, str]:
    """One discovery: registry -> data_facts -> dataset. Returns (agent_id, latency_ms, status)."""
    t0 = time.perf_counter()
    step = "discovery"
    status = "ok"
    err = None
    try:
        agents = discover_datasets(registry_url, keywords=None)
        if not agents:
            status = "fail"
            err = "no_agents"
            return (agent_id, (time.perf_counter() - t0) * 1000, status)
        ag = random.choice(agents)
        df_url = ag.get("data_facts_url")
        if not df_url:
            status = "fail"
            err = "no_data_facts_url"
            return (agent_id, (time.perf_counter() - t0) * 1000, status)
        df = fetch_data_facts(df_url)
        data = fetch_dataset(df)
        if not data:
            status = "fail"
            err = "empty_dataset"
    except Exception as e:
        status = "fail"
        err = str(e)[:80]
    latency_ms = (time.perf_counter() - t0) * 1000
    with logs_lock:
        logs.append(LogEntry(run_tag, agent_id, "treatment", step, latency_ms, status, err))
    return (agent_id, latency_ms, status)


def run_agent_requests(
    agent_id: str,
    n_requests: int,
    registry_url: str,
    run_tag: str,
    jitter_ms: float,
    logs: list,
    logs_lock: threading.Lock,
) -> None:
    """Run n_requests for one agent, with jitter and per-agent concurrency cap."""
    time.sleep(jitter_ms / 1000.0)
    agent_sem = get_agent_semaphore(agent_id)
    for _ in range(n_requests):
        with GLOBAL_SEMAPHORE:
            with agent_sem:
                do_one_discovery(agent_id, registry_url, run_tag, logs, logs_lock)


def main() -> int:
    ap = argparse.ArgumentParser(description="Smoke test: agents do discovery requests")
    ap.add_argument("--registry-url", default="http://registry.chat39.com:6900")
    ap.add_argument("--agents", default="consumer_001:consumer_050", help="agent IDs or range consumer_001:consumer_050")
    ap.add_argument("--requests-per-agent", type=int, default=2)
    ap.add_argument("--duration-seconds", type=int, default=300, help="5 min cap")
    ap.add_argument("--jitter-max-ms", type=int, default=1500)
    ap.add_argument("--out-dir", type=Path, default=None)
    ap.add_argument("--run-tag", type=str, default=None)
    ap.add_argument("--consumer-base-url", type=str, default=None, help="e.g. http://ip:6001 for health checks")
    args = ap.parse_args()

    # Parse agent range
    if ":" in args.agents and "consumer_" in args.agents:
        lo, hi = args.agents.split(":")[-2:]
        lo_num = int(lo.split("_")[-1]) if "_" in lo else int(lo)
        hi_num = int(hi.split("_")[-1]) if "_" in hi else int(hi)
        agent_ids = [f"consumer_{i:03d}" for i in range(lo_num, hi_num + 1)]
    else:
        agent_ids = [a.strip() for a in args.agents.split(",") if a.strip()]

    # Optional: check consumer reachability (health)
    consumer_reachability: dict[str, bool] = {}
    if args.consumer_base_url:
        base = args.consumer_base_url.rstrip("/")
        parts = base.rsplit(":", 1)
        if len(parts) == 2 and parts[1].isdigit():
            base = parts[0]  # http://ip:6001 -> http://ip
        for aid in agent_ids:
            num = int(aid.split("_")[-1]) if "_" in aid else 0
            port = 6000 + num
            url = f"{base}:{port}/health"
            try:
                r = requests.get(url, timeout=3)
                consumer_reachability[aid] = r.status_code == 200
            except Exception:
                consumer_reachability[aid] = False

    run_tag = args.run_tag or f"smoke_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    out_dir = args.out_dir or (ROOT / "experiments" / "results" / "week5" / "exp1")
    out_dir.mkdir(parents=True, exist_ok=True)

    logs: list[LogEntry] = []
    logs_lock = threading.Lock()

    print(f"[smoke] {len(agent_ids)} agents × {args.requests_per_agent} requests, jitter 0–{args.jitter_max_ms}ms")
    print(f"[smoke] run_tag={run_tag} duration_cap={args.duration_seconds}s")

    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=min(50, len(agent_ids) + 5)) as ex:
        futs = []
        for aid in agent_ids:
            jitter = random.uniform(0, args.jitter_max_ms)
            f = ex.submit(
                run_agent_requests,
                aid,
                args.requests_per_agent,
                args.registry_url,
                run_tag,
                jitter,
                logs,
                logs_lock,
            )
            futs.append(f)
            if time.perf_counter() - start > args.duration_seconds:
                break
        for f in as_completed(futs):
            if time.perf_counter() - start > args.duration_seconds:
                break
            try:
                f.result(timeout=60)
            except Exception as e:
                print(f"  [warn] {e}")

    elapsed = time.perf_counter() - start

    # Serialize logs
    log_dicts = [
        {
            "run_tag": e.run_tag,
            "agent_id": e.agent_id,
            "mode": e.mode,
            "step": e.step,
            "latency_ms": round(e.latency_ms, 2),
            "status": e.status,
            "error": e.error,
        }
        for e in logs
    ]

    # Write JSON log
    log_path = out_dir / f"{run_tag}_logs.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump({"run_tag": run_tag, "elapsed_seconds": round(elapsed, 2), "entries": log_dicts}, f, indent=2)
    print(f"[smoke] Logs -> {log_path}")

    # Summary
    by_agent: dict[str, list] = defaultdict(list)
    for e in logs:
        by_agent[e.agent_id].append(e.status)

    total = len(logs)
    ok_count = sum(1 for e in logs if e.status == "ok")
    fail_count = total - ok_count
    pct_success = 100.0 * ok_count / total if total else 0
    agents_with_any_ok = sum(1 for v in by_agent.values() if "ok" in v)
    agents_all_fail = [a for a, v in by_agent.items() if all(s == "fail" for s in v)]
    error_counts: dict[str, int] = defaultdict(int)
    for e in logs:
        if e.error:
            error_counts[e.error] += 1
    common_failures = sorted(error_counts.items(), key=lambda x: -x[1])[:5]

    summary = {
        "run_tag": run_tag,
        "total_requests": total,
        "ok": ok_count,
        "fail": fail_count,
        "pct_success": round(pct_success, 2),
        "agents_tested": len(by_agent),
        "agents_with_any_success": agents_with_any_ok,
        "agents_all_fail": agents_all_fail,
        "common_failures": [{"error": k, "count": v} for k, v in common_failures],
        "elapsed_seconds": round(elapsed, 2),
    }
    if consumer_reachability:
        reachable = sum(1 for v in consumer_reachability.values() if v)
        summary["consumers_reachable"] = reachable
        summary["consumers_total"] = len(consumer_reachability)

    summary_path = out_dir / f"{run_tag}_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    # smoke_test_summary.md
    md_lines = [
        "# Smoke Test Summary",
        "",
        f"**Run tag:** `{run_tag}`",
        f"**Elapsed:** {elapsed:.1f}s",
        "",
        "## Results",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total requests | {total} |",
        f"| Success | {ok_count} |",
        f"| Fail | {fail_count} |",
        f"| **Success %** | **{pct_success:.1f}%** |",
        f"| Agents tested | {len(by_agent)} |",
        f"| Agents with ≥1 success | {agents_with_any_ok} |",
        "",
        "## Common Failures",
        "",
    ]
    for err, cnt in common_failures:
        md_lines.append(f"- `{err}`: {cnt}")
    if not common_failures:
        md_lines.append("- None")
    if consumer_reachability:
        reachable = sum(1 for v in consumer_reachability.values() if v)
        md_lines.append("")
        md_lines.append("## Consumer Reachability (health)")
        md_lines.append("")
        md_lines.append(f"| Reachable | {reachable}/{len(consumer_reachability)} |")
    if agents_all_fail:
        md_lines.append("")
        md_lines.append("## Agents with All Failures")
        md_lines.append("")
        md_lines.append(", ".join(agents_all_fail[:20]) + (" ..." if len(agents_all_fail) > 20 else ""))

    md_path = out_dir / "smoke_test_summary.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))
    print(f"[smoke] Summary -> {md_path}")
    print(f"[smoke] Success: {pct_success:.1f}% ({ok_count}/{total})")
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
