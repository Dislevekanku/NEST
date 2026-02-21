#!/usr/bin/env python3
"""
Unauthorized Consumer — no-auth test agent.

Tries to GET the private dataset endpoint with no Authorization header.

Expected: 401 Access denied.

Usage:
    python unauthorized_consumer.py [--owner-data-url http://localhost:6350]
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


def main():
    ap = argparse.ArgumentParser(description="Unauthorized Consumer Agent")
    ap.add_argument("--owner-data-url", default="http://localhost:6350")
    ap.add_argument("--consumer-id", default="unauthorized_consumer_01")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    endpoint = f"{args.owner_data_url}/private-employee-records"
    result = {
        "agent_id": args.consumer_id,
        "scenario": "unauthorized",
        "steps": [],
    }

    print(f"[{args.consumer_id}] Attempting to fetch without auth header")

    # Try to fetch with no Authorization header at all
    t0 = time.perf_counter()
    try:
        resp = requests.get(endpoint, timeout=10)
        lat = (time.perf_counter() - t0) * 1000
        result["steps"].append({
            "step": "fetch_no_auth",
            "status_code": resp.status_code,
            "latency_ms": round(lat, 2),
        })

        if resp.status_code == 401:
            result["overall"] = "PASS"
            print(f"  [OK] Correctly rejected: {resp.status_code} ({lat:.1f}ms)")
        else:
            result["overall"] = "FAIL"
            print(f"  [FAIL] Expected 401, got {resp.status_code} ({lat:.1f}ms)")
    except Exception as e:
        lat = (time.perf_counter() - t0) * 1000
        result["steps"].append({"step": "fetch_no_auth", "error": str(e), "latency_ms": round(lat, 2)})
        result["overall"] = "ERROR"
        print(f"  [ERROR] {e}")

    # Also try with empty Authorization header
    t0 = time.perf_counter()
    try:
        resp = requests.get(endpoint, headers={"Authorization": ""}, timeout=10)
        lat = (time.perf_counter() - t0) * 1000
        result["steps"].append({
            "step": "fetch_empty_auth",
            "status_code": resp.status_code,
            "latency_ms": round(lat, 2),
        })
        if resp.status_code == 401:
            print(f"  [OK] Empty auth correctly rejected: {resp.status_code} ({lat:.1f}ms)")
        else:
            print(f"  [FAIL] Empty auth: expected 401, got {resp.status_code} ({lat:.1f}ms)")
            result["overall"] = "FAIL"
    except Exception as e:
        lat = (time.perf_counter() - t0) * 1000
        result["steps"].append({"step": "fetch_empty_auth", "error": str(e), "latency_ms": round(lat, 2)})

    print(f"[{args.consumer_id}] {result.get('overall', 'UNKNOWN')}")

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
    return 0 if result.get("overall") == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
