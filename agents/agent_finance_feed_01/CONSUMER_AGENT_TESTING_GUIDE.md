# Consumer Agent Testing Guide

## Overview

This guide explains how to test the data consumer agent, which demonstrates:
1. Registry-based discovery (standard NEST pattern)
2. Data Facts URL extraction from registry
3. Data Facts access
4. Dataset access

## Prerequisites

1. **Finance Feed Agent Running**
   - Must be running on port 6000 (A2A) and 8000 (Data server)
   - Must be registered with the registry

2. **Registry Accessible**
   - Default: `http://registry.chat39.com:6900`
   - Or set `REGISTRY_URL` environment variable

3. **Consumer Agent** (optional, for A2A tests)
   - Runs on port 6001 (default)

## Quick Test

### Option 1: Automated Test Script

Run the PowerShell test script:

```powershell
cd C:\Users\disle\OneDrive\Documents\projects\Nanda\NEST\agents\agent_finance_feed_01
.\test_consumer_agent.ps1
```

This tests:
- ✅ Registry connectivity
- ✅ Finance feed agent discovery
- ✅ Data Facts URL extraction
- ✅ Data Facts access
- ✅ Dataset access

### Option 2: Manual Testing

#### 1. Check Registry

```powershell
$registryUrl = "http://registry.chat39.com:6900"
Invoke-RestMethod -Uri "$registryUrl/list" | ConvertTo-Json -Depth 5
```

Look for:
- Finance feed agent in the list
- `data_facts_url` field in the agent entry

#### 2. Test Data Facts Access

```powershell
$dataFactsUrl = "http://localhost:8000/data_facts/public_stock_ticker.json"
Invoke-RestMethod -Uri $dataFactsUrl | ConvertTo-Json -Depth 5
```

Should return Data Facts JSON with:
- `dataset_id`
- `access_type: "public"`
- `endpoint`
- `evidence` (with checksum, timestamp)

#### 3. Test Dataset Access

```powershell
$endpoint = "http://localhost:8000/stock_data"
Invoke-RestMethod -Uri $endpoint | ConvertTo-Json -Depth 3
```

Should return stock prices JSON.

## Running the Consumer Agent

### Start Consumer Agent

```powershell
cd C:\Users\disle\OneDrive\Documents\projects\Nanda\NEST

# Set environment variables
$env:AGENT_ID="data-consumer-agent"
$env:AGENT_NAME="Data Consumer Agent"
$env:REGISTRY_URL="http://registry.chat39.com:6900"
$env:PORT="6001"

# Run the agent
python examples/data_consumer_agent.py
```

### Test A2A Communication

Once the consumer agent is running, send A2A messages:

```powershell
Invoke-RestMethod -Uri http://localhost:6001/a2a -Method POST `
  -Headers @{"Content-Type"="application/json"} `
  -Body '{
    "content": {
      "text": "fetch stock prices",
      "type": "text"
    },
    "role": "user",
    "conversation_id": "test-123"
  }' | ConvertTo-Json -Depth 5
```

Expected response should include stock prices.

## End-to-End Test Flow

### Step 1: Start Finance Feed Agent

```powershell
cd C:\Users\disle\OneDrive\Documents\projects\Nanda\NEST

$env:AGENT_ID="finance-feed-agent"
$env:AGENT_NAME="Finance Feed Agent"
$env:REGISTRY_URL="http://registry.chat39.com:6900"
$env:PUBLIC_URL="http://localhost:6000"
$env:PORT="6000"
$env:DATA_SERVER_PORT="8000"

python examples/finance_feed_agent.py
```

Wait for:
- "Finance data server started"
- "Agent registered successfully"

### Step 2: Run Test Script

```powershell
cd C:\Users\disle\OneDrive\Documents\projects\Nanda\NEST\agents\agent_finance_feed_01
.\test_consumer_agent.ps1
```

### Step 3: Start Consumer Agent (Optional)

In a new terminal:

```powershell
cd C:\Users\disle\OneDrive\Documents\projects\Nanda\NEST

$env:AGENT_ID="data-consumer-agent"
$env:AGENT_NAME="Data Consumer Agent"
$env:REGISTRY_URL="http://registry.chat39.com:6900"
$env:PORT="6001"

python examples/data_consumer_agent.py
```

### Step 4: Test A2A Communication

Send messages to the consumer agent:

```powershell
Invoke-RestMethod -Uri http://localhost:6001/a2a -Method POST `
  -Headers @{"Content-Type"="application/json"} `
  -Body '{
    "content": {"text": "fetch stock prices", "type": "text"},
    "role": "user",
    "conversation_id": "test-123"
  }'
```

## Expected Results

### Test Script Output

```
============================================================
Data Consumer Agent Test Suite
============================================================

Test 1: Registry Connectivity
============================================================
SUCCESS: Registry is accessible
  Found 1 agent(s) in registry
    - finance-feed-agent

Test 2: Find Finance Feed Agent
============================================================
SUCCESS: Found finance feed agent
  Agent ID: finance-feed-agent
  Data Facts URL: http://localhost:8000/data_facts/public_stock_ticker.json

Test 3: Access Data Facts
============================================================
SUCCESS: Data Facts retrieved
  Dataset ID: public_stock_ticker
  Access Type: public
  Endpoint: http://localhost:8000/stock_data
  TTL: 600 seconds

Test 4: Access Dataset
============================================================
SUCCESS: Dataset retrieved
  Stock Prices:
    TSLA: $448.96
    AAPL: $260.25
    ETH-USD: $3100.76

============================================================
Test Summary
============================================================
PASS: Registry Connectivity
PASS: Find Finance Feed Agent
PASS: Access Data Facts
PASS: Access Dataset

Results: 4 passed, 0 failed, 0 skipped/warned (out of 4 tests)
✅ All critical tests passed!
```

## Troubleshooting

### Registry Not Accessible
- Check registry URL: `http://registry.chat39.com:6900`
- Verify network connectivity
- Check if registry service is running

### Finance Feed Agent Not Found
- Verify finance feed agent is running
- Check if agent is registered: `Invoke-RestMethod -Uri "$registryUrl/list"`
- Ensure agent_id matches "finance-feed-agent"

### No data_facts_url in Registry
- Check if finance feed agent was registered with `data_facts_url`
- Verify `PUBLIC_URL` is set correctly
- Check agent registration output for errors

### Data Facts Not Accessible
- Verify finance feed agent is running
- Check Data Facts endpoint: `http://localhost:8000/data_facts/public_stock_ticker.json`
- Check firewall/network settings

### Dataset Not Accessible
- Verify stock data endpoint: `http://localhost:8000/stock_data`
- Check finance feed agent logs for errors
- Verify yfinance library is installed

## Next Steps

Once all tests pass:
1. ✅ Registry discovery working
2. ✅ Data Facts URL extraction working
3. ✅ Data Facts access working
4. ✅ Dataset access working

You can now:
- Deploy the finance feed agent to production
- Create additional consumer agents
- Extend the pattern to other datasets

