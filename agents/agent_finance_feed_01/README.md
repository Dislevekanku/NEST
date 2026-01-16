# Finance Feed Agent - Real API Experiment (Option A)

This experiment demonstrates agent discovery and data access using real stock market data from Yahoo Finance API.

## Architecture

- **Agent B** (`agent_finance_feed_01`): Exposes a public stock ticker dataset via `data_facts.json`
- **Agent A** (`agent_consumer_demo.py`): Discovers Agent B, follows Data Facts pointer, and fetches stock data

## Setup

### 1. Install Dependencies

```bash
pip install yfinance requests
```

### 2. Start the Agent Facts HTTP Server

This serves the Agent Facts and Data Facts JSON files over HTTP (mimicking NEST's deployment model):

```bash
python scripts/serve_agent_facts.py
```

This starts a server on `http://localhost:9000/` that serves:
- Agent Facts: `http://localhost:9000/agent_facts.json`
- Data Facts: `http://localhost:9000/data_facts/public_stock_ticker.json`

### 3. Start the Stock Server

The stock server fetches real stock prices from Yahoo Finance API:

```bash
python scripts/public_stock_server.py
```

This starts a server on `http://localhost:8000/stock_prices` that serves real stock data for TSLA, AAPL, and ETH-USD.

### 4. Update Data Facts (Optional)

To update the evidence (checksum, last_updated) in Data Facts:

```bash
python scripts/generate_data_facts.py
```

This script:
- Fetches current stock data from the server
- Computes SHA256 checksum
- Updates `data_facts/public_stock_ticker.json` with new evidence

### 5. Run the Consumer Agent

In a separate terminal (while both servers are running):

```bash
python scripts/agent_consumer_demo.py
```

This demonstrates the full flow:
1. Agent A reads `agent_facts.json` to discover Agent B
2. Follows `data_facts_pointer` to load `data_facts.json`
3. Checks access type (public)
4. Verifies data freshness (TTL)
5. Fetches stock data from the endpoint
6. Optionally verifies checksum

## Files Structure

```
agents/agent_finance_feed_01/
├── agent_facts.json              # Agent metadata with pointer to Data Facts
├── data_facts/
│   └── public_stock_ticker.json  # Data Facts describing the stock dataset
└── README.md

scripts/
├── public_stock_server.py        # HTTP server (fetches from Yahoo Finance API)
├── generate_data_facts.py        # Updates Data Facts evidence
└── agent_consumer_demo.py        # Agent A: consumer demo script
```

## Data Flow

1. **Stock Server** (`public_stock_server.py`)
   - Uses `yfinance` library to fetch real-time stock prices
   - Serves data at `http://localhost:8000/stock_prices`
   - Returns JSON: `{"TSLA": 245.31, "AAPL": 186.77, "ETH-USD": 3560.14, "timestamp": ...}`

2. **Agent Facts Server** (`serve_agent_facts.py`)
   - HTTP server that exposes Agent Facts and Data Facts JSON files
   - Serves at: `http://localhost:9000/`
   - Mimics NEST's production deployment model

3. **Data Facts** (`data_facts/public_stock_ticker.json`)
   - Describes the dataset
   - Points to endpoint: `http://localhost:8000/stock_prices`
   - Contains evidence: `last_updated`, `checksum_sha256`, `source`
   - Served at: `http://localhost:9000/data_facts/public_stock_ticker.json`

4. **Agent Facts** (`agent_facts.json`)
   - Describes Agent B
   - Contains pointer: `data_facts_pointer` → URL to Data Facts (`http://localhost:9000/data_facts/public_stock_ticker.json`)
   - Served at: `http://localhost:9000/agent_facts.json`

5. **Consumer Agent** (`agent_consumer_demo.py`)
   - Fetches Agent Facts from HTTP endpoint → discovers Agent B
   - Follows URL pointer → fetches Data Facts over HTTP
   - Calls data endpoint → fetches real stock data
   - Verifies freshness and checksum

## Notes

- Uses **real Yahoo Finance API** (no API key required)
- Stock data updates in real-time
- Data Facts evidence (checksum, timestamp) can be auto-updated via `generate_data_facts.py`
- All communication is JSON-based
- No complex infrastructure required (just Python + HTTP)

