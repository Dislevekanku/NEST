# Agent Facts + Data Facts Experiment Documentation

**For:** Maria & Mukul  
**Date:** January 2026  
**Experiment:** Public Dataset Discovery and Access via Agent Facts & Data Facts

---

## Objective

Demonstrate an end-to-end flow showing:
- **Agent Facts** for agent discovery
- **Data Facts** for dataset metadata and access information
- **Public dataset access** with real-time stock data from Yahoo Finance API

This experiment validates the complete discovery and access pattern using HTTP endpoints, aligning with NEST's deployment model.

---

## Flow

### Step-by-Step Process

1. **Agent Discovery**
   - Agent A discovers Agent B by fetching `agent_facts.json` from HTTP endpoint
   - Agent Facts contain metadata: `agent_id`, `name`, `description`, `capabilities`
   - Agent Facts include `data_facts_pointer` → URL to Data Facts JSON

2. **Data Facts Retrieval**
   - Agent A follows the `data_facts_pointer` URL
   - Fetches `public_stock_ticker.json` (Data Facts) over HTTP
   - Data Facts describe the dataset: `dataset_id`, `dataset_description`, `endpoint`, `access_type`

3. **Access Control Check**
   - Agent A checks `access_type` field
   - Dataset marked as `"access_type": "public"`
   - Proceeds with data access

4. **Freshness Validation**
   - Agent A validates data freshness using:
     - `ttl_seconds`: Time-to-live (600 seconds = 10 minutes)
     - `evidence.last_updated`: Timestamp of last data update
   - Compares current time with `last_updated + ttl_seconds`
   - Status: FRESH or STALE

5. **Dataset Access**
   - Agent A calls the endpoint specified in Data Facts
   - Endpoint: `http://localhost:8000/stock_prices`
   - Fetches real-time stock prices from Yahoo Finance API
   - Returns JSON: `{"TSLA": 448.96, "AAPL": 260.25, "ETH-USD": 3104.07, "timestamp": ...}`

6. **Evidence Verification** (Optional)
   - Agent A computes SHA256 checksum of fetched data
   - Compares with `evidence.checksum_sha256` from Data Facts
   - Validates data integrity

---

## Architecture

```
┌─────────────────┐
│  Agent Facts    │  http://localhost:9000/agent_facts.json
│  HTTP Server    │  Contains: agent metadata + data_facts_pointer
└────────┬────────┘
         │
         │ data_facts_pointer (URL)
         ▼
┌─────────────────┐
│  Data Facts     │  http://localhost:9000/data_facts/public_stock_ticker.json
│  HTTP Server    │  Contains: dataset metadata + endpoint + evidence
└────────┬────────┘
         │
         │ endpoint (URL)
         ▼
┌─────────────────┐
│  Stock Data     │  http://localhost:8000/stock_prices
│  HTTP Server    │  Real Yahoo Finance API data
└─────────────────┘
         │
         │
         ▼
┌─────────────────┐
│  Consumer Agent │  agent_consumer_demo.py
│  (Agent A)      │  Discovers → Reads → Validates → Fetches
└─────────────────┘
```

---

## Artifacts

### 1. `agent_facts.json`
**Location:** `agents/agent_finance_feed_01/agent_facts.json`  
**Served at:** `http://localhost:9000/agent_facts.json`

Agent metadata containing:
- `agent_id`: Unique identifier
- `name`: Display name
- `description`: Agent description
- `capabilities`: List of capabilities
- `data_facts_pointer`: **URL** to Data Facts JSON (not file path)

**Example:**
```json
{
  "agent_id": "agent_finance_feed_01",
  "name": "Finance Feed Agent",
  "description": "Provides a public stock ticker dataset via Data Facts using real Yahoo Finance API.",
  "capabilities": ["serve_public_stock_data"],
  "data_facts_pointer": "http://localhost:9000/data_facts/public_stock_ticker.json"
}
```

### 2. `public_stock_ticker.json` (Data Facts)
**Location:** `agents/agent_finance_feed_01/data_facts/public_stock_ticker.json`  
**Served at:** `http://localhost:9000/data_facts/public_stock_ticker.json`

Dataset metadata containing:
- `dataset_id`: Unique dataset identifier
- `dataset_description`: Dataset description
- `access_type`: `"public"` (public access)
- `endpoint`: URL to fetch the actual data
- `ttl_seconds`: Time-to-live for freshness validation
- `evidence`: Contains `last_updated`, `checksum_sha256`, `source`

**Example:**
```json
{
  "dataset_id": "public_stock_ticker",
  "dataset_description": "Live stock price feed for TSLA, AAPL, ETH-USD via Yahoo Finance API. Updates every 10 minutes.",
  "update_frequency": "10 minutes",
  "data_owner": "agent_finance_feed_01",
  "access_type": "public",
  "endpoint": "http://localhost:8000/stock_prices",
  "evidence": {
    "last_updated": "2026-01-13T01:25:56.657235+00:00",
    "checksum_sha256": "32a79f0699020fee08884f7724347500952f99a1128c5423f0e5e6939a2a8881",
    "source": "yahoo_finance_api"
  },
  "ttl_seconds": 600
}
```

### 3. `public_stock_server.py`
**Location:** `scripts/public_stock_server.py`  
**Port:** 8000

HTTP server that:
- Fetches real-time stock prices from Yahoo Finance API using `yfinance`
- Serves stock data at `http://localhost:8000/stock_prices`
- Returns JSON with ticker symbols and prices
- Updates prices in real-time

**Endpoints:**
- `GET /stock_prices` → Returns `{"TSLA": 448.96, "AAPL": 260.25, "ETH-USD": 3104.07, "timestamp": ...}`

### 4. `generate_data_facts.py`
**Location:** `scripts/generate_data_facts.py`

Script that:
- Fetches current stock data from the stock server
- Computes SHA256 checksum of the data
- Updates `evidence.last_updated` with current timestamp
- Updates `evidence.checksum_sha256` with computed checksum
- Saves updated Data Facts JSON

**Usage:**
```bash
python scripts/generate_data_facts.py
```

### 5. `agent_consumer_demo.py`
**Location:** `scripts/agent_consumer_demo.py`

Consumer agent (Agent A) that demonstrates the complete flow:
1. Fetches Agent Facts from HTTP endpoint
2. Follows `data_facts_pointer` URL to fetch Data Facts
3. Checks `access_type` (must be "public")
4. Validates data freshness using `ttl_seconds` and `last_updated`
5. Fetches dataset from endpoint
6. Verifies checksum (optional)

**Usage:**
```bash
python scripts/agent_consumer_demo.py
```

### 6. `serve_agent_facts.py`
**Location:** `scripts/serve_agent_facts.py`  
**Port:** 9000

HTTP server that serves Agent Facts and Data Facts JSON files:
- Serves `agent_facts.json` at `http://localhost:9000/agent_facts.json`
- Serves Data Facts at `http://localhost:9000/data_facts/public_stock_ticker.json`
- Mimics NEST's production deployment model
- Includes CORS headers for cross-origin requests

---

## Setup Instructions

### Prerequisites
```bash
pip install yfinance requests
```

### Start Servers

**Terminal 1: Agent Facts Server**
```bash
cd NEST
python scripts/serve_agent_facts.py
```
Server runs at: `http://localhost:9000/`

**Terminal 2: Stock Data Server**
```bash
cd NEST
python scripts/public_stock_server.py
```
Server runs at: `http://localhost:8000/stock_prices`

**Terminal 3: Update Data Facts (Optional)**
```bash
cd NEST
python scripts/generate_data_facts.py
```

**Terminal 4: Run Consumer Agent**
```bash
cd NEST
python scripts/agent_consumer_demo.py
```

---

## Logs/Screenshots

### Successful Run Console Output

```
============================================================
Agent Consumer Demo - Real API (Option A)
============================================================

Step 1: Loading Agent Facts...
Fetching Agent Facts from URL: http://localhost:9000/agent_facts.json
[OK] Discovered agent: agent_finance_feed_01
   Name: Finance Feed Agent
   Description: Provides a public stock ticker dataset via Data Facts using real Yahoo Finance API.

Step 2: Following data_facts_pointer...
Fetching Data Facts from URL: http://localhost:9000/data_facts/public_stock_ticker.json
[OK] Loaded Data Facts for dataset: public_stock_ticker
   Description: Live stock price feed for TSLA, AAPL, ETH-USD via Yahoo Finance API. Updates every 10 minutes.
   Source: yahoo_finance_api

Step 3: Checking access type...
[OK] Access type: public

Step 4: Checking data freshness...
[OK] FRESH (TTL: 600s)
   Last updated: 2026-01-13T01:25:56.657235+00:00

Step 5: Fetching public dataset from endpoint...
Fetching from endpoint: http://localhost:8000/stock_prices
[OK] Successfully fetched public dataset:
{
  "TSLA": 448.96,
  "AAPL": 260.25,
  "ETH-USD": 3104.07,
  "timestamp": 1768267579
}

Step 6: Verifying checksum...
[OK] Checksum matches!

============================================================
[OK] Experiment Complete!
============================================================
```

### Data Facts Update Output

```
Fetching stock data from http://localhost:8000/stock_prices...
[OK] Updated Data Facts at 2026-01-13T01:25:56.657235+00:00
[OK] Checksum: 32a79f0699020fee08884f7724347500952f99a1128c5423f0e5e6939a2a8881
[OK] Stock data: {
  "TSLA": 448.96,
  "AAPL": 260.25,
  "ETH-USD": 3104.07,
  "timestamp": 1768267556
}
```

---

## Key Features Demonstrated

✅ **HTTP-based Agent Discovery**: Agent Facts served over HTTP (production model)  
✅ **URL-based Data Facts Pointer**: `data_facts_pointer` uses HTTP URL, not file path  
✅ **Public Dataset Access**: `access_type: "public"` enables open access  
✅ **Freshness Validation**: TTL-based freshness checking using `ttl_seconds` and `last_updated`  
✅ **Real API Integration**: Uses real Yahoo Finance API (no API key required)  
✅ **Evidence Verification**: SHA256 checksum validation for data integrity  
✅ **NEST Deployment Alignment**: Mimics production HTTP-based metadata serving  

---

## Notes

- **Real API**: Uses Yahoo Finance API via `yfinance` library (free, no API key)
- **HTTP Endpoints**: All metadata (Agent Facts, Data Facts) served over HTTP
- **JSON Format**: All communication uses JSON
- **Minimal Infrastructure**: Only Python + HTTP servers required
- **Production-Ready Pattern**: Aligns with NEST's deployment model

---

## File Structure

```
NEST/
├── agents/agent_finance_feed_01/
│   ├── agent_facts.json              # Agent metadata (HTTP endpoint)
│   ├── data_facts/
│   │   └── public_stock_ticker.json  # Data Facts (HTTP endpoint)
│   ├── README.md
│   ├── QUICK_START.md
│   └── EXPERIMENT_DOCUMENTATION.md   # This file
│
└── scripts/
    ├── serve_agent_facts.py          # HTTP server for Agent/Data Facts (port 9000)
    ├── public_stock_server.py        # Stock data server (port 8000)
    ├── generate_data_facts.py        # Update Data Facts evidence
    └── agent_consumer_demo.py        # Consumer agent demo
```

---

**End of Documentation**

