# NEST Deployment Flow Analysis
## Identifying Where to Hook in "Data Attach" Step

---

## Executive Summary

**Primary Deployment Script:** `NEST/scripts/aws-single-agent-deployment.sh`

**Agent Entry Point:** `NEST/examples/nanda_agent.py` (main function)

**Key Finding:** NEST uses a **simple deployment model** - it clones the entire repository and runs `examples/nanda_agent.py` directly. There is **NO separate agent directory creation, file copying, or MCP tool loader** - everything runs from the cloned repository.

---

## Deployment Flow Trace

### 1. Deployment Script: `scripts/aws-single-agent-deployment.sh`

**Location:** Lines 118-183 (user-data script generation)

**What it does:**
1. **Creates EC2 instance** with user-data script
2. **User-data script runs on instance startup** (cloud-init)

### 2. User-Data Script (Generated at Lines 124-183)

**Key Steps:**

#### Step 1: System Setup (Lines 131-133)
```bash
apt-get update -y
apt-get install -y python3 python3-venv python3-pip git curl
```
- **Purpose:** Install system dependencies
- **No agent directory created here**

#### Step 2: Clone Repository (Lines 136-138)
```bash
cd /home/ubuntu
sudo -u ubuntu git clone https://github.com/projnanda/NEST.git nanda-agent-$AGENT_ID
cd nanda-agent-$AGENT_ID
```
- **Purpose:** Clone entire NEST repository
- **Agent directory:** `/home/ubuntu/nanda-agent-$AGENT_ID`
- **This IS the "agent directory"** - it's the entire cloned repo
- **No file copying** - everything is already in the repo

#### Step 3: Virtual Environment (Lines 141-142)
```bash
sudo -u ubuntu python3 -m venv env
sudo -u ubuntu bash -c "source env/bin/activate && pip install --upgrade pip && pip install -e . && pip install anthropic"
```
- **Purpose:** Create Python virtual environment
- **Installs:** NEST package and dependencies
- **No MCP tool loader** - MCP is just a dependency (`pip install -e .` installs it)

#### Step 4: Configure Agent (Line 145)
```bash
sudo -u ubuntu sed -i "s/PORT = 6000/PORT = $PORT/" examples/nanda_agent.py
```
- **Purpose:** Modify port in agent file
- **This is the ONLY file modification**

#### Step 5: Get Public IP (Lines 147-167)
- **Purpose:** Retrieve EC2 public IP for registration

#### Step 6: Set Environment Variables (Lines 178-191)
```bash
sudo -u ubuntu bash -c "
    cd /home/ubuntu/nanda-agent-$AGENT_ID
    source env/bin/activate
    export ANTHROPIC_API_KEY='$ANTHROPIC_API_KEY'
    export AGENT_ID='$AGENT_ID'
    export AGENT_NAME='$AGENT_NAME'
    export AGENT_DOMAIN='$DOMAIN'
    export AGENT_SPECIALIZATION='$SPECIALIZATION'
    export AGENT_DESCRIPTION='$DESCRIPTION'
    export AGENT_CAPABILITIES='$CAPABILITIES'
    export REGISTRY_URL='$REGISTRY_URL'
    export PUBLIC_URL='http://$PUBLIC_IP:$PORT'
    export PORT='$PORT'
    export DATA_PATH='$DATA_PATH'  # <-- Already added in Step 2
    nohup python3 examples/nanda_agent.py > agent.log 2>&1 &
"
```
- **Purpose:** Set all environment variables and start agent
- **This is where environment variables are set**
- **Agent starts here** - runs `examples/nanda_agent.py`

---

## Agent Loading Flow: `examples/nanda_agent.py`

### Entry Point: `main()` function (Line 236)

**Flow:**

1. **Configuration Loading** (Lines 238-243)
   - Prints agent info
   - Loads from environment variables (already set in deployment script)

2. **Data Loading** (Lines 245-257) ✅ **ALREADY IMPLEMENTED**
   ```python
   # Load attached data if DATA_PATH is provided
   attached_data = None
   if DATA_PATH:
       print(f"📂 Loading data from: {DATA_PATH}")
       attached_data = load_attached_data(DATA_PATH)
       if attached_data is not None:
           if PANDAS_AVAILABLE and isinstance(attached_data, pd.DataFrame):
               print(f"📊 Loaded data with shape: {attached_data.shape}")
           AGENT_CONFIG["data"] = attached_data
   ```
   - **This is where data attach happens**
   - **Already implemented in Step 3**

3. **Agent Logic Creation** (Line 268)
   ```python
   agent_logic = create_llm_agent_logic(AGENT_CONFIG)
   ```
   - Creates LLM-powered agent logic
   - **AGENT_CONFIG["data"] is available here** but not currently used

4. **NANDA Agent Creation** (Lines 271-277)
   ```python
   nanda = NANDA(
       agent_id=AGENT_CONFIG["agent_id"],
       agent_logic=agent_logic,
       port=PORT,
       registry_url=AGENT_CONFIG["registry_url"],
       public_url=AGENT_CONFIG["public_url"],
       enable_telemetry=False
   )
   ```
   - Creates NANDA adapter instance
   - **No MCP tools registered here** (MCP not integrated)

5. **Agent Start** (Line 281)
   ```python
   nanda.start()
   ```
   - Starts the A2A server

---

## Key Findings

### ✅ What EXISTS:

1. **Agent Directory Creation:**
   - **Location:** `aws-single-agent-deployment.sh` line 137
   - **Method:** `git clone` creates `/home/ubuntu/nanda-agent-$AGENT_ID`
   - **No separate agent directory** - entire repo is the "agent directory"

2. **Agent Files:**
   - **Location:** Already in cloned repository
   - **No file copying** - files are in `examples/nanda_agent.py`
   - **Only modification:** Port number (line 145)

3. **Environment Variables:**
   - **Location:** `aws-single-agent-deployment.sh` lines 181-191
   - **Method:** `export` statements in bash script
   - **DATA_PATH already added** (line 191)

4. **Data Loading:**
   - **Location:** `examples/nanda_agent.py` lines 245-257
   - **Status:** ✅ Already implemented
   - **Data available in:** `AGENT_CONFIG["data"]`

### ❌ What DOES NOT EXIST:

1. **MCP Tool Loader:**
   - **Status:** MCP client exists (`nanda_core/core/mcp_client.py`) but **NOT integrated**
   - **No MCP tool registration** in agent initialization
   - **No MCP tools exposed** to agent logic
   - **Would need to be added** in `nanda_agent.py` main() function

2. **Separate Agent Runtime:**
   - **No `agent_runtime/` directory**
   - **No `agent_loader/` directory**
   - **No `start.py` or `deploy_agent.py`** (except `scripts/deploy-agent.sh` which is different)

3. **File Copying Mechanism:**
   - **No copying of agent files** - everything runs from cloned repo
   - **No agent-specific file isolation**

---

## Exact Points for "Data Attach" Hook

### ✅ ALREADY IMPLEMENTED:

**Location 1: Deployment Script - Environment Variable** (Line 191)
```bash
export DATA_PATH='$DATA_PATH'
```
- **Status:** ✅ Done in Step 2
- **Purpose:** Pass DATA_PATH to agent process

**Location 2: Agent Code - Data Loading** (Lines 245-257)
```python
if DATA_PATH:
    attached_data = load_attached_data(DATA_PATH)
    AGENT_CONFIG["data"] = attached_data
```
- **Status:** ✅ Done in Step 3
- **Purpose:** Load data and make it available to agent

### 🔧 NEEDS IMPLEMENTATION (Step 4 - MCP Tools):

**Location 3: Agent Code - MCP Tool Registration** (After line 257, before line 268)
```python
# TODO: Register MCP tools if data is available
if AGENT_CONFIG.get("data") is not None:
    # Register MCP tools that expose the data
    # Example: get_row_count, query_data, etc.
    pass
```
- **Status:** ❌ Not implemented
- **Purpose:** Expose data via MCP tools
- **Would integrate with:** `nanda_core/core/mcp_client.py`

**Location 4: Agent Logic - Use Data in Responses** (In `create_llm_agent_logic`, around line 114)
```python
def llm_agent_logic(message: str, conversation_id: str) -> str:
    # TODO: Use AGENT_CONFIG["data"] if available
    # Could pass to LLM as context or use MCP tools
    pass
```
- **Status:** ❌ Not implemented
- **Purpose:** Actually use the loaded data in agent responses

---

## Alternative Deployment Scripts

### `scripts/deploy-agent.sh`
- **Purpose:** Deploy to existing server (not AWS EC2)
- **Similar flow:** Clone repo, create venv, run agent
- **Key difference:** Creates `run_agent.py` instead of using `examples/nanda_agent.py`
- **Data attach point:** Would need to add DATA_PATH handling here too

### `scripts/aws-multi-agent-deployment.sh`
- **Purpose:** Deploy multiple agents on one instance
- **Uses supervisor** to manage multiple agent processes
- **Each agent:** Runs `examples/nanda_agent.py` with different env vars
- **Data attach point:** Same as single-agent (line 191 in user-data script)

---

## Summary: Where to Modify

### For Data Attachment (Already Done ✅):
1. ✅ **Deployment script:** `scripts/aws-single-agent-deployment.sh` line 191
2. ✅ **Agent code:** `examples/nanda_agent.py` lines 245-257

### For MCP Tool Integration (Step 4 - TODO):
1. **Agent initialization:** `examples/nanda_agent.py` after line 257
   - Register MCP tools that expose the data
   - Integrate with `nanda_core/core/mcp_client.py`

2. **Agent logic:** `examples/nanda_agent.py` in `create_llm_agent_logic()` (around line 114)
   - Make data available to LLM via MCP tools
   - Or pass data as context to LLM

3. **Agent bridge:** `nanda_core/core/agent_bridge.py` (optional)
   - Handle MCP tool calls in message processing
   - Execute MCP tools when requested

---

## Conclusion

**The deployment flow is simpler than expected:**
- No separate agent directory creation (just git clone)
- No file copying (everything in repo)
- No MCP tool loader (MCP not integrated yet)
- Environment variables set in deployment script
- Agent runs directly from `examples/nanda_agent.py`

**Data attach is already wired:**
- ✅ DATA_PATH passed via environment variable
- ✅ Data loaded in `nanda_agent.py` main()
- ✅ Data available in `AGENT_CONFIG["data"]`

**Next step (Step 4):**
- Expose data via MCP tools
- Use data in agent responses

