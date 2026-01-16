# A2A Communication Guide: Consumer Agent ↔ Finance Feed Agent

## Overview

The consumer agent has been enhanced to support **Agent-to-Agent (A2A) communication** with the finance feed agent. This allows the consumer agent to query the finance feed agent directly via A2A protocol, in addition to accessing datasets via Data Facts.

---

## Features

### 1. A2A Communication
- Consumer agent can send A2A messages to finance feed agent
- Finance feed agent responds via A2A
- Automatic fallback to dataset access if A2A fails

### 2. Agent Discovery
- Consumer agent discovers finance feed agent via registry (if registered)
- Falls back to direct URL for local testing (`FINANCE_FEED_AGENT_URL` environment variable)

### 3. Dual Access Methods
- **A2A Communication**: Query finance feed agent directly (e.g., "ask finance agent about stock prices")
- **Data Facts Access**: Access datasets via Data Facts (e.g., "fetch stock prices")

---

## Changes Made

### Consumer Agent (`examples/data_consumer_agent.py`)

1. **Added A2A Client Support**
   - Imported `python_a2a` library (A2AClient, Message, TextContent, MessageRole)
   - Added `A2A_AVAILABLE` flag for graceful degradation

2. **New Function: `call_finance_agent_via_a2a()`**
   - Discovers finance feed agent via registry
   - Sends A2A messages to finance feed agent
   - Handles response parsing robustly
   - Supports fallback URL for local testing

3. **Updated Agent Logic: `create_consumer_agent_logic()`**
   - Added A2A communication support
   - Detects stock/finance-related queries
   - Routes to A2A communication when appropriate
   - Falls back to dataset access if A2A fails

4. **Enhanced Main Function**
   - Supports `FINANCE_FEED_AGENT_URL` environment variable for fallback
   - Passes A2A configuration to agent logic
   - Updated help messages to include A2A examples

---

## Usage

### Starting the Agents

#### 1. Start Finance Feed Agent
```bash
cd NEST
python examples/finance_feed_agent.py
```

Finance feed agent will run on:
- **A2A endpoint**: `http://localhost:6000/a2a`
- **Data server**: `http://localhost:8000/stock_data`
- **Data Facts**: `http://localhost:8000/data_facts/public_stock_ticker.json`

#### 2. Start Consumer Agent
```bash
cd NEST
python examples/data_consumer_agent.py
```

Consumer agent will run on:
- **A2A endpoint**: `http://localhost:6001/a2a`
- **Registry**: Uses `REGISTRY_URL` environment variable (or default)

**Optional Environment Variables:**
```bash
export FINANCE_FEED_AGENT_URL=http://localhost:6000  # Fallback URL for local testing
export REGISTRY_URL=http://registry.chat39.com:6900  # Registry URL (optional for local testing)
```

---

## Querying the Consumer Agent

### A2A Communication Queries

The consumer agent will use A2A communication for queries like:

1. **"ask finance agent about stock prices"**
   - Consumer agent sends A2A message to finance feed agent
   - Finance feed agent responds with stock prices
   - Consumer agent returns the response

2. **"what are the current stock prices?"**
   - Detects stock price query
   - Routes to A2A communication
   - Returns finance feed agent's response

3. **"tell me about finance data"**
   - Triggers A2A communication
   - Finance feed agent responds with information

### Dataset Access Queries

The consumer agent will use Data Facts access for queries like:

1. **"fetch stock prices"**
   - Accesses dataset via Data Facts
   - Validates freshness and checksum
   - Returns stock prices

2. **"access dataset"**
   - Uses Data Facts endpoint
   - Returns dataset information

---

## Testing

### Test Script

Run the comprehensive A2A communication test:

```bash
cd NEST/agents/agent_finance_feed_01
python test_a2a_communication.py
```

This test script:
1. Tests finance feed agent A2A endpoint directly
2. Tests consumer agent -> finance feed agent A2A communication
3. Tests end-to-end A2A flow

### Manual Testing

#### Test 1: Finance Feed Agent Direct A2A
```bash
curl -X POST http://localhost:6000/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "content": {"text": "what are the current stock prices?", "type": "text"},
    "role": "user",
    "conversation_id": "test-123"
  }'
```

#### Test 2: Consumer Agent -> Finance Feed Agent A2A
```bash
curl -X POST http://localhost:6001/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "content": {"text": "ask finance agent about stock prices", "type": "text"},
    "role": "user",
    "conversation_id": "test-456"
  }'
```

---

## Communication Flow

### A2A Communication Flow

```
User/Agent
  ↓
Consumer Agent (receives message)
  ↓
Consumer Agent Logic (detects stock/finance query)
  ↓
call_finance_agent_via_a2a()
  ↓
Registry Discovery (or fallback URL)
  ↓
A2AClient.send_message() → Finance Feed Agent A2A endpoint
  ↓
Finance Feed Agent Logic (processes message)
  ↓
Finance Feed Agent Response (via A2A)
  ↓
Consumer Agent (parses response)
  ↓
Consumer Agent (returns response to user/agent)
```

### Dataset Access Flow (Fallback)

```
User/Agent
  ↓
Consumer Agent (receives message)
  ↓
Consumer Agent Logic (detects dataset access request)
  ↓
discover_and_access_dataset()
  ↓
Registry Discovery → Data Facts URL
  ↓
Fetch Data Facts → Dataset Endpoint
  ↓
Consumer Agent (returns dataset data)
```

---

## Requirements

### Python Libraries

```bash
pip install python-a2a  # For A2A communication
pip install requests     # For HTTP requests
pip install yfinance     # For finance feed agent (stock data)
pip install flask        # For finance feed agent (data server)
```

---

## Troubleshooting

### A2A Communication Not Working

1. **Check if `python_a2a` is installed:**
   ```bash
   pip install python-a2a
   ```

2. **Check if finance feed agent is running:**
   ```bash
   curl http://localhost:6000/a2a  # Should return 405 or similar (not connection error)
   ```

3. **Check fallback URL:**
   ```bash
   export FINANCE_FEED_AGENT_URL=http://localhost:6000
   ```

4. **Check registry (if using):**
   - Ensure finance feed agent is registered
   - Verify registry URL is correct

### Consumer Agent Falls Back to Dataset Access

If A2A communication fails, the consumer agent will automatically fall back to dataset access via Data Facts. This is expected behavior and ensures robustness.

---

## Summary

✅ **A2A Communication**: Consumer agent can query finance feed agent via A2A  
✅ **Agent Discovery**: Supports registry discovery and fallback URLs  
✅ **Dual Access**: Supports both A2A communication and Data Facts access  
✅ **Robust Fallback**: Falls back to dataset access if A2A fails  
✅ **Comprehensive Testing**: Test script included for verification

The consumer agent and finance feed agent are now fully integrated with A2A communication support!

