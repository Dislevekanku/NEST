# Deploying Finance Feed Agent with Data Facts URL

## Your Question

> If I deploy both the finance agent and consumer agent using the deployment script, will I be able to see the data_facts_url in the agent facts (registry)?

## Answer: **YES, but you need to modify the deployment script**

The `data_facts_url` will appear in the registry (Agent Facts) **IF** the finance feed agent is deployed correctly and registers with the registry.

---

## Current Situation

### What Works Now

1. **Finance Feed Agent Code** ✅
   - Already constructs `data_facts_url` (line 279)
   - Already passes it to NANDA adapter (line 293)
   - Already registers it with registry (adapter.py, line 132-133)

2. **Registry Integration** ✅
   - NANDA adapter accepts `data_facts_url` parameter
   - Registry registration includes `data_facts_url` in payload
   - Registry stores it (assuming registry supports it)

### What's Missing

**The deployment script doesn't have `DATA_SERVER_PORT` parameter!**

The finance feed agent needs:
- `PORT` (for A2A server, default 6000)
- `DATA_SERVER_PORT` (for Flask data server, default 8000)
- `PUBLIC_URL` (for registry registration)

The deployment script currently only has `PORT`, not `DATA_SERVER_PORT`.

---

## How Finance Feed Agent Constructs data_facts_url

**File:** `examples/finance_feed_agent.py`

```python
# Line 243: Get DATA_SERVER_PORT from environment
data_server_port = int(os.getenv("DATA_SERVER_PORT", "8000"))

# Line 261-265: Construct data_server_public_url
if public_url:
    parsed = urlparse(public_url)
    data_server_public_url = f"{parsed.scheme}://{parsed.hostname}:{data_server_port}"
else:
    data_server_public_url = f"http://localhost:{data_server_port}"

# Line 279: Construct data_facts_url
data_facts_url = f"{data_server_public_url}/data_facts/public_stock_ticker.json"

# Line 293: Pass to NANDA adapter
nanda = NANDA(
    ...,
    data_facts_url=data_facts_url  # ← This gets registered!
)
```

**File:** `nanda_core/core/adapter.py`

```python
# Line 132-133: Includes in registry registration
if self.data_facts_url:
    data["data_facts_url"] = self.data_facts_url  # ← Sent to registry!
```

---

## What Happens When You Deploy

### Current Deployment Script (aws-single-agent-deployment.sh)

**Lines 208-224:**
```bash
export AGENT_ID='$AGENT_ID'
export AGENT_NAME='$AGENT_NAME'
...
export PUBLIC_URL='http://$PUBLIC_IP:$PORT'
export PORT='$PORT'
# DATA_SERVER_PORT is NOT set! ← Problem!
nohup python3 examples/finance_feed_agent.py > agent.log 2>&1 &
```

**Result:**
- `DATA_SERVER_PORT` defaults to `8000` (from code)
- `data_facts_url` will be: `http://PUBLIC_IP:8000/data_facts/public_stock_ticker.json`
- This gets registered with the registry ✅

### Registry Response (GET /list)

When consumer agent queries registry:
```json
{
  "agent_id": "finance-feed-agent",
  "agent_name": "Finance Feed Agent",
  "agent_url": "http://PUBLIC_IP:6000/a2a",
  "data_facts_url": "http://PUBLIC_IP:8000/data_facts/public_stock_ticker.json"  ← HERE!
}
```

---

## Solution: Update Deployment Script (Optional)

If you want to make `DATA_SERVER_PORT` configurable, you can add it to the deployment script:

### Option 1: Use Default (Simplest)

**Just deploy as-is:**
- `DATA_SERVER_PORT` defaults to `8000` in the code
- `data_facts_url` will be: `http://PUBLIC_IP:8000/data_facts/public_stock_ticker.json`
- Works fine! ✅

### Option 2: Add DATA_SERVER_PORT Parameter (More Control)

**Add to deployment script:**

```bash
# Line ~23: Add parameter
DATA_SERVER_PORT="${15:-8000}"  # Optional, defaults to 8000

# Line ~223: Export it
export DATA_SERVER_PORT='$DATA_SERVER_PORT'
```

**Then deploy:**
```bash
bash scripts/aws-single-agent-deployment.sh \
  "finance-feed-agent" \
  "sk-ant-xxxxx" \
  "Finance Feed Agent" \
  "financial data" \
  "stock market data provider" \
  "Provides stock market data via Data Facts" \
  "financial data,stock prices" \
  "" \
  "http://registry.chat39.com:6900" \
  "" \
  "6000" \
  "us-east-1" \
  "t3.micro" \
  "" \
  "8000"  # DATA_SERVER_PORT (new parameter)
```

---

## Testing: Will You See data_facts_url?

### Step 1: Deploy Finance Feed Agent

```bash
# Deploy with default DATA_SERVER_PORT (8000)
bash scripts/aws-single-agent-deployment.sh \
  "finance-feed-agent" \
  "sk-ant-xxxxx" \
  "Finance Feed Agent" \
  "financial data" \
  "stock market data provider" \
  "Provides stock market data via Data Facts" \
  "financial data,stock prices" \
  "" \
  "http://registry.chat39.com:6900" \
  "" \
  "6000" \
  "us-east-1" \
  "t3.micro"
```

**What happens:**
1. Agent starts on EC2
2. `PUBLIC_URL` = `http://PUBLIC_IP:6000`
3. `DATA_SERVER_PORT` = `8000` (default)
4. `data_facts_url` = `http://PUBLIC_IP:8000/data_facts/public_stock_ticker.json`
5. Agent registers with registry including `data_facts_url` ✅

### Step 2: Check Registry

```bash
curl http://registry.chat39.com:6900/list | jq '.[] | select(.agent_id | contains("finance-feed"))'
```

**Expected response:**
```json
{
  "agent_id": "finance-feed-agent-abc123",
  "agent_name": "Finance Feed Agent",
  "agent_url": "http://54.237.202.184:6000/a2a",
  "data_facts_url": "http://54.237.202.184:8000/data_facts/public_stock_ticker.json"  ← YES!
}
```

### Step 3: Deploy Consumer Agent

```bash
bash scripts/aws-single-agent-deployment.sh \
  "data-consumer-agent" \
  "sk-ant-xxxxx" \
  "Data Consumer Agent" \
  "data access" \
  "dataset consumer" \
  "Discovers and accesses datasets via Data Facts" \
  "data access,dataset discovery" \
  "" \
  "http://registry.chat39.com:6900" \
  "" \
  "6001" \
  "us-east-1" \
  "t3.micro"
```

**What happens:**
1. Consumer agent starts
2. Calls `registry.list_agents()`
3. Finds finance feed agent
4. Gets `data_facts_url` from registry response ✅
5. Fetches Data Facts
6. Accesses dataset

---

## Important Notes

### 1. Security Group Ports

**Make sure both ports are open in security group:**
- Port 6000 (A2A server)
- Port 8000 (Data server)

The deployment script only opens `PORT` (6000). You may need to manually open port 8000, or modify the script to open `DATA_SERVER_PORT` as well.

### 2. Registry Support

**The registry must support the `data_facts_url` field!**

If the registry doesn't support it, it might:
- Ignore the field (won't store it)
- Store it but not return it in `/list` response

**Check with registry team** if `data_facts_url` is supported.

### 3. Public URL Construction

The finance feed agent constructs `data_facts_url` from:
- `PUBLIC_URL` (from deployment script)
- `DATA_SERVER_PORT` (defaults to 8000)

So `data_facts_url` will be:
```
http://PUBLIC_IP:8000/data_facts/public_stock_ticker.json
```

Make sure this URL is publicly accessible!

---

## Summary

### Will You See data_facts_url in Agent Facts (Registry)?

**YES!** ✅

**IF:**
1. ✅ Finance feed agent is deployed correctly
2. ✅ `PUBLIC_URL` is set (done by deployment script)
3. ✅ `DATA_SERVER_PORT` is accessible (defaults to 8000)
4. ✅ Registry supports `data_facts_url` field
5. ✅ Port 8000 is open in security group

**The `data_facts_url` will appear in the registry response when you call `GET /list`!**

### Current Deployment Script Status

- ✅ Works with defaults (`DATA_SERVER_PORT=8000`)
- ⚠️ Doesn't expose `DATA_SERVER_PORT` as parameter (but defaults work)
- ⚠️ Only opens port 6000 in security group (need to open 8000 manually)

### Recommended Approach

1. **Deploy finance feed agent** (works with defaults)
2. **Manually open port 8000** in AWS security group
3. **Check registry** to verify `data_facts_url` appears
4. **Deploy consumer agent**
5. **Test end-to-end**

---

## Verification Steps

After deploying finance feed agent:

```bash
# 1. Check registry
curl http://registry.chat39.com:6900/list | jq '.[] | select(.agent_id | contains("finance-feed")) | {agent_id, data_facts_url}'

# 2. Test Data Facts endpoint
curl http://PUBLIC_IP:8000/data_facts/public_stock_ticker.json

# 3. Test stock data endpoint
curl http://PUBLIC_IP:8000/stock_data
```

If all work, you're good! ✅

