# NEST Deployment Process Analysis

## Overview
This document provides a complete understanding of the NEST deployment process, including where agent code lives, where MCP tools are registered, how data is currently NOT handled, and where to hook in the "attach data" step.

---

## 1. Agent Code Location

### Primary Agent Implementation
**Location:** `NEST/examples/nanda_agent.py`

This is the main agent code that gets deployed. Key characteristics:
- Uses Anthropic Claude LLM for intelligent responses
- Configurable via environment variables (AGENT_ID, AGENT_NAME, AGENT_DOMAIN, etc.)
- Creates agent logic function that processes messages
- Initializes NANDA adapter with agent logic

**Key Code Structure:**
```python
# Main entry point
def main():
    agent_logic = create_llm_agent_logic(AGENT_CONFIG)
    nanda = NANDA(
        agent_id=AGENT_CONFIG["agent_id"],
        agent_logic=agent_logic,
        port=PORT,
        registry_url=AGENT_CONFIG["registry_url"],
        public_url=AGENT_CONFIG["public_url"],
        enable_telemetry=False
    )
    nanda.start()
```

### Core Framework Components
- **Adapter:** `NEST/nanda_core/core/adapter.py` - Main NANDA class that wraps agent logic
- **Agent Bridge:** `NEST/nanda_core/core/agent_bridge.py` - Handles A2A communication
- **Registry Client:** `NEST/nanda_core/core/registry_client.py` - Registry integration

### Deployment Reference
In the deployment script (`scripts/aws-single-agent-deployment.sh`), the agent is started at:
- **Line 178:** `nohup python3 examples/nanda_agent.py > agent.log 2>&1 &`

---

## 2. MCP Tools Registration

### Current State: MCP Tools Exist But Are NOT Integrated

**MCP Client Location:** `NEST/nanda_core/core/mcp_client.py`

The MCP client exists with the following capabilities:
- `MCPClient` class for connecting to MCP servers
- `MCPRegistry` class for discovering MCP servers from registry
- Methods to execute queries on MCP servers

**However, MCP tools are NOT currently registered or used in the agent flow:**

1. **No MCP Integration in Agent Bridge:** 
   - `agent_bridge.py` does NOT import or use `MCPClient`
   - Agent logic functions do NOT have access to MCP tools
   - No MCP tool registration in the agent initialization

2. **No MCP Integration in Agent Logic:**
   - `nanda_agent.py` does NOT import or use MCP tools
   - The LLM agent logic does NOT have MCP tools available in its tool list

3. **MCP Registry Exists But Unused:**
   - `registry_client.py` has `get_mcp_servers()` and `get_mcp_server_config()` methods
   - These methods are NOT called during agent initialization or runtime

### Where MCP Tools SHOULD Be Registered (Future Integration Points)

To integrate MCP tools, you would need to:

1. **In `nanda_agent.py` (around line 198):**
   - Import MCPClient
   - Discover available MCP servers from registry
   - Connect to MCP servers and get available tools
   - Pass tools to Anthropic API in the `create_llm_agent_logic` function

2. **In `agent_bridge.py` (in `handle_message` method):**
   - Add MCP tool execution capability
   - Handle tool use responses from LLM

3. **In deployment script (user_data section):**
   - Add environment variables for MCP registry URL
   - Configure MCP server connections

---

## 3. How Data is Currently NOT Handled

### No Data Attachment Mechanism

**Current State:** The deployment process does NOT handle data attachment at all.

1. **No Data Parameters in Deployment Script:**
   - `aws-single-agent-deployment.sh` accepts NO data-related parameters
   - No data files, data URLs, or data sources are passed to the agent

2. **No Data in Agent Configuration:**
   - `nanda_agent.py` does NOT load or process any data files
   - No data directories or data sources are configured
   - Agent only uses environment variables for personality/behavior config

3. **No Data in User Data Script:**
   - The EC2 user data script (`user_data_${AGENT_ID}.sh`) does NOT:
     - Download data files
     - Mount data volumes
     - Configure data access
     - Set up data directories

4. **No Data in Agent Logic:**
   - The `agent_logic` function receives only `(message: str, conversation_id: str)`
   - No data context or data access is provided
   - Agent cannot query or access external data sources

### What's Missing for Data Handling

To add data handling, you would need:
- Data source configuration (files, URLs, databases)
- Data loading mechanism in agent initialization
- Data access methods in agent logic
- Data attachment step in deployment process

---

## 4. Deployment Script Location

### Primary Deployment Script
**Location:** `NEST/scripts/aws-single-agent-deployment.sh`

**Purpose:** Deploys a single agent to AWS EC2

**Key Sections:**
1. **Lines 1-39:** Argument parsing and validation
2. **Lines 54-101:** AWS infrastructure setup (security groups, key pairs)
3. **Lines 116-183:** User data script creation (the actual deployment logic)
4. **Lines 185-241:** EC2 instance launch and output

### Other Deployment Scripts
- `NEST/scripts/aws-multi-agent-deployment.sh` - Multi-agent deployment
- `NEST/scripts/deploy-agent.sh` - Deploy to existing server
- `NEST/scripts/akamai-single-agent-deployment.sh` - Akamai deployment
- `NEST/scripts/akamai-multi-agent-deployment.sh` - Akamai multi-agent

### User Data Script Generation
The deployment script generates a user data script at **lines 118-183** that:
- Installs system dependencies
- Clones NEST repository
- Sets up Python virtual environment
- Configures agent with environment variables
- Starts the agent process

---

## 5. Where to Hook In "Attach Data" Step

### Recommended Integration Points

#### Option 1: In Deployment Script (User Data Section) - RECOMMENDED
**Location:** `NEST/scripts/aws-single-agent-deployment.sh`, lines 163-179

**Current Code:**
```bash
# Start the agent with all configuration
echo "Starting NANDA agent with PUBLIC_URL: http://\$PUBLIC_IP:$PORT"
sudo -u ubuntu bash -c "
    cd /home/ubuntu/nanda-agent-$AGENT_ID
    source env/bin/activate
    export ANTHROPIC_API_KEY='$ANTHROPIC_API_KEY'
    export AGENT_ID='$AGENT_ID'
    # ... more env vars ...
    nohup python3 examples/nanda_agent.py > agent.log 2>&1 &
"
```

**Hook Point - Add BEFORE agent startup:**
```bash
# ATTACH DATA STEP - Add here (around line 163)
echo "Attaching data to agent..."
# Download data files
# Mount data volumes
# Configure data access
# Set DATA_PATH or similar environment variable

# Then start agent with data available
```

**Advantages:**
- Data is available when agent starts
- Can pass data location via environment variables
- Data setup happens once during deployment

#### Option 2: In Agent Initialization
**Location:** `NEST/examples/nanda_agent.py`, in `main()` function (around line 180)

**Current Code:**
```python
def main():
    # ... config loading ...
    agent_logic = create_llm_agent_logic(AGENT_CONFIG)
    nanda = NANDA(...)
    nanda.start()
```

**Hook Point - Add BEFORE creating agent_logic:**
```python
def main():
    # ... config loading ...
    
    # ATTACH DATA STEP - Add here
    data_path = os.getenv("DATA_PATH", None)
    if data_path:
        # Load data files
        # Initialize data access
        # Pass data to agent_logic creation
    
    agent_logic = create_llm_agent_logic(AGENT_CONFIG)
    # ...
```

**Advantages:**
- Data loading happens in Python (more flexible)
- Can validate data before agent starts
- Easier to handle different data formats

#### Option 3: In Deployment Script Arguments
**Location:** `NEST/scripts/aws-single-agent-deployment.sh`, lines 10-20

**Current Code:**
```bash
AGENT_ID="$1"
ANTHROPIC_API_KEY="$2"
AGENT_NAME="$3"
# ... more args ...
```

**Hook Point - Add new parameter:**
```bash
AGENT_ID="$1"
ANTHROPIC_API_KEY="$2"
# ... existing args ...
DATA_SOURCE="${12:-}"  # New parameter for data source
```

**Advantages:**
- Data source specified at deployment time
- Can be different for each agent
- Flexible data source types (URL, S3, local path)

### Recommended Implementation Flow

1. **Add data parameter to deployment script** (Option 3)
2. **Download/attach data in user data script** (Option 1)
3. **Load data in agent initialization** (Option 2)
4. **Make data available to agent logic**

### Specific Code Locations for Data Attachment

**File:** `NEST/scripts/aws-single-agent-deployment.sh`

**Line 20:** Add data parameter:
```bash
DATA_SOURCE="${12:-}"
```

**Line 163-179:** Add data attachment step:
```bash
# Attach data (if provided)
if [ -n "$DATA_SOURCE" ]; then
    echo "Attaching data from: $DATA_SOURCE"
    # Download from URL, S3, or mount volume
    # Set DATA_PATH environment variable
    export DATA_PATH="/home/ubuntu/agent-data"
fi
```

**File:** `NEST/examples/nanda_agent.py`

**Line 180-198:** Add data loading:
```python
def main():
    # ... existing config ...
    
    # Load data if available
    data_path = os.getenv("DATA_PATH", None)
    if data_path:
        # Load and process data
        agent_data = load_agent_data(data_path)
        AGENT_CONFIG["data"] = agent_data
    
    agent_logic = create_llm_agent_logic(AGENT_CONFIG)
    # ...
```

---

## Summary

### Agent Code Location
- **Main agent:** `NEST/examples/nanda_agent.py`
- **Core framework:** `NEST/nanda_core/core/adapter.py`

### MCP Tools Registration
- **MCP client exists:** `NEST/nanda_core/core/mcp_client.py`
- **NOT currently integrated** into agent flow
- **Would need integration** in `nanda_agent.py` and `agent_bridge.py`

### Data Handling
- **Currently NOT handled** at all
- **No data parameters** in deployment
- **No data loading** in agent code
- **No data access** in agent logic

### Deployment Script
- **Location:** `NEST/scripts/aws-single-agent-deployment.sh`
- **User data section:** Lines 118-183
- **Agent startup:** Line 178

### Data Attachment Hook Points
1. **Deployment script arguments** (line 20) - Add DATA_SOURCE parameter
2. **User data script** (line 163) - Download/attach data before agent startup
3. **Agent initialization** (line 180) - Load data in `main()` function
4. **Agent logic creation** (line 198) - Pass data to agent logic

---

## Next Steps for Data Integration

1. Modify `aws-single-agent-deployment.sh` to accept data source parameter
2. Add data download/attachment step in user data script (before line 178)
3. Modify `nanda_agent.py` to load data from DATA_PATH environment variable
4. Update agent logic to have access to loaded data
5. Test deployment with sample data source

