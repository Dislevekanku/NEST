# NEST Agent Alignment Analysis

## Current State: Menu & Concierge Agents

### Discovery Mechanism
- **Registry-based discovery** (HTTP API)
- Agents register with registry at: `REGISTRY_URL` (e.g., `http://registry.chat39.com:6900`)
- Registry endpoints:
  - `GET /list` - List all agents
  - `GET /lookup/{agent_id}` - Look up specific agent
  - `POST /register` - Register agent

### Communication Protocol
- **A2A (Agent-to-Agent) protocol** via `python_a2a` library
- Agents communicate using `@agent-name` syntax
- A2A endpoints: `http://{agent_ip}:{port}/a2a`

### Agent Configuration
- **Environment variables** (not JSON files):
  - `AGENT_ID` - Unique identifier
  - `AGENT_NAME` - Display name
  - `AGENT_DOMAIN` - Domain/field of expertise
  - `AGENT_SPECIALIZATION` - Role description
  - `AGENT_DESCRIPTION` - Detailed description
  - `AGENT_CAPABILITIES` - Comma-separated capabilities
  - `REGISTRY_URL` - Registry endpoint
  - `PUBLIC_URL` - Public agent URL
  - `PORT` - Agent port (default: 6000)

### Registry Registration Data
```python
{
    "agent_id": "menu-agent-abc123",
    "agent_url": "http://54.237.202.184:6000/a2a",
    "api_url": "http://54.237.202.184:6000/api",  # Optional
    "agent_facts_url": "http://54.237.202.184:6000/agent_facts.json"  # Optional
}
```

### Agent Discovery Flow
1. Agent A wants to find Agent B
2. Agent A calls: `GET {REGISTRY_URL}/list`
3. Registry returns list of agents with metadata
4. Agent A filters by `agent_id` or searches by name
5. Agent A gets `agent_url` from registry response
6. Agent A uses `A2AClient` to send A2A message to `agent_url`

---

## Finance Feed Agent Experiment

### Current Implementation
- **HTTP-based Agent Facts** (not registry-based)
- Serves `agent_facts.json` at: `http://localhost:9000/agent_facts.json`
- Uses `data_facts_pointer` URL to point to Data Facts
- Consumer fetches Agent Facts and Data Facts over HTTP

### Differences from NEST Pattern
1. ❌ Not using registry for discovery
2. ❌ Not using A2A protocol for communication
3. ❌ Not using environment variables for configuration
4. ✅ Using HTTP endpoints (similar to `agent_facts_url` in registry)
5. ✅ Demonstrates Data Facts pattern (new concept)

---

## Alignment Options

### Option 1: Full NEST Integration (Recommended)
Make finance feed agent a real NEST agent:

1. **Use NEST agent structure** (`examples/nanda_agent.py`)
2. **Register with registry** using `RegistryClient`
3. **Expose agent_facts_url** in registry registration
4. **Use A2A protocol** for agent-to-agent communication
5. **Keep Data Facts pattern** as additional metadata

**Changes needed:**
- Create `examples/finance_feed_agent.py` based on `nanda_agent.py`
- Add environment variables for configuration
- Register with registry and include `agent_facts_url`
- Serve Agent Facts and Data Facts via HTTP endpoints
- Use A2A for communication (if needed)

### Option 2: Hybrid Approach
Keep experiment as-is but document it as:
- **Agent Facts + Data Facts pattern** (new concept)
- Can be integrated into NEST via `agent_facts_url` in registry
- Demonstrates dataset discovery and access pattern
- Complementary to A2A communication

### Option 3: Registry + Agent Facts
Align with NEST while keeping Agent Facts pattern:

1. **Register with registry** (like other NEST agents)
2. **Include `agent_facts_url`** in registration pointing to Agent Facts endpoint
3. **Use registry for discovery** (standard NEST pattern)
4. **Agent Facts contains Data Facts pointer** (new pattern)
5. **A2A for communication** (standard NEST pattern)

---

## Recommended Alignment

**Use Option 3: Registry + Agent Facts**

This aligns with NEST's architecture while preserving the Agent Facts + Data Facts pattern:

1. Finance feed agent registers with registry
2. Registry entry includes: `agent_facts_url: "http://{agent_ip}:9000/agent_facts.json"`
3. Other agents discover via registry (standard NEST pattern)
4. Agents can fetch Agent Facts from `agent_facts_url` (new pattern)
5. Agent Facts contains `data_facts_pointer` to Data Facts
6. Data Facts describes the public dataset
7. Agents use A2A for communication (standard NEST pattern)

**Benefits:**
- ✅ Aligns with NEST's registry-based discovery
- ✅ Preserves Agent Facts + Data Facts pattern
- ✅ Uses A2A for communication (standard)
- ✅ Can be deployed like other NEST agents
- ✅ Demonstrates dataset discovery pattern

---

## Implementation Plan

1. Create `examples/finance_feed_agent.py` based on `nanda_agent.py`
2. Add environment variables for finance feed configuration
3. Register with registry including `agent_facts_url`
4. Serve Agent Facts at `/agent_facts.json` endpoint
5. Serve Data Facts at `/data_facts/{dataset_id}.json` endpoint
6. Keep stock server as separate service
7. Update consumer demo to use registry for discovery

