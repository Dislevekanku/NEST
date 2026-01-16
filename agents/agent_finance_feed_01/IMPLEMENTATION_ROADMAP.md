# Implementation Roadmap: Aligning Finance Feed Agent with NEST Architecture

## Goal
Transform the finance feed agent experiment into a proper NEST agent that:
- ✅ Uses A2A protocol for agent-to-agent communication (like menu/concierge)
- ✅ Registers with registry (like menu/concierge)
- ✅ Uses environment variables for configuration (like menu/concierge)
- ✅ Preserves Agent Facts + Data Facts pattern (new capability)
- ✅ Can be discovered and communicated with via standard NEST patterns

---

## Current State Analysis

### Finance Feed Agent (Current - Experiment)
- ❌ Standalone HTTP servers (not NEST agent)
- ❌ No registry registration
- ❌ No A2A protocol
- ✅ Agent Facts + Data Facts pattern (good!)
- ✅ HTTP endpoints for metadata

### Menu/Concierge Agents (Reference - NEST Standard)
- ✅ Real NEST agents using `examples/nanda_agent.py`
- ✅ Registry registration
- ✅ A2A protocol communication
- ✅ Environment variable configuration
- ✅ Deployed via `scripts/aws-single-agent-deployment.sh`

---

## Roadmap

### Phase 1: Create Finance Feed Agent as NEST Agent

**Goal:** Make finance feed agent a real NEST agent (like menu/concierge)

**Tasks:**
1. **Create `examples/finance_feed_agent.py`**
   - Copy structure from `examples/nanda_agent.py`
   - Add finance-specific logic (stock data serving)
   - Integrate Agent Facts serving endpoint
   - Integrate Data Facts serving endpoint
   - Keep stock data fetching logic (Yahoo Finance API)

2. **Add HTTP endpoints to NEST agent**
   - `/agent_facts.json` - Serve Agent Facts JSON
   - `/data_facts/{dataset_id}.json` - Serve Data Facts JSON
   - These can be added as additional routes in the A2A server or separate HTTP server on different port

3. **Environment Variables**
   - Use standard NEST env vars: `AGENT_ID`, `AGENT_NAME`, `AGENT_DOMAIN`, etc.
   - Add finance-specific: `STOCK_SERVER_PORT` (optional, defaults to 8000)
   - `AGENT_FACTS_PORT` (optional, defaults to 9000 or same as agent port)

**Deliverables:**
- `examples/finance_feed_agent.py` - Full NEST agent
- Agent registers with registry
- Agent serves Agent Facts and Data Facts
- Agent can receive A2A messages

---

### Phase 2: Registry Integration with Agent Facts URL

**Goal:** Register finance feed agent with registry including `agent_facts_url`

**Tasks:**
1. **Update Registry Registration**
   - Modify `nanda_core/core/adapter.py` or create custom registration
   - Include `agent_facts_url` in registry payload
   - Format: `{"agent_id": "...", "agent_url": "...", "agent_facts_url": "http://{public_url}/agent_facts.json"}`

2. **Agent Facts Endpoint**
   - Serve at: `http://{public_url}/agent_facts.json`
   - Returns Agent Facts JSON (already created)
   - Includes `data_facts_pointer` to Data Facts

3. **Data Facts Endpoint**
   - Serve at: `http://{public_url}/data_facts/public_stock_ticker.json`
   - Returns Data Facts JSON (already created)
   - Points to stock data endpoint

**Deliverables:**
- Registry entry includes `agent_facts_url`
- Agent Facts and Data Facts served via HTTP endpoints
- Integration with existing registry system

---

### Phase 3: Create Consumer Agent as NEST Agent

**Goal:** Make consumer agent a real NEST agent (like concierge agent)

**Tasks:**
1. **Create `examples/data_consumer_agent.py`**
   - Copy structure from `examples/nanda_agent.py`
   - Add logic to:
     - Discover finance feed agent via registry
     - Fetch Agent Facts from `agent_facts_url`
     - Follow `data_facts_pointer` to fetch Data Facts
     - Access public datasets based on Data Facts
     - Use A2A to communicate with finance feed agent if needed

2. **Discovery Logic**
   - Use `RegistryClient` to list/find finance feed agent
   - Get `agent_facts_url` from registry response
   - Fetch Agent Facts from URL
   - Follow Data Facts pointer

3. **A2A Communication**
   - Use `A2AClient` for agent-to-agent messages
   - Can ask finance feed agent questions via A2A
   - Finance feed agent can respond with stock data

4. **Environment Variables**
   - Standard NEST: `AGENT_ID`, `AGENT_NAME`, `AGENT_DOMAIN`, etc.
   - `REGISTRY_URL` - For discovery
   - `TARGET_AGENT_ID` - Optional: specific agent to discover

**Deliverables:**
- `examples/data_consumer_agent.py` - Full NEST agent
- Can discover finance feed agent via registry
- Can fetch Agent Facts and Data Facts
- Can use A2A for communication
- Can access public datasets

---

### Phase 4: Deployment Integration

**Goal:** Enable deployment via standard NEST deployment scripts

**Tasks:**
1. **Update Deployment Scripts (Optional)**
   - `scripts/aws-single-agent-deployment.sh` already supports all needed env vars
   - May need to add logic to start stock server if separate
   - Or integrate stock server into agent itself

2. **Agent Configuration**
   - Finance feed agent: Set `AGENT_ID=finance-feed-agent`, `AGENT_NAME=Finance Feed Agent`, etc.
   - Consumer agent: Set `AGENT_ID=data-consumer-agent`, `AGENT_NAME=Data Consumer Agent`, etc.

3. **Registry Registration**
   - Both agents register with registry automatically
   - Finance feed agent includes `agent_facts_url`
   - Consumer agent can discover finance feed agent

**Deliverables:**
- Both agents deployable via standard NEST scripts
- Registry registration works automatically
- Agents discover each other in production

---

### Phase 5: Integration Testing

**Goal:** Verify end-to-end flow works

**Tasks:**
1. **Local Testing**
   - Start finance feed agent locally
   - Start consumer agent locally
   - Test registry discovery
   - Test Agent Facts fetching
   - Test Data Facts fetching
   - Test A2A communication
   - Test dataset access

2. **Deployment Testing**
   - Deploy finance feed agent to AWS
   - Deploy consumer agent to AWS
   - Test discovery across deployments
   - Test A2A communication
   - Test dataset access

**Deliverables:**
- Working end-to-end flow
- Documentation of test results
- Any bug fixes needed

---

## Architecture After Implementation

```
┌─────────────────────────────────────┐
│         Registry (HTTP API)         │
│  http://registry.chat39.com:6900    │
│                                     │
│  Agents:                            │
│  - finance-feed-agent               │
│    agent_url: http://x.x.x.x:6000/a2a│
│    agent_facts_url: http://x.x.x.x:6000/agent_facts.json│
│                                     │
│  - data-consumer-agent              │
│    agent_url: http://y.y.y.y:6000/a2a│
└──────────────┬──────────────────────┘
               │
               │ Discovery
               │
    ┌──────────┴──────────┐
    │                     │
    ▼                     ▼
┌──────────────┐    ┌──────────────┐
│ Finance Feed │    │   Consumer   │
│   Agent      │    │    Agent     │
│ (NEST Agent) │    │ (NEST Agent) │
├──────────────┤    ├──────────────┤
│ Port: 6000   │    │ Port: 6000   │
│ A2A: /a2a    │◄───│ A2A: /a2a    │ (A2A Communication)
│ Facts:       │    │              │
│ /agent_facts │───►│ Discovers    │
│ .json        │    │              │
│              │    │              │
│ /data_facts/ │───►│ Fetches      │
│ *.json       │    │ Data Facts   │
│              │    │              │
│ Stock Server │───►│ Accesses     │
│ Port: 8000   │    │ Dataset      │
└──────────────┘    └──────────────┘
```

---

## Implementation Details

### Finance Feed Agent Structure

```python
# examples/finance_feed_agent.py

from nanda_core.core.adapter import NANDA
from nanda_core.core.registry_client import RegistryClient
import os

# Environment variables (standard NEST)
AGENT_ID = os.getenv("AGENT_ID", "finance-feed-agent")
AGENT_NAME = os.getenv("AGENT_NAME", "Finance Feed Agent")
# ... other env vars

# Agent logic function
def finance_agent_logic(message: str, conversation_id: str) -> str:
    # Handle A2A messages
    # Serve stock data
    # Return responses
    pass

# Create NANDA agent
nanda = NANDA(
    agent_id=AGENT_ID,
    agent_logic=finance_agent_logic,
    port=PORT,
    registry_url=REGISTRY_URL,
    public_url=PUBLIC_URL
)

# Register with agent_facts_url
registry = RegistryClient(REGISTRY_URL)
registry.register_agent(
    agent_id=AGENT_ID,
    agent_url=f"{PUBLIC_URL}/a2a",
    agent_facts_url=f"{PUBLIC_URL}/agent_facts.json"  # NEW
)

# Start agent
nanda.start()
```

### Consumer Agent Structure

```python
# examples/data_consumer_agent.py

from nanda_core.core.adapter import NANDA
from nanda_core.core.registry_client import RegistryClient
from python_a2a import A2AClient
import requests
import os

# Environment variables (standard NEST)
AGENT_ID = os.getenv("AGENT_ID", "data-consumer-agent")
REGISTRY_URL = os.getenv("REGISTRY_URL")

# Agent logic function
def consumer_agent_logic(message: str, conversation_id: str) -> str:
    # Discover finance feed agent via registry
    registry = RegistryClient(REGISTRY_URL)
    agents = registry.list_agents()
    finance_agent = [a for a in agents if a["agent_id"].startswith("finance-feed")][0]
    
    # Fetch Agent Facts
    agent_facts_url = finance_agent.get("agent_facts_url")
    agent_facts = requests.get(agent_facts_url).json()
    
    # Fetch Data Facts
    data_facts_url = agent_facts["data_facts_pointer"]
    data_facts = requests.get(data_facts_url).json()
    
    # Access dataset if public
    if data_facts["access_type"] == "public":
        dataset = requests.get(data_facts["endpoint"]).json()
        # Use dataset...
    
    # Or use A2A to communicate
    a2a_client = A2AClient(finance_agent["agent_url"])
    response = a2a_client.send_message(message)
    
    return response

# Create NANDA agent
nanda = NANDA(
    agent_id=AGENT_ID,
    agent_logic=consumer_agent_logic,
    port=PORT,
    registry_url=REGISTRY_URL,
    public_url=PUBLIC_URL
)

nanda.start()
```

---

## Key Design Decisions

1. **Agent Facts Serving**
   - **Option A:** Serve on same port as agent (port 6000) as additional HTTP route
   - **Option B:** Serve on separate port (port 9000) as separate HTTP server
   - **Recommendation:** Option A (same port) for simplicity, unless conflicts

2. **Stock Server**
   - **Option A:** Integrate into agent (single process)
   - **Option B:** Keep separate (two processes)
   - **Recommendation:** Option A (integrate) for deployment simplicity

3. **Data Facts Pattern**
   - Keep as-is: JSON files served via HTTP
   - Add to registry: `agent_facts_url` points to Agent Facts
   - Agent Facts contains: `data_facts_pointer` to Data Facts
   - Data Facts contains: `endpoint` to actual dataset

---

## Migration Checklist

### Finance Feed Agent
- [ ] Create `examples/finance_feed_agent.py` based on `nanda_agent.py`
- [ ] Add Agent Facts serving endpoint
- [ ] Add Data Facts serving endpoint
- [ ] Integrate stock server (or keep separate)
- [ ] Add environment variables
- [ ] Update registry registration to include `agent_facts_url`
- [ ] Test locally
- [ ] Test deployment

### Consumer Agent
- [ ] Create `examples/data_consumer_agent.py` based on `nanda_agent.py`
- [ ] Add registry discovery logic
- [ ] Add Agent Facts fetching logic
- [ ] Add Data Facts fetching logic
- [ ] Add A2A communication logic
- [ ] Add dataset access logic
- [ ] Add environment variables
- [ ] Test locally
- [ ] Test deployment

### Integration
- [ ] Test finance feed agent registration
- [ ] Test consumer agent discovery
- [ ] Test Agent Facts fetching
- [ ] Test Data Facts fetching
- [ ] Test A2A communication
- [ ] Test dataset access
- [ ] Test end-to-end flow
- [ ] Update documentation

---

## Timeline Estimate

- **Phase 1:** 2-3 hours (Create finance feed NEST agent)
- **Phase 2:** 1-2 hours (Registry integration)
- **Phase 3:** 2-3 hours (Create consumer NEST agent)
- **Phase 4:** 1 hour (Deployment integration)
- **Phase 5:** 2-3 hours (Testing)
- **Total:** 8-12 hours

---

## Success Criteria

✅ Finance feed agent is a real NEST agent (like menu/concierge)
✅ Consumer agent is a real NEST agent (like menu/concierge)
✅ Both agents register with registry
✅ Agents communicate via A2A protocol
✅ Agent Facts + Data Facts pattern preserved
✅ Agents discover each other via registry
✅ Dataset access works via Data Facts
✅ Can be deployed via standard NEST scripts
✅ End-to-end flow works in production

---

## Next Steps

1. Review this roadmap
2. Start with Phase 1 (Create finance feed NEST agent)
3. Test incrementally after each phase
4. Adjust as needed based on testing

