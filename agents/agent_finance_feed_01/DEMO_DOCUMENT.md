# Data Facts Integration - Demo Document

**Date:** January 2026  
**Status:** ✅ Complete and Deployed  
**Agents:** Finance Feed Agent & Consumer Agent

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [What is Data Facts?](#what-is-data-facts)
3. [Where We Added Data Facts in Agent Facts](#where-we-added-data-facts)
4. [Data Facts JSON Structure](#data-facts-json-structure)
5. [Demo Examples](#demo-examples)
6. [Complete Flow Diagrams](#complete-flow-diagrams)
7. [Future Steps](#future-steps)

---

## Executive Summary

We successfully integrated **Data Facts** into the NEST agent framework, allowing agents to expose and discover public datasets through standardized metadata. The `data_facts_url` is stored in the registry (Agent Facts), enabling seamless dataset discovery and access.

### Key Achievements

- ✅ Added `data_facts_url` to registry registration
- ✅ Finance Feed Agent exposes stock price data via Data Facts
- ✅ Consumer Agent discovers and accesses datasets via Data Facts
- ✅ Both A2A communication and Data Facts access work end-to-end
- ✅ Freshness validation and checksum verification implemented
- ✅ Deployed to AWS EC2 instances

---

## What is Data Facts?

**Data Facts** is a metadata pattern that describes a public dataset in a standardized JSON format. It provides:

1. **Dataset Description** - What the dataset contains
2. **Access Information** - How to access it (endpoint, access type)
3. **Evidence** - Proof of data integrity (checksum, last updated timestamp)
4. **Freshness Metadata** - TTL (Time To Live) for cache validation
5. **Ownership** - Which agent owns/provides the dataset

### Key Concepts

- **Data Facts ≠ Agent Facts**: 
  - **Agent Facts** = Metadata about the agent (stored in registry)
  - **Data Facts** = Metadata about a dataset (served via HTTP endpoint)

- **Access Types**:
  - `public` - Anyone can access
  - `private` - Requires authentication (future)

- **Freshness**: Data Facts include TTL to ensure consumers get fresh data

---

## Where We Added Data Facts in Agent Facts

The `data_facts_url` was integrated directly into the **registry** (which serves as Agent Facts). Here's exactly where and how:

### 1. Registry Registration (Agent Facts)

**File:** `NEST/nanda_core/core/adapter.py`

**Location:** Line 132-133

```python
def _register(self):
    """Register agent with registry"""
    try:
        data = {
            "agent_id": self.agent_id,
            "agent_url": self.public_url
        }
        if self.data_facts_url:
            data["data_facts_url"] = self.data_facts_url  # ← ADDED HERE
        response = requests.post(f"{self.registry_url}/register", json=data, timeout=10)
```

**File:** `NEST/nanda_core/core/registry_client.py`

**Location:** Line 24-37

```python
def register_agent(self, agent_id: str, agent_url: str, api_url: Optional[str] = None, 
                   agent_facts_url: Optional[str] = None, data_facts_url: Optional[str] = None) -> bool:
    """Register an agent with the registry"""
    try:
        data = {
            "agent_id": agent_id,
            "agent_url": agent_url
        }
        if api_url:
            data["api_url"] = api_url
        if agent_facts_url:
            data["agent_facts_url"] = agent_facts_url
        if data_facts_url:
            data["data_facts_url"] = data_facts_url  # ← ADDED HERE
        response = self.session.post(f"{self.registry_url}/register", json=data)
        return response.status_code == 200
```

### 2. Agent Facts Response (Registry Query)

When you query the registry (`GET /list`), the response now includes `data_facts_url`:

**Example Registry Response (Agent Facts):**

```json
{
  "agent_id": "finance-feed-agent",
  "agent_name": "Finance Feed Agent",
  "agent_url": "http://54.172.251.235:6000/a2a",
  "data_facts_url": "http://54.172.251.235:8000/data_facts/public_stock_ticker.json"  ← HERE!
}
```

### 3. Finance Feed Agent Registration

**File:** `NEST/examples/finance_feed_agent.py`

**Location:** Lines 279-293

```python
# Build data_facts_url for registry registration
data_facts_url = f"{data_server_public_url}/data_facts/public_stock_ticker.json"

# Initialize NANDA agent
nanda = NANDA(
    agent_id=agent_id,
    agent_logic=agent_logic,
    port=port,
    registry_url=registry_url,
    public_url=public_url,
    enable_telemetry=False,
    data_facts_url=data_facts_url  # ← PASSED HERE
)
```

### Visual Flow: Where Data Facts URL Lives

```
┌─────────────────────────────────────────────────────────┐
│                    Registry (Agent Facts)                │
│                                                          │
│  GET /list Response:                                     │
│  {                                                       │
│    "agent_id": "finance-feed-agent",                    │
│    "agent_url": "http://IP:6000/a2a",                   │
│    "data_facts_url": "http://IP:8000/data_facts/..."  ← HERE
│  }                                                       │
└─────────────────────────────────────────────────────────┘
                           ▲
                           │ Consumer Agent queries registry
                           │
┌──────────────────────────┴──────────────────────────────┐
│              Consumer Agent                              │
│  1. Queries registry → Gets data_facts_url              │
│  2. Fetches Data Facts from data_facts_url              │
│  3. Accesses dataset from endpoint in Data Facts        │
└──────────────────────────────────────────────────────────┘
```

---

## Data Facts JSON Structure

### Complete Schema

```json
{
  "dataset_id": "string (required)",
  "dataset_description": "string (required)",
  "access_type": "public | private (required)",
  "endpoint": "string (URL, required)",
  "evidence": {
    "last_updated": "string (ISO 8601 timestamp, required)",
    "checksum_sha256": "string (64-char hex, required)",
    "source": "string (optional)"
  },
  "ttl_seconds": "number (required, > 0)",
  "update_frequency": "string (optional)",
  "data_owner": "string (optional)"
}
```

### Real Example from Finance Feed Agent

**Endpoint:** `http://54.172.251.235:8000/data_facts/public_stock_ticker.json`

```json
{
  "dataset_id": "public_stock_ticker",
  "dataset_description": "Live stock price feed for TSLA, AAPL, ETH-USD via Yahoo Finance API. Updates every 10 minutes.",
  "update_frequency": "10 minutes",
  "data_owner": "finance-feed-agent",
  "access_type": "public",
  "endpoint": "http://54.172.251.235:8000/stock_data",
  "evidence": {
    "last_updated": "2026-01-16T16:51:00.123456+00:00",
    "checksum_sha256": "d7fc37cf56be91adc0902141e319e67977c487e9bab71d9d2ddf81f359b85f50",
    "source": "yahoo_finance_api"
  },
  "ttl_seconds": 600
}
```

### Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `dataset_id` | string | ✅ | Unique identifier for the dataset |
| `dataset_description` | string | ✅ | Human-readable description |
| `access_type` | string | ✅ | `"public"` or `"private"` |
| `endpoint` | string (URL) | ✅ | URL to fetch the actual dataset |
| `evidence.last_updated` | string (ISO 8601) | ✅ | Timestamp when data was last updated |
| `evidence.checksum_sha256` | string (64 hex chars) | ✅ | SHA256 hash of dataset (excluding timestamp) |
| `evidence.source` | string | ⭕ | Source of the data (e.g., "yahoo_finance_api") |
| `ttl_seconds` | number | ✅ | Time-to-live in seconds (how long data is valid) |
| `update_frequency` | string | ⭕ | Human-readable update frequency (e.g., "10 minutes") |
| `data_owner` | string | ⭕ | Agent ID that owns this dataset |

### Validation Rules

1. **access_type** must be `"public"` or `"private"`
2. **ttl_seconds** must be positive integer
3. **endpoint** must be valid HTTP(S) URL
4. **last_updated** must be valid ISO 8601 timestamp
5. **checksum_sha256** must be 64-character hexadecimal string

---

## Demo Examples

### Example 1: Query Registry and Discover Data Facts

**Step 1: Query Registry**

```bash
curl http://registry.chat39.com:6900/list | jq '.[] | select(.agent_id | contains("finance"))'
```

**Response (Agent Facts):**

```json
{
  "agent_id": "finance-feed-agent",
  "agent_name": "Finance Feed Agent",
  "agent_url": "http://54.172.251.235:6000/a2a",
  "data_facts_url": "http://54.172.251.235:8000/data_facts/public_stock_ticker.json"
}
```

**Step 2: Fetch Data Facts**

```bash
curl http://54.172.251.235:8000/data_facts/public_stock_ticker.json
```

**Response (Data Facts):**

```json
{
  "dataset_id": "public_stock_ticker",
  "dataset_description": "Live stock price feed for TSLA, AAPL, ETH-USD...",
  "access_type": "public",
  "endpoint": "http://54.172.251.235:8000/stock_data",
  "evidence": {
    "last_updated": "2026-01-16T16:51:00.123456+00:00",
    "checksum_sha256": "d7fc37cf56be91adc0902141e319e67977c487e9bab71d9d2ddf81f359b85f50",
    "source": "yahoo_finance_api"
  },
  "ttl_seconds": 600
}
```

**Step 3: Access Dataset**

```bash
curl http://54.172.251.235:8000/stock_data
```

**Response (Dataset):**

```json
{
  "TSLA": 439.32,
  "AAPL": 256.31,
  "ETH-USD": 3281.34,
  "timestamp": 1768578099
}
```

---

### Example 2: Consumer Agent Using Data Facts

**Python Code:**

```python
from nanda_core.core.registry_client import RegistryClient
import requests
from datetime import datetime, timezone

# Step 1: Discover agent via registry
registry = RegistryClient("http://registry.chat39.com:6900")
agents = registry.list_agents()

# Find finance feed agent
finance_agent = next(a for a in agents if "finance-feed" in a["agent_id"].lower())

# Step 2: Extract data_facts_url from Agent Facts
data_facts_url = finance_agent["data_facts_url"]
print(f"Found Data Facts URL: {data_facts_url}")

# Step 3: Fetch Data Facts
data_facts = requests.get(data_facts_url).json()
print(f"Dataset: {data_facts['dataset_id']}")
print(f"Access Type: {data_facts['access_type']}")

# Step 4: Validate access type
if data_facts["access_type"] != "public":
    print("Access denied: Dataset is private")
    exit(1)

# Step 5: Check freshness
last_updated = datetime.fromisoformat(data_facts["evidence"]["last_updated"].replace("Z", "+00:00"))
age_seconds = (datetime.now(timezone.utc) - last_updated).total_seconds()
is_fresh = age_seconds <= data_facts["ttl_seconds"]

print(f"Data age: {age_seconds:.1f}s")
print(f"TTL: {data_facts['ttl_seconds']}s")
print(f"Fresh: {is_fresh}")

# Step 6: Access dataset
if is_fresh:
    dataset = requests.get(data_facts["endpoint"]).json()
    print(f"Stock prices: {dataset}")
else:
    print("Warning: Data is stale (older than TTL)")
```

**Output:**

```
Found Data Facts URL: http://54.172.251.235:8000/data_facts/public_stock_ticker.json
Dataset: public_stock_ticker
Access Type: public
Data age: 15.3s
TTL: 600s
Fresh: True
Stock prices: {'TSLA': 439.32, 'AAPL': 256.31, 'ETH-USD': 3281.34, 'timestamp': 1768578099}
```

---

### Example 3: End-to-End Flow via Consumer Agent A2A

**Query Consumer Agent:**

```bash
curl -X POST http://44.223.52.126:6001/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "content": {
      "text": "ask finance agent about stock prices",
      "type": "text"
    },
    "role": "user",
    "conversation_id": "demo-123"
  }'
```

**Response:**

```json
{
  "parts": [{
    "text": "[data-consumer-agent] I queried the Finance Feed Agent via A2A, and here's what they said:\n\n[finance-feed-agent] Current stock prices: TSLA: $439.32, AAPL: $256.31, ETH-USD: $3281.34"
  }]
}
```

**What Happened Behind the Scenes:**

1. Consumer Agent received query
2. Consumer Agent discovered Finance Feed Agent via registry
3. Consumer Agent sent A2A message to Finance Feed Agent
4. Finance Feed Agent fetched stock data and responded
5. Consumer Agent returned response to user

---

## Complete Flow Diagrams

### Flow 1: Data Facts Discovery and Access

```
┌──────────────────────────────────────────────────────────────┐
│ Step 1: Consumer Agent Starts                                │
│   - Consumer Agent queries Registry                          │
│   - Registry returns Agent Facts (including data_facts_url)  │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│ Step 2: Extract data_facts_url                               │
│   data_facts_url = agent_facts["data_facts_url"]             │
│   Example: "http://54.172.251.235:8000/data_facts/..."       │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│ Step 3: Fetch Data Facts JSON                                │
│   GET http://54.172.251.235:8000/data_facts/...              │
│   Returns: { dataset_id, endpoint, evidence, ttl_seconds }   │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│ Step 4: Validate Access Type                                 │
│   if data_facts["access_type"] == "public":                  │
│       continue                                                │
│   else:                                                       │
│       access_denied()                                         │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│ Step 5: Check Freshness                                       │
│   age = now() - data_facts["evidence"]["last_updated"]       │
│   if age <= data_facts["ttl_seconds"]:                       │
│       is_fresh = True                                         │
│   else:                                                       │
│       is_fresh = False (stale data)                          │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│ Step 6: Verify Checksum (Optional)                           │
│   computed = sha256(dataset)                                  │
│   expected = data_facts["evidence"]["checksum_sha256"]       │
│   if computed == expected:                                    │
│       checksum_valid = True                                   │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│ Step 7: Access Dataset                                        │
│   GET data_facts["endpoint"]                                  │
│   Returns: Actual dataset data                                │
└──────────────────────────────────────────────────────────────┘
```

### Flow 2: A2A Communication

```
┌──────────────────────────────────────────────────────────────┐
│ User Query: "ask finance agent about stock prices"           │
│   → Consumer Agent (A2A endpoint)                            │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│ Consumer Agent Logic:                                         │
│   1. Detect finance/stock keywords                           │
│   2. Discover Finance Feed Agent (registry or fallback)      │
│   3. Send A2A message via python_a2a library                 │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│ A2A Message Sent:                                             │
│   POST http://54.172.251.235:6000/a2a                        │
│   Body: {                                                     │
│     "content": {"text": "what are stock prices?", ...},      │
│     "conversation_id": "..."                                 │
│   }                                                           │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│ Finance Feed Agent:                                           │
│   1. Receives A2A message                                     │
│   2. Fetches stock data from Yahoo Finance                    │
│   3. Formats response with stock prices                       │
│   4. Sends A2A response back                                  │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│ Consumer Agent:                                               │
│   1. Receives A2A response                                    │
│   2. Parses stock price information                           │
│   3. Returns formatted response to user                       │
└──────────────────────────────────────────────────────────────┘
```

---

## Implementation Details

### File Locations

| Component | File Path | Key Lines |
|-----------|-----------|-----------|
| Registry Client | `nanda_core/core/registry_client.py` | 24-37 (data_facts_url parameter) |
| NANDA Adapter | `nanda_core/core/adapter.py` | 34 (parameter), 132-133 (registration) |
| Finance Feed Agent | `examples/finance_feed_agent.py` | 279 (data_facts_url construction), 293 (NANDA init) |
| Consumer Agent | `examples/data_consumer_agent.py` | 231-296 (discover_and_access_dataset) |
| Data Facts Server | `examples/finance_feed_agent.py` | 78-148 (FinanceDataServer class) |

### Code Snippets

#### 1. Registering data_facts_url

```python
# In finance_feed_agent.py
data_facts_url = f"{data_server_public_url}/data_facts/public_stock_ticker.json"

nanda = NANDA(
    agent_id=agent_id,
    # ... other params
    data_facts_url=data_facts_url  # This gets registered in registry
)
```

#### 2. Discovering via Registry

```python
# In data_consumer_agent.py
registry = RegistryClient(registry_url)
agents = registry.list_agents()

finance_agent = next(a for a in agents if "finance" in a["agent_id"].lower())
data_facts_url = finance_agent["data_facts_url"]  # Extract from Agent Facts
```

#### 3. Accessing Data Facts

```python
# Fetch Data Facts
data_facts = requests.get(data_facts_url).json()

# Access dataset
dataset = requests.get(data_facts["endpoint"]).json()
```

---

## Demo Examples

### Demo 1: Browser Access

**Open in browser:**

1. **Data Facts:** http://54.172.251.235:8000/data_facts/public_stock_ticker.json
2. **Stock Data:** http://54.172.251.235:8000/stock_data
3. **Consumer A2A:** http://44.223.52.126:6001/a2a

### Demo 2: Using React Demo UI

The React demo app (`demo-ui/`) provides interactive interfaces:

1. **Query Interface** - Type queries and see flow
2. **Stock Prices** - Live prices with Data Facts metadata
3. **Registry Explorer** - Browse agents and their Data Facts URLs
4. **API Playground** - Test endpoints interactively

**Start demo UI:**

```bash
cd demo-ui
npm start
```

### Demo 3: Command Line

```bash
# 1. Query registry
curl http://registry.chat39.com:6900/list | jq '.[] | select(.data_facts_url)'

# 2. Get Data Facts
curl http://54.172.251.235:8000/data_facts/public_stock_ticker.json | jq

# 3. Get stock data
curl http://54.172.251.235:8000/stock_data | jq

# 4. Test A2A
curl -X POST http://44.223.52.126:6001/a2a \
  -H "Content-Type: application/json" \
  -d '{"content":{"text":"stock prices?","type":"text"},"role":"user","conversation_id":"test"}' | jq
```

---

## Future Steps

### Phase 1: Enhancements (Short-term)

1. **Private Dataset Support**
   - Add authentication/authorization for `access_type: "private"`
   - API key or OAuth token support
   - Access control lists (ACLs)

2. **Schema Validation**
   - JSON Schema validation for Data Facts
   - Automated validation on registration
   - Schema versioning support

3. **Caching & Performance**
   - Client-side caching with TTL awareness
   - CDN support for Data Facts endpoints
   - Rate limiting on dataset endpoints

4. **Multiple Datasets per Agent**
   - Support multiple `data_facts_url` entries
   - Dataset catalog/listing endpoint
   - Agent can expose multiple datasets

### Phase 2: Advanced Features (Medium-term)

5. **Data Facts Versioning**
   - Support dataset versioning
   - Historical Data Facts access
   - Version comparison tools

6. **Data Lineage**
   - Track data sources and transformations
   - Data provenance information
   - Dependency graphs

7. **Rich Metadata**
   - Column schemas for tabular data
   - Data quality metrics
   - Update frequency statistics
   - Data size estimates

8. **Subscription Model**
   - Webhook notifications on data updates
   - Push-based data delivery
   - Change data capture (CDC)

### Phase 3: Enterprise Features (Long-term)

9. **Data Catalog Integration**
   - Integration with data catalogs (e.g., Apache Atlas)
   - Data governance support
   - Compliance tracking (GDPR, HIPAA)

10. **Advanced Security**
    - End-to-end encryption
    - Data masking for sensitive fields
    - Audit logging
    - Access policies (RBAC)

11. **Data Quality Framework**
    - Automated data quality checks
    - Data freshness monitoring
    - Anomaly detection
    - Quality scoring

12. **Multi-Cloud Support**
    - Cross-cloud dataset access
    - Federation across registries
    - Data location transparency

---

## Migration Guide

### For Existing Agents

To add Data Facts support to an existing agent:

1. **Create Data Facts Endpoint**
   - Add HTTP endpoint serving Data Facts JSON
   - Compute checksums dynamically
   - Update `last_updated` timestamps

2. **Update Registration**
   - Pass `data_facts_url` to NANDA adapter
   - Re-register agent with registry

3. **Test**
   - Verify Data Facts JSON is valid
   - Test dataset endpoint accessibility
   - Validate freshness and checksum

### Example Migration

```python
# Before (no Data Facts)
nanda = NANDA(
    agent_id="my-agent",
    agent_logic=my_logic,
    port=6000,
    registry_url=registry_url,
    public_url=public_url,
)

# After (with Data Facts)
data_facts_url = f"{public_url}/data_facts/my_dataset.json"

nanda = NANDA(
    agent_id="my-agent",
    agent_logic=my_logic,
    port=6000,
    registry_url=registry_url,
    public_url=public_url,
    data_facts_url=data_facts_url  # ← ADD THIS
)
```

---

## Troubleshooting

### Common Issues

**Issue:** `data_facts_url` not in registry response

**Solution:**
- Verify agent registered with `data_facts_url` parameter
- Check registry supports `data_facts_url` field
- Re-register agent if needed

**Issue:** Data Facts endpoint returns 404

**Solution:**
- Ensure Data Facts server is running
- Check `data_facts_url` is correct
- Verify port is open in security group

**Issue:** Checksum mismatch

**Solution:**
- Checksum excludes `timestamp` field
- Ensure consistent JSON serialization (sorted keys)
- Re-compute checksum after data updates

---

## Summary

✅ **Data Facts URL Location:** Stored in registry (Agent Facts) as `data_facts_url` field  
✅ **Data Facts Format:** Standardized JSON with metadata, evidence, and access info  
✅ **Integration Points:** Registry registration, Consumer Agent discovery, Finance Feed Agent exposure  
✅ **Demo Examples:** Registry → Data Facts → Dataset flow fully functional  
✅ **Future Steps:** Private datasets, versioning, security, data quality framework

The Data Facts pattern is now fully integrated and ready for production use! 🎉
