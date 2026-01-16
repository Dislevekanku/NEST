# Clear Architecture: Registry + Data Facts

## Understanding the Components

### 1. Registry (Central Directory)
**What it is:** The central service that stores agent metadata
**Where:** `http://registry.chat39.com:6900`
**What it stores:**
- `agent_id` - Unique identifier
- `agent_name` - Display name
- `domain` - Field of expertise
- `capabilities` - What the agent can do
- `agent_url` - A2A endpoint
- `api_url` - Optional API endpoint
- `data_facts_url` - **NEW:** Points to Data Facts (for agents with datasets)

**Registry IS the "agent facts"** - it contains all agent metadata!

### 2. Data Facts (Dataset Metadata)
**What it is:** JSON file that describes a dataset
**Where:** Served by the agent at `/data_facts/{dataset_id}.json`
**What it stores:**
- `dataset_id` - Dataset identifier
- `dataset_description` - What the dataset contains
- `access_type` - "public" or "private"
- `endpoint` - URL to fetch the actual data
- `evidence` - Checksum, timestamp, source
- `ttl_seconds` - Time-to-live

### 3. Dataset Endpoint
**What it is:** The actual data (stock prices, etc.)
**Where:** Served by the agent at `/stock_data` or similar
**What it returns:** The actual dataset (JSON, CSV, etc.)

## The Flow

```
┌─────────────────────────────────────────┐
│  Registry (Central Directory)           │
│  http://registry.chat39.com:6900        │
│                                         │
│  GET /list returns:                     │
│  {                                      │
│    "agent_id": "finance-feed-agent",    │
│    "agent_name": "Finance Feed Agent",  │
│    "domain": "financial data",          │
│    "capabilities": [...],               │
│    "agent_url": "http://x.x.x.x:6000/a2a",│
│    "data_facts_url": "http://x.x.x.x:6000/data_facts/public_stock_ticker.json" │
│  }                                      │
└──────────────┬──────────────────────────┘
               │
               │ Consumer discovers via registry
               │ (gets agent_url + data_facts_url)
               │
    ┌──────────┴──────────┐
    │                     │
    ▼                     ▼
┌──────────────┐    ┌──────────────┐
│ Finance Feed │    │   Consumer   │
│   Agent      │    │    Agent     │
│              │    │              │
│ A2A: /a2a    │◄───│ Uses A2A     │
│              │    │ to communicate│
│              │    │              │
│ Data Facts:  │───►│ Follows      │
│ /data_facts/ │    │ data_facts_url│
│ *.json       │    │              │
│              │    │              │
│ Dataset:     │───►│ Fetches      │
│ /stock_data  │    │ dataset      │
└──────────────┘    └──────────────┘
```

## Key Points

1. **Registry = Agent Facts**
   - Registry already contains all agent metadata
   - No separate "Agent Facts" file needed
   - `agent_facts_url` field exists but isn't used by menu/concierge agents

2. **Data Facts = Dataset Metadata**
   - Describes datasets the agent provides
   - Points to dataset endpoints
   - NEW concept (not in current NEST)

3. **Simplified Approach**
   - Add `data_facts_url` to registry registration
   - Registry returns agent metadata + `data_facts_url` in one call
   - Consumer follows `data_facts_url` → Data Facts → Dataset

## Why This Makes Sense

- ✅ **No duplication** - Registry is single source of truth for agent metadata
- ✅ **Simple** - One registry call gets everything
- ✅ **Aligned with NEST** - Uses existing registry pattern
- ✅ **Clean separation** - Registry (agent info) vs Data Facts (dataset info)

