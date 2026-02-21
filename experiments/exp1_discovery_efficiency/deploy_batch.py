#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NEST Batch Deployment with Safety Controls

Deploys consumers in batches with:
- Client-side jitter (0-1500ms start delay)
- Concurrency caps (per-agent: 3, global: 25)
- Run tagging and structured logging
- Smoke tests after each batch

Usage:
    python deploy_batch.py --batch A    # Deploy consumers 001-010
    python deploy_batch.py --batch B    # Deploy consumers 011-025
    python deploy_batch.py --batch C    # Deploy consumers 026-050
    python deploy_batch.py --batch all  # Deploy all in sequence
"""
import argparse
import asyncio
import json
import logging
import os
import random
import sys
import time
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor
import threading

# Add parent paths
SCRIPT_DIR = Path(__file__).parent.absolute()
NEST_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(NEST_ROOT))

try:
    import requests
except ImportError:
    print("Installing requests...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "-q"])
    import requests

# =============================================================================
# CONFIGURATION
# =============================================================================

MANIFEST_FILE = SCRIPT_DIR / "agents_manifest_v1.json"
RESULTS_DIR = SCRIPT_DIR / "results" / "week5"
DEFAULT_REGISTRY_URL = "http://registry.chat39.com:6900"
DEFAULT_HOST = "localhost"

# Safety controls
JITTER_MAX_MS = 1500  # Max random start delay
PER_AGENT_CONCURRENCY = 3  # Max concurrent queries per agent
GLOBAL_CONCURRENCY = 25  # Max total in-flight requests

# Smoke test config
SMOKE_TEST_REQUESTS_PER_AGENT = 2
SMOKE_TEST_DURATION_MINUTES = 5

# Batch definitions
BATCHES = {
    "A": list(range(1, 11)),    # consumers 001-010
    "B": list(range(11, 26)),   # consumers 011-025
    "C": list(range(26, 51)),   # consumers 026-050
}

# Consumer script
CONSUMER_SCRIPT = NEST_ROOT / "examples" / "data_consumer_agent_refactored.py"


# =============================================================================
# LOGGING SETUP
# =============================================================================

@dataclass
class RequestLog:
    """Structured log entry for each request."""
    timestamp: str
    run_tag: str
    agent_id: str
    mode: str
    step: str
    latency_ms: float
    status: str
    error: Optional[str] = None
    details: Optional[Dict] = None

    def to_dict(self) -> Dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


class StructuredLogger:
    """Logger with run tagging and structured output."""

    def __init__(self, run_tag: str, output_dir: Path):
        self.run_tag = run_tag
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.log_file = output_dir / f"{run_tag}_requests.jsonl"
        self.summary_file = output_dir / f"{run_tag}_summary.json"

        self.logs: List[RequestLog] = []
        self._lock = threading.Lock()

        # Setup console logger
        self.console = logging.getLogger(f"nest.{run_tag}")
        self.console.setLevel(logging.INFO)
        if not self.console.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(
                '%(asctime)s [%(levelname)s] %(message)s',
                datefmt='%H:%M:%S'
            ))
            self.console.addHandler(handler)

    def log_request(
        self,
        agent_id: str,
        mode: str,
        step: str,
        latency_ms: float,
        status: str,
        error: Optional[str] = None,
        details: Optional[Dict] = None
    ):
        """Log a single request with all metadata."""
        entry = RequestLog(
            timestamp=datetime.utcnow().isoformat() + "Z",
            run_tag=self.run_tag,
            agent_id=agent_id,
            mode=mode,
            step=step,
            latency_ms=round(latency_ms, 2),
            status=status,
            error=error,
            details=details
        )

        with self._lock:
            self.logs.append(entry)
            # Append to JSONL file
            with open(self.log_file, "a") as f:
                f.write(json.dumps(entry.to_dict()) + "\n")

        # Console output
        status_icon = "✓" if status == "success" else "✗"
        self.console.info(
            f"{status_icon} [{agent_id}] {mode}/{step} - {latency_ms:.0f}ms - {status}"
        )

    def get_summary(self) -> Dict:
        """Generate summary statistics."""
        with self._lock:
            total = len(self.logs)
            successes = sum(1 for log in self.logs if log.status == "success")
            failures = total - successes

            latencies = [log.latency_ms for log in self.logs if log.status == "success"]
            avg_latency = sum(latencies) / len(latencies) if latencies else 0

            # Group by error type
            error_counts = {}
            for log in self.logs:
                if log.error:
                    error_counts[log.error] = error_counts.get(log.error, 0) + 1

            return {
                "run_tag": self.run_tag,
                "total_requests": total,
                "successes": successes,
                "failures": failures,
                "success_rate": round(successes / total * 100, 2) if total > 0 else 0,
                "avg_latency_ms": round(avg_latency, 2),
                "error_breakdown": error_counts
            }

    def save_summary(self):
        """Save summary to file."""
        summary = self.get_summary()
        with open(self.summary_file, "w") as f:
            json.dump(summary, f, indent=2)
        return summary


# =============================================================================
# CONCURRENCY CONTROLS
# =============================================================================

class ConcurrencyController:
    """Manages concurrency limits to avoid self-DDoS."""

    def __init__(self, per_agent_limit: int = PER_AGENT_CONCURRENCY,
                 global_limit: int = GLOBAL_CONCURRENCY):
        self.per_agent_limit = per_agent_limit
        self.global_limit = global_limit
        self.global_semaphore = threading.Semaphore(global_limit)
        self.agent_semaphores: Dict[str, threading.Semaphore] = {}
        self._lock = threading.Lock()

    def get_agent_semaphore(self, agent_id: str) -> threading.Semaphore:
        """Get or create semaphore for an agent."""
        with self._lock:
            if agent_id not in self.agent_semaphores:
                self.agent_semaphores[agent_id] = threading.Semaphore(self.per_agent_limit)
            return self.agent_semaphores[agent_id]

    def acquire(self, agent_id: str, timeout: float = 30.0) -> bool:
        """Acquire both global and per-agent semaphores."""
        if not self.global_semaphore.acquire(timeout=timeout):
            return False
        agent_sem = self.get_agent_semaphore(agent_id)
        if not agent_sem.acquire(timeout=timeout):
            self.global_semaphore.release()
            return False
        return True

    def release(self, agent_id: str):
        """Release both semaphores."""
        self.get_agent_semaphore(agent_id).release()
        self.global_semaphore.release()


# =============================================================================
# AGENT DEPLOYMENT
# =============================================================================

def apply_jitter():
    """Apply random start delay (0-1500ms)."""
    delay = random.uniform(0, JITTER_MAX_MS / 1000.0)
    time.sleep(delay)
    return delay * 1000  # Return in ms


def load_manifest() -> Dict:
    """Load agents manifest."""
    with open(MANIFEST_FILE) as f:
        return json.load(f)


def get_consumer_by_number(manifest: Dict, num: int) -> Optional[Dict]:
    """Get consumer agent config by number (1-50)."""
    agent_id = f"consumer_{num:03d}"
    for consumer in manifest.get("consumers", []):
        if consumer["agent_id"] == agent_id:
            return consumer
    return None


def launch_consumer(
    agent: Dict,
    registry_url: str,
    logger: StructuredLogger,
    concurrency: ConcurrencyController
) -> Optional[subprocess.Popen]:
    """Launch a single consumer agent with jitter."""
    agent_id = agent["agent_id"]
    port = agent["port"]

    # Apply jitter
    jitter_ms = apply_jitter()
    logger.log_request(agent_id, "deploy", "jitter", jitter_ms, "success")

    env = os.environ.copy()
    env["AGENT_ID"] = agent_id
    env["AGENT_NAME"] = agent.get("agent_name", agent_id)
    env["PORT"] = str(port)
    env["REGISTRY_URL"] = registry_url

    try:
        start = time.time()
        process = subprocess.Popen(
            [sys.executable, str(CONSUMER_SCRIPT)],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(NEST_ROOT)
        )
        latency = (time.time() - start) * 1000
        logger.log_request(agent_id, "deploy", "launch", latency, "success",
                          details={"pid": process.pid, "port": port})
        return process
    except Exception as e:
        logger.log_request(agent_id, "deploy", "launch", 0, "failed", error=str(e))
        return None


def check_agent_health(
    agent_id: str,
    url: str,
    logger: StructuredLogger,
    concurrency: ConcurrencyController,
    timeout: int = 5
) -> bool:
    """Check if agent is healthy via /a2a/health (python_a2a endpoint)."""
    if not concurrency.acquire(agent_id, timeout=10):
        logger.log_request(agent_id, "health", "acquire", 0, "failed",
                          error="concurrency_limit")
        return False

    try:
        start = time.time()
        # python_a2a exposes health at /a2a/health
        response = requests.get(f"{url}/a2a/health", timeout=timeout)
        latency = (time.time() - start) * 1000

        if response.status_code == 200:
            logger.log_request(agent_id, "health", "check", latency, "success")
            return True
        else:
            logger.log_request(agent_id, "health", "check", latency, "failed",
                              error=f"http_{response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        logger.log_request(agent_id, "health", "check", 0, "failed",
                          error="connection_refused")
        return False
    except requests.exceptions.Timeout:
        logger.log_request(agent_id, "health", "check", timeout * 1000, "failed",
                          error="timeout")
        return False
    except Exception as e:
        logger.log_request(agent_id, "health", "check", 0, "failed", error=str(e))
        return False
    finally:
        concurrency.release(agent_id)


def register_agent(
    agent_id: str,
    agent_url: str,
    registry_url: str,
    logger: StructuredLogger,
    concurrency: ConcurrencyController
) -> bool:
    """Register agent with NEST registry."""
    if not concurrency.acquire(agent_id, timeout=10):
        logger.log_request(agent_id, "registry", "acquire", 0, "failed",
                          error="concurrency_limit")
        return False

    try:
        start = time.time()
        response = requests.post(
            f"{registry_url}/register",
            json={
                "agent_id": agent_id,
                "agent_url": agent_url,
                "capabilities": ["data_consumer", "registry_lookup", "a2a_communication"]
            },
            timeout=10
        )
        latency = (time.time() - start) * 1000

        if response.status_code in [200, 201]:
            logger.log_request(agent_id, "registry", "register", latency, "success")
            return True
        else:
            logger.log_request(agent_id, "registry", "register", latency, "failed",
                              error=f"http_{response.status_code}")
            return False
    except Exception as e:
        logger.log_request(agent_id, "registry", "register", 0, "failed", error=str(e))
        return False
    finally:
        concurrency.release(agent_id)


# =============================================================================
# SMOKE TEST
# =============================================================================

def run_discovery_request(
    agent_id: str,
    registry_url: str,
    logger: StructuredLogger,
    concurrency: ConcurrencyController,
    request_num: int
) -> bool:
    """Run a single discovery request from an agent."""
    if not concurrency.acquire(agent_id, timeout=30):
        logger.log_request(agent_id, "smoke", f"discovery_{request_num}",
                          0, "failed", error="concurrency_limit")
        return False

    try:
        # Add per-request jitter
        jitter = random.uniform(0, 0.5)
        time.sleep(jitter)

        start = time.time()
        # Query registry for available agents
        response = requests.get(
            f"{registry_url}/list",
            timeout=10
        )
        latency = (time.time() - start) * 1000

        if response.status_code == 200:
            agents = response.json()
            logger.log_request(agent_id, "smoke", f"discovery_{request_num}",
                              latency, "success",
                              details={"agents_found": len(agents) if isinstance(agents, list) else 0})
            return True
        else:
            logger.log_request(agent_id, "smoke", f"discovery_{request_num}",
                              latency, "failed", error=f"http_{response.status_code}")
            return False
    except Exception as e:
        logger.log_request(agent_id, "smoke", f"discovery_{request_num}",
                          0, "failed", error=str(e))
        return False
    finally:
        concurrency.release(agent_id)


def run_smoke_test(
    agent_ids: List[str],
    registry_url: str,
    logger: StructuredLogger,
    concurrency: ConcurrencyController,
    requests_per_agent: int = SMOKE_TEST_REQUESTS_PER_AGENT,
    duration_minutes: int = SMOKE_TEST_DURATION_MINUTES
) -> Dict:
    """Run smoke test for a batch of agents."""
    print(f"\n{'='*60}")
    print(f"SMOKE TEST: {len(agent_ids)} agents, {requests_per_agent} requests each")
    print(f"Duration: {duration_minutes} minutes")
    print(f"{'='*60}\n")

    start_time = time.time()
    end_time = start_time + (duration_minutes * 60)

    results = {agent_id: {"success": 0, "failed": 0} for agent_id in agent_ids}

    def agent_smoke_test(agent_id: str):
        """Run smoke test for a single agent."""
        for req_num in range(1, requests_per_agent + 1):
            if time.time() > end_time:
                break

            # Spread requests over time
            delay = random.uniform(0, duration_minutes * 60 / requests_per_agent)
            time.sleep(min(delay, end_time - time.time()))

            if time.time() > end_time:
                break

            success = run_discovery_request(
                agent_id, registry_url, logger, concurrency, req_num
            )
            if success:
                results[agent_id]["success"] += 1
            else:
                results[agent_id]["failed"] += 1

    # Run smoke tests in parallel
    with ThreadPoolExecutor(max_workers=min(len(agent_ids), GLOBAL_CONCURRENCY)) as executor:
        futures = [executor.submit(agent_smoke_test, aid) for aid in agent_ids]
        for future in futures:
            try:
                future.result(timeout=duration_minutes * 60 + 30)
            except Exception as e:
                print(f"Smoke test error: {e}")

    # Calculate summary
    total_success = sum(r["success"] for r in results.values())
    total_failed = sum(r["failed"] for r in results.values())
    total = total_success + total_failed

    return {
        "agents_tested": len(agent_ids),
        "total_requests": total,
        "successes": total_success,
        "failures": total_failed,
        "success_rate": round(total_success / total * 100, 2) if total > 0 else 0,
        "per_agent_results": results
    }


# =============================================================================
# BATCH DEPLOYMENT
# =============================================================================

def deploy_batch(
    batch_name: str,
    manifest: Dict,
    registry_url: str,
    host: str,
    run_tag: str
) -> Dict:
    """Deploy a batch of consumers."""
    if batch_name not in BATCHES:
        raise ValueError(f"Unknown batch: {batch_name}")

    consumer_numbers = BATCHES[batch_name]
    exp_dir = RESULTS_DIR / "exp1" / f"batch_{batch_name.lower()}"
    logger = StructuredLogger(run_tag, exp_dir)
    concurrency = ConcurrencyController()

    print(f"\n{'='*60}")
    print(f"DEPLOYING BATCH {batch_name}: consumers {consumer_numbers[0]:03d}-{consumer_numbers[-1]:03d}")
    print(f"Run tag: {run_tag}")
    print(f"Output: {exp_dir}")
    print(f"{'='*60}\n")

    processes = {}
    deployed_agents = []

    # Deploy each consumer
    for num in consumer_numbers:
        agent = get_consumer_by_number(manifest, num)
        if not agent:
            print(f"Warning: consumer_{num:03d} not found in manifest")
            continue

        agent_id = agent["agent_id"]
        port = agent["port"]
        agent_url = f"http://{host}:{port}"

        print(f"Deploying {agent_id}...")

        # Launch agent
        process = launch_consumer(agent, registry_url, logger, concurrency)
        if process:
            processes[agent_id] = process
            deployed_agents.append(agent_id)

    # Wait for agents to initialize (Flask/python_a2a needs ~8-10s to bind port)
    # Scale wait time with batch size: 10s base + 0.5s per agent
    wait_time = max(10, 10 + len(deployed_agents) // 2)
    print(f"\nWaiting for agents to initialize ({wait_time}s for {len(deployed_agents)} agents)...")
    time.sleep(wait_time)

    # Health check and registration
    print(f"\nValidating and registering agents...")
    healthy_agents = []

    for agent_id in deployed_agents:
        agent = get_consumer_by_number(manifest, int(agent_id.split("_")[1]))
        port = agent["port"]
        agent_url = f"http://{host}:{port}"

        # Health check with retries (5 attempts, 2s apart)
        for attempt in range(5):
            if check_agent_health(agent_id, agent_url, logger, concurrency):
                healthy_agents.append(agent_id)
                # Register with NEST
                register_agent(agent_id, agent_url, registry_url, logger, concurrency)
                break
            time.sleep(2)

    print(f"\nHealthy agents: {len(healthy_agents)}/{len(deployed_agents)}")

    # Run smoke test
    if healthy_agents:
        smoke_results = run_smoke_test(
            healthy_agents, registry_url, logger, concurrency,
            requests_per_agent=SMOKE_TEST_REQUESTS_PER_AGENT,
            duration_minutes=SMOKE_TEST_DURATION_MINUTES
        )
    else:
        smoke_results = {"error": "No healthy agents to test"}

    # Save summary
    summary = logger.save_summary()
    summary["batch"] = batch_name
    summary["deployed"] = len(deployed_agents)
    summary["healthy"] = len(healthy_agents)
    summary["smoke_test"] = smoke_results

    # Save extended summary
    with open(exp_dir / f"{run_tag}_full_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n{'='*60}")
    print(f"BATCH {batch_name} COMPLETE")
    print(f"{'='*60}")
    print(f"Deployed: {len(deployed_agents)}")
    print(f"Healthy:  {len(healthy_agents)}")
    print(f"Smoke test success rate: {smoke_results.get('success_rate', 'N/A')}%")
    print(f"{'='*60}\n")

    return {
        "batch": batch_name,
        "processes": processes,
        "summary": summary
    }


def deploy_all_batches(manifest: Dict, registry_url: str, host: str):
    """Deploy all batches in sequence."""
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    all_results = {}
    all_processes = {}

    for batch in ["A", "B", "C"]:
        run_tag = f"batch_{batch.lower()}_{timestamp}"
        result = deploy_batch(batch, manifest, registry_url, host, run_tag)
        all_results[batch] = result["summary"]
        all_processes.update(result["processes"])

        # Brief pause between batches
        if batch != "C":
            print(f"\nPausing before next batch...")
            time.sleep(5)

    # Generate combined summary
    generate_smoke_test_summary(all_results, RESULTS_DIR / "exp1")

    return all_processes


def generate_smoke_test_summary(results: Dict, output_dir: Path):
    """Generate smoke_test_summary.md."""
    output_file = output_dir / "smoke_test_summary.md"

    total_deployed = sum(r.get("deployed", 0) for r in results.values())
    total_healthy = sum(r.get("healthy", 0) for r in results.values())
    total_requests = sum(r.get("smoke_test", {}).get("total_requests", 0) for r in results.values())
    total_success = sum(r.get("smoke_test", {}).get("successes", 0) for r in results.values())

    overall_rate = round(total_success / total_requests * 100, 2) if total_requests > 0 else 0

    # Collect all errors
    all_errors = {}
    for batch, result in results.items():
        for error, count in result.get("error_breakdown", {}).items():
            all_errors[error] = all_errors.get(error, 0) + count

    content = f"""# NEST Smoke Test Summary

**Generated**: {datetime.utcnow().isoformat()}Z

## Overview

| Metric | Value |
|--------|-------|
| Total Consumers Deployed | {total_deployed} |
| Total Healthy | {total_healthy} |
| Health Rate | {round(total_healthy/total_deployed*100, 1) if total_deployed > 0 else 0}% |
| Total Discovery Requests | {total_requests} |
| Successful Requests | {total_success} |
| **Overall Success Rate** | **{overall_rate}%** |

## Batch Results

| Batch | Consumers | Deployed | Healthy | Smoke Success % |
|-------|-----------|----------|---------|-----------------|
"""

    for batch in ["A", "B", "C"]:
        r = results.get(batch, {})
        batch_range = f"{BATCHES[batch][0]:03d}-{BATCHES[batch][-1]:03d}"
        deployed = r.get("deployed", 0)
        healthy = r.get("healthy", 0)
        smoke_rate = r.get("smoke_test", {}).get("success_rate", "N/A")
        content += f"| {batch} | {batch_range} | {deployed} | {healthy} | {smoke_rate}% |\n"

    content += """
## Common Failures

| Error Type | Count |
|------------|-------|
"""

    if all_errors:
        for error, count in sorted(all_errors.items(), key=lambda x: -x[1]):
            content += f"| {error} | {count} |\n"
    else:
        content += "| None | 0 |\n"

    content += """
## Safety Controls Applied

- **Client-side jitter**: 0-1500ms random start delay
- **Per-agent concurrency**: Max 3 concurrent queries
- **Global concurrency**: Max 25 in-flight requests

## Recommendations

"""

    if overall_rate >= 95:
        content += "- System is stable and ready for experiments\n"
    elif overall_rate >= 80:
        content += "- System is mostly stable, investigate failing agents\n"
        content += "- Consider increasing health check retries\n"
    else:
        content += "- System needs attention before proceeding\n"
        content += "- Check registry connectivity\n"
        content += "- Verify agent startup logs\n"

    with open(output_file, "w") as f:
        f.write(content)

    print(f"\nSmoke test summary saved to: {output_file}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    global SMOKE_TEST_DURATION_MINUTES

    parser = argparse.ArgumentParser(description="NEST Batch Deployment with Safety Controls")
    parser.add_argument("--batch", choices=["A", "B", "C", "all"], default="all",
                        help="Batch to deploy (A=001-010, B=011-025, C=026-050, all=sequential)")
    parser.add_argument("--registry", default=DEFAULT_REGISTRY_URL,
                        help="NEST registry URL")
    parser.add_argument("--host", default=DEFAULT_HOST,
                        help="Host for agent URLs")
    parser.add_argument("--smoke-duration", type=int, default=5,
                        help="Smoke test duration in minutes (default: 5)")
    parser.add_argument("--validate-only", action="store_true",
                        help="Only validate existing agents, don't deploy")

    args = parser.parse_args()
    SMOKE_TEST_DURATION_MINUTES = args.smoke_duration

    # Load manifest
    manifest = load_manifest()
    print(f"Loaded manifest: {len(manifest['consumers'])} consumers")

    # Check registry
    try:
        response = requests.get(f"{args.registry}/health", timeout=5)
        if response.status_code != 200:
            print(f"Warning: Registry returned {response.status_code}")
    except Exception as e:
        print(f"Error: Cannot reach registry at {args.registry}: {e}")
        sys.exit(1)

    if args.validate_only:
        print("Validate-only mode not implemented yet")
        sys.exit(0)

    # Deploy
    if args.batch == "all":
        processes = deploy_all_batches(manifest, args.registry, args.host)
    else:
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        run_tag = f"batch_{args.batch.lower()}_{timestamp}"
        result = deploy_batch(args.batch, manifest, args.registry, args.host, run_tag)
        processes = result["processes"]

        # Generate summary for single batch
        generate_smoke_test_summary({args.batch: result["summary"]}, RESULTS_DIR / "exp1")

    # Keep running
    if processes:
        print(f"\n{len(processes)} agents running. Press Ctrl+C to stop all.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping all agents...")
            for agent_id, process in processes.items():
                print(f"  Stopping {agent_id}...")
                process.terminate()
            print("All agents stopped.")


if __name__ == "__main__":
    main()
