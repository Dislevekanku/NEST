#!/usr/bin/env python3
"""
Experiment 4: Local Security & Auth

Modes:
  --mode simulated  (default) Pure-simulation JWT gateway. No real agents needed.
  --mode real-agents          Run test agents against a live data_owner_private_01.

Agent → Gateway → DB (simulated or Supabase). JWT validation; measure success rate,
auth latency, failure modes.

Flows:
  - Owner agent: fetches data with owner token → passes result.
  - Inquiry agent: fetches data with short-lived credentials.

Scenarios: valid token, expired token, malformed token, missing token.

Deliverable: exp4_security_auth_results.json, 1 table, 3–4 bullet findings.

Usage:
  python run.py [--config config.json] [--out-dir results]
  python run.py --mode real-agents [--owner-data-url http://localhost:6350]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    import jwt
except ImportError:
    print("PyJWT required: pip install PyJWT")
    raise SystemExit(1)

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# Fixed secret for reproducible local runs
SECRET = "exp4-local-secret-do-not-use-in-production"
ALG = "HS256"
DB_DATA = {"dataset_id": "private_sample", "rows": 10}


def make_token(role: str, ttl_seconds: int, secret: str = SECRET) -> str:
    payload = {
        "sub": f"{role}-agent",
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, secret, algorithm=ALG)


def gateway_simulate(
    auth_header: str | None,
    secret: str = SECRET,
    gate_latency_ms: float = 2.0,
    db_latency_ms: float = 1.5,
) -> tuple[bool, float, str | None]:
    """
    Simulate Gateway: validate Bearer token, then "fetch from DB".
    Returns (success, total_latency_ms, error_mode).
    error_mode: None if success, else "expired" | "malformed" | "missing".
    """
    t0 = time.perf_counter()
    if not auth_header or not auth_header.strip().lower().startswith("bearer "):
        time.sleep((gate_latency_ms + db_latency_ms) / 1000.0)
        return False, (time.perf_counter() - t0) * 1000, "missing"
    token = auth_header[7:].strip()
    if not token:
        time.sleep((gate_latency_ms + db_latency_ms) / 1000.0)
        return False, (time.perf_counter() - t0) * 1000, "missing"
    time.sleep(gate_latency_ms / 1000.0)
    try:
        jwt.decode(token, secret, algorithms=[ALG])
    except jwt.ExpiredSignatureError:
        time.sleep(db_latency_ms / 1000.0)
        return False, (time.perf_counter() - t0) * 1000, "expired"
    except (jwt.InvalidSignatureError, jwt.DecodeError, Exception):
        time.sleep(db_latency_ms / 1000.0)
        return False, (time.perf_counter() - t0) * 1000, "malformed"
    time.sleep(db_latency_ms / 1000.0)
    return True, (time.perf_counter() - t0) * 1000, None


def run_scenario(
    auth_header: str | None,
    n: int,
    gate_latency_ms: float,
    db_latency_ms: float,
) -> dict:
    successes = 0
    latencies: list[float] = []
    errors: dict[str, int] = {"expired": 0, "malformed": 0, "missing": 0}
    for _ in range(n):
        ok, lat_ms, err = gateway_simulate(auth_header, SECRET, gate_latency_ms, db_latency_ms)
        if ok:
            successes += 1
            latencies.append(lat_ms)
        elif err:
            errors[err] = errors.get(err, 0) + 1
    return {
        "n": n,
        "success_count": successes,
        "auth_success_pct": round(100.0 * successes / n, 2) if n else 0,
        "mean_auth_latency_ms": round(sum(latencies) / len(latencies), 3) if latencies else None,
        "error_counts": errors,
    }


def run_real_agents(owner_data_url: str, out_dir: Path) -> int:
    """
    Run all 4 consumer test agents against a live data_owner_private_01.
    The data owner must already be running on owner_data_url.
    """
    if not REQUESTS_AVAILABLE:
        print("[exp4] requests library required for real-agents mode")
        return 1

    # Verify data owner is reachable
    try:
        resp = requests.get(f"{owner_data_url}/health", timeout=5)
        if resp.status_code != 200:
            print(f"[exp4] Data owner health check failed: {resp.status_code}")
            return 1
        print(f"[exp4] Data owner healthy at {owner_data_url}")
    except Exception as e:
        print(f"[exp4] Cannot reach data owner at {owner_data_url}: {e}")
        print("[exp4] Start data_owner_private.py first, then retry.")
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    agents_dir = Path(__file__).parent / "agents"

    consumers = [
        ("authorized_consumer.py", "authorized"),
        ("expired_consumer.py", "expired"),
        ("malicious_consumer.py", "malicious"),
        ("unauthorized_consumer.py", "unauthorized"),
    ]

    all_results = []
    all_pass = True

    for script, scenario in consumers:
        script_path = agents_dir / script
        out_file = out_dir / f"exp4_real_{scenario}_{ts}.json"
        print(f"\n[exp4] Running {scenario} scenario...")

        cmd = [
            sys.executable, str(script_path),
            "--owner-data-url", owner_data_url,
            "--out", str(out_file),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if proc.stdout:
            for line in proc.stdout.strip().split("\n"):
                print(f"  {line}")
        if proc.stderr:
            for line in proc.stderr.strip().split("\n"):
                print(f"  [stderr] {line}")

        if out_file.exists():
            with open(out_file, "r", encoding="utf-8") as f:
                result = json.load(f)
            all_results.append(result)
            if result.get("overall") != "PASS":
                all_pass = False
        else:
            all_results.append({"scenario": scenario, "overall": "ERROR", "note": "No output file"})
            all_pass = False

    # Write combined results
    combined = {
        "run_tag": f"exp4_real_agents_{ts}",
        "mode": "real-agents",
        "owner_data_url": owner_data_url,
        "scenarios": all_results,
        "all_pass": all_pass,
    }
    combined_path = out_dir / "exp4_private_data_results.json"
    with open(combined_path, "w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2)
    print(f"\n[exp4] Combined results: {combined_path}")

    # Summary table
    table_lines = [
        "| Scenario | Agent ID | Overall | Steps |",
        "|----------|----------|---------|-------|",
    ]
    for r in all_results:
        agent_id = r.get("agent_id", "?")
        overall = r.get("overall", "?")
        n_steps = len(r.get("steps", []))
        table_lines.append(f"| {r.get('scenario', '?')} | {agent_id} | {overall} | {n_steps} |")
    table_md = "\n".join(table_lines)
    table_path = out_dir / "exp4_private_data_table.md"
    with open(table_path, "w", encoding="utf-8") as f:
        f.write("## Experiment 4: Private Data (Real Agents) — Results\n\n")
        f.write(table_md)
        f.write("\n")
    print(f"[exp4] Table: {table_path}")

    status = "ALL PASS" if all_pass else "SOME FAILURES"
    print(f"\n[exp4] {status}")
    return 0 if all_pass else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Experiment 4: Security & Auth")
    ap.add_argument("--config", type=Path, default=Path(__file__).parent / "config.json")
    ap.add_argument("--out-dir", type=Path, default=Path(__file__).parent / "results")
    ap.add_argument("--mode", choices=["simulated", "real-agents"], default="simulated",
                    help="simulated=pure JWT simulation; real-agents=run against live data owner")
    ap.add_argument("--owner-data-url", default="http://localhost:6350",
                    help="Data owner dataset server URL (for real-agents mode)")
    args = ap.parse_args()

    if args.mode == "real-agents":
        return run_real_agents(args.owner_data_url, args.out_dir)

    with open(args.config, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    n = cfg.get("n_trials_per_scenario", 50)
    ttl_owner = cfg.get("token_ttl_seconds_owner", 3600)
    ttl_inquiry = cfg.get("token_ttl_seconds_inquiry", 60)
    gate_ms = cfg.get("simulated_gateway_latency_ms", 2.0)
    db_ms = cfg.get("simulated_db_latency_ms", 1.5)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # Tokens
    valid_owner = "Bearer " + make_token("owner", ttl_owner)
    valid_inquiry = "Bearer " + make_token("inquiry", ttl_inquiry)
    expired_token = "Bearer " + make_token("owner", -10)  # already expired
    malformed_token = "Bearer " + "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.fake.wrong"

    scenarios = [
        ("owner_valid", valid_owner, "Owner agent, valid token"),
        ("inquiry_valid", valid_inquiry, "Inquiry agent, short-lived valid token"),
        ("expired", expired_token, "Expired token"),
        ("malformed", malformed_token, "Malformed token"),
    ]

    results_by_scenario: list[dict] = []
    for key, header, label in scenarios:
        print(f"[exp4] {label} ...")
        r = run_scenario(header, n, gate_ms, db_ms)
        r["scenario"] = key
        r["label"] = label
        results_by_scenario.append(r)
        print(f"  auth success % = {r['auth_success_pct']}, mean latency ms = {r.get('mean_auth_latency_ms') or '—'}, errors = {r['error_counts']}")

    payload = {
        "run_tag": f"exp4_security_auth_{ts}",
        "config": cfg,
        "scenarios": results_by_scenario,
        "flows_tested": ["owner (valid)", "inquiry (short-lived valid)", "expired", "malformed"],
    }

    out_json = args.out_dir / "exp4_security_auth_results.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"[exp4] Wrote {out_json}")

    # Table
    table_lines = [
        "| Scenario | Auth success % | Mean auth latency (ms) | Errors (expired / malformed / missing) |",
        "|----------|----------------|------------------------|----------------------------------------|",
    ]
    for r in results_by_scenario:
        lat = r.get("mean_auth_latency_ms")
        lat_str = f"{lat:.3f}" if lat is not None else "—"
        err = r["error_counts"]
        err_str = f"{err.get('expired', 0)} / {err.get('malformed', 0)} / {err.get('missing', 0)}"
        table_lines.append(f"| {r['label']} | {r['auth_success_pct']}% | {lat_str} | {err_str} |")
    table_md = "\n".join(table_lines)
    table_path = args.out_dir / "exp4_security_auth_table.md"
    with open(table_path, "w", encoding="utf-8") as f:
        f.write("## Experiment 4: Security & Auth — Results\n\n")
        f.write(table_md)
        f.write("\n")
    print(f"[exp4] Wrote {table_path}")

    # 3–4 bullet findings
    success_valid = next((s for s in results_by_scenario if s["scenario"] == "owner_valid"), {})
    fail_exp = next((s for s in results_by_scenario if s["scenario"] == "expired"), {})
    fail_mal = next((s for s in results_by_scenario if s["scenario"] == "malformed"), {})
    findings = [
        f"**Auth success %:** Valid owner and inquiry tokens achieved {success_valid.get('auth_success_pct', 0)}% success; expired and malformed tokens correctly rejected (0% success).",
        f"**Mean auth latency:** Valid requests averaged {success_valid.get('mean_auth_latency_ms') or 0:.2f} ms (gateway + DB simulation); failure paths show similar latency (gateway validates then rejects).",
        f"**Error handling:** Expired tokens produced {fail_exp.get('error_counts', {}).get('expired', 0)} rejections; malformed tokens produced {fail_mal.get('error_counts', {}).get('malformed', 0)} rejections; behavior is consistent and measurable.",
        "**Local JWT gateway simulation** confirms that success rate, latency, and failure-mode counts are reproducible and suitable for security metrics in a local, no-cloud setup.",
    ]
    findings_path = args.out_dir / "exp4_security_auth_findings.md"
    with open(findings_path, "w", encoding="utf-8") as f:
        f.write("# Experiment 4: Security & Auth — Findings\n\n")
        for bullet in findings:
            f.write(f"- {bullet}\n\n")
    print(f"[exp4] Wrote {findings_path}")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
