# Quick Start Guide - Real API Experiment (Option A)

## Prerequisites

```bash
pip install yfinance requests
```

## Run the Experiment

### Terminal 1: Start Agent Facts HTTP Server

```bash
cd NEST
python scripts/serve_agent_facts.py
```

Server runs at: `http://localhost:9000/`
- Agent Facts: `http://localhost:9000/agent_facts.json`
- Data Facts: `http://localhost:9000/data_facts/public_stock_ticker.json`

### Terminal 2: Start Stock Server

```bash
cd NEST
python scripts/public_stock_server.py
```

Server runs at: `http://localhost:8000/stock_prices`

### Terminal 3: Update Data Facts (Optional)

```bash
cd NEST
python scripts/generate_data_facts.py
```

This updates the checksum and timestamp in Data Facts.

### Terminal 4: Run Consumer Agent

```bash
cd NEST
python scripts/agent_consumer_demo.py
```

## Expected Output

The consumer agent will:
1. ✅ Fetch Agent Facts from HTTP endpoint (`http://localhost:9000/agent_facts.json`)
2. ✅ Follow URL pointer to fetch Data Facts over HTTP
3. ✅ Check access type (public)
4. ✅ Verify data freshness
5. ✅ Fetch real stock data from Yahoo Finance API
6. ✅ Verify checksum

## Files Created

- `agents/agent_finance_feed_01/agent_facts.json` - Agent metadata (served via HTTP)
- `agents/agent_finance_feed_01/data_facts/public_stock_ticker.json` - Data Facts (served via HTTP)
- `scripts/serve_agent_facts.py` - HTTP server for Agent Facts and Data Facts
- `scripts/public_stock_server.py` - Real API server (Yahoo Finance)
- `scripts/generate_data_facts.py` - Auto-update Data Facts
- `scripts/agent_consumer_demo.py` - Consumer agent demo (fetches over HTTP)

## Notes

- Uses **real Yahoo Finance API** (no API key needed)
- Stock prices update in real-time
- All communication is JSON-based
- Minimal infrastructure (Python + HTTP)

