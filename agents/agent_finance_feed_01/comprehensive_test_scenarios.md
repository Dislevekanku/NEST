# Comprehensive Test Scenarios

## Test Scenarios Overview

This document outlines all test scenarios for validating the complete Agent A → Agent B → Data Facts → Dataset Endpoint flow.

---

## Scenario 1: Complete End-to-End Flow (Agent A → Agent B → Data Facts → Dataset)

**Objective:** Verify that Consumer Agent (Agent A) can discover Finance Feed Agent (Agent B) via registry, read Data Facts, and access the dataset endpoint.

**Steps:**
1. Consumer Agent queries Registry for Finance Feed Agent
2. Registry returns Agent Facts including `data_facts_url`
3. Consumer Agent extracts `data_facts_url` from Agent Facts
4. Consumer Agent fetches Data Facts from `data_facts_url`
5. Consumer Agent validates `access_type` (must be "public")
6. Consumer Agent accesses dataset endpoint from Data Facts
7. Consumer Agent receives dataset successfully

**Expected Results:**
- ✅ Registry returns Finance Feed Agent with `data_facts_url`
- ✅ Data Facts fetched successfully
- ✅ Access type is "public"
- ✅ Dataset endpoint accessible
- ✅ Dataset returned with valid data

---

## Scenario 2: Freshness Validation Flow

**Objective:** Verify that the freshness validation mechanism works correctly using TTL and `last_updated` timestamp.

**Steps:**
1. Fetch Data Facts (records `last_updated` timestamp)
2. Wait for a short period (less than TTL)
3. Verify data is marked as FRESH
4. Optionally: Wait longer than TTL and verify data is marked as STALE

**Expected Results:**
- ✅ Fresh data (age < TTL) is validated as FRESH
- ✅ Stale data (age > TTL) is validated as STALE
- ✅ TTL value matches Data Facts specification (600 seconds)
- ✅ `last_updated` timestamp is valid ISO 8601 format

**Test Cases:**
- **Fresh Data**: Data updated within TTL period → Should be FRESH
- **Stale Data**: Data older than TTL → Should be STALE
- **Edge Case**: Data exactly at TTL boundary → Should be FRESH (age <= TTL)

---

## Scenario 3: Checksum Verification Flow

**Objective:** Verify that checksum validation ensures data integrity between Data Facts and actual dataset.

**Steps:**
1. Fetch Data Facts (contains `checksum_sha256` in evidence)
2. Fetch dataset from endpoint
3. Compute SHA256 checksum of dataset (excluding timestamp)
4. Compare computed checksum with expected checksum from Data Facts
5. Verify checksums match

**Expected Results:**
- ✅ Checksum computation matches Data Facts format
- ✅ Checksums match when data is unchanged
- ✅ Checksum mismatch detected if data has changed
- ✅ Timestamp excluded from checksum computation

**Test Cases:**
- **Valid Checksum**: Dataset matches Data Facts checksum → Verification passes
- **Invalid Checksum**: Dataset changed after Data Facts update → Verification fails
- **Format Validation**: Checksum is valid SHA256 hex string

---

## Scenario 4: A2A Communication Flow (Agent A → Agent B)

**Objective:** Verify that Consumer Agent can communicate with Finance Feed Agent via A2A protocol.

**Steps:**
1. Consumer Agent receives query
2. Consumer Agent discovers Finance Feed Agent via registry (or fallback URL)
3. Consumer Agent sends A2A message to Finance Feed Agent
4. Finance Feed Agent processes query and responds
5. Consumer Agent receives and parses A2A response

**Expected Results:**
- ✅ Finance Feed Agent discovered successfully
- ✅ A2A message sent successfully
- ✅ Finance Feed Agent responds correctly
- ✅ Response contains expected stock price information

---

## Scenario 5: Combined Flow (A2A + Data Facts Fallback)

**Objective:** Verify that Consumer Agent can use A2A for queries and fallback to Data Facts for dataset access.

**Steps:**
1. Consumer Agent receives query requesting stock prices
2. Consumer Agent attempts A2A communication with Finance Feed Agent
3. If A2A fails, Consumer Agent falls back to Data Facts discovery
4. Consumer Agent accesses dataset via Data Facts endpoint

**Expected Results:**
- ✅ A2A communication attempted first
- ✅ Fallback to Data Facts if A2A fails
- ✅ Dataset accessed successfully via fallback method

---

## Scenario 6: Registry Discovery Flow

**Objective:** Verify that Consumer Agent can discover Finance Feed Agent via registry and extract `data_facts_url`.

**Steps:**
1. Consumer Agent queries registry (`/list` endpoint)
2. Registry returns list of agents
3. Consumer Agent filters for "finance-feed-agent"
4. Consumer Agent extracts `data_facts_url` from agent metadata
5. Consumer Agent validates `data_facts_url` is present and valid

**Expected Results:**
- ✅ Registry responds with agent list
- ✅ Finance Feed Agent found in registry
- ✅ `data_facts_url` present in agent metadata
- ✅ `data_facts_url` is a valid HTTP(S) URL

---

## Scenario 7: Error Handling

**Objective:** Verify proper error handling for various failure scenarios.

**Test Cases:**
1. **Registry Unavailable**: Consumer Agent cannot reach registry → Fallback URL used
2. **Agent Not Found**: Finance Feed Agent not in registry → Error handled gracefully
3. **Data Facts Unavailable**: Data Facts endpoint returns 404 → Error reported
4. **Dataset Endpoint Unavailable**: Dataset endpoint returns 404 → Error reported
5. **Invalid Access Type**: Access type is "private" → Access denied
6. **Network Timeout**: Request timeout → Error handled gracefully

**Expected Results:**
- ✅ All errors handled gracefully
- ✅ Informative error messages returned
- ✅ No unhandled exceptions
- ✅ System remains stable after errors

---

## Scenario 8: Data Facts Schema Validation

**Objective:** Verify that Data Facts conform to expected schema.

**Steps:**
1. Fetch Data Facts JSON
2. Validate required fields: `dataset_id`, `dataset_description`, `access_type`, `endpoint`, `evidence`, `ttl_seconds`
3. Validate `evidence` structure: `last_updated`, `checksum_sha256`, `source`
4. Validate data types and formats

**Expected Results:**
- ✅ All required fields present
- ✅ Data types match schema
- ✅ `access_type` is valid ("public" or "private")
- ✅ `endpoint` is valid URL
- ✅ `ttl_seconds` is positive integer
- ✅ `last_updated` is valid ISO 8601 timestamp
- ✅ `checksum_sha256` is valid hex string (64 characters)

---

## Test Execution Order

Recommended execution order:
1. **Scenario 6**: Registry Discovery Flow (prerequisite)
2. **Scenario 1**: Complete End-to-End Flow (core functionality)
3. **Scenario 2**: Freshness Validation Flow
4. **Scenario 3**: Checksum Verification Flow
5. **Scenario 8**: Data Facts Schema Validation
6. **Scenario 4**: A2A Communication Flow
7. **Scenario 5**: Combined Flow (A2A + Data Facts Fallback)
8. **Scenario 7**: Error Handling

---

## Success Criteria

All scenarios pass if:
- ✅ All steps execute without errors
- ✅ All expected results match actual results
- ✅ Logs capture detailed information at each step
- ✅ Timing information recorded for performance analysis
- ✅ Error handling works correctly
- ✅ No memory leaks or resource issues
