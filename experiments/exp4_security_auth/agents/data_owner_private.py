#!/usr/bin/env python3
"""
Data Owner Agent — serves private_employee_records from Supabase.

Registers with registry as semi-private (discoverable, JWT-gated).
Issues JWTs via /negotiate_access on the dataset server.

Usage:
    python data_owner_private.py [--port 6300] [--data-port 6350]
"""
import os
import sys
import time
import argparse

# Fix encoding for Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from dotenv import load_dotenv
load_dotenv()

from nanda_core.core.adapter import NANDA
from nanda_core.dataset.server import DatasetServer
from nanda_core.dataset.supabase_provider import SupabaseDatasetProvider


def safe_print(*args, **kwargs):
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        safe_args = [
            a.encode("ascii", "replace").decode("ascii") if isinstance(a, str) else a
            for a in args
        ]
        print(*safe_args, **kwargs)


def create_agent_logic(provider, data_server):
    def agent_logic(message: str, conversation_id: str) -> str:
        msg = message.lower()
        if "hello" in msg or "hi" in msg:
            return (
                f"I'm the data owner for {provider.get_dataset_id()}. "
                f"Access type: {provider.get_access_type()}. "
                "Negotiate access via /negotiate_access to get a JWT."
            )
        if "data" in msg or "dataset" in msg:
            return (
                f"Dataset: {provider.get_dataset_id()} ({provider.get_access_type()}). "
                f"Data Facts: {data_server.get_data_facts_url()}"
            )
        return "I serve private employee records. Ask about data or say hello."
    return agent_logic


def main():
    ap = argparse.ArgumentParser(description="Data Owner Private Agent")
    ap.add_argument("--port", type=int, default=int(os.getenv("PORT", "6300")))
    ap.add_argument("--data-port", type=int, default=int(os.getenv("DATA_PORT", "6350")))
    ap.add_argument("--registry-url", default=os.getenv("REGISTRY_URL"))
    ap.add_argument("--public-url", default=os.getenv("PUBLIC_URL"))
    args = ap.parse_args()

    agent_id = "data_owner_private_01"
    public_url = args.public_url or f"http://localhost:{args.port}"
    data_server_url = f"http://localhost:{args.data_port}"

    safe_print("=" * 60)
    safe_print(f"[DATA OWNER] {agent_id}")
    safe_print(f"  A2A port: {args.port}")
    safe_print(f"  Dataset port: {args.data_port}")
    safe_print(f"  Access type: semi-private")
    safe_print("=" * 60)

    # Create Supabase-backed provider
    provider = SupabaseDatasetProvider(
        table_name="private_employee_records",
        dataset_id="private_employee_records",
        description="Private employee records (semi-private, JWT-gated)",
        access_type="semi-private",
        ttl_seconds=300,
        row_limit=100,
    )

    # Start dataset server (has /negotiate_access route built in)
    data_server = DatasetServer(
        provider=provider,
        port=args.data_port,
        public_url=data_server_url,
        data_owner=agent_id,
    )
    data_server.start()
    time.sleep(0.5)

    data_facts_url = data_server.get_data_facts_url()
    safe_print(f"  Data Facts: {data_facts_url}")

    # Create and start NANDA agent
    agent_logic = create_agent_logic(provider, data_server)
    nanda = NANDA(
        agent_id=agent_id,
        agent_logic=agent_logic,
        port=args.port,
        registry_url=args.registry_url,
        public_url=public_url,
        enable_telemetry=False,
        data_facts_url=data_facts_url,
    )

    safe_print(f"  A2A: http://localhost:{args.port}/a2a")
    safe_print(f"  Dataset: {data_server_url}/private-employee-records")
    safe_print(f"  Negotiate: {data_server_url}/negotiate_access")
    safe_print("Press Ctrl+C to stop")
    safe_print("=" * 60)

    try:
        nanda.start()
    except KeyboardInterrupt:
        safe_print("\nShutting down...")
        nanda.stop()


if __name__ == "__main__":
    main()
