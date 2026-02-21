#!/usr/bin/env python3
"""
Malicious Consumer — token forgery test agent.

Attempts to access the private dataset using:
  1. A JWT signed with a wrong secret (forgery)
  2. A manually crafted garbage token (malformed)

Expected: 401 Access denied for both attempts.

Usage:
    python malicious_consumer.py [--owner-data-url http://localhost:6350]
"""
import os
import sys
import time
import json
import argparse
import requests
from datetime import datetime, timezone, timedelta

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

try:
    import jwt as pyjwt
except ImportError:
    print("PyJWT required: pip install PyJWT")
    sys.exit(1)


def main():
    ap = argparse.ArgumentParser(description="Malicious Consumer Agent")
    ap.add_argument("--owner-data-url", default="http://localhost:6350")
    ap.add_argument("--consumer-id", default="malicious_consumer_01")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    endpoint = f"{args.owner_data_url}/private-employee-records"
    result = {
        "agent_id": args.consumer_id,
        "scenario": "malicious",
        "steps": [],
    }

    print(f"[{args.consumer_id}] Starting malicious token tests")

    # Attack 1: Forged JWT (wrong secret)
    wrong_secret = "wrong-secret-not-the-real-one"
    forged_token = pyjwt.encode(
        {
            "sub": args.consumer_id,
            "role": "inquiry",
            "scope": "read",
            "dataset_id": "private_employee_records",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iat": datetime.now(timezone.utc),
        },
        wrong_secret,
        algorithm="HS256",
    )
    result["steps"].append(_try_fetch(endpoint, forged_token, "forged_wrong_secret"))

    # Attack 2: Garbage / malformed token
    garbage_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.fake-payload.wrong-signature"
    result["steps"].append(_try_fetch(endpoint, garbage_token, "malformed_garbage"))

    # Determine overall result
    all_rejected = all(s.get("status_code") == 401 for s in result["steps"])
    result["overall"] = "PASS" if all_rejected else "FAIL"
    print(f"[{args.consumer_id}] {result['overall']}")

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
    return 0 if all_rejected else 1


def _try_fetch(endpoint, token, label):
    t0 = time.perf_counter()
    try:
        resp = requests.get(
            endpoint, headers={"Authorization": f"Bearer {token}"}, timeout=10
        )
        lat = (time.perf_counter() - t0) * 1000
        step = {
            "step": label,
            "status_code": resp.status_code,
            "latency_ms": round(lat, 2),
        }
        if resp.status_code == 401:
            print(f"  [OK] {label}: correctly rejected 401 ({lat:.1f}ms)")
        else:
            print(f"  [FAIL] {label}: expected 401, got {resp.status_code} ({lat:.1f}ms)")
        return step
    except Exception as e:
        lat = (time.perf_counter() - t0) * 1000
        print(f"  [ERROR] {label}: {e}")
        return {"step": label, "error": str(e), "latency_ms": round(lat, 2)}


if __name__ == "__main__":
    sys.exit(main())
