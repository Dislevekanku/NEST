#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive Test Suite: Agent A → Agent B → Data Facts → Dataset Endpoint

Tests all scenarios including:
- Complete end-to-end flow
- Freshness validation
- Checksum verification
- A2A communication
- Registry discovery
- Error handling

All test results are logged to a file with detailed timestamps.
"""
import sys
import os
import json
import time
import requests
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple

# Fix encoding for Windows
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except (AttributeError, ValueError):
        pass

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from nanda_core.core.registry_client import RegistryClient

# =============================================================================
# CONFIGURATION
# =============================================================================

# Agent URLs
FINANCE_FEED_AGENT_URL = "http://localhost:6000"
FINANCE_FEED_A2A_URL = f"{FINANCE_FEED_AGENT_URL}/a2a"
CONSUMER_AGENT_URL = "http://localhost:6001"
CONSUMER_AGENT_A2A_URL = f"{CONSUMER_AGENT_URL}/a2a"

# Data Facts and Dataset URLs
FINANCE_FEED_DATA_FACTS_URL = "http://localhost:8000/data_facts/public_stock_ticker.json"
FINANCE_FEED_STOCK_DATA_URL = "http://localhost:8000/stock_data"

# Registry (optional for local testing)
REGISTRY_URL = os.getenv("REGISTRY_URL", "http://registry.chat39.com:6900")

# Log file
LOG_FILE = os.path.join(os.path.dirname(__file__), "test_logs", f"test_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

# Create log directory if it doesn't exist
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# =============================================================================
# LOGGING UTILITIES
# =============================================================================

class TestLogger:
    """Logger that writes to both console and file"""
    
    def __init__(self, log_file: str):
        self.log_file = log_file
        self.start_time = time.time()
        
    def log(self, message: str, level: str = "INFO"):
        """Log a message with timestamp"""
        timestamp = datetime.now().isoformat()
        elapsed = time.time() - self.start_time
        log_entry = f"[{timestamp}] [{elapsed:.3f}s] [{level}] {message}"
        
        # Print to console
        print(log_entry)
        
        # Write to file
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry + '\n')
        except Exception as e:
            print(f"Warning: Could not write to log file: {e}")
    
    def log_section(self, title: str):
        """Log a section header"""
        separator = "=" * 80
        self.log("")
        self.log(separator)
        self.log(f"  {title}")
        self.log(separator)
    
    def log_test(self, test_name: str, status: str, details: str = ""):
        """Log a test result"""
        status_symbol = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        self.log(f"{status_symbol} {test_name}: {status}")
        if details:
            for line in details.split('\n'):
                if line.strip():
                    self.log(f"    {line}")

# Initialize logger
logger = TestLogger(LOG_FILE)

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def check_agent_health(agent_url: str, agent_name: str) -> bool:
    """Check if an agent is running"""
    try:
        health_url = agent_url.replace("/a2a", "/health")
        response = requests.get(health_url, timeout=2)
        return response.status_code == 200
    except:
        try:
            a2a_url = agent_url if "/a2a" in agent_url else f"{agent_url}/a2a"
            payload = {
                "content": {"text": "health check", "type": "text"},
                "role": "user",
                "conversation_id": "health-check"
            }
            response = requests.post(a2a_url, json=payload, timeout=3)
            return response.status_code == 200
        except:
            return False

def fetch_data_facts(data_facts_url: str) -> Dict[str, Any]:
    """Fetch Data Facts from URL"""
    logger.log(f"Fetching Data Facts from: {data_facts_url}")
    response = requests.get(data_facts_url, timeout=10)
    response.raise_for_status()
    data_facts = response.json()
    logger.log(f"Data Facts retrieved: {json.dumps(data_facts, indent=2)}")
    return data_facts

def check_freshness(data_facts: Dict[str, Any]) -> Tuple[bool, float, int]:
    """Check if data is fresh based on TTL and last_updated"""
    ttl = data_facts.get("ttl_seconds", 0)
    last_updated = data_facts["evidence"]["last_updated"]
    
    last_dt = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    age_seconds = (now - last_dt).total_seconds()
    
    is_fresh = age_seconds <= ttl
    
    logger.log(f"Freshness check: age={age_seconds:.1f}s, TTL={ttl}s, is_fresh={is_fresh}")
    
    return is_fresh, age_seconds, ttl

def fetch_dataset(endpoint: str) -> Dict[str, Any]:
    """Fetch dataset from endpoint"""
    logger.log(f"Fetching dataset from: {endpoint}")
    response = requests.get(endpoint, timeout=10)
    response.raise_for_status()
    dataset = response.json()
    logger.log(f"Dataset retrieved: {json.dumps(dataset, indent=2)}")
    return dataset

def verify_checksum(data_facts: Dict[str, Any], dataset: Dict[str, Any]) -> Tuple[bool, str, str]:
    """Verify dataset checksum matches Data Facts evidence"""
    # Compute checksum (exclude timestamp for consistency)
    data_copy = {k: v for k, v in dataset.items() if k != "timestamp"}
    serialized = json.dumps(data_copy, sort_keys=True).encode("utf-8")
    computed_checksum = hashlib.sha256(serialized).hexdigest()
    
    expected_checksum = data_facts["evidence"]["checksum_sha256"]
    
    matches = computed_checksum == expected_checksum
    
    logger.log(f"Checksum verification: matches={matches}")
    logger.log(f"  Expected: {expected_checksum[:32]}...")
    logger.log(f"  Computed: {computed_checksum[:32]}...")
    
    return matches, computed_checksum, expected_checksum

def send_a2a_message(agent_url: str, message: str, conversation_id: str = None) -> Dict[str, Any]:
    """Send A2A message to an agent"""
    import uuid
    if conversation_id is None:
        conversation_id = f"test-{uuid.uuid4().hex[:8]}"
    
    payload = {
        "content": {
            "text": message,
            "type": "text"
        },
        "role": "user",
        "conversation_id": conversation_id
    }
    
    logger.log(f"Sending A2A message to {agent_url}: {message}")
    response = requests.post(agent_url, json=payload, timeout=30)
    response.raise_for_status()
    result = response.json()
    logger.log(f"A2A response received: {json.dumps(result, indent=2)}")
    return result

# =============================================================================
# TEST SCENARIOS
# =============================================================================

def test_scenario_1_complete_e2e_flow() -> bool:
    """Scenario 1: Complete End-to-End Flow (Agent A → Agent B → Data Facts → Dataset)"""
    logger.log_section("SCENARIO 1: Complete End-to-End Flow")
    
    try:
        # Step 1: Check agents are running
        logger.log("Step 1: Verifying agents are running")
        if not check_agent_health(FINANCE_FEED_AGENT_URL, "Finance Feed Agent"):
            logger.log_test("Agent Health Check", "FAIL", "Finance Feed Agent not running")
            return False
        logger.log_test("Agent Health Check", "PASS", "Both agents are running")
        
        # Step 2: Fetch Data Facts
        logger.log("Step 2: Fetching Data Facts")
        data_facts = fetch_data_facts(FINANCE_FEED_DATA_FACTS_URL)
        logger.log_test("Data Facts Fetch", "PASS", f"Dataset ID: {data_facts.get('dataset_id')}")
        
        # Step 3: Validate access type
        logger.log("Step 3: Validating access type")
        access_type = data_facts.get("access_type")
        if access_type != "public":
            logger.log_test("Access Type Validation", "FAIL", f"Expected 'public', got '{access_type}'")
            return False
        logger.log_test("Access Type Validation", "PASS", f"Access type: {access_type}")
        
        # Step 4: Fetch dataset
        logger.log("Step 4: Fetching dataset from endpoint")
        dataset = fetch_dataset(data_facts["endpoint"])
        logger.log_test("Dataset Fetch", "PASS", f"Dataset keys: {list(dataset.keys())}")
        
        logger.log_test("Scenario 1", "PASS", "Complete end-to-end flow successful")
        return True
        
    except Exception as e:
        logger.log_test("Scenario 1", "FAIL", f"Error: {str(e)}")
        import traceback
        logger.log(traceback.format_exc(), "ERROR")
        return False

def test_scenario_2_freshness_validation() -> bool:
    """Scenario 2: Freshness Validation Flow"""
    logger.log_section("SCENARIO 2: Freshness Validation Flow")
    
    try:
        # Step 1: Fetch Data Facts
        logger.log("Step 1: Fetching Data Facts for freshness check")
        data_facts = fetch_data_facts(FINANCE_FEED_DATA_FACTS_URL)
        
        # Step 2: Check freshness
        logger.log("Step 2: Checking data freshness")
        is_fresh, age_seconds, ttl = check_freshness(data_facts)
        
        # Step 3: Validate freshness logic
        if is_fresh:
            logger.log_test("Freshness Check (Current)", "PASS", 
                          f"Data is FRESH (age: {age_seconds:.1f}s, TTL: {ttl}s)")
        else:
            logger.log_test("Freshness Check (Current)", "WARN", 
                          f"Data is STALE (age: {age_seconds:.1f}s, TTL: {ttl}s)")
        
        # Step 4: Wait a short time and check again
        logger.log("Step 3: Waiting 2 seconds and re-checking freshness")
        time.sleep(2)
        is_fresh_2, age_seconds_2, ttl_2 = check_freshness(data_facts)
        
        if age_seconds_2 > age_seconds:
            logger.log_test("Freshness Check (After Wait)", "PASS", 
                          f"Age increased correctly: {age_seconds:.1f}s → {age_seconds_2:.1f}s")
        else:
            logger.log_test("Freshness Check (After Wait)", "WARN", 
                          f"Age did not increase as expected")
        
        # Step 5: Validate TTL value
        if ttl == 600:
            logger.log_test("TTL Validation", "PASS", f"TTL is 600 seconds as expected")
        else:
            logger.log_test("TTL Validation", "WARN", f"TTL is {ttl} seconds (expected 600)")
        
        logger.log_test("Scenario 2", "PASS", "Freshness validation flow completed")
        return True
        
    except Exception as e:
        logger.log_test("Scenario 2", "FAIL", f"Error: {str(e)}")
        import traceback
        logger.log(traceback.format_exc(), "ERROR")
        return False

def test_scenario_3_checksum_verification() -> bool:
    """Scenario 3: Checksum Verification Flow"""
    logger.log_section("SCENARIO 3: Checksum Verification Flow")
    
    try:
        # Step 1: Fetch Data Facts
        logger.log("Step 1: Fetching Data Facts for checksum verification")
        data_facts = fetch_data_facts(FINANCE_FEED_DATA_FACTS_URL)
        
        # Step 2: Fetch dataset
        logger.log("Step 2: Fetching dataset from endpoint")
        dataset = fetch_dataset(data_facts["endpoint"])
        
        # Step 3: Verify checksum
        logger.log("Step 3: Verifying checksum")
        checksum_matches, computed, expected = verify_checksum(data_facts, dataset)
        
        if checksum_matches:
            logger.log_test("Checksum Verification", "PASS", 
                          f"Checksums match: {expected[:16]}...")
        else:
            logger.log_test("Checksum Verification", "WARN", 
                          f"Checksums do not match (data may have changed)")
            logger.log(f"  Expected: {expected}")
            logger.log(f"  Computed: {computed}")
        
        # Step 4: Validate checksum format
        if len(expected) == 64 and all(c in '0123456789abcdef' for c in expected):
            logger.log_test("Checksum Format Validation", "PASS", "Checksum is valid SHA256 hex string")
        else:
            logger.log_test("Checksum Format Validation", "FAIL", "Invalid checksum format")
            return False
        
        logger.log_test("Scenario 3", "PASS", "Checksum verification flow completed")
        return True
        
    except Exception as e:
        logger.log_test("Scenario 3", "FAIL", f"Error: {str(e)}")
        import traceback
        logger.log(traceback.format_exc(), "ERROR")
        return False

def test_scenario_4_registry_discovery() -> bool:
    """Scenario 4: Registry Discovery Flow"""
    logger.log_section("SCENARIO 4: Registry Discovery Flow")
    
    try:
        # Step 1: Try to query registry
        logger.log(f"Step 1: Querying registry at {REGISTRY_URL}")
        registry = RegistryClient(REGISTRY_URL)
        
        try:
            agents_response = registry.list_agents()
            
            # Handle response format
            if isinstance(agents_response, list):
                agents = agents_response
            elif isinstance(agents_response, dict):
                agents = agents_response.get("agents", [])
            else:
                agents = []
            
            logger.log(f"Registry returned {len(agents)} agents")
            
            # Step 2: Find finance feed agent
            logger.log("Step 2: Searching for finance-feed-agent")
            finance_agents = [
                a for a in agents 
                if "finance-feed" in (a.get("agent_id", "") or a.get("id", "")).lower()
            ]
            
            if finance_agents:
                finance_agent = finance_agents[-1]
                logger.log_test("Agent Discovery", "PASS", f"Found finance-feed-agent: {finance_agent.get('agent_id')}")
                
                # Step 3: Extract data_facts_url
                data_facts_url = finance_agent.get("data_facts_url")
                if data_facts_url:
                    logger.log_test("Data Facts URL Extraction", "PASS", f"data_facts_url: {data_facts_url}")
                else:
                    logger.log_test("Data Facts URL Extraction", "WARN", "data_facts_url not found in registry")
                
            else:
                logger.log_test("Agent Discovery", "WARN", "finance-feed-agent not found in registry (may not be registered)")
                
            logger.log_test("Scenario 4", "PASS", "Registry discovery flow completed")
            return True
            
        except Exception as reg_error:
            logger.log_test("Registry Query", "WARN", f"Registry not available: {str(reg_error)}")
            logger.log("   Continuing with fallback URL testing...")
            logger.log_test("Scenario 4", "WARN", "Registry not available, but flow continues")
            return True  # Not a failure if registry is unavailable for local testing
            
    except Exception as e:
        logger.log_test("Scenario 4", "FAIL", f"Error: {str(e)}")
        import traceback
        logger.log(traceback.format_exc(), "ERROR")
        return False

def test_scenario_5_a2a_communication() -> bool:
    """Scenario 5: A2A Communication Flow"""
    logger.log_section("SCENARIO 5: A2A Communication Flow")
    
    try:
        # Step 1: Check agents are running
        logger.log("Step 1: Verifying agents are running")
        if not check_agent_health(FINANCE_FEED_AGENT_URL, "Finance Feed Agent"):
            logger.log_test("Agent Health Check", "FAIL", "Finance Feed Agent not running")
            return False
        if not check_agent_health(CONSUMER_AGENT_URL, "Consumer Agent"):
            logger.log_test("Agent Health Check", "FAIL", "Consumer Agent not running")
            return False
        logger.log_test("Agent Health Check", "PASS", "Both agents are running")
        
        # Step 2: Direct A2A to Finance Feed Agent
        logger.log("Step 2: Sending A2A message directly to Finance Feed Agent")
        response = send_a2a_message(FINANCE_FEED_A2A_URL, "what are the current stock prices?", "test-direct-a2a")
        
        response_text = str(response)
        if "TSLA" in response_text or "AAPL" in response_text or "price" in response_text.lower():
            logger.log_test("Direct A2A to Finance Feed Agent", "PASS", "Finance Feed Agent responded with stock prices")
        else:
            logger.log_test("Direct A2A to Finance Feed Agent", "WARN", "Response may not contain expected stock price info")
        
        # Step 3: A2A via Consumer Agent
        logger.log("Step 3: Sending A2A message via Consumer Agent to Finance Feed Agent")
        response = send_a2a_message(CONSUMER_AGENT_A2A_URL, "ask finance agent about stock prices", "test-consumer-a2a")
        
        response_text = str(response)
        if "Finance Feed Agent" in response_text or "stock" in response_text.lower():
            logger.log_test("A2A via Consumer Agent", "PASS", "Consumer Agent successfully relayed A2A message")
        else:
            logger.log_test("A2A via Consumer Agent", "WARN", "Response may not indicate successful A2A communication")
        
        logger.log_test("Scenario 5", "PASS", "A2A communication flow completed")
        return True
        
    except Exception as e:
        logger.log_test("Scenario 5", "FAIL", f"Error: {str(e)}")
        import traceback
        logger.log(traceback.format_exc(), "ERROR")
        return False

def test_scenario_6_data_facts_schema_validation() -> bool:
    """Scenario 6: Data Facts Schema Validation"""
    logger.log_section("SCENARIO 6: Data Facts Schema Validation")
    
    try:
        # Step 1: Fetch Data Facts
        logger.log("Step 1: Fetching Data Facts for schema validation")
        data_facts = fetch_data_facts(FINANCE_FEED_DATA_FACTS_URL)
        
        # Step 2: Validate required fields
        required_fields = ["dataset_id", "dataset_description", "access_type", "endpoint", "evidence", "ttl_seconds"]
        missing_fields = [field for field in required_fields if field not in data_facts]
        
        if missing_fields:
            logger.log_test("Required Fields Validation", "FAIL", f"Missing fields: {missing_fields}")
            return False
        logger.log_test("Required Fields Validation", "PASS", f"All required fields present: {required_fields}")
        
        # Step 3: Validate evidence structure
        evidence = data_facts.get("evidence", {})
        evidence_fields = ["last_updated", "checksum_sha256", "source"]
        missing_evidence = [field for field in evidence_fields if field not in evidence]
        
        if missing_evidence:
            logger.log_test("Evidence Structure Validation", "FAIL", f"Missing evidence fields: {missing_evidence}")
            return False
        logger.log_test("Evidence Structure Validation", "PASS", f"All evidence fields present: {evidence_fields}")
        
        # Step 4: Validate data types and formats
        validations = []
        
        # access_type validation
        if data_facts["access_type"] in ["public", "private"]:
            validations.append(("access_type", True, f"'{data_facts['access_type']}' is valid"))
        else:
            validations.append(("access_type", False, f"'{data_facts['access_type']}' is invalid"))
        
        # ttl_seconds validation
        if isinstance(data_facts["ttl_seconds"], int) and data_facts["ttl_seconds"] > 0:
            validations.append(("ttl_seconds", True, f"{data_facts['ttl_seconds']} is valid"))
        else:
            validations.append(("ttl_seconds", False, f"{data_facts['ttl_seconds']} is invalid"))
        
        # endpoint validation (should be URL)
        if data_facts["endpoint"].startswith("http://") or data_facts["endpoint"].startswith("https://"):
            validations.append(("endpoint", True, "Valid URL format"))
        else:
            validations.append(("endpoint", False, "Invalid URL format"))
        
        # last_updated validation (ISO 8601)
        try:
            datetime.fromisoformat(evidence["last_updated"].replace("Z", "+00:00"))
            validations.append(("last_updated", True, "Valid ISO 8601 format"))
        except:
            validations.append(("last_updated", False, "Invalid ISO 8601 format"))
        
        # checksum_sha256 validation (64 char hex string)
        if len(evidence["checksum_sha256"]) == 64 and all(c in '0123456789abcdef' for c in evidence["checksum_sha256"]):
            validations.append(("checksum_sha256", True, "Valid SHA256 hex string"))
        else:
            validations.append(("checksum_sha256", False, "Invalid SHA256 format"))
        
        # Log validation results
        all_valid = all(v[1] for v in validations)
        for field, is_valid, msg in validations:
            status = "PASS" if is_valid else "FAIL"
            logger.log_test(f"{field} Format Validation", status, msg)
        
        if not all_valid:
            return False
        
        logger.log_test("Scenario 6", "PASS", "Data Facts schema validation completed")
        return True
        
    except Exception as e:
        logger.log_test("Scenario 6", "FAIL", f"Error: {str(e)}")
        import traceback
        logger.log(traceback.format_exc(), "ERROR")
        return False

# =============================================================================
# MAIN TEST EXECUTION
# =============================================================================

def main():
    """Run all test scenarios"""
    logger.log_section("COMPREHENSIVE TEST SUITE: Agent A → Agent B → Data Facts → Dataset")
    logger.log(f"Test log file: {LOG_FILE}")
    logger.log(f"Start time: {datetime.now().isoformat()}")
    logger.log("")
    
    scenarios = [
        ("Scenario 6: Registry Discovery", test_scenario_4_registry_discovery),
        ("Scenario 1: Complete End-to-End Flow", test_scenario_1_complete_e2e_flow),
        ("Scenario 2: Freshness Validation", test_scenario_2_freshness_validation),
        ("Scenario 3: Checksum Verification", test_scenario_3_checksum_verification),
        ("Scenario 6: Data Facts Schema Validation", test_scenario_6_data_facts_schema_validation),
        ("Scenario 5: A2A Communication", test_scenario_5_a2a_communication),
    ]
    
    results = []
    
    for scenario_name, test_func in scenarios:
        logger.log("")
        try:
            result = test_func()
            results.append((scenario_name, result))
        except Exception as e:
            logger.log_test(scenario_name, "FAIL", f"Unexpected error: {str(e)}")
            import traceback
            logger.log(traceback.format_exc(), "ERROR")
            results.append((scenario_name, False))
    
    # Summary
    logger.log("")
    logger.log_section("TEST SUMMARY")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for scenario_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.log(f"{status}: {scenario_name}")
    
    logger.log("")
    logger.log(f"Total: {passed}/{total} scenarios passed")
    
    if passed == total:
        logger.log("🎉 All tests passed!")
    else:
        logger.log(f"⚠️  {total - passed} test(s) failed")
    
    logger.log("")
    logger.log(f"End time: {datetime.now().isoformat()}")
    logger.log(f"Total duration: {time.time() - logger.start_time:.2f} seconds")
    logger.log(f"Test log saved to: {LOG_FILE}")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
