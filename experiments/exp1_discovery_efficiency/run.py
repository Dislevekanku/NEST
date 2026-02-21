#!/usr/bin/env python3
"""
Experiment 1: Discovery Efficiency

Simulate N agent queries for datasets.
- Baseline: agent-only discovery (manual endpoint knowledge) — direct GET to dataset.
- Treatment: Agent Facts + Data Facts URL — registry → data_facts_url → Data Facts → dataset.

Metrics: time-to-first-data (s), failed lookups, steps/messages, % successful retrievals.

Usage:
  python run.py --N 50 --mode both [--config config.json] [--out-dir results] [--debug]
  python run.py --N 200 --mode both  # record run
  python run.py --sweep 50,200       # run N=50 (debug) and N=200 (record), emit table + plot
  python run.py --scale-50           # paper-grade: 50 agents, N=50 then N=200, exp1_scale_50agents_* + exp1_raw.jsonl
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# NEST root
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import random
from nanda_core.dataset.client import (
    fetch_dataset_direct,
    discover_and_access_dataset,
    discover_datasets,
    fetch_data_facts,
    fetch_dataset,
    check_freshness,
    verify_checksum,
)


def load_config(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    eco_ip = os.environ.get("ECOSYSTEM_IP", "").strip()
    if eco_ip:
        def _sub(v):
            if isinstance(v, str):
                return v.replace("ECOSYSTEM_IP", eco_ip)
            if isinstance(v, list):
                return [_sub(x) for x in v]
            if isinstance(v, dict):
                return {k: _sub(x) for k, x in v.items()}
            return v
        cfg = _sub(cfg)
    return cfg


def _p95(latencies: list[float]) -> float | None:
    if not latencies:
        return None
    s = sorted(latencies)
    idx = min(len(s) - 1, int(len(s) * 0.95))
    return s[idx]


def run_baseline(
    config: dict, n: int, debug: bool, raw_jsonl_file=None
) -> dict:
    """Baseline: direct GET to dataset endpoint (manual endpoint knowledge). 1 step."""
    endpoints = config.get("dataset_endpoints")
    if endpoints:
        rng = random.Random(config.get("rng_seed"))
        def pick():
            return rng.choice(endpoints)
    else:
        ep = config.get("dataset_endpoint")
        if not ep:
            raise ValueError("config must have dataset_endpoint or dataset_endpoints")
        def pick():
            return ep
    latencies: list[float] = []
    failed = 0
    steps_per_query = 1

    for i in range(n):
        t0 = time.perf_counter()
        try:
            fetch_dataset_direct(pick())
            elapsed = time.perf_counter() - t0
            latencies.append(elapsed)
            if raw_jsonl_file:
                raw_jsonl_file.write(
                    json.dumps(
                        {
                            "mode": "baseline",
                            "n": n,
                            "query_idx": i,
                            "success": True,
                            "time_to_first_data_seconds": round(elapsed, 6),
                            "steps_per_query": steps_per_query,
                        },
                        ensure_ascii=True,
                    ) + "\n"
                )
        except Exception as e:
            failed += 1
            if raw_jsonl_file:
                raw_jsonl_file.write(
                    json.dumps(
                        {
                            "mode": "baseline",
                            "n": n,
                            "query_idx": i,
                            "success": False,
                            "error": str(e)[:200],
                            "steps_per_query": steps_per_query,
                        },
                        ensure_ascii=True,
                    ) + "\n"
                )
            if debug:
                print(f"  [baseline] query {i+1}/{n} failed: {e}")
        if debug and (i + 1) % 10 == 0:
            print(f"  [baseline] {i+1}/{n} done, failed={failed}")

    successful = n - failed
    return {
        "mode": "baseline",
        "n": n,
        "steps_per_query": steps_per_query,
        "total_queries": n,
        "failed_lookups": failed,
        "successful_retrievals": successful,
        "pct_success": 100.0 * successful / n if n else 0,
        "time_to_first_data_seconds": latencies,
        "mean_time_to_first_data_seconds": sum(latencies) / len(latencies) if latencies else None,
        "median_time_to_first_data_seconds": sorted(latencies)[len(latencies) // 2] if latencies else None,
        "p95_time_to_first_data_seconds": _p95(latencies),
    }


def run_treatment(
    config: dict, n: int, debug: bool, raw_jsonl_file=None
) -> dict:
    """Treatment: registry → data_facts_url → Data Facts → dataset. 3 steps."""
    registry_url = config["registry_url"]
    target_agent_id = config.get("target_agent_id")
    target_dataset_id = config.get("target_dataset_id")
    use_multiple = config.get("use_multiple_agents", False)
    keywords = config.get("keywords") if config.get("keywords") is not None else ([] if use_multiple else ["finance", "stock"])
    ttl_enabled = config.get("ttl_enabled", True)
    checksum_enabled = config.get("checksum_enabled", True)
    rng = random.Random(config.get("rng_seed"))

    latencies: list[float] = []
    failed = 0
    steps_per_query = 3  # registry, data facts, dataset

    agents_multi: list[dict] = []
    if use_multiple:
        agents_multi = discover_datasets(registry_url, keywords if keywords else None)
        if not agents_multi:
            if debug:
                print("  [treatment] no agents with data_facts_url found")
            for j in range(n):
                failed += 1
                if raw_jsonl_file:
                    raw_jsonl_file.write(
                        json.dumps(
                            {
                                "mode": "treatment",
                                "n": n,
                                "query_idx": j,
                                "success": False,
                                "error": "no agents with data_facts_url",
                                "steps_per_query": steps_per_query,
                            },
                            ensure_ascii=True,
                        ) + "\n"
                    )
            return _treatment_result(n, failed, steps_per_query, latencies)

    for i in range(n):
        t0 = time.perf_counter()
        try:
            if use_multiple and agents_multi:
                ag = rng.choice(agents_multi)
                df_url = ag.get("data_facts_url")
                if not df_url:
                    raise RuntimeError("agent missing data_facts_url")
                data_facts = fetch_data_facts(df_url)
                if target_dataset_id and data_facts.get("dataset_id") != target_dataset_id:
                    raise RuntimeError("dataset id mismatch")
                if ttl_enabled and not check_freshness(data_facts):
                    pass  # still use; we log latency
                dataset = fetch_dataset(data_facts)
                if checksum_enabled:
                    verify_checksum(data_facts, dataset)
            else:
                result = discover_and_access_dataset(
                    registry_url=registry_url,
                    target_agent_id=target_agent_id,
                    target_dataset_id=target_dataset_id,
                    keywords=keywords if not target_agent_id else None,
                    ttl_enabled=ttl_enabled,
                    checksum_enabled=checksum_enabled,
                )
                if result is None or not result.get("dataset"):
                    raise RuntimeError("discover_and_access_dataset returned no dataset")
            elapsed = time.perf_counter() - t0
            latencies.append(elapsed)
            if raw_jsonl_file:
                raw_jsonl_file.write(
                    json.dumps(
                        {
                            "mode": "treatment",
                            "n": n,
                            "query_idx": i,
                            "success": True,
                            "time_to_first_data_seconds": round(elapsed, 6),
                            "steps_per_query": steps_per_query,
                        },
                        ensure_ascii=True,
                    ) + "\n"
                )
        except Exception as e:
            failed += 1
            if raw_jsonl_file:
                raw_jsonl_file.write(
                    json.dumps(
                        {
                            "mode": "treatment",
                            "n": n,
                            "query_idx": i,
                            "success": False,
                            "error": str(e)[:200],
                            "steps_per_query": steps_per_query,
                        },
                        ensure_ascii=True,
                    ) + "\n"
                )
            if debug:
                print(f"  [treatment] query {i+1}/{n} failed: {e}")
        if debug and (i + 1) % 10 == 0:
            print(f"  [treatment] {i+1}/{n} done, failed={failed}")

    return _treatment_result(n, failed, steps_per_query, latencies)


def _treatment_result(n: int, failed: int, steps_per_query: int, latencies: list[float]) -> dict:
    successful = n - failed
    return {
        "mode": "treatment",
        "n": n,
        "steps_per_query": steps_per_query,
        "total_queries": n,
        "failed_lookups": failed,
        "successful_retrievals": successful,
        "pct_success": 100.0 * successful / n if n else 0,
        "time_to_first_data_seconds": latencies,
        "mean_time_to_first_data_seconds": sum(latencies) / len(latencies) if latencies else None,
        "median_time_to_first_data_seconds": sorted(latencies)[len(latencies) // 2] if latencies else None,
        "p95_time_to_first_data_seconds": _p95(latencies),
    }


def _dry_run(args) -> int:
    """Emit mock results for N=50,200 (no HTTP)."""
    sweep_ns = [50, 200]
    config = load_config(args.config)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_tag = f"exp1_sweep_50_200_{ts}"

    results = []
    for n in sweep_ns:
        base_ttd = [0.10 + 0.02 * (i % 10) / 10 for i in range(n)]
        results.append({
            "mode": "baseline",
            "n": n,
            "steps_per_query": 1,
            "total_queries": n,
            "failed_lookups": 0,
            "successful_retrievals": n,
            "pct_success": 100.0,
            "time_to_first_data_seconds": base_ttd,
            "mean_time_to_first_data_seconds": sum(base_ttd) / len(base_ttd),
            "median_time_to_first_data_seconds": sorted(base_ttd)[len(base_ttd) // 2],
            "p95_time_to_first_data_seconds": _p95(base_ttd),
        })
        treat_ttd = [0.35 + 0.05 * (i % 10) / 10 for i in range(n)]
        results.append({
            "mode": "treatment",
            "n": n,
            "steps_per_query": 3,
            "total_queries": n,
            "failed_lookups": 0,
            "successful_retrievals": n,
            "pct_success": 100.0,
            "time_to_first_data_seconds": treat_ttd,
            "mean_time_to_first_data_seconds": sum(treat_ttd) / len(treat_ttd),
            "median_time_to_first_data_seconds": sorted(treat_ttd)[len(treat_ttd) // 2],
            "p95_time_to_first_data_seconds": _p95(treat_ttd),
        })

    print("[exp1] Dry-run: mock results for N=50,200")
    _write_outputs(
        results, run_tag, config, args.out_dir, args.no_plot, sweep_ns,
        scale_50_names=getattr(args, "scale_50", False),
    )
    if getattr(args, "scale_50", False):
        raw_path = args.out_dir / "exp1_raw.jsonl"
        with open(raw_path, "w", encoding="utf-8") as rf:
            rf.write(json.dumps({"event": "run_start", "run_tag": run_tag, "sweep_ns": sweep_ns, "scale_50": True}, ensure_ascii=True) + "\n")
            for r in results:
                for i in range(r["n"]):
                    ttd = r["time_to_first_data_seconds"][i] if i < len(r["time_to_first_data_seconds"]) else None
                    rf.write(
                        json.dumps(
                            {
                                "mode": r["mode"],
                                "n": r["n"],
                                "query_idx": i,
                                "success": True,
                                "time_to_first_data_seconds": round(ttd, 6) if ttd is not None else None,
                                "steps_per_query": r["steps_per_query"],
                            },
                            ensure_ascii=True,
                        ) + "\n"
                    )
            rf.write(json.dumps({"event": "run_end", "run_tag": run_tag}, ensure_ascii=True) + "\n")
        print(f"[exp1] Wrote {raw_path} (dry-run)")
    return 0


def _write_outputs(
    results: list[dict],
    run_tag: str,
    config: dict,
    out_dir: Path,
    no_plot: bool,
    sweep_ns: list[int] | None,
    scale_50_names: bool = False,
) -> None:
    """Emit structured log, table, plot, summary. If scale_50_names, also write exp1_scale_50agents_*."""
    summary: list[dict] = []
    for r in results:
        s = {k: v for k, v in r.items() if k != "time_to_first_data_seconds"}
        s["time_to_first_data_seconds_count"] = len(r.get("time_to_first_data_seconds", []))
        summary.append(s)

    log_path = out_dir / f"{run_tag}_results.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump({
            "run_tag": run_tag,
            "sweep_ns": sweep_ns,
            "config": {k: v for k, v in config.items() if k != "access_headers"},
            "summary": summary,
            "full_results": results,
        }, f, indent=2)
    print(f"[exp1] Wrote {log_path}")

    # Table: p50 (median), p95, mean TTD; failed lookups; steps/query; success rate
    table_lines = [
        "| Mode | N | Mean TTD (s) | p50 TTD (s) | p95 TTD (s) | Failed lookups | Steps/query | Success rate |",
        "|------|---|--------------|-------------|-------------|----------------|-------------|--------------|",
    ]
    for r in results:
        mean_ttd = r["mean_time_to_first_data_seconds"]
        p50 = r.get("median_time_to_first_data_seconds")
        p95 = r.get("p95_time_to_first_data_seconds")
        mean_str = f"{mean_ttd:.3f}" if mean_ttd is not None else "—"
        p50_str = f"{p50:.3f}" if p50 is not None else "—"
        p95_str = f"{p95:.3f}" if p95 is not None else "—"
        table_lines.append(
            f"| {r['mode']} | {r['n']} | {mean_str} | {p50_str} | {p95_str} | {r['failed_lookups']} | {r['steps_per_query']} | {r['pct_success']:.1f}% |"
        )
    table_md = "\n".join(table_lines)
    table_path = out_dir / f"{run_tag}_table.md"
    with open(table_path, "w", encoding="utf-8") as f:
        f.write("## Experiment 1: Baseline vs Data Facts\n\n")
        f.write(table_md)
        f.write("\n")
    print(f"[exp1] Wrote {table_path}")
    if scale_50_names:
        scale_table = out_dir / "exp1_scale_50agents_table.md"
        with open(scale_table, "w", encoding="utf-8") as f:
            f.write("## Experiment 1: Discovery Efficiency — 50 agents (N=50, 200)\n\n")
            f.write(table_md)
            f.write("\n")
        print(f"[exp1] Wrote {scale_table}")

    if not no_plot and results:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ImportError:
            print("[exp1] matplotlib not installed, skipping plot")
        else:
            fig, ax = plt.subplots()
            ns = sorted({r["n"] for r in results})
            base_means = [next((r["mean_time_to_first_data_seconds"] for r in results if r["mode"] == "baseline" and r["n"] == n), None) for n in ns]
            treat_means = [next((r["mean_time_to_first_data_seconds"] for r in results if r["mode"] == "treatment" and r["n"] == n), None) for n in ns]
            x = range(len(ns))
            w = 0.35
            ax.bar([i - w / 2 for i in x], [m or 0 for m in base_means], width=w, label="Baseline", color="#2ecc71")
            ax.bar([i + w / 2 for i in x], [m or 0 for m in treat_means], width=w, label="Treatment (Data Facts)", color="#3498db")
            ax.set_xticks(x)
            ax.set_xticklabels([str(n) for n in ns])
            ax.set_ylabel("Mean time-to-first-data (seconds)")
            ax.set_xlabel("N (number of queries)")
            ax.set_title("Experiment 1: Discovery Efficiency — Time-to-First-Data vs N")
            ax.legend()
            fig.tight_layout()
            plot_path = out_dir / f"{run_tag}_plot.png"
            fig.savefig(plot_path, dpi=120)
            plt.close()
            print(f"[exp1] Wrote {plot_path}")
            if scale_50_names:
                scale_plot = out_dir / "exp1_scale_50agents_plot.png"
                fig2, ax2 = plt.subplots()
                ax2.bar([i - w / 2 for i in x], [m or 0 for m in base_means], width=w, label="Baseline", color="#2ecc71")
                ax2.bar([i + w / 2 for i in x], [m or 0 for m in treat_means], width=w, label="Treatment (Data Facts)", color="#3498db")
                ax2.set_xticks(x)
                ax2.set_xticklabels([str(n) for n in ns])
                ax2.set_ylabel("Mean time-to-first-data (seconds)")
                ax2.set_xlabel("N (number of queries)")
                ax2.set_title("Experiment 1: Discovery Efficiency — 50 agents (N=50, 200)")
                ax2.legend()
                fig2.tight_layout()
                fig2.savefig(scale_plot, dpi=120)
                plt.close()
                print(f"[exp1] Wrote {scale_plot}")

    bullets = [
        "Experiment 1 (Discovery Efficiency): N agent queries per mode (Baseline: direct dataset endpoint; Treatment: registry → data facts → dataset).",
        "Baseline: 1 step/query (direct GET); Treatment: 3 steps/query (registry → Data Facts → dataset).",
        "Metrics: time-to-first-data (mean, p50, p95), failed lookups, success rate, steps/query.",
    ]
    for r in results:
        mean_ttd = r["mean_time_to_first_data_seconds"]
        p50 = r.get("median_time_to_first_data_seconds")
        p95 = r.get("p95_time_to_first_data_seconds")
        m = r["mode"]
        if mean_ttd is not None:
            p50_str = f", p50={p50:.3f}s" if p50 is not None else ""
            p95_str = f", p95={p95:.3f}s" if p95 is not None else ""
            bullets.append(
                f"{m.capitalize()} N={r['n']}: {r['successful_retrievals']}/{r['total_queries']} successful ({r['pct_success']:.1f}%), "
                f"failed={r['failed_lookups']}, mean TTD={mean_ttd:.3f}s{p50_str}{p95_str}, steps/query={r['steps_per_query']}."
            )
        else:
            bullets.append(f"{m.capitalize()} N={r['n']}: 0% success, all {r['total_queries']} lookups failed.")
    bullets.append(f"Structured results: {log_path.name}; table: {table_path.name}.")
    if not no_plot and results:
        bullets.append(f"Plot: {run_tag}_plot.png")

    summary_path = out_dir / f"{run_tag}_summary.md"
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("# Experiment 1: Discovery Efficiency — Results Summary\n\n")
        for b in bullets:
            f.write(f"- {b}\n")
        f.write("\n## Baseline vs Data Facts\n\n")
        f.write(table_md)
        f.write("\n")
    print(f"[exp1] Wrote {summary_path}")
    if scale_50_names:
        scale_summary = out_dir / "exp1_scale_50agents_summary.md"
        with open(scale_summary, "w", encoding="utf-8") as f:
            f.write("# Experiment 1: Discovery Efficiency — 50 agents scale (paper-grade)\n\n")
            for b in bullets:
                f.write(f"- {b}\n")
            f.write("\n## Baseline vs Data Facts\n\n")
            f.write(table_md)
            f.write("\n")
        print(f"[exp1] Wrote {scale_summary}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Experiment 1: Discovery Efficiency")
    ap.add_argument("--N", type=int, help="Number of simulated agent queries (e.g. 50, 200)")
    ap.add_argument("--sweep", type=str, help="Comma-separated N values, e.g. 50,200 (runs both, then table+plot)")
    ap.add_argument("--mode", choices=["baseline", "treatment", "both"], default="both")
    ap.add_argument("--config", type=Path, default=Path(__file__).parent / "config.json")
    ap.add_argument("--out-dir", type=Path, default=Path(__file__).parent / "results")
    ap.add_argument("--debug", action="store_true", help="Verbose logging (e.g. for N=50 debug run)")
    ap.add_argument("--no-plot", action="store_true", help="Skip generating plot")
    ap.add_argument("--dry-run", action="store_true", help="No HTTP; emit mock results (table, plot, summary) for N=50,200")
    ap.add_argument(
        "--scale-50",
        action="store_true",
        help="Paper-grade 50-agent run: sweep 50,200, config_ecosystem_50.json, emit exp1_scale_50agents_* and exp1_raw.jsonl",
    )
    args = ap.parse_args()

    if args.dry_run:
        return _dry_run(args)

    if args.scale_50:
        args.config = Path(__file__).parent / "config_ecosystem_50.json"
        args.sweep = "50,200"
        sweep_ns = [50, 200]
    elif args.sweep:
        sweep_ns = [int(x.strip()) for x in args.sweep.split(",")]
    elif args.N is not None:
        sweep_ns = [args.N]
    else:
        ap.error("Provide --N, --sweep, or --scale-50")

    config = load_config(args.config)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_tag = f"exp1_sweep_{'_'.join(map(str, sweep_ns))}_{ts}" if len(sweep_ns) > 1 else f"exp1_N{sweep_ns[0]}_{ts}"

    raw_jsonl_path = args.out_dir / "exp1_raw.jsonl" if args.scale_50 else None
    raw_file = None
    if raw_jsonl_path:
        raw_file = open(raw_jsonl_path, "w", encoding="utf-8")
        raw_file.write(json.dumps({"event": "run_start", "run_tag": run_tag, "sweep_ns": sweep_ns, "scale_50": True}, ensure_ascii=True) + "\n")

    results: list[dict] = []
    try:
        for n in sweep_ns:
            if args.mode in ("baseline", "both"):
                print(f"[exp1] Baseline N={n} ...")
                r = run_baseline(config, n, args.debug, raw_jsonl_file=raw_file)
                results.append(r)
                mean_ttd = r["mean_time_to_first_data_seconds"]
                print(f"  baseline: {r['successful_retrievals']}/{r['total_queries']} success, failed={r['failed_lookups']}, mean TTD={f'{mean_ttd:.3f}s' if mean_ttd else 'N/A'}")
            if args.mode in ("treatment", "both"):
                print(f"[exp1] Treatment N={n} ...")
                r = run_treatment(config, n, args.debug, raw_jsonl_file=raw_file)
                results.append(r)
                mean_ttd = r["mean_time_to_first_data_seconds"]
                print(f"  treatment: {r['successful_retrievals']}/{r['total_queries']} success, failed={r['failed_lookups']}, mean TTD={f'{mean_ttd:.3f}s' if mean_ttd else 'N/A'}")
    finally:
        if raw_file:
            if raw_jsonl_path:
                raw_file.write(json.dumps({"event": "run_end", "run_tag": run_tag}, ensure_ascii=True) + "\n")
            raw_file.close()
            if raw_jsonl_path:
                print(f"[exp1] Wrote {raw_jsonl_path}")
                # Archive copy for paper trail
                archive_path = args.out_dir / f"exp1_raw_{ts}.jsonl"
                shutil.copy(raw_jsonl_path, archive_path)
                print(f"[exp1] Archived {archive_path}")

    _write_outputs(
        results,
        run_tag,
        config,
        args.out_dir,
        args.no_plot,
        sweep_ns if len(sweep_ns) > 1 else None,
        scale_50_names=bool(args.scale_50),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
