# Private Data Architecture — NEST

**Status:** Locked. Implementation complete, ready for experiments.
**Date:** 2026-02-11

---

## 1. Access Type Definitions

| Type | Discoverable? | Data Facts `access_type` | Credential Flow |
|------|--------------|--------------------------|-----------------|
| **Public** | Yes (registry + data_facts_url) | `"public"` | None — open GET |
| **Semi-private** | Yes (registry + data_facts_url) | `"semi-private"` | Discoverable, but dataset endpoint requires Bearer JWT. Consumer calls `POST /negotiate_access` to get a token. |
| **Private** | No (not in registry or no data_facts_url) | `"private"` | Out-of-band credential handoff. Consumer must already know the agent URL and have a pre-shared token. |

**Key rule:** Data Facts JSON is always served if discoverable. It tells you the `access_type` so the consumer knows what to do next. The **dataset endpoint** is what's gated, not the metadata.

---

## 2. Gateway Flow (Semi-Private)

```
Consumer Agent                  Data Owner Agent                     Supabase
     |                                |                                |
     |-- GET /data_facts/X.json ----->|                                |
     |<-- { access_type: "semi-private", ... }                         |
     |                                |                                |
     |-- POST /negotiate_access ----->|                                |
     |   { consumer_agent_id, ttl }   |                                |
     |                                |-- validate + sign JWT          |
     |<-- { token, ttl_seconds } -----|                                |
     |                                |                                |
     |-- GET /dataset-route --------->|                                |
     |   Authorization: Bearer <jwt>  |                                |
     |                                |-- decode JWT, check exp        |
     |                                |-- fetch rows from ------------>|
     |                                |<-- rows -----------------------|
     |<-- 200 { rows }               |                                |
```

### JWT Spec

| Field | Value |
|-------|-------|
| Algorithm | HS256 |
| Secret | `NEST_JWT_SECRET` env var (default: `nest-local-dev-secret`) |
| `sub` | consumer_agent_id |
| `role` | `"owner"` or `"inquiry"` |
| `scope` | `"read"` (v1 only) |
| `dataset_id` | Target dataset |
| `exp` | `iat + ttl_seconds` |
| `iat` | UTC now |

### TTL Defaults

| Role | TTL |
|------|-----|
| Owner | 3600s (1 hour) |
| Inquiry (semi-private) | 60s |
| Experiment short-lived | 2-5s |

---

## 3. Supabase Integration

- **Project:** `nest-private-data` on supabase.com
- **Table:** `private_employee_records` (20 seeded rows, rng_seed=42)
- **Access:** Data owner uses `SUPABASE_SERVICE_KEY` (service_role); consumers never touch Supabase directly
- **Library:** `supabase-py` (>= 2.0.0)

### Setup

```bash
pip install supabase PyJWT python-dotenv
cp .env.template .env  # fill in SUPABASE_URL, SUPABASE_SERVICE_KEY, NEST_JWT_SECRET

# Create table in Supabase SQL Editor, then seed:
python experiments/exp4_security_auth/seed_supabase.py
```

---

## 4. Implementation Map

| Component | File | What Changed |
|-----------|------|-------------|
| Base provider auth | `nanda_core/dataset/provider.py` | `validate_access()` decodes JWT; `negotiate_access()` issues JWT |
| Dataset server | `nanda_core/dataset/server.py` | Auth gate on dataset endpoint; `/negotiate_access` route |
| Client helpers | `nanda_core/dataset/client.py` | `negotiate_access()` function; auto-negotiate in `discover_and_access_dataset()` |
| Supabase provider | `nanda_core/dataset/supabase_provider.py` | `SupabaseDatasetProvider` subclass |
| Data owner agent | `experiments/exp4_security_auth/agents/data_owner_private.py` | Serves private_employee_records |
| Authorized consumer | `experiments/exp4_security_auth/agents/authorized_consumer.py` | Happy-path test |
| Expired consumer | `experiments/exp4_security_auth/agents/expired_consumer.py` | TTL expiry test |
| Malicious consumer | `experiments/exp4_security_auth/agents/malicious_consumer.py` | Forgery test |
| Unauthorized consumer | `experiments/exp4_security_auth/agents/unauthorized_consumer.py` | No-auth test |
| Experiment runner | `experiments/exp4_security_auth/run.py` | `--mode real-agents` |
| Agent manifest | `experiments/exp4_security_auth/agents_manifest_private.json` | Topology |
| Seed script | `experiments/exp4_security_auth/seed_supabase.py` | Seeds Supabase |

---

## 5. Pass/Fail Conditions

| Condition | Scenario | Expected HTTP | Pass Criteria |
|-----------|----------|---------------|---------------|
| Auth success | Valid JWT | 200 | `row_count > 0`, checksum matches |
| TTL expiry | Expired JWT | 401 | Rejected after TTL elapses |
| Token forgery | Wrong-secret JWT | 401 | Rejected |
| Malformed token | Garbage string | 401 | Rejected |
| Missing auth | No header | 401 | Rejected |

---

## 6. Running Experiments

```bash
# Terminal 1: Start data owner
python experiments/exp4_security_auth/agents/data_owner_private.py

# Terminal 2: Run all scenarios (simulated)
python experiments/exp4_security_auth/run.py --mode simulated

# Terminal 2: Run all scenarios (real agents against live owner)
python experiments/exp4_security_auth/run.py --mode real-agents

# Manual verification
curl http://localhost:6350/data_facts/private_employee_records.json
curl http://localhost:6350/private-employee-records  # → 401
curl -X POST http://localhost:6350/negotiate_access \
  -H "Content-Type: application/json" \
  -d '{"consumer_agent_id": "test"}'
# Use returned token:
curl http://localhost:6350/private-employee-records \
  -H "Authorization: Bearer <token>"
```

---

## 7. Exit Criteria

Can explain this end-to-end in 2 minutes:

1. Data owner registers with registry (semi-private, has `data_facts_url`)
2. Consumer discovers owner via registry, fetches Data Facts → sees `access_type: "semi-private"`
3. Consumer POSTs `/negotiate_access` with its agent_id → gets short-lived JWT
4. Consumer GETs dataset with `Authorization: Bearer <jwt>` → 200 + data
5. Expired/forged/missing tokens → 401
6. All backed by real Supabase data, measured with real latencies
