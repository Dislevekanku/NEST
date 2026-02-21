"""
Dataset Client Utilities

Helper functions for discovering and accessing datasets via Data Facts.
These functions work with any dataset provider, not just finance.
"""
import json
import hashlib
import requests
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

from nanda_core.core.registry_client import RegistryClient


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


def negotiate_access(agent_url: str,
                     consumer_agent_id: str,
                     ttl_seconds: int = 60) -> Optional[Dict[str, Any]]:
    """
    Negotiate access with a data owner agent's /negotiate_access endpoint.

    Args:
        agent_url: Base URL of the data owner agent (e.g., http://localhost:6300)
        consumer_agent_id: ID of the requesting consumer agent
        ttl_seconds: Requested token TTL

    Returns:
        Dict with access_granted, token, ttl_seconds; or None on failure
    """
    try:
        url = f"{agent_url.rstrip('/')}/negotiate_access"
        payload = {
            "consumer_agent_id": consumer_agent_id,
            "ttl_seconds": ttl_seconds,
        }
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"Error negotiating access at {agent_url}: {e}")
        return None


def fetch_dataset(data_facts: Dict[str, Any],
                  headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Fetch dataset from endpoint specified in Data Facts.

    For semi-private/private datasets, pass authentication headers:
        headers = {"Authorization": "Bearer <jwt>"}
        dataset = fetch_dataset(data_facts, headers=headers)
    """
    endpoint = data_facts["endpoint"]
    try:
        response = requests.get(endpoint, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise Exception(f"Failed to fetch dataset from {endpoint}: {e}")


def fetch_dataset_direct(endpoint_url: str,
                         headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Fetch dataset directly from URL (without Data Facts).
    Use when use_data_facts=false in experiment config.
    """
    try:
        response = requests.get(endpoint_url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise Exception(f"Failed to fetch dataset from {endpoint_url}: {e}")


def verify_checksum(data_facts: Dict[str, Any], dataset: Dict[str, Any]) -> bool:
    """Verify dataset checksum matches Data Facts evidence"""
    # Compute checksum (exclude timestamp for consistency)
    data_copy = {k: v for k, v in dataset.items() if k != "timestamp"}
    serialized = json.dumps(data_copy, sort_keys=True).encode("utf-8")
    computed_checksum = hashlib.sha256(serialized).hexdigest()
    
    expected_checksum = data_facts["evidence"]["checksum_sha256"]
    
    return computed_checksum == expected_checksum


def discover_datasets(registry_url: str, 
                     dataset_keywords: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Discover agents with datasets via registry.
    
    Args:
        registry_url: Registry URL
        dataset_keywords: Optional keywords to filter agents (e.g., ["finance", "stock"])
        
    Returns:
        List of agents with data_facts_url
    """
    registry = RegistryClient(registry_url)
    agents_response = registry.list_agents()
    
    # Handle both list and dict responses
    if isinstance(agents_response, list):
        agents = agents_response
    elif isinstance(agents_response, dict):
        agents = agents_response.get("agents", [])
    else:
        agents = []
    
    # Normalize: registry may return data_facts_url (snake_case) or dataFactsURL (camelCase)
    def _data_facts_url(a: Dict[str, Any]) -> Optional[str]:
        url = a.get("data_facts_url") or a.get("dataFactsURL") or a.get("data_facts_URL")
        return url if url else None

    agents_with_datasets = []
    for agent in agents:
        df_url = _data_facts_url(agent)
        if df_url:
            # Ensure downstream code can use agent["data_facts_url"]
            a = dict(agent)
            a["data_facts_url"] = df_url
            agents_with_datasets.append(a)
    
    # Filter by keywords if provided
    if dataset_keywords:
        filtered = []
        for agent in agents_with_datasets:
            agent_id = (agent.get("agent_id") or agent.get("id", "")).lower()
            agent_name = (agent.get("agent_name") or agent.get("name", "")).lower()
            if any(keyword.lower() in agent_id or keyword.lower() in agent_name 
                   for keyword in dataset_keywords):
                filtered.append(agent)
        return filtered
    
    return agents_with_datasets


def discover_and_access_dataset(registry_url: str,
                               target_agent_id: Optional[str] = None,
                               target_dataset_id: Optional[str] = None,
                               keywords: Optional[List[str]] = None,
                               access_headers: Optional[Dict[str, str]] = None,
                               ttl_enabled: bool = True,
                               checksum_enabled: bool = True) -> Optional[Dict[str, Any]]:
    """
    Discover agent via registry and access its dataset using Data Facts.

    Supports experiment toggles (see experiments/experiment_config_template.json):
    - ttl_enabled: when True, check freshness; when False, skip (is_fresh=True).
    - checksum_enabled: when True, verify checksum; when False, skip (checksum_matches=True).

    This is a generic function that works with any dataset provider,
    not just finance. It can discover weather, traffic, or any other datasets.

    Args:
        registry_url: Registry URL
        target_agent_id: Specific agent ID to find (optional)
        target_dataset_id: Specific dataset ID to find (optional)
        keywords: Keywords to search for (e.g., ["finance", "stock"] or ["weather"])
        access_headers: Authentication headers for private datasets
        ttl_enabled: If True, run freshness check; if False, skip (is_fresh=True).
        checksum_enabled: If True, verify checksum; if False, skip (checksum_matches=True).

    Returns:
        Dictionary with discovery and access results, or None if failed
    """
    try:
        # Discover agents with datasets
        if target_agent_id:
            # Find specific agent
            registry = RegistryClient(registry_url)
            agents_response = registry.list_agents()

            if isinstance(agents_response, list):
                agents = agents_response
            elif isinstance(agents_response, dict):
                agents = agents_response.get("agents", [])
            else:
                agents = []

            target_agent = None
            for agent in agents:
                agent_id = agent.get("agent_id") or agent.get("id", "")
                if agent_id.startswith(target_agent_id) or target_agent_id in agent_id:
                    target_agent = agent
                    break
        else:
            # Find agents matching keywords
            agents_with_datasets = discover_datasets(registry_url, keywords)
            if not agents_with_datasets:
                return None
            target_agent = agents_with_datasets[0]  # Use first match

        if not target_agent:
            return None

        # Get data_facts_url from registry response
        data_facts_url = target_agent.get("data_facts_url")
        if not data_facts_url:
            return None

        # Fetch Data Facts
        data_facts = fetch_data_facts(data_facts_url)

        # Check if dataset matches target (if specified)
        if target_dataset_id and data_facts.get("dataset_id") != target_dataset_id:
            return None

        # Check access type and negotiate if needed
        access_type = data_facts.get("access_type", "public")
        if access_type in ("semi-private", "private") and not access_headers:
            agent_url = target_agent.get("agent_url", "")
            negotiated = negotiate_access(
                agent_url=agent_url,
                consumer_agent_id=target_agent_id or "anonymous",
            )
            if negotiated and negotiated.get("access_granted") and negotiated.get("token"):
                access_headers = {"Authorization": f"Bearer {negotiated['token']}"}
            else:
                print(f"Failed to negotiate access for {access_type} dataset")
                return None

        # Toggle: TTL on/off
        is_fresh = check_freshness(data_facts) if ttl_enabled else True

        # Fetch dataset
        dataset = fetch_dataset(data_facts, headers=access_headers)

        # Toggle: Checksum on/off
        checksum_matches = verify_checksum(data_facts, dataset) if checksum_enabled else True

        return {
            "agent": target_agent,
            "data_facts": data_facts,
            "dataset": dataset,
            "is_fresh": is_fresh,
            "checksum_matches": checksum_matches,
        }

    except Exception as e:
        print(f"Error discovering/accessing dataset: {e}")
        import traceback
        traceback.print_exc()
        return None


def access_dataset_from_config(config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Access dataset using experiment config (experiments/experiment_config_template.json).

    Toggles:
    - use_data_facts: True = Data Facts flow; False = direct GET to dataset_endpoint.
    - ttl_enabled: when use_data_facts, enforce freshness (default True).
    - checksum_enabled: when use_data_facts, verify checksum (default True).

    When use_data_facts=True:
    - If data_facts_url is set: fetch Data Facts from URL, then dataset; no registry.
    - Else: use registry_url + target_agent_id/keywords (discover_and_access_dataset).
    When use_data_facts=False: dataset_endpoint required.
    """
    use_data_facts = config.get("use_data_facts", True)
    ttl_enabled = config.get("ttl_enabled", True)
    checksum_enabled = config.get("checksum_enabled", True)
    headers = config.get("access_headers")

    if not use_data_facts:
        endpoint = config.get("dataset_endpoint")
        if not endpoint:
            raise ValueError("dataset_endpoint required when use_data_facts=False")
        try:
            dataset = fetch_dataset_direct(endpoint, headers=headers)
            return {
                "agent": None,
                "data_facts": None,
                "dataset": dataset,
                "is_fresh": None,
                "checksum_matches": None,
            }
        except Exception as e:
            print(f"Error fetching dataset directly: {e}")
            return None

    # Use Data Facts
    data_facts_url = config.get("data_facts_url")
    if data_facts_url:
        try:
            data_facts = fetch_data_facts(data_facts_url)
            if config.get("target_dataset_id") and data_facts.get("dataset_id") != config["target_dataset_id"]:
                return None
            is_fresh = check_freshness(data_facts) if ttl_enabled else True
            dataset = fetch_dataset(data_facts, headers=headers)
            checksum_matches = verify_checksum(data_facts, dataset) if checksum_enabled else True
            return {
                "agent": None,
                "data_facts": data_facts,
                "dataset": dataset,
                "is_fresh": is_fresh,
                "checksum_matches": checksum_matches,
            }
        except Exception as e:
            print(f"Error accessing dataset via data_facts_url: {e}")
            return None
    else:
        registry_url = config.get("registry_url")
        if not registry_url:
            raise ValueError("registry_url or data_facts_url required when use_data_facts=True")
        return discover_and_access_dataset(
            registry_url=registry_url,
            target_agent_id=config.get("target_agent_id"),
            target_dataset_id=config.get("target_dataset_id"),
            keywords=config.get("keywords"),
            access_headers=headers,
            ttl_enabled=ttl_enabled,
            checksum_enabled=checksum_enabled,
        )
