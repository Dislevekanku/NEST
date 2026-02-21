# Architecture Lock v1: 52-Agent Topology

## Topology (paper-clean)

| Component | Count | IDs |
|-----------|-------|-----|
| **Registry** | 1 | NEST registry (e.g. `http://registry.chat39.com:6900`) |
| **Providers** | 2 | `provider_finance_01`, `provider_weather_01` |
| **Consumers** | 50 | `consumer_001` … `consumer_050` |

**Total agents:** 52

---

## NEST Protocol Readiness Checklist

| Requirement | Providers | Consumers |
|-------------|-----------|-----------|
| **Health endpoint** | ✅ `/health` (MultiDatasetServer) | ✅ `/health` (per consumer) |
| **A2A endpoint** | N/A (dataset server) | ✅ `/{base}/a2a` |
| **Agent Facts** (with `data_facts_url`) | ✅ Registry stores `data_facts_url` | Registry stores `agent_url` only |
| **Registry visibility** | ✅ Registered with `agent_id`, `agent_url`, `data_facts_url` | ✅ Registered with `agent_id`, `agent_url` |

### Provider endpoints

- **Health:** `GET http://<provider_ip>:8000/health`
- **Data Facts:** `GET http://<provider_ip>:8000/data_facts/public_stock_ticker.json` (finance)
- **Data Facts:** `GET http://<provider_ip>:8000/data_facts/public_weather_data.json` (weather)
- **Dataset:** `GET http://<provider_ip>:8000/public-stock-ticker`, `.../public-weather-data`

### Consumer endpoints

- **Health:** `GET http://<consumer_ip>:<port>/health`
- **A2A:** `POST http://<consumer_ip>:<port>/a2a`

### Registry

- **List agents:** `GET http://registry.chat39.com:6900/list`
- **Lookup:** `GET http://registry.chat39.com:6900/lookup/<agent_id>`
- **Register:** `POST http://registry.chat39.com:6900/register`

---

## Artifacts

- **agents_manifest_v1.json** — All 52 agents, roles, URL templates
- **config_manifest_v1.json** — Ecosystem config for `run_ecosystem.py`
- **deploy_report.json** — Post-deploy validation (agent_id → status, url)

---

## Deployment Checklist

1. **Deploy providers** (2) + register 50 consumers:
   ```powershell
   cd NEST\scripts
   $env:SECURITY_GROUP_ID = (aws ec2 describe-security-groups --group-names "nanda-finance-consumer-agents" --region us-east-1 --query 'SecurityGroups[0].GroupId' --output text 2>$null)
   .\deploy_ecosystem_50.ps1 -ConfigName "config_manifest_v1.json"
   ```

2. **Validate** (after ~90s):
   ```powershell
   $env:PROVIDER_IP = "<public-ip-from-deploy>"
   python scripts/deploy_and_validate_52.py --no-deploy
   ```

3. **deploy_report.json** will be written to `experiments/ecosystem/deploy_report.json`.
