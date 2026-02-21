# NEST Experiments

Experiment configs, **Data Facts v1** spec, and toggles for technical prep and A/B-style runs.

## Deliverables

| Deliverable | Location |
|-------------|----------|
| **Data Facts v1 — Frozen** | [DATA_FACTS_V1_FROZEN.md](./DATA_FACTS_V1_FROZEN.md) |
| **`/experiments/` folder** | This directory |
| **README** | This file |
| **Experiment config template** | [experiment_config_template.json](./experiment_config_template.json) |

## Contents

| Item | Description |
|------|-------------|
| **[DATA_FACTS_V1_FROZEN.md](./DATA_FACTS_V1_FROZEN.md)** | Data Facts v1 — frozen spec (endpoint, schema, stability) |
| **[experiment_config_template.json](./experiment_config_template.json)** | Experiment config template with Data Facts toggles |
| **[exp1_discovery_efficiency/](./exp1_discovery_efficiency/)** | **Experiment 1: Discovery Efficiency** — Baseline vs Data Facts (N=50, 200), table, plot, summary |
| **[exp2_freshness_correctness/](./exp2_freshness_correctness/)** | **Experiment 2: Freshness Correctness** — TTL not cosmetic; stale vs detected, error-rate comparison, interpretation |
| **[exp3_trust_integrity/](./exp3_trust_integrity/)** | **Experiment 3: Integrity / corruption detection** — Checksum, security relevance |
| **[exp4_security_auth/](./exp4_security_auth/)** | **Experiment 4: Local Security & Auth** — JWT Agent → Gateway → DB; success %, auth latency, expired/malformed token handling |
| **[ecosystem/](./ecosystem/)** | **Multi-agent ecosystem** — one EC2, multi-dataset server; 2-agent or **50-agent** (data + non-data). See [DESIGN_50_AGENTS.md](./ecosystem/DESIGN_50_AGENTS.md). |

## Experiment config template

Use `experiment_config_template.json` as the base for runs. Key toggles:

| Toggle | Type | Description |
|--------|------|-------------|
| **`use_data_facts`** | `bool` | **With Data Facts** (`true`): discover via registry → fetch Data Facts → validate → fetch dataset. **Without** (`false`): fetch dataset directly from `dataset_endpoint` (no Data Facts). |
| **`ttl_enabled`** | `bool` | When using Data Facts: **on** = enforce freshness (TTL); **off** = skip freshness check. |
| **`checksum_enabled`** | `bool` | When using Data Facts: **on** = verify checksum; **off** = skip checksum verification. |

**Config reference:**

- **`use_data_facts=true`**: Use Data Facts. Set either `data_facts_url` (direct URL to Data Facts JSON) or `registry_url` (discover via registry). Optionally `target_agent_id`, `target_dataset_id`, `keywords`.
- **`use_data_facts=false`**: Skip Data Facts. Set `dataset_endpoint` to the raw dataset URL (e.g. `http://host:8000/public-stock-ticker` or `http://host:8000/public_stock_ticker`; see provider route).

## Public Data Facts endpoint (stable)

The Data Facts endpoint is **stable** and defined in [Data Facts v1 — Frozen](./DATA_FACTS_V1_FROZEN.md). Implementations must not change the v1 response shape or semantics.

- **Path**: `GET /data_facts/{dataset_id}.json`
- **Base URL**: e.g. `http://<finance-feed-host>:8000` (or your dataset server)

## Quick start

1. Copy `experiment_config_template.json` and adjust toggles and URLs.
2. Use the dataset client with the config:
   - **Config-driven**: `access_dataset_from_config(config)` from `nanda_core.dataset.client`. Reads `use_data_facts`, `ttl_enabled`, `checksum_enabled`, plus `registry_url` / `data_facts_url` / `dataset_endpoint`.
   - **Direct API**: `discover_and_access_dataset(..., ttl_enabled=..., checksum_enabled=...)` or `fetch_dataset_direct(endpoint)` when `use_data_facts` is `false`.
3. Run your experiment harness (e.g. `experiment/harness/run.py`) or custom runner, feeding it the config.

## Multi-agent ecosystem (budget-friendly)

Deploy **many** agents with public data on **one** EC2 instance:

1. **Deploy**: `bash scripts/deploy_ecosystem_single.sh [REGISTRY_URL] [REGION] [INSTANCE_TYPE]`
2. **Ecosystem** runs a multi-dataset server (stock + weather) and registers `finance-agent`, `weather-agent` with the registry.
3. **Experiments**: Use `config_ecosystem.json` and `ECOSYSTEM_IP` for Exp 1 multi-agent discovery (baseline = direct GET to multiple endpoints; treatment = registry discovery over multiple agents).

See [ecosystem/README.md](./ecosystem/README.md) and [scripts/deploy_ecosystem_single.sh](../scripts/deploy_ecosystem_single.sh).

## Local testing (no deploy)

**Build 50 agents with public data** locally, run **Exp 1** and **Exp 2**, and **redo results**:

1. Start **local registry** (`python experiments/local_registry.py`) and **50-agent ecosystem** (`experiments/ecosystem/run_ecosystem.py` with `config_50_agents.json`, `REGISTRY_URL=http://localhost:6900`, `PUBLIC_URL=http://localhost:8000`).
2. Run **Exp 1** and **Exp 2**: `python experiments/run_exp1_exp2_only.py` (or `--quick` for a faster Exp 1 sweep).

See [LOCAL_TESTING.md](./LOCAL_TESTING.md) for step-by-step commands. Optional one-shot: `python experiments/run_local_experiments.py` (or `--quick`).

## Relation to `experiment/` harness

The **`experiment/`** folder holds the generic harness (logging, tiers, fixtures). **`experiments/`** holds Data-Facts-specific config and the frozen v1 spec. Use the experiment config template here for Data Facts A/B or toggle experiments.
