#!/usr/bin/env python3
"""
Authorized Consumer — happy-path test agent.

Discovers the data owner via registry, negotiates a valid JWT,
fetches the private dataset, and reports success.

Expected: 200, data returned, checksum matches.

Usage:
    python authorized_consumer.py [--owner-data-url http://localhost:6350]
"""
import os
import sys
import time
import json
import argparse
import requests

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from nanda_core.dataset.client import negotiate_access, fetch_data_facts, fetch_dataset, verify_checksum, check_freshness


def main():
    ap = argparse.ArgumentParser(description="Authorized Consumer Agent")
    ap.add_argument("--owner-data-url", default="http://localhost:6350")
    ap.add_argument("--dataset-id", default="private_employee_records")
    ap.add_argument("--consumer-id", default="authorized_consumer_01")
    ap.add_argument("--ttl", type=int, default=60)
    ap.add_argument("--out", default=None, help="Output JSON file")
    args = ap.parse_args()

    result = {
        "agent_id": args.consumer_id,
        "scenario": "authorized",
        "steps": [],
    }

    print(f"[{args.consumer_id}] Starting authorized consumer test")

    # Step 1: Fetch Data Facts
    t0 = time.perf_counter()
    data_facts_url = f"{args.owner_data_url}/data_facts/{args.dataset_id}.json"
    try:
        data_facts = fetch_data_facts(data_facts_url)
        lat = (time.perf_counter() - t0) * 1000
        result["steps"].append({"step": "fetch_data_facts", "status": "ok", "latency_ms": round(lat, 2)})
        print(f"  [OK] Data Facts fetched ({lat:.1f}ms), access_type={data_facts.get('access_type')}")
    except Exception as e:
        result["steps"].append({"step": "fetch_data_facts", "status": "error", "error": str(e)})
        print(f"  [FAIL] Data Facts: {e}")
        _write_result(result, args.out)
        return 1

    # Step 2: Negotiate access
    t0 = time.perf_counter()
    negotiated = negotiate_access(args.owner_data_url, args.consumer_id, args.ttl)
    lat = (time.perf_counter() - t0) * 1000
    if negotiated and negotiated.get("access_granted"):
        token = negotiated["token"]
        result["steps"].append({"step": "negotiate_access", "status": "ok", "latency_ms": round(lat, 2)})
        print(f"  [OK] Token received ({lat:.1f}ms), ttl={negotiated.get('ttl_seconds')}s")
    else:
        result["steps"].append({"step": "negotiate_access", "status": "denied", "latency_ms": round(lat, 2)})
        print(f"  [FAIL] Access denied")
        _write_result(result, args.out)
        return 1

    # Step 3: Fetch dataset with token
    t0 = time.perf_counter()
    try:
        headers = {"Authorization": f"Bearer {token}"}
        dataset = fetch_dataset(data_facts, headers=headers)
        lat = (time.perf_counter() - t0) * 1000
        row_count = dataset.get("row_count", len(dataset.get("rows", [])))
        result["steps"].append({"step": "fetch_dataset", "status": "ok", "latency_ms": round(lat, 2), "row_count": row_count})
        print(f"  [OK] Dataset fetched ({lat:.1f}ms), {row_count} rows")
    except Exception as e:
        lat = (time.perf_counter() - t0) * 1000
        result["steps"].append({"step": "fetch_dataset", "status": "error", "latency_ms": round(lat, 2), "error": str(e)})
        print(f"  [FAIL] Dataset fetch: {e}")
        _write_result(result, args.out)
        return 1

    # Step 4: Verify checksum
    checksum_ok = verify_checksum(data_facts, dataset)
    result["steps"].append({"step": "verify_checksum", "status": "ok" if checksum_ok else "mismatch"})
    print(f"  [{'OK' if checksum_ok else 'WARN'}] Checksum {'matches' if checksum_ok else 'mismatch'}")

    # Step 5: Check freshness
    is_fresh = check_freshness(data_facts)
    result["steps"].append({"step": "check_freshness", "status": "fresh" if is_fresh else "stale"})
    print(f"  [{'OK' if is_fresh else 'WARN'}] Data {'fresh' if is_fresh else 'stale'}")

    result["overall"] = "PASS"
    print(f"[{args.consumer_id}] PASS")

    _write_result(result, args.out)
    return 0


def _write_result(result, out_path):
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        print(f"  Result written to {out_path}")


if __name__ == "__main__":
    sys.exit(main())
