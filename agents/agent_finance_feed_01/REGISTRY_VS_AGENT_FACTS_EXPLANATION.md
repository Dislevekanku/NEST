# Registry vs Agent Facts - Clarification

## The Confusion

You're seeing:
- **Registry** that stores agent metadata (agent_id, agent_name, domain, etc.)
- **`agent_facts_url`** field in the registry that points to a separate JSON file

And asking: **Are they the same thing or different?**

## The Answer

**The Registry IS the source of truth for agent metadata.** The `agent_facts_url` field appears to be an optional/legacy field that's not actually being used in practice.

### What the Registry Stores (Current Practice)

When you call `GET {REGISTRY_URL}/list`, the registry returns:

```json
{
  "agent_id": "menu-agent-abc123",
  "agent_name": "Menu Agent",           // ← Agent metadata
  "domain": "food",                      // ← Agent metadata
  "specialization": "menu assistant",    // ← Agent metadata
  "description": "...",                  // ← Agent metadata
  "capabilities": ["menu", "food"],      // ← Agent metadata
  "agent_url": "http://x.x.x.x:6000/a2a",
  "api_url": "http://x.x.x.x:6000/api",
  "agent_facts_url": "..."  // ← Optional, but NOT USED by menu/concierge agents
}
```

### What `agent_facts_url` Was Supposed To Be

The `agent_facts_url` field was probably intended to point to a separate JSON file with additional agent metadata, but:

1. **It's optional** - Not all agents use it
2. **Menu/concierge agents don't use it** - They rely on registry metadata directly
3. **It duplicates registry data** - The registry already has all the agent metadata

### What We Should Do

**Skip the separate Agent Facts file entirely!** Just add `data_facts_url` directly to the registry registration.

## Simplified Architecture

### Current NEST Pattern (Menu/Concierge)
```
Registry
  ├── agent_id
  ├── agent_name          ← All agent metadata
  ├── domain              ← stored in registry
  ├── capabilities        ← (no separate agent_facts.json)
  ├── agent_url
  └── api_url
```

### What We Should Do (Finance Feed)
```
Registry
  ├── agent_id
  ├── agent_name          ← All agent metadata
  ├── domain              ← stored in registry
  ├── capabilities
  ├── agent_url
  ├── api_url
  └── data_facts_url      ← NEW: Points to Data Facts JSON
      └── Data Facts JSON
          └── Points to dataset endpoint
```

## Conclusion

- ✅ **Registry = Source of truth** for agent metadata (already working)
- ❌ **Separate Agent Facts file = Not needed** (duplicates registry data)
- ✅ **`data_facts_url` in registry = What we need** (points to Data Facts)

**So we should:**
1. Register agent with registry (standard NEST pattern)
2. Include `data_facts_url` in registry registration
3. Consumer gets everything from registry in one call
4. Consumer follows `data_facts_url` → Data Facts → Dataset

**No separate Agent Facts file needed!**

