#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data Consumer NEST Agent

A NEST agent that discovers other agents via registry and accesses their datasets using Data Facts.
Demonstrates the complete flow:
1. Registry discovery (standard NEST pattern)
2. Get data_facts_url from registry
3. Fetch Data Facts from URL
4. Access dataset via Data Facts endpoint
"""
import os
import sys
import json
import requests
from datetime import datetime, timezone
from typing import Dict, Any, Optional

# Fix encoding for Windows console
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except (AttributeError, ValueError):
        try:
            import codecs
            if hasattr(sys.stdout, 'buffer'):
                sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
            if hasattr(sys.stderr, 'buffer'):
                sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
        except Exception:
            pass

def safe_print(*args, **kwargs):
    """Print function that handles Unicode encoding errors gracefully."""
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        safe_args = []
        for arg in args:
            if isinstance(arg, str):
                safe_args.append(arg.encode('ascii', 'replace').decode('ascii'))
            else:
                safe_args.append(arg)
        print(*safe_args, **kwargs)

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from nanda_core.core.adapter import NANDA
from nanda_core.core.registry_client import RegistryClient
from dotenv import load_dotenv
load_dotenv()

# Try to import A2A client for agent-to-agent communication
try:
    from python_a2a import A2AClient, Message, TextContent, MessageRole
    import uuid
    A2A_AVAILABLE = True
except ImportError:
    A2A_AVAILABLE = False
    safe_print("⚠️ Warning: python_a2a library not available. A2A calls will not work.")

# =============================================================================
# A2A COMMUNICATION
# =============================================================================

def call_finance_agent_via_a2a(question: str, registry_url: str = None, fallback_url: str = None) -> str:
    """
    Call the Finance Feed Agent via A2A to get stock prices or information.
    This function looks up the finance feed agent in the registry and sends an A2A message.
    """
    if not A2A_AVAILABLE:
        return "A2A communication not available. Please install python_a2a library."
    
    try:
        # Look up finance feed agent in registry
        finance_agent_url = None
        target_agent_id = "finance-feed-agent"
        
        if registry_url:
            try:
                # Try to find finance feed agent in registry
                registry = RegistryClient(registry_url)
                agents_response = registry.list_agents()
                
                # Handle response format
                if isinstance(agents_response, list):
                    agents = agents_response
                elif isinstance(agents_response, dict):
                    agents = agents_response.get("agents", [])
                else:
                    agents = []
                
                # Find the finance feed agent
                finance_agents = [a for a in agents if "finance-feed" in (a.get("agent_id", "") or a.get("id", "")).lower()]
                if finance_agents:
                    # Get the most recent one
                    finance_agent = finance_agents[-1]
                    finance_agent_url = finance_agent.get("agent_url")
                    target_agent_id = finance_agent.get("agent_id", "finance-feed-agent")
                    safe_print(f"🌐 Found Finance Feed Agent in registry: {target_agent_id} at {finance_agent_url}")
            except Exception as e:
                safe_print(f"⚠️ Registry lookup failed: {e}")
        
        if not finance_agent_url:
            # Use fallback URL (for local testing)
            if fallback_url:
                finance_agent_url = fallback_url
                safe_print(f"🏠 Using fallback Finance Feed Agent URL: {finance_agent_url}")
            else:
                return "Finance Feed Agent not found in registry and no fallback URL provided."
        
        # Ensure URL has /a2a endpoint
        if not finance_agent_url.endswith('/a2a'):
            finance_agent_url = f"{finance_agent_url}/a2a"
        
        safe_print(f"📤 Calling Finance Feed Agent via A2A: {question}")
        
        # Create A2A message
        client = A2AClient(finance_agent_url, timeout=30)
        a2a_message = Message(
            role=MessageRole.USER,
            content=TextContent(text=question),
            conversation_id=f"consumer-finance-request-{uuid.uuid4().hex[:8]}"
        )
        
        # Send message and get response
        response = client.send_message(a2a_message)
        safe_print(f"🛰️ Received response from Finance Feed Agent")
        
        # Extract response text robustly
        def _extract_text(resp):
            # python_a2a Message with parts
            if resp and hasattr(resp, 'parts'):
                try:
                    parts = getattr(resp, 'parts', None)
                    if parts and len(parts) > 0:
                        if hasattr(parts[0], 'text'):
                            return getattr(parts[0], 'text', '')
                        if isinstance(parts[0], dict) and 'text' in parts[0]:
                            return parts[0]['text']
                except Exception as e:
                    safe_print(f"[DEBUG] Error accessing resp.parts: {e}")
                    pass
            
            # dict-like with parts
            if isinstance(resp, dict):
                parts = resp.get("parts") or resp.get("content") or None
                if parts and isinstance(parts, list) and len(parts) > 0:
                    first = parts[0]
                    if isinstance(first, dict) and "text" in first:
                        return first.get("text")
                    if hasattr(first, 'text'):
                        return getattr(first, 'text', '')
                if "text" in resp:
                    return resp.get("text")
            
            # Try to access as attribute
            if resp and hasattr(resp, 'text'):
                try:
                    return getattr(resp, 'text', '')
                except:
                    pass
            
            # Fallback: convert to string
            try:
                return str(resp)
            except:
                return "Finance Feed Agent responded but could not parse the response."
        
        response_text = _extract_text(response)
        safe_print(f"✅ Received response from Finance Feed Agent: {response_text[:100]}...")
        return response_text or "Finance Feed Agent responded but response format was unexpected."
            
    except Exception as e:
        error_msg = f"Error calling Finance Feed Agent: {str(e)}"
        safe_print(f"❌ {error_msg}")
        import traceback
        traceback.print_exc()
        return error_msg

# =============================================================================
# DATA FACTS AND DATASET ACCESS
# =============================================================================

def fetch_data_facts(data_facts_url: str) -> Dict[str, Any]:
    """Fetch Data Facts from URL"""
    try:
        response = requests.get(data_facts_url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise Exception(f"Failed to fetch Data Facts from {data_facts_url}: {e}")

def check_freshness(data_facts: Dict[str, Any]) -> bool:
    """Check if data is fresh based on TTL and last_updated"""
    ttl = data_facts.get("ttl_seconds", 0)
    last_updated = data_facts["evidence"]["last_updated"]
    
    last_dt = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    age_seconds = (now - last_dt).total_seconds()
    
    return age_seconds <= ttl

def fetch_dataset(data_facts: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch dataset from endpoint specified in Data Facts"""
    endpoint = data_facts["endpoint"]
    try:
        response = requests.get(endpoint, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise Exception(f"Failed to fetch dataset from {endpoint}: {e}")

def verify_checksum(data_facts: Dict[str, Any], dataset: Dict[str, Any]) -> bool:
    """Verify dataset checksum matches Data Facts evidence"""
    import hashlib
    
    # Compute checksum (exclude timestamp for consistency)
    data_copy = {k: v for k, v in dataset.items() if k != "timestamp"}
    serialized = json.dumps(data_copy, sort_keys=True).encode("utf-8")
    computed_checksum = hashlib.sha256(serialized).hexdigest()
    
    expected_checksum = data_facts["evidence"]["checksum_sha256"]
    
    return computed_checksum == expected_checksum

def discover_and_access_dataset(registry_url: str, target_agent_id: str = "finance-feed-agent") -> Optional[Dict[str, Any]]:
    """
    Discover agent via registry and access its dataset using Data Facts
    
    Returns:
        Dictionary with discovery and access results, or None if failed
    """
    try:
        safe_print(f"🔍 Discovering agent '{target_agent_id}' via registry...")
        
        # Create registry client
        registry = RegistryClient(registry_url)
        
        # List all agents
        agents_response = registry.list_agents()
        
        # Handle both list and dict responses
        if isinstance(agents_response, list):
            agents = agents_response
        elif isinstance(agents_response, dict):
            agents = agents_response.get("agents", [])
        else:
            agents = []
        
        if not agents:
            safe_print(f"❌ No agents found in registry")
            return None
        
        # Find target agent
        target_agent = None
        for agent in agents:
            agent_id = agent.get("agent_id") or agent.get("id", "")
            if agent_id.startswith(target_agent_id) or target_agent_id in agent_id:
                target_agent = agent
                break
        
        if not target_agent:
            safe_print(f"❌ Agent '{target_agent_id}' not found in registry")
            safe_print(f"   Available agents: {[a.get('agent_id', a.get('id', 'unknown')) for a in agents]}")
            return None
        
        safe_print(f"✅ Found agent: {target_agent.get('agent_id', target_agent.get('id'))}")
        
        # Get data_facts_url from registry response
        data_facts_url = target_agent.get("data_facts_url")
        
        if not data_facts_url:
            safe_print(f"⚠️ Agent found but no 'data_facts_url' in registry response")
            safe_print(f"   Registry response: {json.dumps(target_agent, indent=2)}")
            return None
        
        safe_print(f"📋 Data Facts URL: {data_facts_url}")
        
        # Fetch Data Facts
        safe_print(f"\n📥 Fetching Data Facts...")
        data_facts = fetch_data_facts(data_facts_url)
        safe_print(f"✅ Data Facts retrieved:")
        safe_print(f"   Dataset ID: {data_facts['dataset_id']}")
        safe_print(f"   Access Type: {data_facts['access_type']}")
        safe_print(f"   Endpoint: {data_facts['endpoint']}")
        
        # Check access type
        if data_facts.get("access_type") != "public":
            safe_print(f"⚠️ Dataset access_type is '{data_facts.get('access_type')}', not 'public'. Skipping.")
            return None
        
        # Check freshness
        safe_print(f"\n⏰ Checking data freshness...")
        is_fresh = check_freshness(data_facts)
        freshness_status = "✅ FRESH" if is_fresh else "⚠️ STALE"
        safe_print(f"{freshness_status} (TTL: {data_facts.get('ttl_seconds')}s)")
        safe_print(f"   Last updated: {data_facts['evidence']['last_updated']}")
        
        # Fetch dataset
        safe_print(f"\n📊 Fetching dataset from endpoint...")
        dataset = fetch_dataset(data_facts)
        safe_print(f"✅ Dataset retrieved: {json.dumps(dataset, indent=2)}")
        
        # Verify checksum (optional)
        safe_print(f"\n🔐 Verifying checksum...")
        checksum_matches = verify_checksum(data_facts, dataset)
        if checksum_matches:
            safe_print(f"✅ Checksum matches!")
        else:
            safe_print(f"⚠️ Checksum mismatch (data may have changed since last update)")
        
        return {
            "agent": target_agent,
            "data_facts": data_facts,
            "dataset": dataset,
            "is_fresh": is_fresh,
            "checksum_matches": checksum_matches
        }
        
    except Exception as e:
        safe_print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

# =============================================================================
# AGENT LOGIC
# =============================================================================

def create_consumer_agent_logic(registry_url: str, use_a2a: bool = True, fallback_finance_url: str = None):
    """Create agent logic function for data consumer agent"""
    
    def agent_logic(message: str, conversation_id: str) -> str:
        """Agent logic that discovers and accesses datasets, with A2A communication support"""
        message_lower = message.lower()
        
        if "hello" in message_lower or "hi" in message_lower:
            return "Hello! I'm a Data Consumer Agent. I can discover agents via the registry and communicate with them via A2A or access their datasets using Data Facts. Try asking me to fetch stock prices or query the finance agent."
        
        # A2A communication with finance feed agent
        if use_a2a and ("stock" in message_lower or "price" in message_lower or "finance" in message_lower or "ask finance" in message_lower or "query finance" in message_lower):
            try:
                safe_print(f"\n🤖 Using A2A to communicate with Finance Feed Agent...")
                # Use A2A to query the finance feed agent
                a2a_response = call_finance_agent_via_a2a(message, registry_url, fallback_finance_url)
                if a2a_response and not a2a_response.startswith("Error") and not a2a_response.startswith("Finance Feed Agent not found"):
                    return f"I queried the Finance Feed Agent via A2A, and here's what they said:\n\n{a2a_response}"
                else:
                    # Fallback to dataset access if A2A fails
                    safe_print(f"⚠️ A2A communication failed, falling back to dataset access...")
            except Exception as e:
                safe_print(f"⚠️ A2A communication error: {e}, falling back to dataset access...")
        
        # Dataset access (fallback or when explicitly requested)
        if "dataset" in message_lower or "fetch" in message_lower or "data facts" in message_lower:
            try:
                safe_print(f"\n📊 Accessing dataset via Data Facts...")
                result = discover_and_access_dataset(registry_url, "finance-feed-agent")
                if result:
                    dataset = result["dataset"]
                    prices = {k: v for k, v in dataset.items() if k != "timestamp"}
                    price_str = ", ".join([f"{k}: ${v}" if v else f"{k}: N/A" for k, v in prices.items()])
                    return f"I successfully accessed the dataset via Data Facts! Stock prices: {price_str}"
                else:
                    return "Sorry, I couldn't access the dataset. The agent might not be registered or the dataset might not be available."
            except Exception as e:
                return f"Sorry, I encountered an error: {str(e)}"
        
        if "help" in message_lower:
            return """I'm a Data Consumer Agent. I can help you with:
- A2A Communication: Query the Finance Feed Agent directly via A2A (e.g., "ask finance agent about stock prices")
- Dataset Access: Access datasets using Data Facts (e.g., "fetch stock prices")
- Agent Discovery: Discover agents via registry

Try: "ask finance agent about stock prices" or "fetch stock prices" or "what are the current stock prices"
"""
        
        return "I'm a Data Consumer Agent. Ask me to query the finance agent about stock prices, or fetch stock prices via dataset access!"
    
    return agent_logic

# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Main function to start the data consumer agent"""
    # Get configuration from environment variables
    agent_id = os.getenv("AGENT_ID", "data-consumer-agent")
    agent_name = os.getenv("AGENT_NAME", "Data Consumer Agent")
    registry_url = os.getenv("REGISTRY_URL", "http://registry.chat39.com:6900")
    public_url = os.getenv("PUBLIC_URL", None)
    port = int(os.getenv("PORT", "6001"))  # Use 6001 to avoid conflict with finance feed agent
    
    safe_print("=" * 60)
    safe_print(f"🤖 {agent_name}")
    safe_print(f"📊 Agent ID: {agent_id}")
    safe_print("=" * 60)
    
    if not registry_url:
        safe_print("❌ Error: REGISTRY_URL environment variable is required")
        safe_print("   Set it to: export REGISTRY_URL=http://registry.chat39.com:6900")
        sys.exit(1)
    
    safe_print(f"🌐 Registry: {registry_url}")
    
    # Fallback finance feed agent URL (for local testing when not registered)
    fallback_finance_url = os.getenv("FINANCE_FEED_AGENT_URL", "http://localhost:6000")
    
    # Create agent logic (with A2A support)
    agent_logic = create_consumer_agent_logic(registry_url, use_a2a=A2A_AVAILABLE, fallback_finance_url=fallback_finance_url)
    
    # Create NANDA agent
    nanda = NANDA(
        agent_id=agent_id,
        agent_logic=agent_logic,
        port=port,
        registry_url=registry_url,
        public_url=public_url,
        enable_telemetry=False
    )
    
    safe_print(f"🚀 A2A endpoint: http://localhost:{port}/a2a")
    safe_print("\n💡 Try sending A2A messages like:")
    if A2A_AVAILABLE:
        safe_print("   - 'ask finance agent about stock prices' (A2A communication)")
        safe_print("   - 'what are the current stock prices?' (A2A communication)")
    safe_print("   - 'fetch stock prices' (Dataset access via Data Facts)")
    safe_print("   - 'access dataset' (Dataset access via Data Facts)")
    safe_print("   - 'hello'")
    safe_print("🛑 Press Ctrl+C to stop")
    safe_print("=" * 60)
    
    # Start the agent (this blocks)
    try:
        nanda.start()
    except KeyboardInterrupt:
        safe_print("\n🛑 Shutting down...")
        nanda.stop()

if __name__ == "__main__":
    main()

