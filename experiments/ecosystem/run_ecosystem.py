#!/usr/bin/env python3
"""
Ecosystem runner: multi-dataset server + registry registration.

Runs one MultiDatasetServer on DATA_SERVER_PORT. Registers **data agents** with
data_facts_url; **non-data agents** with agent_id + agent_url only (no Data Facts).
Supports config_50_agents.json: 50 agents, mix of data vs non-data.

Env:
  REGISTRY_URL, PUBLIC_URL (or EC2 metadata), DATA_SERVER_PORT, CONFIG_PATH.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from nanda_core.dataset.server import MultiDatasetServer
from nanda_core.dataset.providers.stock import StockDatasetProvider
from nanda_core.dataset.providers.weather import WeatherDatasetProvider
from nanda_core.dataset.providers.timestamp import TimestampDatasetProvider
from nanda_core.dataset.providers.uuid_provider import UuidDatasetProvider
from nanda_core.dataset.providers.lorem import LoremDatasetProvider
from nanda_core.dataset.providers.countries import CountriesDatasetProvider
from nanda_core.core.registry_client import RegistryClient

PROVIDERS = {
    "stock": StockDatasetProvider,
    "weather": WeatherDatasetProvider,
    "timestamp": TimestampDatasetProvider,
    "uuid": UuidDatasetProvider,
    "lorem": LoremDatasetProvider,
    "countries": CountriesDatasetProvider,
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
            port = os.environ.get("DATA_SERVER_PORT", "8000")
            return f"http://{ip}:{port}"
    except Exception:
        pass
    port = os.environ.get("DATA_SERVER_PORT", "8000")
    return f"http://localhost:{port}"


def main() -> int:
    config_path = Path(os.environ.get("CONFIG_PATH", Path(__file__).parent / "config.json"))
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    registry_url = os.environ.get("REGISTRY_URL") or cfg.get("registry_url")
    port = int(os.environ.get("DATA_SERVER_PORT") or cfg.get("data_server_port", 8000))
    public_url = get_public_url()
    if "localhost" in public_url and "PUBLIC_URL" not in os.environ:
        public_url = f"http://localhost:{port}"

    data_agents = [a for a in cfg["agents"] if a.get("has_data", True) and a.get("provider")]
    non_data_agents = [a for a in cfg["agents"] if a.get("has_data") is False]

    providers: list[tuple] = []
    for ag in data_agents:
        pid = ag.get("provider", "stock")
        cls = PROVIDERS.get(pid)
        if not cls:
            raise ValueError(f"unknown provider: {pid}")
        providers.append((cls(), ag["agent_id"]))

    if providers:
        server = MultiDatasetServer(providers, port=port, public_url=public_url)
        server.start()
        time.sleep(1)
    else:
        server = None

    if registry_url:
        client = RegistryClient(registry_url)
        for ag, (prov, _) in zip(data_agents, providers):
            df_url = server.get_data_facts_url(prov)
            ok = client.register_agent(
                agent_id=ag["agent_id"],
                agent_url=public_url,
                data_facts_url=df_url,
            )
            print(f"  registered {ag['agent_id']} (data) -> {df_url} ({'ok' if ok else 'fail'})")
        for ag in non_data_agents:
            ok = client.register_agent(
                agent_id=ag["agent_id"],
                agent_url=public_url,
            )
            print(f"  registered {ag['agent_id']} (no data) ({'ok' if ok else 'fail'})")
    else:
        print("  no REGISTRY_URL; skip registration")

    print("  ecosystem running; exit with Ctrl+C.")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
