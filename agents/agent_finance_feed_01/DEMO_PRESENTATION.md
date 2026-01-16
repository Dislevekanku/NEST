# Data Facts Demo - Presentation Guide

**Duration:** 10-15 minutes  
**Audience:** Technical stakeholders, developers, product managers  
**Format:** Live demo with React UI + command-line examples

---

## 🎯 Demo Objectives

1. Show how Data Facts enables dataset discovery
2. Demonstrate A2A communication between agents
3. Validate freshness and checksum verification
4. Highlight the integration with existing NEST architecture

---

## 📋 Demo Script

### Part 1: Introduction (2 minutes)

**What We Built:**
- Two NEST agents: Finance Feed Agent & Consumer Agent
- Data Facts integration for dataset discovery
- A2A communication for agent collaboration
- Both deployed to AWS EC2

**Key Concept:**
> "Data Facts is metadata about a dataset, stored separately from Agent Facts (which is metadata about an agent). The `data_facts_url` pointer lives in the registry, making datasets discoverable."

---

### Part 2: Architecture Overview (1 minute)

**Show:** Architecture Diagram tab in React UI

**Explain:**
- Registry stores agent metadata (Agent Facts)
- Registry includes `data_facts_url` for agents with datasets
- Consumer Agent discovers agents and their datasets
- Two access methods: A2A (conversational) and Data Facts (direct)

---

### Part 3: Live Demo - React UI (5 minutes)

#### 3.1 Query Interface

**Action:**
1. Go to "Query Interface" tab
2. Type: "what are the current stock prices?"
3. Click "Send"

**What to Show:**
- Real-time step-by-step flow visualization
- Step 1: Consumer Agent receives query
- Step 2: Discovers Finance Feed Agent via Registry
- Step 3: Sends A2A message
- Step 4: Finance Feed Agent processes
- Step 5: Response with stock prices

**Highlight:**
- See the complete communication path
- All steps happen automatically
- A2A enables conversational interaction

#### 3.2 Stock Prices Display

**Action:**
1. Go to "Stock Prices" tab

**What to Show:**
- Live stock prices (TSLA, AAPL, ETH-USD)
- Data Facts metadata panel
- Freshness indicator (🟢 Fresh / 🟡 Stale / 🔴 Expired)
- Click "Open Data Facts URL" to show raw JSON

**Highlight:**
- Data Facts JSON structure
- Evidence (checksum, last_updated)
- TTL validation
- Real-time updates

#### 3.3 Registry Explorer

**Action:**
1. Go to "Registry Explorer" tab
2. Click "Refresh Agent List"
3. Click on Finance Feed Agent card

**What to Show:**
- Agent list from registry
- `data_facts_url` visible in agent metadata
- Click to expand and see full metadata

**Highlight:**
- Registry serves as Agent Facts
- `data_facts_url` stored alongside `agent_url`
- Easy discovery via registry query

---

### Part 4: Technical Deep Dive (3 minutes)

#### 4.1 Where Data Facts Was Added

**Show Code:**

**File:** `nanda_core/core/adapter.py` (Line 132-133)

```python
if self.data_facts_url:
    data["data_facts_url"] = self.data_facts_url  # ← Added to registry
```

**File:** `nanda_core/core/registry_client.py` (Line 36-37)

```python
if data_facts_url:
    data["data_facts_url"] = data_facts_url  # ← Registration parameter
```

**Explain:**
- Minimal changes to core NEST framework
- `data_facts_url` is optional parameter
- Backward compatible (existing agents work without it)

#### 4.2 Data Facts JSON Structure

**Show Example:**

```json
{
  "dataset_id": "public_stock_ticker",
  "dataset_description": "Live stock price feed...",
  "access_type": "public",
  "endpoint": "http://54.172.251.235:8000/stock_data",
  "evidence": {
    "last_updated": "2026-01-16T16:51:00Z",
    "checksum_sha256": "d7fc37cf...",
    "source": "yahoo_finance_api"
  },
  "ttl_seconds": 600
}
```

**Explain:**
- Standardized schema
- Evidence provides data integrity proof
- TTL enables freshness validation
- Access type controls permissions

#### 4.3 Complete Flow

**Show Flow Diagram:**

```
Consumer Agent → Registry → data_facts_url → Data Facts JSON → Dataset Endpoint → Stock Prices
```

**Explain:**
1. Consumer queries registry
2. Registry returns `data_facts_url` in Agent Facts
3. Consumer fetches Data Facts JSON
4. Consumer validates access type and freshness
5. Consumer accesses dataset from endpoint

---

### Part 5: Comparison View (2 minutes)

**Action:**
1. Go to "Comparison" tab
2. Click "Test A2A" and "Test Data Facts" side-by-side

**What to Show:**
- A2A response time vs Data Facts response time
- Different response formats
- Use case comparison

**Explain:**
- **A2A**: Best for queries, conversations, agent collaboration
- **Data Facts**: Best for direct dataset access, metadata discovery, bulk data
- **Both work together**: Consumer can choose based on use case

---

### Part 6: Test Suite (1 minute)

**Action:**
1. Go to "Tests" tab
2. Click "Run All Tests"

**What to Show:**
- All 6 test scenarios pass
- Test results with timing
- Expandable test details

**Highlight:**
- Comprehensive validation
- Freshness checks
- Checksum verification
- End-to-end flow validation

---

### Part 7: Future Steps (1 minute)

**Discuss:**
1. **Private Datasets** - Authentication support
2. **Multiple Datasets** - Agents expose multiple Data Facts
3. **Schema Validation** - Automated validation
4. **Data Catalog Integration** - Enterprise features

---

## 🎨 Visual Aids

### Slide 1: Architecture Diagram
- Registry in center
- Finance Feed Agent on right
- Consumer Agent on left
- Arrows showing flows

### Slide 2: Data Facts Location
```
Registry (Agent Facts)
├── agent_id
├── agent_url
└── data_facts_url  ← HERE!
```

### Slide 3: Data Facts JSON
- Highlighted fields
- Color-coded sections
- Annotations explaining purpose

### Slide 4: Flow Diagram
- Step-by-step numbered flow
- Color-coded arrows
- Status indicators

---

## 🎬 Demo Checklist

**Before Demo:**
- [ ] React UI running (`npm start`)
- [ ] Finance Feed Agent running (check http://54.172.251.235:6000/a2a)
- [ ] Consumer Agent running (check http://44.223.52.126:6001/a2a)
- [ ] Registry accessible (optional, fallback works)
- [ ] Browser open to http://localhost:3000

**During Demo:**
- [ ] Show Query Interface with flow
- [ ] Show Stock Prices with Data Facts
- [ ] Show Registry Explorer with data_facts_url
- [ ] Show Architecture Diagram
- [ ] Run comparison view
- [ ] Run test suite
- [ ] Discuss code locations
- [ ] Show JSON structure

**After Demo:**
- [ ] Q&A session
- [ ] Show future roadmap
- [ ] Provide documentation links

---

## 💡 Talking Points

### Key Messages

1. **"Agent Facts = Registry"**
   - The registry response IS the Agent Facts
   - No separate Agent Facts file needed
   - `data_facts_url` stored directly in registry

2. **"Data Facts ≠ Agent Facts"**
   - Agent Facts: About the agent (stored in registry)
   - Data Facts: About a dataset (served via HTTP endpoint)
   - They work together but serve different purposes

3. **"Backward Compatible"**
   - Existing agents work without changes
   - `data_facts_url` is optional
   - Gradual adoption possible

4. **"Two Ways to Access Data"**
   - A2A: Conversational, real-time queries
   - Data Facts: Direct, structured access
   - Choose based on use case

5. **"Production Ready"**
   - Deployed to AWS EC2
   - Tested end-to-end
   - All scenarios validated

---

## 📊 Demo Metrics to Highlight

- **Response Times:**
  - A2A: ~120-200ms
  - Data Facts: ~45-80ms
  - Dataset access: ~100-150ms

- **Test Results:**
  - 6/6 test scenarios pass
  - All validation checks pass
  - Zero errors in production

- **Deployment:**
  - 2 EC2 instances
  - 3 open ports (6000, 6001, 8000)
  - Automatic startup on instance boot

---

## 🎯 Expected Questions & Answers

**Q: Why store data_facts_url in registry instead of a separate service?**

**A:** Simplicity. Registry already handles agent discovery, so adding dataset discovery there reduces complexity. One query gets both agent info and dataset pointers.

**Q: What if an agent has multiple datasets?**

**A:** Future enhancement. For now, one `data_facts_url` per agent. We plan to support multiple URLs or a catalog endpoint.

**Q: How do you handle authentication for private datasets?**

**A:** Not yet implemented. Planned for Phase 1. Will support API keys and OAuth tokens.

**Q: What about data versioning?**

**A:** Future feature. Current Data Facts represent "current" version. Versioning will be added in Phase 2.

**Q: How do you ensure Data Facts JSON is valid?**

**A:** Client-side validation against expected schema. Future: Server-side validation on registration.

---

## 📝 Demo Handout (1-pager)

```
┌─────────────────────────────────────────────────────────┐
│  Data Facts Integration - Quick Reference               │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Where: Registry stores data_facts_url in Agent Facts   │
│  What: JSON metadata describing a public dataset        │
│  How: Consumer → Registry → Data Facts → Dataset        │
│                                                          │
│  Endpoints:                                              │
│  • Finance Agent A2A: 54.172.251.235:6000/a2a          │
│  • Data Facts: 54.172.251.235:8000/data_facts/...      │
│  • Consumer Agent: 44.223.52.126:6001/a2a              │
│                                                          │
│  React UI: http://localhost:3000                        │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## ✅ Success Criteria

**Demo is successful if:**

1. ✅ All UI components work smoothly
2. ✅ Data Facts JSON displays correctly
3. ✅ Stock prices update in real-time
4. ✅ A2A communication works end-to-end
5. ✅ All tests pass
6. ✅ Audience understands the flow
7. ✅ Code locations are clear
8. ✅ Future steps are understood

---

**Ready to demo!** 🎉
