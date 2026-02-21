#!/usr/bin/env python3
"""
Start consumer processes in batches and register with NEST registry.

Batch A: consumer_001..010 (10)
Batch B: consumer_011..025 (15)
Batch C: consumer_026..050 (25)

Usage:
  CONSUMER_BASE_PORT=6001 REGISTRY_URL=... PUBLIC_URL=... python consumer_batch_runner.py --batch A
  python consumer_batch_runner.py --batch B  # after A is running
  python consumer_batch_runner.py --batch C  # after B is running
  python consumer_batch_runner.py --batch all  # start all 50
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from nanda_core.core.registry_client import RegistryClient

BATCHES = {
    "A": (1, 10),
    "B": (11, 25),
    "C": (26, 50),
    "all": (1, 50),
}


def get_public_url() -> str:
    url = os.environ.get("PUBLIC_URL", "").strip()
    if url:
        return url.rstrip("/")
    try:
        import requests
        tok = requests.put(
            "http://169.254.169.254/latest/api/token",
            headers={"X-aws-ec2-metadata-token-ttl-seconds": "21600"},
            timeout=5,
        ).text
        ip = requests.get(
            "http://169.254.169.254/latest/meta-data/public-ipv4",
            headers={"X-aws-ec2-metadata-token": tok},
            timeout=5,
        ).text.strip()
        if ip and len(ip) < 20:
            return f"http://{ip}"
    except Exception:
        pass
    return "http://localhost"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", choices=["A", "B", "C", "all"], required=True)
    ap.add_argument("--base-port", type=int, default=6001)
    args = ap.parse_args()

    registry_url = os.environ.get("REGISTRY_URL", "http://registry.chat39.com:6900")
    public_url = get_public_url()
    if "localhost" in public_url and "PUBLIC_URL" not in os.environ:
        host = os.environ.get("CONSUMER_HOST", "127.0.0.1")
        public_url = f"http://{host}"

    lo, hi = BATCHES[args.batch]
    processes = []

    for i in range(lo, hi + 1):
        agent_id = f"consumer_{i:03d}"
        port = args.base_port + i - 1
        env = os.environ.copy()
        env["CONSUMER_AGENT_ID"] = agent_id
        env["CONSUMER_PORT"] = str(port)
        proc = subprocess.Popen(
            [sys.executable, str(Path(__file__).parent / "consumer_process.py")],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=str(ROOT),
        )
        processes.append((agent_id, port, proc))
        time.sleep(0.15)  # stagger starts

    time.sleep(2)  # let them bind

    client = RegistryClient(registry_url)
    base = f"{public_url.rstrip('/')}"
    for agent_id, port, _ in processes:
        agent_url = f"{base}:{port}"
        ok = client.register_agent(agent_id=agent_id, agent_url=agent_url)
        print(f"  registered {agent_id} -> {agent_url} ({'ok' if ok else 'fail'})")

    if args.daemon:
        print(f"[batch {args.batch}] {len(processes)} consumers started (daemon mode).")
        return 0

    print(f"[batch {args.batch}] {len(processes)} consumers started. Press Ctrl+C to stop.")
    try:
        for _, _, p in processes:
            p.wait()
    except KeyboardInterrupt:
        for _, _, p in processes:
            p.terminate()
    return 0


if __name__ == "__main__":
    sys.exit(main())
