#!/usr/bin/env python3
"""
Expired Consumer — TTL expiry test agent.

Negotiates access with a very short TTL (2s), waits 3s, then tries to
fetch the dataset. The JWT should be expired by the time the request
arrives.

Expected: 401 Access denied (expired token).

Usage:
    python expired_consumer.py [--owner-data-url http://localhost:6350]
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

from nanda_core.dataset.client import negotiate_access, fetch_data_facts


def main():
    ap = argparse.ArgumentParser(description="Expired Consumer Agent")
    ap.add_argument("--owner-data-url", default="http://localhost:6350")
    ap.add_argument("--dataset-id", default="private_employee_records")
    ap.add_argument("--consumer-id", default="expired_consumer_01")
    ap.add_argument("--ttl", type=int, default=2, help="Short TTL to force expiry")
    ap.add_argument("--wait", type=int, default=3, help="Seconds to wait before fetching")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    result = {
        "agent_id": args.consumer_id,
        "scenario": "expired",
        "steps": [],
    }

    print(f"[{args.consumer_id}] Starting expired token test (TTL={args.ttl}s, wait={args.wait}s)")

    # Step 1: Negotiate access with short TTL
    t0 = time.perf_counter()
    negotiated = negotiate_access(args.owner_data_url, args.consumer_id, ttl_seconds=args.ttl)
    lat = (time.perf_counter() - t0) * 1000
    if not (negotiated and negotiated.get("token")):
        result["steps"].append({"step": "negotiate_access", "status": "denied"})
        print(f"  [FAIL] Could not obtain token")
        _write(result, args.out)
        return 1

    token = negotiated["token"]
    result["steps"].append({"step": "negotiate_access", "status": "ok", "latency_ms": round(lat, 2), "ttl": args.ttl})
    print(f"  [OK] Token received ({lat:.1f}ms), TTL={args.ttl}s")

    # Step 2: Wait for token to expire
    print(f"  Waiting {args.wait}s for token to expire...")
    time.sleep(args.wait)

    # Step 3: Try to fetch dataset with expired token
    endpoint = f"{args.owner_data_url}/private-employee-records"
    t0 = time.perf_counter()
    try:
        resp = requests.get(endpoint, headers={"Authorization": f"Bearer {token}"}, timeout=10)
        lat = (time.perf_counter() - t0) * 1000
        result["steps"].append({
            "step": "fetch_dataset_expired",
            "status_code": resp.status_code,
            "latency_ms": round(lat, 2),
            "body": resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text[:200],
        })

        if resp.status_code == 401:
            result["overall"] = "PASS"
            print(f"  [OK] Correctly rejected: {resp.status_code} ({lat:.1f}ms)")
        else:
            result["overall"] = "FAIL"
            print(f"  [FAIL] Expected 401, got {resp.status_code} ({lat:.1f}ms)")
    except Exception as e:
        lat = (time.perf_counter() - t0) * 1000
        result["steps"].append({"step": "fetch_dataset_expired", "error": str(e), "latency_ms": round(lat, 2)})
        result["overall"] = "ERROR"
        print(f"  [ERROR] {e}")

    print(f"[{args.consumer_id}] {result.get('overall', 'UNKNOWN')}")
    _write(result, args.out)
    return 0 if result.get("overall") == "PASS" else 1


def _write(result, out_path):
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)


if __name__ == "__main__":
    sys.exit(main())
