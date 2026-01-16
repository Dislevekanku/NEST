# Data Facts URL Registry Registration Flow

## Overview

The `data_facts_url` is added to the registry registration in three key places:

1. **Finance Feed Agent** (`examples/finance_feed_agent.py`) - Creates the URL
2. **NANDA Adapter** (`nanda_core/core/adapter.py`) - Stores and passes it to registration
3. **Registry Client** (`nanda_core/core/registry_client.py`) - Adds it to registration payload

---

## 1. Finance Feed Agent Creates data_facts_url

**File:** `examples/finance_feed_agent.py`

**Lines 278-293:**

```python
# Build data_facts_url for registry registration
data_facts_url = f"{data_server_public_url}/data_facts/public_stock_ticker.json"

if registry_url:
    safe_print(f"🌐 Registry: {registry_url}")
    safe_print(f"📋 Data Facts URL: {data_facts_url}")

# Create NANDA agent
nanda = NANDA(
    agent_id=agent_id,
    agent_logic=agent_logic,
    port=port,
    registry_url=registry_url,
    public_url=public_url,
    enable_telemetry=False,
    data_facts_url=data_facts_url  # ← Passed to NANDA adapter
)
```

**What happens:** The finance feed agent constructs the `data_facts_url` pointing to its Data Facts endpoint and passes it to the NANDA adapter.

---

## 2. NANDA Adapter Stores data_facts_url

**File:** `nanda_core/core/adapter.py`

### Constructor (Lines 32-59):

```python
def __init__(self, 
             agent_id: str,
             agent_logic: Optional[Callable[[str, str], str]] = None,
             agent: Optional[AgentInterface] = None,
             port: int = 6000,
             registry_url: Optional[str] = None,
             mcp_registry_url: Optional[str] = None,
             public_url: Optional[str] = None,
             host: str = "0.0.0.0",
             enable_telemetry: bool = True,
             smithery_api_key: Optional[str] = None,
             data_facts_url: Optional[str] = None):  # ← Accepts parameter
    # ...
    self.data_facts_url = data_facts_url  # ← Stores it
```

### Registration Method (Lines 125-140):

```python
def _register(self):
    """Register agent with registry"""
    try:
        data = {
            "agent_id": self.agent_id,
            "agent_url": self.public_url
        }
        if self.data_facts_url:  # ← Checks if provided
            data["data_facts_url"] = self.data_facts_url  # ← Adds to registration payload
        response = requests.post(f"{self.registry_url}/register", json=data, timeout=10)
        if response.status_code == 200:
            print(f"✅ Agent '{self.agent_id}' registered successfully")
        else:
            print(f"⚠️ Failed to register agent: HTTP {response.status_code}")
    except Exception as e:
        print(f"⚠️ Registration error: {e}")
```

**What happens:** The NANDA adapter accepts `data_facts_url` as a parameter, stores it, and includes it in the registry registration payload when `_register()` is called.

---

## 3. Registry Client Also Supports It (Optional)

**File:** `nanda_core/core/registry_client.py`

**Lines 32-50:**

```python
def register_agent(self, agent_id: str, agent_url: str, api_url: Optional[str] = None, 
                   agent_facts_url: Optional[str] = None, 
                   data_facts_url: Optional[str] = None) -> bool:  # ← Accepts parameter
    """Register an agent with the registry"""
    try:
        data = {
            "agent_id": agent_id,
            "agent_url": agent_url
        }
        if api_url:
            data["api_url"] = api_url
        if agent_facts_url:
            data["agent_facts_url"] = agent_facts_url
        if data_facts_url:  # ← Adds to payload if provided
            data["data_facts_url"] = data_facts_url

        response = self.session.post(f"{self.registry_url}/register", json=data)
        return response.status_code == 200
    except Exception as e:
        print(f"Error registering agent: {e}")
        return False
```

**What happens:** The RegistryClient also supports `data_facts_url` (for direct use, though NANDA adapter's `_register()` is the standard path).

---

## Complete Flow

```
Finance Feed Agent
    ↓ (constructs data_facts_url)
    ↓ (passes to NANDA constructor)
NANDA Adapter.__init__()
    ↓ (stores in self.data_facts_url)
NANDA Adapter._register()
    ↓ (includes in registration payload)
Registry POST /register
    ↓
Registry stores:
{
  "agent_id": "finance-feed-agent",
  "agent_url": "http://x.x.x.x:6000/a2a",
  "data_facts_url": "http://x.x.x.x:8000/data_facts/public_stock_ticker.json"  ← HERE!
}
```

---

## Key Code Locations

1. **Finance Feed Agent** (`examples/finance_feed_agent.py`)
   - Line 279: Constructs `data_facts_url`
   - Line 293: Passes to `NANDA()` constructor

2. **NANDA Adapter** (`nanda_core/core/adapter.py`)
   - Line 34: Parameter in `__init__`
   - Line 59: Stores as `self.data_facts_url`
   - Line 132-133: Adds to registration payload in `_register()`

3. **Registry Client** (`nanda_core/core/registry_client.py`)
   - Line 32: Parameter in `register_agent()`
   - Line 43-44: Adds to payload if provided

---

## Registration Payload

When the agent registers, it sends:

```json
{
  "agent_id": "finance-feed-agent",
  "agent_url": "http://localhost:6000/a2a",
  "data_facts_url": "http://localhost:8000/data_facts/public_stock_ticker.json"
}
```

The registry stores this, and when other agents call `GET /list`, they receive:

```json
{
  "agent_id": "finance-feed-agent",
  "agent_url": "http://localhost:6000/a2a",
  "data_facts_url": "http://localhost:8000/data_facts/public_stock_ticker.json",
  ...
}
```

This allows consumer agents to discover the Data Facts URL directly from the registry!

