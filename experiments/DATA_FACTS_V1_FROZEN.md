# Data Facts v1 — Frozen

**Status:** Frozen. No further changes to v1 semantics or response shape.

This document defines the **Data Facts v1** spec. The Public Data Facts endpoint and response format are **stable** for experiments. Implementations must preserve this contract.

---

## 1. Endpoint

| Property | Value |
|----------|--------|
| **Method** | `GET` |
| **Path** | `/data_facts/{dataset_id}.json` |
| **Example** | `http://<host>:8000/data_facts/public_stock_ticker.json` |
| **Content-Type** | `application/json` |

The dataset server also exposes:

- **Dataset**: `GET /{dataset_route}` (e.g. `GET /public_stock_ticker` or `GET /public-stock-ticker`, provider-defined).
- **Health**: `GET /health`.

---

## 2. Response schema (Data Facts JSON)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `dataset_id` | string | ✅ | Unique dataset identifier |
| `dataset_description` | string | ✅ | Human-readable description |
| `access_type` | string | ✅ | `"public"` or `"private"` |
| `endpoint` | string | ✅ | Full URL to fetch dataset (GET) |
| `evidence` | object | ✅ | Integrity evidence |
| `evidence.last_updated` | string | ✅ | ISO 8601 timestamp (UTC) |
| `evidence.checksum_sha256` | string | ✅ | 64-char hex SHA256 of dataset (excluding `timestamp`) |
| `evidence.source` | string | ❌ | Optional data source identifier |
| `ttl_seconds` | integer | ✅ | Time-to-live in seconds (> 0) |
| `update_frequency` | string | ❌ | e.g. `"10 minutes"` |
| `data_owner` | string | ❌ | Agent ID that owns the dataset |

### Example

```json
{
  "dataset_id": "public_stock_ticker",
  "dataset_description": "Public stock ticker data from Yahoo Finance",
  "access_type": "public",
  "endpoint": "http://host:8000/public_stock_ticker",
  "evidence": {
    "last_updated": "2026-01-25T12:00:00.000Z",
    "checksum_sha256": "d7fc37cf56be91adc0902141e319e67977c487e9bab71d9d2ddf81f359b85f50",
    "source": "yahoo_finance_api"
  },
  "ttl_seconds": 600,
  "update_frequency": "10 minutes",
  "data_owner": "finance-feed-agent"
}
```

---

## 3. Checksum rules (frozen)

- **Input**: Dataset JSON as served by the dataset endpoint.
- **Excluded**: `timestamp` field (if present).
- **Algorithm**: JSON serialization with **sorted keys**, UTF-8, then SHA256 hex.
- **Comparison**: Consumer computes same hash and compares to `evidence.checksum_sha256`.

---

## 4. TTL / freshness (frozen)

- **`evidence.last_updated`**: When the dataset was last generated (ISO 8601 UTC).
- **`ttl_seconds`**: Max age (seconds) for which data is considered fresh.
- **Freshness**: `age_seconds = now - last_updated`; data is **fresh** iff `age_seconds <= ttl_seconds`.

---

## 5. Registry integration

- Agents expose Data Facts via **`data_facts_url`** in the registry (Agent Facts).
- `data_facts_url` points to the Data Facts JSON endpoint (e.g. `http://host:8000/data_facts/public_stock_ticker.json`).
- Discovery: list agents → filter by `data_facts_url` → GET `data_facts_url` → use `endpoint` to fetch dataset.

---

## 6. Experiment toggles (consumer-side)

Experiments may **toggle** usage of Data Facts, TTL, and checksum **without** changing the endpoint or response:

| Toggle | Effect |
|--------|--------|
| **With Data Facts vs Without** | **With**: full flow (registry → Data Facts → validate → dataset). **Without**: GET dataset endpoint directly, no Data Facts. |
| **TTL on/off** | **On**: enforce freshness using `ttl_seconds` and `last_updated`. **Off**: skip freshness check. |
| **Checksum on/off** | **On**: verify `checksum_sha256` vs computed hash. **Off**: skip checksum verification. |

The **Public Data Facts endpoint always returns the full v1 shape** (including TTL and checksum). Toggles are applied only in the **consumer** (client) or experiment config.

---

## 7. Implementation references

| Component | Location |
|-----------|----------|
| Dataset server (Data Facts + dataset routes) | `nanda_core/dataset/server.py` |
| Provider / metadata builder | `nanda_core/dataset/provider.py` |
| Client helpers (fetch, freshness, checksum) | `nanda_core/dataset/client.py` |
| Experiment config template | `experiments/experiment_config_template.json` |

---

**Frozen as of:** 2026-01.
**Spec version:** Data Facts v1.

---

## Addendum: Semi-Private Access Type (2026-02)

The `access_type` field now accepts three values: `"public"`, `"semi-private"`, `"private"`.

- **`"semi-private"`**: Dataset is discoverable via registry, but the dataset endpoint requires a Bearer JWT. Consumers call `POST /negotiate_access` on the data owner's server to obtain a short-lived token.

This is an **additive** extension — existing public-only consumers are unaffected. The response shape and all other v1 semantics remain unchanged. See `experiments/PRIVATE_DATA_ARCHITECTURE.md` for the full flow.
