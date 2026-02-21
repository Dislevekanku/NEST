#!/usr/bin/env python3
"""
Experiment 4 — Full Execution: A/B/C

Runs all three sub-experiments against a live data_owner_private_01:
  A. Authentication & Access Control  (valid creds, missing creds, unintended access)
  B. TTL & Revocation                 (within TTL, after TTL, stale access)
  C. Misuse / Malicious Agent         (token reuse, wrong agent, altered claims)

Requires data_owner_private.py running on --data-port (default 6350).

Usage:
  python run_experiments_abc.py [--owner-data-url http://localhost:6350] [--trials 20]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import requests

try:
    import jwt as pyjwt
except ImportError:
    print("PyJWT required: pip install PyJWT")
    sys.exit(1)

from dotenv import load_dotenv
load_dotenv()

JWT_SECRET = os.environ.get("NEST_JWT_SECRET", "nest-local-dev-secret")
WRONG_SECRET = "this-is-not-the-real-secret"


# ── helpers ──────────────────────────────────────────────────────────────

def discover_agent_via_registry(registry_url: str, agent_id: str) -> dict | None:
    """Step 1: Query registry to find agent card (agent_url, agentFactsURL)."""
    try:
        r = requests.get(f"{registry_url}/lookup/{agent_id}", timeout=10)
        if r.status_code == 200:
            return r.json()
        return None
    except Exception:
        return None


def query_agent_a2a(agent_url: str) -> dict | None:
    """Step 2: Send A2A message to agent asking for dataset info.

    Returns dict with data_facts_url, dataset_id extracted from response.
    """
    try:
        from python_a2a import A2AClient, Message, MessageRole, TextContent
        client = A2AClient(f"{agent_url}/a2a", timeout=15)
        resp = client.send_message(
            Message(role=MessageRole.USER, content=TextContent(text="What dataset do you serve?"))
        )
        text = resp.content.text if hasattr(resp.content, "text") else str(resp.content)
        # Parse data_facts_url from response
        import re
        url_match = re.search(r"Data Facts:\s*(http[^\s]+)", text)
        data_facts_url = url_match.group(1) if url_match else None
        return {"raw_response": text, "data_facts_url": data_facts_url}
    except Exception as e:
        return {"raw_response": str(e), "data_facts_url": None}


def fetch_data_facts_url(data_facts_url: str) -> dict | None:
    """Fetch Data Facts from a full URL."""
    try:
        r = requests.get(data_facts_url, timeout=10)
        if r.status_code == 200:
            return r.json()
        return None
    except Exception:
        return None


def fetch_data_facts(base_url: str, dataset_id: str) -> dict | None:
    """GET /data_facts/{dataset_id}.json → Data Facts metadata.

    Returns dict with keys: access_type, endpoint, dataset_id, evidence, etc.
    Returns None on failure.
    """
    url = f"{base_url}/data_facts/{dataset_id}.json"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return r.json()
        return None
    except Exception:
        return None


def negotiate(base_url: str, consumer_id: str, ttl: int = 60) -> dict | None:
    """POST /negotiate_access → {access_granted, token, ttl_seconds}"""
    try:
        r = requests.post(
            f"{base_url}/negotiate_access",
            json={"consumer_agent_id": consumer_id, "ttl_seconds": ttl},
            timeout=10,
        )
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None


def fetch_with_token(base_url: str, route: str, token: str | None) -> tuple[int, float, dict | None]:
    """GET dataset endpoint; returns (status_code, latency_ms, body_or_none)."""
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    t0 = time.perf_counter()
    try:
        r = requests.get(f"{base_url}/{route}", headers=headers, timeout=10)
        lat = (time.perf_counter() - t0) * 1000
        body = r.json() if r.headers.get("content-type", "").startswith("application/json") else None
        return r.status_code, lat, body
    except Exception as e:
        lat = (time.perf_counter() - t0) * 1000
        return 0, lat, {"error": str(e)}


def verify_checksum(body: dict | None, expected_checksum: str | None) -> bool:
    """Verify dataset checksum against Data Facts evidence.

    Matches provider.compute_checksum(): excludes 'timestamp', then
    SHA256 of sorted JSON.
    """
    if not body or not expected_checksum:
        return False
    import hashlib
    data_copy = {k: v for k, v in body.items() if k != "timestamp"}
    serialized = json.dumps(data_copy, sort_keys=True).encode("utf-8")
    computed = hashlib.sha256(serialized).hexdigest()
    return computed == expected_checksum


def make_forged_token(consumer_id: str, dataset_id: str, secret: str, ttl: int = 3600) -> str:
    now = datetime.now(timezone.utc)
    return pyjwt.encode(
        {"sub": consumer_id, "role": "inquiry", "scope": "read",
         "dataset_id": dataset_id, "exp": now + timedelta(seconds=ttl), "iat": now},
        secret, algorithm="HS256",
    )


def make_altered_claims_token(consumer_id: str, ttl: int = 3600) -> str:
    """Valid signature but wrong dataset_id claim."""
    now = datetime.now(timezone.utc)
    return pyjwt.encode(
        {"sub": consumer_id, "role": "admin", "scope": "write",
         "dataset_id": "nonexistent_dataset", "exp": now + timedelta(seconds=ttl), "iat": now},
        JWT_SECRET, algorithm="HS256",
    )


# ── Experiment A: Authentication & Access Control ────────────────────────

def run_experiment_a(base_url: str, route: str, n: int, dataset_id: str = "private_employee_records") -> dict:
    """
    A1: Full discovery flow (Data Facts → check access_type → negotiate → fetch → verify checksum)
    A2: Missing credentials (no header)
    A3: Empty Authorization header
    A4: Bearer prefix only (no token)
    """
    results = {"experiment": "A", "title": "Authentication & Access Control", "trials": n, "scenarios": {}}

    # A1: Valid credentials — full Data Facts discovery flow
    a1 = {"successes": 0, "failures": 0, "latencies_ms": [], "row_counts": [],
           "discovery_ok": 0, "checksum_ok": 0, "discovery_latencies_ms": []}
    for _ in range(n):
        # Step 1: Fetch Data Facts
        t0 = time.perf_counter()
        df = fetch_data_facts(base_url, dataset_id)
        df_lat = (time.perf_counter() - t0) * 1000
        if not df:
            a1["failures"] += 1
            continue
        a1["discovery_ok"] += 1
        a1["discovery_latencies_ms"].append(round(df_lat, 2))

        # Step 2: Check access_type → decide auth flow
        access_type = df.get("access_type", "public")
        expected_checksum = (df.get("evidence") or {}).get("checksum_sha256")

        # Step 3: If semi-private, negotiate access
        token = None
        if access_type in ("semi-private", "private"):
            neg = negotiate(base_url, "exp_a_valid_consumer")
            if not neg or not neg.get("token"):
                a1["failures"] += 1
                continue
            token = neg["token"]

        # Step 4: Fetch dataset with token
        code, lat, body = fetch_with_token(base_url, route, token)
        if code == 200 and body and body.get("row_count", 0) > 0:
            a1["successes"] += 1
            a1["latencies_ms"].append(round(lat, 2))
            a1["row_counts"].append(body["row_count"])
            # Step 5: Verify checksum
            if verify_checksum(body, expected_checksum):
                a1["checksum_ok"] += 1
        else:
            a1["failures"] += 1
    a1["success_rate"] = round(100 * a1["successes"] / n, 2) if n else 0
    a1["mean_latency_ms"] = round(sum(a1["latencies_ms"]) / len(a1["latencies_ms"]), 2) if a1["latencies_ms"] else None
    a1["mean_discovery_latency_ms"] = round(sum(a1["discovery_latencies_ms"]) / len(a1["discovery_latencies_ms"]), 2) if a1["discovery_latencies_ms"] else None
    results["scenarios"]["A1_valid_credentials"] = a1

    # A2: Missing credentials (no header at all)
    a2 = {"blocked": 0, "leaked": 0, "status_codes": {}}
    for _ in range(n):
        code, lat, body = fetch_with_token(base_url, route, None)
        a2["status_codes"][str(code)] = a2["status_codes"].get(str(code), 0) + 1
        if code == 401:
            a2["blocked"] += 1
        else:
            a2["leaked"] += 1
    a2["block_rate"] = round(100 * a2["blocked"] / n, 2) if n else 0
    a2["unintended_access"] = a2["leaked"] > 0
    results["scenarios"]["A2_missing_credentials"] = a2

    # A3: Empty Authorization header
    a3 = {"blocked": 0, "leaked": 0, "status_codes": {}}
    for _ in range(n):
        headers = {"Authorization": ""}
        t0 = time.perf_counter()
        r = requests.get(f"{base_url}/{route}", headers=headers, timeout=10)
        code = r.status_code
        a3["status_codes"][str(code)] = a3["status_codes"].get(str(code), 0) + 1
        if code == 401:
            a3["blocked"] += 1
        else:
            a3["leaked"] += 1
    a3["block_rate"] = round(100 * a3["blocked"] / n, 2) if n else 0
    a3["unintended_access"] = a3["leaked"] > 0
    results["scenarios"]["A3_empty_auth_header"] = a3

    # A4: Bearer prefix with no token
    a4 = {"blocked": 0, "leaked": 0, "status_codes": {}}
    for _ in range(n):
        headers = {"Authorization": "Bearer "}
        r = requests.get(f"{base_url}/{route}", headers=headers, timeout=10)
        code = r.status_code
        a4["status_codes"][str(code)] = a4["status_codes"].get(str(code), 0) + 1
        if code == 401:
            a4["blocked"] += 1
        else:
            a4["leaked"] += 1
    a4["block_rate"] = round(100 * a4["blocked"] / n, 2) if n else 0
    a4["unintended_access"] = a4["leaked"] > 0
    results["scenarios"]["A4_bearer_no_token"] = a4

    return results


# ── Experiment B: TTL & Revocation ────────────────────────────────────────

def run_experiment_b(base_url: str, route: str, n: int) -> dict:
    """
    B1: Access within TTL (token fresh)
    B2: Access after TTL expiry (token expired)
    B3: Boundary test (request at TTL edge)
    """
    results = {"experiment": "B", "title": "TTL & Revocation", "trials": n, "scenarios": {}}

    # B1: Access within TTL (TTL=30s, use immediately)
    b1 = {"successes": 0, "failures": 0, "latencies_ms": []}
    for _ in range(n):
        neg = negotiate(base_url, "exp_b_fresh_consumer", ttl=30)
        if not neg or not neg.get("token"):
            b1["failures"] += 1
            continue
        code, lat, body = fetch_with_token(base_url, route, neg["token"])
        if code == 200:
            b1["successes"] += 1
            b1["latencies_ms"].append(round(lat, 2))
        else:
            b1["failures"] += 1
    b1["success_rate"] = round(100 * b1["successes"] / n, 2) if n else 0
    b1["mean_latency_ms"] = round(sum(b1["latencies_ms"]) / len(b1["latencies_ms"]), 2) if b1["latencies_ms"] else None
    results["scenarios"]["B1_within_ttl"] = b1

    # B2: Access after TTL expiry (TTL=2s, wait 3s)
    b2 = {"expired_rejected": 0, "stale_access": 0, "latencies_ms": []}
    for i in range(n):
        neg = negotiate(base_url, "exp_b_expired_consumer", ttl=2)
        if not neg or not neg.get("token"):
            continue
        # Wait for expiry
        time.sleep(3)
        code, lat, body = fetch_with_token(base_url, route, neg["token"])
        b2["latencies_ms"].append(round(lat, 2))
        if code == 401:
            b2["expired_rejected"] += 1
        else:
            b2["stale_access"] += 1
        # Print progress for long-running test
        print(f"    B2 trial {i+1}/{n}: {'rejected' if code == 401 else f'STALE ACCESS ({code})'}")
    b2["rejection_rate"] = round(100 * b2["expired_rejected"] / n, 2) if n else 0
    b2["stale_access_detected"] = b2["stale_access"] > 0
    results["scenarios"]["B2_after_ttl_expiry"] = b2

    # B3: Boundary — TTL=10s, use at t=2s (should work) then wait past exp (should fail)
    # Note: TTL=3s is impractical due to ~2s Flask/Supabase server latency;
    # the negotiate round-trip alone consumes most of a 3s TTL.
    b3 = {"within_boundary_ok": 0, "past_boundary_rejected": 0, "boundary_failures": 0,
           "ttl_used": 10, "note": ""}
    boundary_trials = min(n, 5)  # fewer trials since each takes ~12s
    for i in range(boundary_trials):
        neg = negotiate(base_url, "exp_b_boundary_consumer", ttl=10)
        if not neg or not neg.get("token"):
            b3["boundary_failures"] += 1
            continue
        token = neg["token"]
        # At t=2s after receiving token (well within TTL=10s)
        time.sleep(2)
        code1, _, _ = fetch_with_token(base_url, route, token)
        if code1 == 200:
            b3["within_boundary_ok"] += 1
        # Wait until past TTL (sleep 9s more, total ~11s from issue)
        time.sleep(9)
        code2, _, _ = fetch_with_token(base_url, route, token)
        if code2 == 401:
            b3["past_boundary_rejected"] += 1
        print(f"    B3 trial {i+1}/{boundary_trials}: t=2s->{code1}, t=11s->{code2}")
    b3["note"] = ("TTL=10s used instead of 3s; short TTLs (<5s) are impractical when "
                  "server latency (~2s) consumes most of the token lifetime.")
    results["scenarios"]["B3_ttl_boundary"] = b3

    return results


# ── Experiment C: Misuse / Malicious Agent ─────────────────────────────────

def run_experiment_c(base_url: str, route: str, n: int) -> dict:
    """
    C1: Token reuse (same token, multiple requests)
    C2: Token from wrong secret (forgery)
    C3: Garbage / malformed token
    C4: Altered claims (wrong dataset_id)
    C5: Token issued to agent A used by agent B (impersonation)
    """
    results = {"experiment": "C", "title": "Misuse / Malicious Agent", "trials": n, "scenarios": {}}

    # C1: Token reuse — same valid token used multiple times
    c1 = {"requests": 0, "successes": 0, "failures": 0}
    neg = negotiate(base_url, "exp_c_reuse_consumer", ttl=60)
    if neg and neg.get("token"):
        token = neg["token"]
        for _ in range(n):
            code, _, body = fetch_with_token(base_url, route, token)
            c1["requests"] += 1
            if code == 200:
                c1["successes"] += 1
            else:
                c1["failures"] += 1
    c1["note"] = "Token reuse within TTL is expected to succeed (stateless JWT, no revocation list in v1)"
    results["scenarios"]["C1_token_reuse"] = c1

    # C2: Forged token (wrong secret)
    c2 = {"blocked": 0, "leaked": 0}
    for _ in range(n):
        forged = make_forged_token("exp_c_forger", "private_employee_records", WRONG_SECRET)
        code, _, _ = fetch_with_token(base_url, route, forged)
        if code == 401:
            c2["blocked"] += 1
        else:
            c2["leaked"] += 1
    c2["block_rate"] = round(100 * c2["blocked"] / n, 2) if n else 0
    c2["data_leaked"] = c2["leaked"] > 0
    results["scenarios"]["C2_forged_wrong_secret"] = c2

    # C3: Garbage / malformed tokens
    garbage_tokens = [
        "not-a-jwt-at-all",
        "eyJhbGciOiJIUzI1NiJ9.fake-payload.wrong-sig",
        "",
        "Bearer eyJhbGciOiJIUzI1NiJ9",  # double Bearer
        "null",
        "undefined",
    ]
    c3 = {"blocked": 0, "leaked": 0, "per_token": []}
    for gt in garbage_tokens:
        code, lat, _ = fetch_with_token(base_url, route, gt)
        entry = {"token_preview": gt[:40], "status_code": code, "latency_ms": round(lat, 2)}
        c3["per_token"].append(entry)
        if code == 401:
            c3["blocked"] += 1
        else:
            c3["leaked"] += 1
    c3["block_rate"] = round(100 * c3["blocked"] / len(garbage_tokens), 2)
    c3["data_leaked"] = c3["leaked"] > 0
    results["scenarios"]["C3_malformed_garbage"] = c3

    # C4: Altered claims (valid signature, wrong dataset_id)
    c4 = {"blocked": 0, "leaked": 0}
    for _ in range(n):
        altered = make_altered_claims_token("exp_c_altered_claims")
        code, _, body = fetch_with_token(base_url, route, altered)
        if code == 401:
            c4["blocked"] += 1
        else:
            c4["leaked"] += 1
    c4["block_rate"] = round(100 * c4["blocked"] / n, 2) if n else 0
    c4["data_leaked"] = c4["leaked"] > 0
    c4["note"] = "Token has valid signature but claims dataset_id=nonexistent_dataset, role=admin, scope=write"
    results["scenarios"]["C4_altered_claims"] = c4

    # C5: Impersonation — token issued to agent A, used by agent B
    c5 = {"requests": 0, "successes": 0, "failures": 0}
    neg_a = negotiate(base_url, "agent_alice", ttl=60)
    if neg_a and neg_a.get("token"):
        token_a = neg_a["token"]
        # "agent_bob" uses agent_alice's token (impersonation)
        for _ in range(n):
            code, _, body = fetch_with_token(base_url, route, token_a)
            c5["requests"] += 1
            if code == 200:
                c5["successes"] += 1
            else:
                c5["failures"] += 1
    c5["note"] = ("v1 JWT is stateless and does not bind to caller IP/identity at request time. "
                  "Token passed to another agent succeeds within TTL. "
                  "Mitigation: add audience/fingerprint claims in v2.")
    results["scenarios"]["C5_impersonation"] = c5

    return results


# ── Main ──────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description="Exp4 Full Execution: A/B/C")
    ap.add_argument("--owner-data-url", default="http://localhost:6350")
    ap.add_argument("--registry-url", default="http://registry.chat39.com:6900")
    ap.add_argument("--agent-id", default="data_owner_private_01")
    ap.add_argument("--trials", type=int, default=20, help="Trials per scenario")
    ap.add_argument("--out-dir", type=Path, default=Path(__file__).parent / "results")
    args = ap.parse_args()

    dataset_id = "private_employee_records"
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    args.out_dir.mkdir(parents=True, exist_ok=True)

    pipeline = {}

    # ── Step 1: Registry Discovery ──
    print(f"[exp4] Step 1: Registry lookup for '{args.agent_id}'...")
    t0 = time.perf_counter()
    agent_card = discover_agent_via_registry(args.registry_url, args.agent_id)
    registry_lat = (time.perf_counter() - t0) * 1000
    if not agent_card:
        print(f"[exp4] FAILED: Agent not found in registry")
        return 1
    agent_url = agent_card.get("agent_url", "")
    agent_facts_url = agent_card.get("agentFactsURL", "")
    print(f"[exp4]   agent_url: {agent_url}")
    print(f"[exp4]   agentFactsURL: {agent_facts_url}")
    print(f"[exp4]   registry_latency: {registry_lat:.0f}ms")
    pipeline["registry"] = {"agent_url": agent_url, "agentFactsURL": agent_facts_url,
                             "latency_ms": round(registry_lat, 2)}

    # ── Step 2: A2A Query ──
    print(f"\n[exp4] Step 2: A2A query to {agent_url} for dataset info...")
    t0 = time.perf_counter()
    a2a_result = query_agent_a2a(agent_url)
    a2a_lat = (time.perf_counter() - t0) * 1000
    data_facts_url = (a2a_result or {}).get("data_facts_url")
    if not data_facts_url:
        print(f"[exp4] WARNING: A2A did not return data_facts_url, falling back to direct URL")
        data_facts_url = f"{args.owner_data_url}/data_facts/{dataset_id}.json"
    print(f"[exp4]   data_facts_url: {data_facts_url}")
    print(f"[exp4]   a2a_latency: {a2a_lat:.0f}ms")
    pipeline["a2a"] = {"data_facts_url": data_facts_url, "latency_ms": round(a2a_lat, 2),
                        "raw_response": (a2a_result or {}).get("raw_response", "")}

    # ── Step 3: Fetch Data Facts ──
    print(f"\n[exp4] Step 3: Fetching Data Facts from {data_facts_url}...")
    t0 = time.perf_counter()
    df = fetch_data_facts_url(data_facts_url)
    df_lat = (time.perf_counter() - t0) * 1000
    if not df:
        print(f"[exp4] FAILED: Could not fetch Data Facts")
        return 1
    access_type = df.get("access_type", "unknown")
    endpoint = df.get("endpoint", "")
    route = endpoint.rstrip("/").split("/")[-1] if endpoint else "private-employee-records"
    checksum = (df.get("evidence") or {}).get("checksum_sha256", "N/A")
    # Derive base_url from the data_facts_url (same host:port as dataset server)
    from urllib.parse import urlparse
    parsed = urlparse(data_facts_url)
    data_base_url = f"{parsed.scheme}://{parsed.netloc}"
    print(f"[exp4]   access_type: {access_type}")
    print(f"[exp4]   endpoint: {endpoint}")
    print(f"[exp4]   route: /{route}")
    print(f"[exp4]   checksum: {checksum[:16]}...")
    print(f"[exp4]   data_facts_latency: {df_lat:.0f}ms")
    pipeline["data_facts"] = {"access_type": access_type, "endpoint": endpoint,
                               "dataset_id": dataset_id, "checksum": checksum,
                               "latency_ms": round(df_lat, 2)}

    # ── Step 4: Health check on dataset server ──
    print(f"\n[exp4] Step 4: Health check on {data_base_url}...")
    try:
        r = requests.get(f"{data_base_url}/health", timeout=5)
        assert r.status_code == 200
        print(f"[exp4]   Data owner healthy")
    except Exception as e:
        print(f"[exp4] FAILED: {e}")
        return 1

    total_discovery = registry_lat + a2a_lat + df_lat
    print(f"\n[exp4] Full pipeline discovery: {total_discovery:.0f}ms "
          f"(registry={registry_lat:.0f} + a2a={a2a_lat:.0f} + data_facts={df_lat:.0f})")

    all_results = {"pipeline": pipeline, "data_facts": pipeline["data_facts"]}

    # ── Experiment A ──
    print(f"\n{'='*60}")
    print(f"  EXPERIMENT A: Authentication & Access Control ({args.trials} trials)")
    print(f"{'='*60}")
    exp_a = run_experiment_a(data_base_url, route, args.trials, dataset_id=dataset_id)
    all_results["A"] = exp_a
    for key, s in exp_a["scenarios"].items():
        sr = s.get("success_rate") or s.get("block_rate", "?")
        print(f"  {key}: {sr}%")

    # ── Experiment B ──
    print(f"\n{'='*60}")
    print(f"  EXPERIMENT B: TTL & Revocation ({args.trials} trials)")
    print(f"{'='*60}")
    exp_b = run_experiment_b(data_base_url, route, args.trials)
    all_results["B"] = exp_b
    for key, s in exp_b["scenarios"].items():
        sr = s.get("success_rate") or s.get("rejection_rate", "?")
        print(f"  {key}: {sr}%")

    # ── Experiment C ──
    print(f"\n{'='*60}")
    print(f"  EXPERIMENT C: Misuse / Malicious Agent ({args.trials} trials)")
    print(f"{'='*60}")
    exp_c = run_experiment_c(data_base_url, route, args.trials)
    all_results["C"] = exp_c
    for key, s in exp_c["scenarios"].items():
        sr = s.get("block_rate", s.get("successes", "?"))
        print(f"  {key}: {sr}")

    # ── Save raw results ──
    raw_path = args.out_dir / f"exp4_abc_raw_{ts}.json"
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump({"run_tag": f"exp4_abc_{ts}", "trials": args.trials, "experiments": all_results}, f, indent=2)
    print(f"\n[exp4] Raw results: {raw_path}")

    # ── Generate table ──
    table = generate_table(all_results)
    table_path = args.out_dir / f"exp4_abc_table_{ts}.md"
    with open(table_path, "w", encoding="utf-8") as f:
        f.write(table)
    print(f"[exp4] Table: {table_path}")

    # ── Generate notes ──
    notes = generate_notes(all_results, args.trials)
    notes_path = args.out_dir / f"exp4_abc_notes_{ts}.md"
    with open(notes_path, "w", encoding="utf-8") as f:
        f.write(notes)
    print(f"[exp4] Notes: {notes_path}")

    # ── Final verdict ──
    leaked = any_leakage(all_results)
    status = "PASS (no unintended access)" if not leaked else "FAIL (data leakage detected)"
    print(f"\n[exp4] Final: {status}")
    return 0 if not leaked else 1


def any_leakage(results: dict) -> bool:
    for exp_key, exp in results.items():
        for s_key, s in exp.get("scenarios", {}).items():
            if s.get("unintended_access") or s.get("data_leaked") or s.get("stale_access_detected"):
                return True
            if s.get("leaked", 0) > 0:
                return True
    return False


def generate_table(results: dict) -> str:
    df_info = results.get("data_facts", {})
    pipe = results.get("pipeline", {})
    lines = ["# Experiment 4: Security & Auth — Full Results\n"]
    if pipe:
        reg = pipe.get("registry", {})
        a2a = pipe.get("a2a", {})
        dff = pipe.get("data_facts", {})
        total = reg.get("latency_ms", 0) + a2a.get("latency_ms", 0) + dff.get("latency_ms", 0)
        lines.append(f"**Pipeline:** Registry ({reg.get('latency_ms', '?')}ms) -> "
                     f"A2A ({a2a.get('latency_ms', '?')}ms) -> "
                     f"Data Facts ({dff.get('latency_ms', '?')}ms) = "
                     f"{total:.0f}ms total")
        lines.append(f"**access_type:** {dff.get('access_type', 'N/A')} | "
                     f"**dataset:** {dff.get('dataset_id', 'N/A')}\n")
    elif df_info:
        lines.append(f"**Discovery method:** Data Facts v1 | "
                     f"**access_type:** {df_info.get('access_type', 'N/A')} | "
                     f"**dataset:** {df_info.get('dataset_id', 'N/A')}\n")
    lines += [
        "## Experiment A: Authentication & Access Control\n",
        "| Scenario | Trials | Success/Block Rate | Unintended Access | Checksum | Mean Latency |",
        "|----------|--------|--------------------|-------------------|----------|--------------|",
    ]
    for key, s in results["A"]["scenarios"].items():
        trials = s.get("successes", 0) + s.get("failures", 0) + s.get("blocked", 0) + s.get("leaked", 0)
        rate = s.get("success_rate") or s.get("block_rate", "N/A")
        unintended = "YES" if s.get("unintended_access") or s.get("leaked", 0) > 0 else "No"
        chk = f"{s['checksum_ok']}/{s['successes']}" if s.get("checksum_ok") is not None else "N/A"
        lat = f"{s['mean_latency_ms']:.1f}ms" if s.get("mean_latency_ms") else "N/A"
        lines.append(f"| {key} | {trials} | {rate}% | {unintended} | {chk} | {lat} |")

    lines += [
        "\n## Experiment B: TTL & Revocation\n",
        "| Scenario | Trials | Rate | Stale Access | Mean Latency |",
        "|----------|--------|------|--------------|--------------|",
    ]
    for key, s in results["B"]["scenarios"].items():
        if "success_rate" in s:
            trials = s.get("successes", 0) + s.get("failures", 0)
            rate = f"{s['success_rate']}% success"
        elif "rejection_rate" in s:
            trials = s.get("expired_rejected", 0) + s.get("stale_access", 0)
            rate = f"{s['rejection_rate']}% rejected"
        else:
            trials = s.get("within_boundary_ok", 0) + s.get("past_boundary_rejected", 0)
            rate = f"{s.get('within_boundary_ok', 0)} ok / {s.get('past_boundary_rejected', 0)} rejected"
        stale = "YES" if s.get("stale_access_detected") or s.get("stale_access", 0) > 0 else "No"
        lat = f"{s['mean_latency_ms']:.1f}ms" if s.get("mean_latency_ms") else "N/A"
        lines.append(f"| {key} | {trials} | {rate} | {stale} | {lat} |")

    lines += [
        "\n## Experiment C: Misuse / Malicious Agent\n",
        "| Scenario | Trials | Block Rate | Data Leaked | Note |",
        "|----------|--------|------------|-------------|------|",
    ]
    for key, s in results["C"]["scenarios"].items():
        if "block_rate" in s:
            trials = s.get("blocked", 0) + s.get("leaked", 0)
            rate = f"{s['block_rate']}%"
            leaked = "YES" if s.get("data_leaked") else "No"
        else:
            trials = s.get("requests", 0)
            rate = f"{s.get('successes', 0)}/{trials} pass"
            leaked = "N/A"
        note = (s.get("note") or "")[:60]
        lines.append(f"| {key} | {trials} | {rate} | {leaked} | {note} |")

    return "\n".join(lines) + "\n"


def generate_notes(results: dict, n: int) -> str:
    df_info = results.get("data_facts", {})
    pipe = results.get("pipeline", {})
    lines = [
        "# Experiment 4: Security & Auth — Notes\n",
        f"**Date:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"**Trials per scenario:** {n}",
        f"**Data owner:** localhost:6350 (Supabase: private_employee_records, 20 rows)",
    ]
    if pipe:
        reg = pipe.get("registry", {})
        a2a = pipe.get("a2a", {})
        dff = pipe.get("data_facts", {})
        total = reg.get("latency_ms", 0) + a2a.get("latency_ms", 0) + dff.get("latency_ms", 0)
        lines.append("")
        lines.append("### Discovery Pipeline")
        lines.append(f"- **Step 1 - Registry:** Lookup agent -> agent_url={reg.get('agent_url', 'N/A')} ({reg.get('latency_ms', 'N/A')}ms)")
        lines.append(f"- **Step 2 - A2A:** Query agent -> data_facts_url ({a2a.get('latency_ms', 'N/A')}ms)")
        lines.append(f"- **Step 3 - Data Facts:** access_type={dff.get('access_type', 'N/A')}, checksum={dff.get('checksum', 'N/A')[:16]}... ({dff.get('latency_ms', 'N/A')}ms)")
        lines.append(f"- **Total discovery:** {total:.0f}ms")
    elif df_info:
        lines.append(f"**Discovery:** Data Facts v1 (access_type={df_info.get('access_type', 'N/A')}, "
                     f"checksum={df_info.get('checksum', 'N/A')[:16]}...)")
    lines.append("")
    lines.append("## Experiment A: Authentication & Access Control\n")

    a = results["A"]["scenarios"]
    a1 = a["A1_valid_credentials"]
    discovery_note = ""
    if a1.get("discovery_ok"):
        discovery_note = (f" Data Facts discovery: {a1['discovery_ok']}/{n} OK"
                         f" ({a1.get('mean_discovery_latency_ms', 'N/A')}ms avg).")
    checksum_note = ""
    if a1.get("checksum_ok") is not None:
        checksum_note = f" Checksum verified: {a1['checksum_ok']}/{a1['successes']}."
    lines.append(f"- **Valid credentials (full discovery flow):** {a1['success_rate']}% success ({a1['successes']}/{n}). "
                 f"Mean fetch latency {a1.get('mean_latency_ms', 'N/A')}ms."
                 f"{discovery_note}{checksum_note}")
    a2 = a["A2_missing_credentials"]
    lines.append(f"- **Missing credentials:** {a2['block_rate']}% blocked. "
                 f"Error type: HTTP {list(a2['status_codes'].keys())}. "
                 f"Unintended access: {'YES' if a2['unintended_access'] else 'None'}.")
    a3 = a["A3_empty_auth_header"]
    lines.append(f"- **Empty auth header:** {a3['block_rate']}% blocked. "
                 f"Unintended access: {'YES' if a3['unintended_access'] else 'None'}.")
    a4 = a["A4_bearer_no_token"]
    lines.append(f"- **Bearer prefix only:** {a4['block_rate']}% blocked. "
                 f"Unintended access: {'YES' if a4['unintended_access'] else 'None'}.")

    lines += ["\n## Experiment B: TTL & Revocation\n"]
    b = results["B"]["scenarios"]
    b1 = b["B1_within_ttl"]
    lines.append(f"- **Within TTL:** {b1['success_rate']}% success. Fresh tokens work reliably.")
    b2 = b["B2_after_ttl_expiry"]
    lines.append(f"- **After TTL expiry:** {b2['rejection_rate']}% correctly rejected. "
                 f"Stale access: {'YES' if b2['stale_access_detected'] else 'None detected'}.")
    b3 = b["B3_ttl_boundary"]
    ttl = b3.get("ttl_used", 10)
    lines.append(f"- **Boundary test (TTL={ttl}s):** {b3['within_boundary_ok']} OK at t=2s, "
                 f"{b3['past_boundary_rejected']} rejected at t=11s.")
    if b3.get("note"):
        lines.append(f"  - *Note:* {b3['note']}")

    lines += ["\n## Experiment C: Misuse / Malicious Agent\n"]
    c = results["C"]["scenarios"]
    c1 = c["C1_token_reuse"]
    lines.append(f"- **Token reuse:** {c1['successes']}/{c1['requests']} succeeded within TTL. "
                 f"Expected (stateless JWT, no revocation in v1).")
    c2 = c["C2_forged_wrong_secret"]
    lines.append(f"- **Forged token (wrong secret):** {c2['block_rate']}% blocked. "
                 f"Data leaked: {'YES' if c2['data_leaked'] else 'No'}.")
    c3 = c["C3_malformed_garbage"]
    lines.append(f"- **Malformed/garbage tokens:** {c3['block_rate']}% blocked ({c3['blocked']}/{len(c3['per_token'])}). "
                 f"Data leaked: {'YES' if c3['data_leaked'] else 'No'}.")
    c4 = c["C4_altered_claims"]
    lines.append(f"- **Altered claims (wrong dataset_id):** {c4['block_rate']}% blocked. "
                 f"Data leaked: {'YES' if c4['data_leaked'] else 'No'}.")
    c5 = c["C5_impersonation"]
    lines.append(f"- **Impersonation (agent B uses agent A's token):** "
                 f"{c5['successes']}/{c5['requests']} succeeded. "
                 f"v1 JWT is stateless; mitigation planned for v2 (audience claims).")

    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys.exit(main())
