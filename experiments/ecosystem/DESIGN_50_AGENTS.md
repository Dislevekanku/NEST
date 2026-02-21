# 50-Agent Ecosystem: Design & Experiment Ideas

## Goal

Deploy **50 agents** on NEST, register them with the registry, and run experiments. Some agents **have data** (Data Facts + dataset); others **do not** (registry-only). This models a realistic ecosystem: many agents, but only a subset serve discoverable datasets.

---

## Agent Mix

| Type | Count | Description |
|------|-------|-------------|
| **Data agents** | ~15–20 | Have `data_facts_url`; serve a dataset via Data Facts. |
| **Non-data agents** | ~30–35 | Registry-only. No `data_facts_url`. Used for discovery noise, orchestration, placeholders. |

### Data Agents (have Data Facts + dataset)

Each maps to a **provider** and a **dataset_id**. All run on one **MultiDatasetServer** (single EC2, single process).

| # | agent_id | dataset_id | provider | source |
|---|----------|------------|----------|--------|
| 1 | finance-agent | public_stock_ticker | stock | yfinance |
| 2 | weather-agent | public_weather_data | weather | Open-Meteo |
| 3 | time-agent | public_timestamp | timestamp | generated (no API) |
| 4 | uuid-agent | public_uuid | uuid | generated (no API) |
| 5 | lorem-agent | public_lorem | lorem | static |
| 6 | countries-agent | public_countries | countries | static (ISO) |
| 7 | quotes-agent | public_quotes | quotes | quotable.io or static |
| 8 | jokes-agent | public_jokes | jokes | icanhazdadjoke or static |
| 9 | crypto-agent | public_crypto | crypto | CoinGecko or synthetic |
| 10 | fx-agent | public_fx_rates | fx | synthetic / free API |
| 11 | holidays-agent | public_holidays | holidays | static / pyholidays |
| 12 | products-agent | public_products | products | dummyjson or static |
| 13 | users-agent | public_random_users | users | synthetic |
| 14 | geo-agent | public_geo_demo | geo | ip-api or static |
| 15 | nasa-agent | public_nasa_apod | nasa | NASA API (optional key) |

We implement a **first batch** (e.g. timestamp, uuid, lorem, countries) as synthetic/static; add more over time.

### Non-Data Agents (registry-only)

No provider, no Data Facts. Registered with `agent_id` + `agent_url` only. Roles are **conceptual** (for discovery variety and experiments):

| Role | Example IDs | Purpose |
|------|-------------|---------|
| **Orchestrator** | orchestrator-01 … orchestrator-05 | Route to other agents; no dataset. |
| **Helper** | helper-format-01 … helper-format-03, helper-validate-01 … helper-validate-03 | Format / validate; no dataset. |
| **Router** | router-01 … router-05 | Route requests; no dataset. |
| **Analyst** | analyst-01 … analyst-05 | Analytics; no dataset. |
| **Placeholder** | placeholder-01 … placeholder-15 | Fill registry for scaling experiments. |

`agent_url` can point at the same ecosystem base URL (e.g. `http://<ecosystem-ip>:8000/`) or a stub. Experiments filter by `data_facts_url` when they need “agents with data.”

---

## Deployment (Budget-Friendly)

- **One EC2** (e.g. t3.small for more providers; t3.micro if we keep minimal).
- **One MultiDatasetServer** — all data providers run in a single Flask app on port 8000.
- **One registration script** — iterates over 50 agents:
  - **Data agents:** register with `agent_id`, `agent_url`, `data_facts_url`.
  - **Non-data agents:** register with `agent_id`, `agent_url` only.
- **No per-agent processes**, no LLM. Same deploy flow as `deploy_ecosystem_single.sh`.

---

## Experiment Ideas

### 1. Discovery efficiency (Exp 1, extended)

- **Baseline:** Direct GET to **known** dataset endpoints (only the ~15 data URLs). Random pick per query.
- **Treatment:** Registry discovery over **50 agents**. Filter to those with `data_facts_url`; randomly pick one; fetch Data Facts → dataset.
- **Metrics:** Time-to-first-data, failed lookups, % success. Compare baseline vs treatment when the registry has 50 agents but only ~15 have data.

### 2. Precision of discovery

- **Setup:** 50 agents, 15 with data, 35 without.
- **Metric:** “Time / number of registry or filter steps until we **first** hit an agent with data.”
- **Variants:** Keyword search vs list-all-then-filter; measure how often we “waste” lookups on non-data agents.

### 3. Scaling N

- Use **synthetic registry entries** (or duplicate agent definitions) to simulate 50, 200, 1000 agents.
- Fix the **number of data agents** (e.g. 15). Vary **total** N.
- **Metrics:** Discovery latency, success rate, optional “time to first data agent” as N grows.

### 4. Staleness / TTL (Exp 2)

- Unchanged for now (simulated). Later: point at **real** data endpoints and optionally inject staleness for a subset of data agents.

### 5. Mixed workload

- **Queries:** Some ask for “any dataset,” some for “finance,” “weather,” etc.
- **Metrics:** Success rate and latency by “intent” (keyword-specific vs broad).

---

## Config & Schema

### Ecosystem config (`config_50_agents.json`)

```json
{
  "registry_url": "http://registry.chat39.com:6900",
  "data_server_port": 8000,
  "agents": [
    { "agent_id": "finance-agent", "dataset_id": "public_stock_ticker", "provider": "stock" },
    { "agent_id": "weather-agent", "dataset_id": "public_weather_data", "provider": "weather" },
    { "agent_id": "time-agent", "dataset_id": "public_timestamp", "provider": "timestamp" },
    { "agent_id": "orchestrator-01", "has_data": false },
    { "agent_id": "placeholder-01", "has_data": false }
  ]
}
```

- **Data agents:** `provider` + `dataset_id` (optional `agent_name`). `has_data` true by default when `provider` is set.
- **Non-data agents:** `has_data: false`. No `provider` or `dataset_id`.

### Exp 1 multi-agent config

- `use_multiple_agents: true`
- `dataset_endpoints`: list of **data** endpoints only (for baseline).
- **Treatment:** discover from registry → filter `data_facts_url` present → randomly pick → fetch Data Facts + dataset.

---

## Implementation Phases

1. **Phase 1:** Add synthetic/static providers (timestamp, uuid, lorem, countries). Extend ecosystem config to support `has_data: false`. Implement `config_50_agents.json` with 50 agents (~15 data, ~35 non-data). Update `run_ecosystem` to register both types. *(Done.)*
2. **Phase 2:** Deploy single EC2, register 50 agents, run Exp 1 with 50-agent config. Optionally add more providers (quotes, jokes, etc.). See **Phase 2: Deploy 50 agents** below.
3. **Phase 3:** Add experiments 2–5 (precision, scaling N, mixed workload) as separate runners or config flags.

---

## How the Finance Agent Was Deployed (vs 50-Agent Ecosystem)

### Finance + Consumer deployment (`deploy_finance_consumer_agents.sh`)

- **Two EC2 instances**: one for **finance-feed-agent**, one for **data-consumer-agent**.
- **Finance EC2**:
  - Clones NEST → runs `examples/finance_feed_agent.py`.
  - **A2A** on port **6000** (Agent-to-Agent protocol).
  - **Data Facts + stock dataset** on port **8000** (Flask).
  - Registers with the **registry** (Agent Facts + `data_facts_url`) via the NANDA adapter inside the agent. Uses **Anthropic API key**.
- **Consumer EC2**:
  - Clones NEST → runs `examples/data_consumer_agent.py`.
  - **A2A** on port **6001**.
  - Discovers finance via **registry**, reads **Data Facts** from `data_facts_url`, then fetches dataset. Uses **FINANCE_FEED_AGENT_URL** (finance’s public IP).
- **Security group:** `nanda-finance-consumer-agents`. Ports: 22, 6000, 6001, 8000.
- **Key:** `nanda-finance-consumer-key.pem`.

**Deploy command:**
```bash
bash scripts/deploy_finance_consumer_agents.sh "<ANTHROPIC_API_KEY>" "http://registry.chat39.com:6900" us-east-1 t3.micro
```

### 50-agent ecosystem deployment (`deploy_ecosystem_single.sh` / `deploy_ecosystem_50.ps1`)

- **One EC2 instance**: runs `experiments/ecosystem/run_ecosystem.py`.
- **MultiDatasetServer** (single Flask app) on port **8000**: serves 6 **data** providers (stock, weather, timestamp, uuid, lorem, countries) and their Data Facts.
- **No A2A**, no LLM, no per-agent processes. **RegistryClient** registers **50 agents**:
  - **6 data agents:** `agent_id`, `agent_url`, `data_facts_url` (points at MultiDatasetServer).
  - **44 non-data agents:** `agent_id`, `agent_url` only.
- **Security group:** `nanda-ecosystem`. Ports: 22, 8000.
- **Key:** `nanda-ecosystem-key.pem`.

**Difference:** Finance deployment = full NEST agents (A2A, LLM, Agent Facts). 50-agent deployment = lightweight **registry entries** + one **multi-dataset server**; experiments use **registry → Data Facts → dataset**, not A2A.

---

## Phase 2: Deploy 50 agents

**Prerequisites:** AWS CLI configured (`aws configure`), permissions for EC2 `RunInstances`, `CreateSecurityGroup`, `CreateKeyPair`, etc. Use a **fork** of NEST with Phase 1 code (ecosystem, providers, `config_50_agents.json`) as `REPO_URL` if upstream does not have it.

### Deploy (single EC2, 50-agent)

**Bash (Linux / Git Bash):**
```bash
cd NEST
bash scripts/deploy_ecosystem_single.sh "http://registry.chat39.com:6900" us-east-1 t3.micro "https://github.com/YOUR_USER/NEST.git" config_50_agents.json
```

**PowerShell (Windows):**
```powershell
cd NEST\scripts
.\deploy_ecosystem_50.ps1 -RegistryUrl "http://registry.chat39.com:6900" -Region us-east-1 -InstanceType t3.micro -RepoUrl "https://github.com/YOUR_USER/NEST.git"
```

Replace `YOUR_USER` with your GitHub user (or use `projnanda/NEST` if that repo has the 50-agent code). The script creates one t3.micro, runs the multi-dataset server + registration for 50 agents (6 data, 44 non-data).

### After deploy

1. Wait ~90 seconds for the ecosystem to start.
2. Set `ECOSYSTEM_IP` to the instance public IP (printed by the deploy script).
3. Run **Exp 1** with the 50-agent config:

```bash
export ECOSYSTEM_IP=<public-IP>   # or $env:ECOSYSTEM_IP = "<public-IP>" on PowerShell
cd NEST/experiments/exp1_discovery_efficiency
python run.py --sweep 50,200 --config config_ecosystem_50.json
```

### Verify

- **Health:** `http://<ECOSYSTEM_IP>:8000/health`
- **Data Facts (e.g. stock):** `http://<ECOSYSTEM_IP>:8000/data_facts/public_stock_ticker.json`
- **Registry:** List agents; you should see 50 (6 with `data_facts_url`, 44 without).

### Troubleshooting

- **"Could not create or find security group"**  
  Your IAM user may lack `ec2:CreateSecurityGroup` / `ec2:DescribeSecurityGroups`. Use an existing security group:
  1. Reuse the **finance** SG: `nanda-finance-consumer-agents` (ensure ports **22** and **8000** are open).
  2. Set `SECURITY_GROUP_ID` to its ID, then run the deploy again:
     ```powershell
     $id = (aws ec2 describe-security-groups --group-names "nanda-finance-consumer-agents" --region us-east-1 --query 'SecurityGroups[0].GroupId' --output text)
     $env:SECURITY_GROUP_ID = $id
     .\deploy_ecosystem_50.ps1 -RegistryUrl "http://registry.chat39.com:6900" -Region us-east-1 -InstanceType t3.micro
     ```
  If you use the finance SG, add ingress for **8000** if not already open:
  `aws ec2 authorize-security-group-ingress --group-id $id --protocol tcp --port 8000 --cidr 0.0.0.0/0 --region us-east-1`
- **AWS "Access denied"**  
  Run `aws configure` and ensure your user has EC2 `RunInstances`, `CreateKeyPair`, and (if not using existing SG) `CreateSecurityGroup` / `AuthorizeSecurityGroupIngress`.

---

## Summary

- **50 agents:** ~15–20 with data, ~30–35 without.
- **Single EC2**, one multi-dataset server, one registration script.
- **Experiments:** Discovery over 50 agents (only some have data), precision, scaling N, mixed workload.
- **Config:** `config_50_agents.json`; `has_data` distinguishes data vs non-data agents.
