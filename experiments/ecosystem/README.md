# Multi-Agent Ecosystem (Budget-Friendly)

One EC2 instance runs a **multi-dataset server** and registers **multiple agents** with the registry. No LLM, no per-agent processes.

- **2-agent**: `config.json` — finance + weather.
- **50-agent**: `config_50_agents.json` — 6 data agents (stock, weather, timestamp, uuid, lorem, countries) + 44 non-data (orchestrator, helper, router, analyst, placeholder). See [DESIGN_50_AGENTS.md](./DESIGN_50_AGENTS.md).

## What runs

- **MultiDatasetServer** (port 8000): serves Data Facts + dataset for `public_stock_ticker` and `public_weather_data`.
- **Registry registration**: each agent in `config.json` is registered with `data_facts_url` pointing at the server.

## Deploy (single EC2, budget-friendly)

```bash
# From NEST root.
# Args: [REGISTRY_URL] [REGION] [INSTANCE_TYPE] [REPO_URL] [CONFIG_NAME]
bash scripts/deploy_ecosystem_single.sh [REGISTRY_URL] [REGION] [INSTANCE_TYPE] [REPO_URL] [CONFIG_NAME]
# 2-agent (default):
bash scripts/deploy_ecosystem_single.sh "http://registry.chat39.com:6900" us-east-1 t3.micro
# 50-agent (6 data + 44 non-data):
bash scripts/deploy_ecosystem_single.sh "http://registry.chat39.com:6900" us-east-1 t3.micro "https://github.com/projnanda/NEST.git" config_50_agents.json
```

- **CONFIG_NAME** defaults to `config.json` (finance + weather). Use `config_50_agents.json` for 50 agents.
- One instance runs the multi-dataset server and registers all agents. No LLM.

## Local run

```bash
export REGISTRY_URL="http://registry.chat39.com:6900"
export DATA_SERVER_PORT=8000
# PUBLIC_URL optional; default localhost:8000
python experiments/ecosystem/run_ecosystem.py
```

## Config

- **Data agents**: `agent_id`, `dataset_id`, `provider` (`stock` | `weather` | `timestamp` | `uuid` | `lorem` | `countries`).
- **Non-data agents**: `agent_id`, `has_data: false`. Registered with registry only; no `data_facts_url`.
- **config.json**: 2 agents. **config_50_agents.json**: 50 agents (6 data, 44 non-data).

## Endpoints

- `GET /health` — server health, lists datasets.
- `GET /` — index with `datasets` and `data_facts_urls`.
- `GET /data_facts/public_stock_ticker.json` — Data Facts for stock.
- `GET /data_facts/public_weather_data.json` — Data Facts for weather.
- `GET /public-stock-ticker` — stock dataset.
- `GET /public-weather-data` — weather dataset.

## Experiments

1. Deploy ecosystem, then `export ECOSYSTEM_IP=<public-IP>`.
2. **Exp 1 multi-agent**:
   - **2-agent**: `--config config_ecosystem.json` (baseline: stock + weather; treatment: discover both).
   - **50-agent**: `--config config_ecosystem_50.json` (baseline: direct GET to 6 data endpoints; treatment: discover among 50 agents, use only those with `data_facts_url`).
3. **Exp 2**: Unchanged (simulated freshness).
