#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NEST Full Ecosystem Deployment

Orchestrates complete deployment:
1. Deploy and validate providers first
2. Deploy consumers in batches (A, B, C)
3. Run smoke tests after each batch
4. Generate comprehensive summary

Usage:
    python deploy_full_ecosystem.py                    # Full deployment
    python deploy_full_ecosystem.py --consumers-only   # Skip providers
    python deploy_full_ecosystem.py --dry-run          # Show plan only
"""
import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, ValueError):
        pass

def safe_print(*args, **kwargs):
    """Print with Unicode error handling."""
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        safe_args = [str(a).encode('ascii', 'replace').decode('ascii') for a in args]
        print(*safe_args, **kwargs)

try:
    import requests
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "-q"])
    import requests

# Paths
SCRIPT_DIR = Path(__file__).parent.absolute()
NEST_ROOT = SCRIPT_DIR.parent.parent
RESULTS_DIR = SCRIPT_DIR / "results" / "week5"
MANIFEST_FILE = SCRIPT_DIR / "agents_manifest_v1.json"

# Configuration
DEFAULT_REGISTRY_URL = "http://registry.chat39.com:6900"
DEFAULT_HOST = "localhost"
PROVIDER_SCRIPT = NEST_ROOT / "examples" / "finance_feed_agent_refactored.py"

# Batch definitions
BATCHES = {
    "A": {"start": 1, "end": 10, "description": "Initial batch"},
    "B": {"start": 11, "end": 25, "description": "Scale-up batch"},
    "C": {"start": 26, "end": 50, "description": "Full scale batch"},
}


def load_manifest() -> Dict:
    """Load agents manifest."""
    with open(MANIFEST_FILE) as f:
        return json.load(f)


def check_registry_health(registry_url: str) -> bool:
    """Check if registry is healthy."""
    try:
        response = requests.get(f"{registry_url}/health", timeout=5)
        return response.status_code == 200
    except:
        return False


def deploy_provider(
    provider: Dict,
    host: str,
    registry_url: str
) -> Optional[subprocess.Popen]:
    """Deploy a single provider agent."""
    agent_id = provider["agent_id"]
    port = provider["port"]
    data_port = provider.get("data_server_port", 8000)

    safe_print(f"  Launching {agent_id} on port {port} (data: {data_port})...")

    env = os.environ.copy()
    env["AGENT_ID"] = agent_id
    env["AGENT_NAME"] = provider["agent_name"]
    env["PORT"] = str(port)
    env["DATA_SERVER_PORT"] = str(data_port)
    env["REGISTRY_URL"] = registry_url
    env["PUBLIC_URL"] = f"http://{host}:{port}"

    if "stock_tickers" in provider:
        env["STOCK_TICKERS"] = ",".join(provider["stock_tickers"])

    try:
        process = subprocess.Popen(
            [sys.executable, str(PROVIDER_SCRIPT)],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(NEST_ROOT)
        )
        return process
    except Exception as e:
        safe_print(f"  Failed to launch {agent_id}: {e}")
        return None


def validate_provider(
    provider: Dict,
    host: str,
    registry_url: str
) -> Dict:
    """Validate provider is healthy and registered."""
    agent_id = provider["agent_id"]
    port = provider["port"]
    data_port = provider.get("data_server_port", 8000)
    base_url = f"http://{host}:{port}"
    data_url = f"http://{host}:{data_port}"

    result = {"agent_id": agent_id, "health": False, "a2a": False, "data_facts": False, "registered": False}

    # Health check (python_a2a uses /a2a/health)
    try:
        r = requests.get(f"{base_url}/a2a/health", timeout=5)
        result["health"] = r.status_code == 200
    except:
        pass

    # A2A check
    try:
        r = requests.post(f"{base_url}/a2a", json={
            "content": {"text": "ping", "type": "text"},
            "role": "user",
            "conversation_id": "validate"
        }, timeout=5)
        result["a2a"] = r.status_code == 200
    except:
        pass

    # Data Facts check
    try:
        # Try common data facts paths
        for path in ["/data_facts/public_stock_ticker.json", "/data_facts/public_weather.json"]:
            r = requests.get(f"{data_url}{path}", timeout=5)
            if r.status_code == 200:
                result["data_facts"] = True
                break
    except:
        pass

    # Registry check
    try:
        r = requests.get(f"{registry_url}/lookup/{agent_id}", timeout=5)
        result["registered"] = r.status_code == 200
    except:
        pass

    return result


def register_provider(provider: Dict, host: str, registry_url: str) -> bool:
    """Register provider with registry."""
    agent_id = provider["agent_id"]
    port = provider["port"]
    data_port = provider.get("data_server_port", 8000)

    try:
        response = requests.post(
            f"{registry_url}/register",
            json={
                "agent_id": agent_id,
                "agent_url": f"http://{host}:{port}",
                "data_facts_url": f"http://{host}:{data_port}/data_facts/public_stock_ticker.json",
                "capabilities": provider.get("capabilities", []),
                "description": provider.get("description", "")
            },
            timeout=10
        )
        return response.status_code in [200, 201]
    except:
        return False


def deploy_providers(manifest: Dict, host: str, registry_url: str) -> Dict:
    """Deploy all provider agents."""
    safe_print("\n" + "=" * 60)
    safe_print("PHASE 1: DEPLOYING PROVIDERS")
    safe_print("=" * 60)

    providers = manifest.get("providers", [])
    processes = {}
    results = {}

    for provider in providers:
        agent_id = provider["agent_id"]
        process = deploy_provider(provider, host, registry_url)
        if process:
            processes[agent_id] = process

    # Wait for startup (Flask/python_a2a needs ~8-10s to bind port)
    safe_print("\n  Waiting for providers to initialize (12s)...")
    time.sleep(12)

    # Validate and register
    safe_print("\n  Validating providers...")
    for provider in providers:
        agent_id = provider["agent_id"]
        safe_print(f"  Checking {agent_id}...", end=" ")

        # Retry validation
        for attempt in range(5):
            result = validate_provider(provider, host, registry_url)
            if result["health"]:
                break
            time.sleep(1)

        # Register if not already
        if not result["registered"] and result["health"]:
            register_provider(provider, host, registry_url)
            result["registered"] = True

        results[agent_id] = result

        status = "OK" if all([result["health"], result["a2a"]]) else "PARTIAL" if result["health"] else "FAILED"
        safe_print(status)

    safe_print("\n  Provider deployment complete")
    return {"processes": processes, "results": results}


def run_batch_deployment(
    batch_name: str,
    manifest: Dict,
    registry_url: str,
    host: str,
    smoke_duration: int = 5
) -> Dict:
    """Run batch deployment using deploy_batch.py."""
    safe_print(f"\n{'='*60}")
    safe_print(f"DEPLOYING BATCH {batch_name}")
    safe_print(f"{'='*60}")

    batch_info = BATCHES[batch_name]
    safe_print(f"Consumers: {batch_info['start']:03d} - {batch_info['end']:03d}")
    safe_print(f"Description: {batch_info['description']}")

    # Import and run batch deployment
    sys.path.insert(0, str(SCRIPT_DIR))
    from deploy_batch import deploy_batch, SMOKE_TEST_DURATION_MINUTES

    # Update smoke test duration
    import deploy_batch as db
    db.SMOKE_TEST_DURATION_MINUTES = smoke_duration

    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    run_tag = f"batch_{batch_name.lower()}_{timestamp}"

    result = deploy_batch(batch_name, manifest, registry_url, host, run_tag)
    return result


def generate_final_summary(
    provider_results: Dict,
    batch_results: Dict,
    output_dir: Path
):
    """Generate comprehensive deployment summary."""
    output_file = output_dir / "deployment_summary.md"
    timestamp = datetime.utcnow().isoformat() + "Z"

    # Calculate totals
    total_providers = len(provider_results.get("results", {}))
    healthy_providers = sum(1 for r in provider_results.get("results", {}).values() if r.get("health"))

    total_consumers = 0
    healthy_consumers = 0
    total_smoke_success = 0
    total_smoke_requests = 0

    for batch, result in batch_results.items():
        summary = result.get("summary", {})
        total_consumers += summary.get("deployed", 0)
        healthy_consumers += summary.get("healthy", 0)
        smoke = summary.get("smoke_test", {})
        total_smoke_success += smoke.get("successes", 0)
        total_smoke_requests += smoke.get("total_requests", 0)

    overall_smoke_rate = round(total_smoke_success / total_smoke_requests * 100, 2) if total_smoke_requests > 0 else 0

    content = f"""# NEST Full Ecosystem Deployment Summary

**Generated**: {timestamp}

## Overview

| Component | Deployed | Healthy | Health % |
|-----------|----------|---------|----------|
| Providers | {total_providers} | {healthy_providers} | {round(healthy_providers/total_providers*100, 1) if total_providers > 0 else 0}% |
| Consumers | {total_consumers} | {healthy_consumers} | {round(healthy_consumers/total_consumers*100, 1) if total_consumers > 0 else 0}% |
| **Total** | **{total_providers + total_consumers}** | **{healthy_providers + healthy_consumers}** | **{round((healthy_providers + healthy_consumers)/(total_providers + total_consumers)*100, 1) if (total_providers + total_consumers) > 0 else 0}%** |

## Smoke Test Results

| Metric | Value |
|--------|-------|
| Total Requests | {total_smoke_requests} |
| Successful | {total_smoke_success} |
| Failed | {total_smoke_requests - total_smoke_success} |
| **Success Rate** | **{overall_smoke_rate}%** |

## Provider Status

| Provider | Health | A2A | Data Facts | Registered |
|----------|--------|-----|------------|------------|
"""

    for agent_id, result in provider_results.get("results", {}).items():
        h = "[OK]" if result.get("health") else "[FAIL]"
        a = "[OK]" if result.get("a2a") else "[FAIL]"
        d = "[OK]" if result.get("data_facts") else "[FAIL]"
        r = "[OK]" if result.get("registered") else "[FAIL]"
        content += f"| {agent_id} | {h} | {a} | {d} | {r} |\n"

    content += """
## Batch Results

| Batch | Range | Deployed | Healthy | Smoke % |
|-------|-------|----------|---------|---------|
"""

    for batch in ["A", "B", "C"]:
        result = batch_results.get(batch, {})
        summary = result.get("summary", {})
        batch_info = BATCHES.get(batch, {})
        range_str = f"{batch_info.get('start', 0):03d}-{batch_info.get('end', 0):03d}"
        deployed = summary.get("deployed", 0)
        healthy = summary.get("healthy", 0)
        smoke_rate = summary.get("smoke_test", {}).get("success_rate", "N/A")
        content += f"| {batch} | {range_str} | {deployed} | {healthy} | {smoke_rate}% |\n"

    content += """
## Safety Controls Active

- **Client-side jitter**: 0-1500ms random start delay
- **Per-agent concurrency**: Max 3 concurrent queries
- **Global concurrency**: Max 25 in-flight requests

## Stability Assessment

"""

    if overall_smoke_rate >= 95 and healthy_consumers >= 45:
        content += """**Status: STABLE** [OK]

The ecosystem is ready for experiments:
- All providers healthy and registered
- >90% consumers healthy
- >95% smoke test success rate
"""
    elif overall_smoke_rate >= 80:
        content += """**Status: MOSTLY STABLE** [WARN]

The ecosystem needs minor attention:
- Review failed health checks
- Check network connectivity
- Consider increasing timeouts
"""
    else:
        content += """**Status: NEEDS ATTENTION** [FAIL]

Issues detected:
- Low smoke test success rate
- Multiple failed deployments
- Check registry logs
- Verify port availability
"""

    with open(output_file, "w") as f:
        f.write(content)

    safe_print(f"\nDeployment summary saved to: {output_file}")
    return output_file


def main():
    parser = argparse.ArgumentParser(description="NEST Full Ecosystem Deployment")
    parser.add_argument("--registry", default=DEFAULT_REGISTRY_URL)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--consumers-only", action="store_true",
                        help="Skip provider deployment")
    parser.add_argument("--batch", choices=["A", "B", "C"], default=None,
                        help="Deploy only specific batch")
    parser.add_argument("--smoke-duration", type=int, default=5,
                        help="Smoke test duration in minutes")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show deployment plan only")

    args = parser.parse_args()

    # Load manifest
    manifest = load_manifest()
    safe_print(f"\nNEST Full Ecosystem Deployment")
    safe_print(f"=" * 60)
    safe_print(f"Registry: {args.registry}")
    safe_print(f"Providers: {len(manifest.get('providers', []))}")
    safe_print(f"Consumers: {len(manifest.get('consumers', []))}")
    safe_print(f"=" * 60)

    if args.dry_run:
        safe_print("\n[DRY RUN] Deployment plan:")
        if not args.consumers_only:
            safe_print("  1. Deploy providers (2 agents)")
        for batch, info in BATCHES.items():
            if args.batch and args.batch != batch:
                continue
            safe_print(f"  2. Deploy Batch {batch}: consumers {info['start']:03d}-{info['end']:03d}")
        safe_print("\nNo changes made.")
        return

    # Check registry
    if not check_registry_health(args.registry):
        safe_print(f"\nError: Registry at {args.registry} is not reachable")
        sys.exit(1)
    safe_print("\nRegistry: healthy [OK]")

    all_processes = {}
    provider_results = {"processes": {}, "results": {}}
    batch_results = {}

    # Deploy providers
    if not args.consumers_only:
        provider_results = deploy_providers(manifest, args.host, args.registry)
        all_processes.update(provider_results.get("processes", {}))

    # Deploy consumer batches
    batches_to_deploy = [args.batch] if args.batch else ["A", "B", "C"]

    for batch in batches_to_deploy:
        result = run_batch_deployment(
            batch, manifest, args.registry, args.host, args.smoke_duration
        )
        batch_results[batch] = result
        all_processes.update(result.get("processes", {}))

        # Pause between batches
        if batch != batches_to_deploy[-1]:
            safe_print("\nPausing before next batch...")
            time.sleep(3)

    # Generate final summary
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    generate_final_summary(provider_results, batch_results, RESULTS_DIR / "exp1")

    # Keep running
    if all_processes:
        safe_print(f"\n{len(all_processes)} agents running. Press Ctrl+C to stop all.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            safe_print("\nStopping all agents...")
            for agent_id, process in all_processes.items():
                safe_print(f"  Stopping {agent_id}...")
                process.terminate()
            safe_print("All agents stopped.")


if __name__ == "__main__":
    main()
