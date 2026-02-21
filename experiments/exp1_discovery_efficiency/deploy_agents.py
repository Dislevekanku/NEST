#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NEST Agent Deployment Automation Script

Deploys agents from agents_manifest_v1.json:
- Launches agents (local processes or containers)
- Registers them in NEST registry
- Validates each agent via health check
- Outputs deploy_report.json with status

Usage:
    # Deploy all agents locally
    python deploy_agents.py --mode local --count 12

    # Deploy specific agents
    python deploy_agents.py --agents provider_finance_01,consumer_001,consumer_002

    # Validate only (no deployment)
    python deploy_agents.py --validate-only
"""
import argparse
import json
import os
import sys
import time
import subprocess
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add parent paths for imports
SCRIPT_DIR = Path(__file__).parent.absolute()
NEST_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(NEST_ROOT))

# Configuration
MANIFEST_FILE = SCRIPT_DIR / "agents_manifest_v1.json"
DEPLOY_REPORT_FILE = SCRIPT_DIR / "deploy_report.json"
DEFAULT_REGISTRY_URL = "http://registry.chat39.com:6900"
DEFAULT_HOST = "localhost"
HEALTH_CHECK_TIMEOUT = 5
STARTUP_WAIT = 2

# Agent scripts
PROVIDER_SCRIPT = NEST_ROOT / "examples" / "finance_feed_agent_refactored.py"
CONSUMER_SCRIPT = NEST_ROOT / "examples" / "data_consumer_agent_refactored.py"


def load_manifest() -> Dict:
    """Load the agents manifest file."""
    if not MANIFEST_FILE.exists():
        raise FileNotFoundError(f"Manifest file not found: {MANIFEST_FILE}")

    with open(MANIFEST_FILE, "r") as f:
        return json.load(f)


def check_health(url: str, timeout: int = HEALTH_CHECK_TIMEOUT) -> Dict[str, Any]:
    """Check agent health endpoint (python_a2a uses /a2a/health)."""
    health_url = f"{url}/a2a/health"
    try:
        response = requests.get(health_url, timeout=timeout)
        if response.status_code == 200:
            return {"status": "healthy", "response": response.json()}
        else:
            return {"status": "unhealthy", "error": f"HTTP {response.status_code}"}
    except requests.exceptions.ConnectionError:
        return {"status": "unreachable", "error": "Connection refused"}
    except requests.exceptions.Timeout:
        return {"status": "timeout", "error": "Request timed out"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def check_a2a(url: str, timeout: int = HEALTH_CHECK_TIMEOUT) -> Dict[str, Any]:
    """Check A2A endpoint with a simple ping message."""
    a2a_url = f"{url}/a2a"
    try:
        # Send a minimal A2A message
        payload = {
            "content": {"text": "ping", "type": "text"},
            "role": "user",
            "conversation_id": f"deploy-check-{int(time.time())}"
        }
        response = requests.post(a2a_url, json=payload, timeout=timeout)
        if response.status_code == 200:
            return {"status": "responsive", "response_code": 200}
        else:
            return {"status": "error", "error": f"HTTP {response.status_code}"}
    except requests.exceptions.ConnectionError:
        return {"status": "unreachable", "error": "Connection refused"}
    except requests.exceptions.Timeout:
        return {"status": "timeout", "error": "Request timed out"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def check_data_facts(url: str, timeout: int = HEALTH_CHECK_TIMEOUT) -> Dict[str, Any]:
    """Check Data Facts endpoint (for providers)."""
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code == 200:
            data = response.json()
            return {"status": "available", "dataset_id": data.get("dataset_id", "unknown")}
        else:
            return {"status": "error", "error": f"HTTP {response.status_code}"}
    except requests.exceptions.ConnectionError:
        return {"status": "unreachable", "error": "Connection refused"}
    except requests.exceptions.Timeout:
        return {"status": "timeout", "error": "Request timed out"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def check_registry(registry_url: str, agent_id: str) -> Dict[str, Any]:
    """Check if agent is registered in NEST registry."""
    lookup_url = f"{registry_url}/lookup/{agent_id}"
    try:
        response = requests.get(lookup_url, timeout=HEALTH_CHECK_TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            return {"status": "registered", "agent_url": data.get("agent_url")}
        elif response.status_code == 404:
            return {"status": "not_registered", "error": "Agent not found in registry"}
        else:
            return {"status": "error", "error": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def validate_agent(agent: Dict, host: str, registry_url: str) -> Dict[str, Any]:
    """Validate a single agent by checking all endpoints."""
    agent_id = agent["agent_id"]
    port = agent["port"]
    role = agent.get("role", "consumer")
    base_url = f"http://{host}:{port}"

    result = {
        "agent_id": agent_id,
        "role": role,
        "url": base_url,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "checks": {}
    }

    # Check health endpoint
    result["checks"]["health"] = check_health(base_url)

    # Check A2A endpoint
    result["checks"]["a2a"] = check_a2a(base_url)

    # Check Data Facts (providers only)
    if role == "provider":
        data_server_port = agent.get("data_server_port", 8000)
        data_facts_url = agent.get("data_facts_url_template", "").format(
            host=host, data_server_port=data_server_port
        )
        if data_facts_url:
            result["checks"]["data_facts"] = check_data_facts(data_facts_url)
            result["data_facts_url"] = data_facts_url

    # Check registry registration
    result["checks"]["registry"] = check_registry(registry_url, agent_id)

    # Determine overall status
    health_ok = result["checks"]["health"]["status"] == "healthy"
    a2a_ok = result["checks"]["a2a"]["status"] == "responsive"

    if health_ok and a2a_ok:
        result["status"] = "operational"
    elif health_ok or a2a_ok:
        result["status"] = "partial"
    else:
        result["status"] = "failed"

    return result


def launch_provider_agent(agent: Dict, host: str, registry_url: str, public_url: Optional[str] = None) -> subprocess.Popen:
    """Launch a provider agent process."""
    env = os.environ.copy()
    env["AGENT_ID"] = agent["agent_id"]
    env["AGENT_NAME"] = agent["agent_name"]
    env["PORT"] = str(agent["port"])
    env["DATA_SERVER_PORT"] = str(agent.get("data_server_port", 8000))
    env["REGISTRY_URL"] = registry_url

    if "stock_tickers" in agent:
        env["STOCK_TICKERS"] = ",".join(agent["stock_tickers"])

    if public_url:
        env["PUBLIC_URL"] = public_url

    # Use finance feed agent for now (weather provider would need a separate script)
    script = PROVIDER_SCRIPT
    if "weather" in agent["agent_id"]:
        print(f"  Note: Weather provider uses same script as finance (mock mode)")

    process = subprocess.Popen(
        [sys.executable, str(script)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(NEST_ROOT)
    )
    return process


def launch_consumer_agent(agent: Dict, host: str, registry_url: str, public_url: Optional[str] = None) -> subprocess.Popen:
    """Launch a consumer agent process."""
    env = os.environ.copy()
    env["AGENT_ID"] = agent["agent_id"]
    env["AGENT_NAME"] = agent["agent_name"]
    env["PORT"] = str(agent["port"])
    env["REGISTRY_URL"] = registry_url

    if public_url:
        env["PUBLIC_URL"] = public_url

    process = subprocess.Popen(
        [sys.executable, str(CONSUMER_SCRIPT)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(NEST_ROOT)
    )
    return process


def deploy_agents(
    manifest: Dict,
    mode: str = "local",
    count: int = 12,
    agents_filter: Optional[List[str]] = None,
    host: str = DEFAULT_HOST,
    registry_url: str = DEFAULT_REGISTRY_URL
) -> Dict[str, Any]:
    """
    Deploy agents from manifest.

    Args:
        manifest: Loaded agents manifest
        mode: Deployment mode (local, docker, ec2)
        count: Number of agents to deploy (providers + consumers)
        agents_filter: Specific agent IDs to deploy
        host: Host for agent URLs
        registry_url: NEST registry URL

    Returns:
        Deployment report dictionary
    """
    report = {
        "deployment_id": f"deploy_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "mode": mode,
        "registry_url": registry_url,
        "host": host,
        "agents": {},
        "summary": {
            "total_requested": 0,
            "deployed": 0,
            "validated": 0,
            "failed": 0
        }
    }

    processes = {}
    agents_to_deploy = []

    # Build list of agents to deploy
    providers = manifest.get("providers", [])
    consumers = manifest.get("consumers", [])

    if agents_filter:
        # Deploy specific agents
        for agent in providers + consumers:
            if agent["agent_id"] in agents_filter:
                agents_to_deploy.append(agent)
    else:
        # Deploy providers first, then consumers up to count
        agents_to_deploy.extend(providers)
        remaining = count - len(providers)
        if remaining > 0:
            agents_to_deploy.extend(consumers[:remaining])

    report["summary"]["total_requested"] = len(agents_to_deploy)

    print(f"\n{'='*60}")
    print(f"NEST Agent Deployment")
    print(f"{'='*60}")
    print(f"Mode: {mode}")
    print(f"Registry: {registry_url}")
    print(f"Agents to deploy: {len(agents_to_deploy)}")
    print(f"{'='*60}\n")

    # Deploy agents
    for agent in agents_to_deploy:
        agent_id = agent["agent_id"]
        role = agent.get("role", "consumer")
        port = agent["port"]

        print(f"Deploying {agent_id} ({role}) on port {port}...")

        try:
            if mode == "local":
                if role == "provider":
                    process = launch_provider_agent(agent, host, registry_url)
                else:
                    process = launch_consumer_agent(agent, host, registry_url)
                processes[agent_id] = process
                report["agents"][agent_id] = {
                    "status": "launched",
                    "pid": process.pid,
                    "port": port,
                    "role": role
                }
                report["summary"]["deployed"] += 1
                print(f"  Launched with PID {process.pid}")
            else:
                print(f"  Mode '{mode}' not yet implemented")
                report["agents"][agent_id] = {"status": "skipped", "error": f"Mode {mode} not implemented"}
        except Exception as e:
            print(f"  Failed: {e}")
            report["agents"][agent_id] = {"status": "failed", "error": str(e)}
            report["summary"]["failed"] += 1

    # Wait for agents to start
    if processes:
        print(f"\nWaiting {STARTUP_WAIT}s for agents to initialize...")
        time.sleep(STARTUP_WAIT)

    # Validate agents
    print(f"\nValidating deployed agents...")
    print("-" * 40)

    for agent in agents_to_deploy:
        agent_id = agent["agent_id"]
        if agent_id in report["agents"] and report["agents"][agent_id].get("status") == "launched":
            print(f"Validating {agent_id}...", end=" ")
            validation = validate_agent(agent, host, registry_url)

            # Update report
            report["agents"][agent_id].update({
                "url": validation["url"],
                "validation": validation["checks"],
                "overall_status": validation["status"]
            })

            if "data_facts_url" in validation:
                report["agents"][agent_id]["data_facts_url"] = validation["data_facts_url"]

            if validation["status"] == "operational":
                report["summary"]["validated"] += 1
                print("OK")
            elif validation["status"] == "partial":
                print("PARTIAL")
            else:
                report["summary"]["failed"] += 1
                print("FAILED")

    # Summary
    print(f"\n{'='*60}")
    print("DEPLOYMENT SUMMARY")
    print(f"{'='*60}")
    print(f"Total requested: {report['summary']['total_requested']}")
    print(f"Deployed:        {report['summary']['deployed']}")
    print(f"Validated:       {report['summary']['validated']}")
    print(f"Failed:          {report['summary']['failed']}")
    print(f"{'='*60}")

    # Store processes for cleanup
    report["_processes"] = processes

    return report


def validate_only(
    manifest: Dict,
    host: str = DEFAULT_HOST,
    registry_url: str = DEFAULT_REGISTRY_URL,
    agents_filter: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Validate agents without deploying (assumes they're already running)."""
    report = {
        "validation_id": f"validate_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "registry_url": registry_url,
        "host": host,
        "agents": {},
        "summary": {
            "total_checked": 0,
            "operational": 0,
            "partial": 0,
            "failed": 0
        }
    }

    providers = manifest.get("providers", [])
    consumers = manifest.get("consumers", [])
    all_agents = providers + consumers

    if agents_filter:
        all_agents = [a for a in all_agents if a["agent_id"] in agents_filter]

    print(f"\n{'='*60}")
    print(f"NEST Agent Validation")
    print(f"{'='*60}")
    print(f"Registry: {registry_url}")
    print(f"Agents to validate: {len(all_agents)}")
    print(f"{'='*60}\n")

    for agent in all_agents:
        agent_id = agent["agent_id"]
        report["summary"]["total_checked"] += 1

        print(f"Validating {agent_id}...", end=" ")
        validation = validate_agent(agent, host, registry_url)

        report["agents"][agent_id] = {
            "role": agent.get("role", "consumer"),
            "url": validation["url"],
            "status": validation["status"],
            "checks": validation["checks"]
        }

        if "data_facts_url" in validation:
            report["agents"][agent_id]["data_facts_url"] = validation["data_facts_url"]

        if validation["status"] == "operational":
            report["summary"]["operational"] += 1
            print("OK")
        elif validation["status"] == "partial":
            report["summary"]["partial"] += 1
            print("PARTIAL")
        else:
            report["summary"]["failed"] += 1
            print("FAILED")

    # Summary
    print(f"\n{'='*60}")
    print("VALIDATION SUMMARY")
    print(f"{'='*60}")
    print(f"Total checked:  {report['summary']['total_checked']}")
    print(f"Operational:    {report['summary']['operational']}")
    print(f"Partial:        {report['summary']['partial']}")
    print(f"Failed:         {report['summary']['failed']}")
    print(f"{'='*60}")

    return report


def save_report(report: Dict, filename: Path = DEPLOY_REPORT_FILE):
    """Save deployment report to JSON file."""
    # Remove non-serializable items
    clean_report = {k: v for k, v in report.items() if not k.startswith("_")}

    with open(filename, "w") as f:
        json.dump(clean_report, f, indent=2)

    print(f"\nReport saved to: {filename}")


def main():
    parser = argparse.ArgumentParser(description="NEST Agent Deployment Automation")
    parser.add_argument("--mode", choices=["local", "docker", "ec2"], default="local",
                        help="Deployment mode")
    parser.add_argument("--count", type=int, default=12,
                        help="Number of agents to deploy (default: 12)")
    parser.add_argument("--agents", type=str, default=None,
                        help="Comma-separated list of specific agent IDs to deploy")
    parser.add_argument("--host", type=str, default=DEFAULT_HOST,
                        help="Host for agent URLs")
    parser.add_argument("--registry", type=str, default=DEFAULT_REGISTRY_URL,
                        help="NEST registry URL")
    parser.add_argument("--validate-only", action="store_true",
                        help="Only validate agents (no deployment)")
    parser.add_argument("--output", type=str, default=None,
                        help="Output file for report")

    args = parser.parse_args()

    # Load manifest
    try:
        manifest = load_manifest()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Parse agent filter
    agents_filter = None
    if args.agents:
        agents_filter = [a.strip() for a in args.agents.split(",")]

    # Run deployment or validation
    if args.validate_only:
        report = validate_only(manifest, args.host, args.registry, agents_filter)
    else:
        report = deploy_agents(
            manifest,
            mode=args.mode,
            count=args.count,
            agents_filter=agents_filter,
            host=args.host,
            registry_url=args.registry
        )

    # Save report
    output_file = Path(args.output) if args.output else DEPLOY_REPORT_FILE
    save_report(report, output_file)

    # Keep processes running if in interactive mode
    if not args.validate_only and "_processes" in report and report["_processes"]:
        print("\nAgents are running. Press Ctrl+C to stop all agents.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping all agents...")
            for agent_id, process in report["_processes"].items():
                print(f"  Stopping {agent_id} (PID {process.pid})...")
                process.terminate()
                process.wait(timeout=5)
            print("All agents stopped.")


if __name__ == "__main__":
    main()
