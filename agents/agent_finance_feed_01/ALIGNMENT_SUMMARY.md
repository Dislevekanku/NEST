# NEST Alignment Summary

## Key Finding: Menu & Concierge Agents Use A2A + Registry

### How Menu & Concierge Agents Discover Each Other

1. **Registry-based Discovery** (HTTP API)
   - Agents register with: `REGISTRY_URL` (e.g., `http://registry.chat39.com:6900`)
   - Discovery via: `GET {REGISTRY_URL}/list`
   - Registry returns: `agent_id`, `agent_url`, `api_url`, `agent_facts_url` (optional)

2. **A2A Protocol for Communication**
   - Agents communicate using **A2A protocol** via `python_a2a` library
   - A2A endpoint: `http://{agent_ip}:{port}/a2a`
   - Syntax: `@agent-name` in messages

3. **Environment Variables for Configuration**
   - `AGENT_ID`, `AGENT_NAME`, `AGENT_DOMAIN`, `AGENT_SPECIALIZATION`
   - `AGENT_DESCRIPTION`, `AGENT_CAPABILITIES` (comma-separated)
   - `REGISTRY_URL`, `PUBLIC_URL`, `PORT`

### Finance Feed Agent Alignment

**Current State:**
- ✅ Uses HTTP endpoints for Agent Facts (similar to `agent_facts_url` in registry)
- ✅ Demonstrates Data Facts pattern (new concept)
- ❌ Not using registry for discovery
- ❌ Not using A2A protocol
- ❌ Not using environment variables

**Aligned Structure:**
- Updated `agent_facts.json` to include NEST-standard fields:
  - `agent_name` (matches `AGENT_NAME`)
  - `agent_domain` (matches `AGENT_DOMAIN`)
  - `agent_specialization` (matches `AGENT_SPECIALIZATION`)
  - `agent_description` (matches `AGENT_DESCRIPTION`)
  - `capabilities` (matches `AGENT_CAPABILITIES`)
  - `registry_url`, `agent_url`, `public_url` (for registry integration)

**Integration Path:**
1. Register finance feed agent with registry
2. Include `agent_facts_url` in registration pointing to Agent Facts endpoint
3. Other agents discover via registry (standard NEST pattern)
4. Agents can fetch Agent Facts from `agent_facts_url` (new pattern)
5. Agent Facts contains `data_facts_pointer` to Data Facts
6. Use A2A for agent-to-agent communication (standard NEST pattern)

---

## Recommendation

The finance feed agent experiment demonstrates a **complementary pattern** to NEST's standard discovery:

- **NEST Standard**: Registry → A2A communication
- **Agent Facts Pattern**: Registry → Agent Facts URL → Data Facts → Dataset access

Both can coexist:
- Registry provides agent discovery and A2A endpoints
- Agent Facts provides dataset discovery and access metadata
- A2A handles agent-to-agent communication

This aligns with NEST's architecture while introducing the Agent Facts + Data Facts pattern for dataset discovery.

