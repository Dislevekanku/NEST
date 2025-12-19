#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM-Powered Modular NANDA Agent

This agent uses Anthropic Claude for intelligent responses based on configurable personality and expertise.
Simply update the AGENT_CONFIG section to create different agent personalities.
"""
import os
import sys
import time
import uuid
from datetime import datetime
from typing import Dict, List, Any
import pandas as pd

# Fix encoding for Windows console
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except (AttributeError, ValueError):
        # Python < 3.7 doesn't have reconfigure, or encoding already set
        try:
            import codecs
            if hasattr(sys.stdout, 'buffer'):
                sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
            if hasattr(sys.stderr, 'buffer'):
                sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
        except Exception:
            # If all else fails, create a safe print function
            pass

# Safe print function that handles encoding errors
def safe_print(*args, **kwargs):
    """Print function that handles Unicode encoding errors gracefully."""
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        # Fallback: replace problematic characters
        safe_args = []
        for arg in args:
            if isinstance(arg, str):
                safe_args.append(arg.encode('ascii', 'replace').decode('ascii'))
            else:
                safe_args.append(arg)
        print(*safe_args, **kwargs)

# Add the parent directory to the path to allow importing streamlined_adapter
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from nanda_core.core.adapter import NANDA

# Try to import Anthropic - will fail gracefully if not available
try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    safe_print("⚠️ Warning: anthropic library not available. Install with: pip install anthropic")

# Try to import A2A client for agent-to-agent communication
try:
    from python_a2a import A2AClient, Message, TextContent, MessageRole
    import requests
    A2A_AVAILABLE = True
except ImportError:
    A2A_AVAILABLE = False
    safe_print("⚠️ Warning: python_a2a library not available. A2A calls will not work.")


# =============================================================================
# AGENT CONFIGURATION - Customize this section for different agents
# =============================================================================

# Get configuration from environment variables or use defaults
def get_agent_config():
    """Load agent configuration from environment variables or use defaults"""
    
    # Generate agent_id with hex suffix for uniqueness
    base_agent_id = os.getenv("AGENT_ID", "helpful-ubuntu-agent")
    if not base_agent_id.endswith('-') and '-' not in base_agent_id.split('-')[-1]:
        # Add 6-character hex suffix if not already present
        hex_suffix = uuid.uuid4().hex[:6]
        agent_id = f"{base_agent_id}-{hex_suffix}"
    else:
        agent_id = base_agent_id
    
    print(f"Generated agent_id: {agent_id}")
    agent_name = os.getenv("AGENT_NAME", "Ubuntu Helper")
    domain = os.getenv("AGENT_DOMAIN", "general assistance")
    specialization = os.getenv("AGENT_SPECIALIZATION", "helpful and friendly AI assistant")
    description = os.getenv("AGENT_DESCRIPTION", "I am a helpful AI assistant specializing in general tasks and Ubuntu system administration.")
    capabilities = os.getenv("AGENT_CAPABILITIES", "general assistance,Ubuntu system administration,Python development,cloud deployment,agent-to-agent communication")
    registry_url = os.getenv("REGISTRY_URL", None)
    public_url = os.getenv("PUBLIC_URL", None)
    
    # Parse capabilities into a list
    expertise_list = [cap.strip() for cap in capabilities.split(",")]
    
    # Create dynamic system prompt based on configuration
    system_prompt = f"""You are {agent_name}, a {specialization} working in the domain of {domain}.

{description}

You are part of the NANDA (Network of Autonomous Distributed Agents) system. You can communicate with other agents and help users with various tasks.

Your capabilities include:
{chr(10).join([f"- {cap}" for cap in expertise_list])}

Always be helpful, accurate, and concise in your responses. If you're unsure about something, say so honestly. You can also help with basic calculations, provide time information, and engage in casual conversation.

When someone asks about yourself, mention that you're part of the NANDA agent network and can communicate with other agents using the @agent_name syntax."""

    return {
        "agent_id": agent_id,
        "agent_name": agent_name,
        "domain": domain,
        "specialization": specialization,
        "description": description,
        "expertise": expertise_list,
        "registry_url": registry_url,
        "public_url": public_url,
        "system_prompt": system_prompt,
        "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY"),
        "model": "claude-3-haiku-20240307"  # Fast and cost-effective model
    }

# Load configuration
AGENT_CONFIG = get_agent_config()

# Port configuration - use environment variable or default to 6000
PORT = int(os.getenv("PORT", "6000"))

# =============================================================================
# DATA LOADING - Load attached data if DATA_PATH is provided
# =============================================================================

def load_agent_data(data_path: str):
    """Load agent-attached data if provided."""
    if not data_path:
        return None

    safe_print(f"📂 Loading data from: {data_path}")

    if data_path.endswith(".csv"):
        df = pd.read_csv(data_path)
        safe_print(f"✅ Loaded CSV data with shape: {df.shape}")
        return df

    raise ValueError(f"Unsupported data format: {data_path}")

# =============================================================================
# LLM-POWERED AGENT LOGIC - Uses Anthropic Claude for intelligent responses
# =============================================================================

def create_data_tools(agent_data):
    """Create MCP tools for accessing agent data"""
    if agent_data is None:
        return []
    
    tools = []
    
    # Tool 1: Get row count
    tools.append({
        "name": "get_row_count",
        "description": "Returns the number of rows in the attached dataset. Use this to answer questions like 'how many items', 'how many records', 'how many rows'.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    })
    
    # Tool 2: Query data
    tools.append({
        "name": "query_data",
        "description": "Query the dataset. Can filter by any column, find min/max values, calculate averages, or list all data. Returns relevant rows from the dataset. Use this for ANY question about the data.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "What to query. Examples: 'all items', 'cheapest item', 'most expensive', 'average price', 'items in Main category', 'lowest price', 'highest price'"
                }
            },
            "required": ["query"]
        }
    })
    
    # Tool 3: Get data summary
    tools.append({
        "name": "get_data_summary",
        "description": "Get a summary of the dataset including column names, row count, and basic statistics. Use this to understand the dataset structure.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    })
    
    # Step 6.1: Debug print to confirm tools are registered
    tool_names = [t["name"] for t in tools]
    safe_print(f"🔧 Registered MCP tools: {tool_names}")
    
    return tools

def execute_data_tool(tool_name: str, tool_input: Dict[str, Any], agent_data):
    """Execute a data tool and return the result"""
    if agent_data is None:
        return "No data available"
    
    # Step 6.4: Log tool invocation for debugging
    safe_print(f"🛠️ Tool invoked: {tool_name} with args {tool_input}")
    
    try:
        if tool_name == "get_row_count":
            if isinstance(agent_data, pd.DataFrame):
                return f"The dataset has {len(agent_data)} rows"
            return "Data is not in the expected format"
        
        elif tool_name == "query_data":
            query = tool_input.get("query", "").lower()
            df = agent_data
            
            # Generic: List all data
            if "all" in query or "list" in query or "show" in query:
                return df.to_string(index=False)
            
            # Generic: Find cheapest/lowest price
            if any(word in query for word in ["cheapest", "lowest", "minimum", "min price"]):
                if 'price' in df.columns:
                    min_price_idx = df['price'].idxmin()
                    min_item = df.loc[min_price_idx]
                    return f"Cheapest item: {min_item.to_dict()}"
                elif 'salary' in df.columns:
                    min_salary_idx = df['salary'].idxmin()
                    min_item = df.loc[min_salary_idx]
                    return f"Lowest: {min_item.to_dict()}"
            
            # Generic: Find most expensive/highest price
            if any(word in query for word in ["expensive", "highest", "maximum", "max price", "most expensive"]):
                if 'price' in df.columns:
                    max_price_idx = df['price'].idxmax()
                    max_item = df.loc[max_price_idx]
                    return f"Most expensive item: {max_item.to_dict()}"
                elif 'salary' in df.columns:
                    max_salary_idx = df['salary'].idxmax()
                    max_item = df.loc[max_salary_idx]
                    return f"Highest: {max_item.to_dict()}"
            
            # Generic: Calculate average
            if "average" in query or "mean" in query or "avg" in query:
                if 'price' in df.columns:
                    avg_price = df['price'].mean()
                    return f"Average price: ${avg_price:.2f}"
                elif 'salary' in df.columns:
                    avg_salary = df['salary'].mean()
                    return f"Average salary: ${avg_salary:,.2f}"
            
            # Generic: Filter by category/department
            if 'category' in df.columns:
                for cat in df['category'].unique():
                    if cat.lower() in query:
                        result = df[df['category'].str.lower() == cat.lower()]
                        return result.to_string(index=False) if len(result) > 0 else f"No items found in {cat} category"
            
            if 'department' in df.columns:
                for dept in df['department'].unique():
                    if dept.lower() in query:
                        result = df[df['department'].str.lower() == dept.lower()]
                        return result.to_string(index=False) if len(result) > 0 else f"No employees found in {dept} department"
            
            # Generic: Filter by specific column value
            for col in df.columns:
                if col.lower() in query:
                    # Try to find matching values
                    for val in df[col].unique():
                        if str(val).lower() in query:
                            result = df[df[col] == val]
                            return result.to_string(index=False) if len(result) > 0 else f"No matches found for {val} in {col}"
            
            # Fallback: return all data if query not understood
            return f"Query '{query}' not fully understood. Here's all the data:\n{df.to_string(index=False)}"
        
        elif tool_name == "get_data_summary":
            df = agent_data
            summary = f"Dataset Summary:\n"
            summary += f"- Rows: {len(df)}\n"
            summary += f"- Columns: {', '.join(df.columns.tolist())}\n"
            
            # Add column-specific summaries
            if 'price' in df.columns:
                summary += f"- Price range: ${df['price'].min():.2f} - ${df['price'].max():.2f}\n"
                summary += f"- Average price: ${df['price'].mean():.2f}\n"
            if 'salary' in df.columns:
                summary += f"- Salary range: ${df['salary'].min():,} - ${df['salary'].max():,}\n"
                summary += f"- Average salary: ${df['salary'].mean():,.2f}\n"
            if 'category' in df.columns:
                summary += f"- Categories: {', '.join(df['category'].unique())}\n"
            if 'department' in df.columns:
                summary += f"- Departments: {', '.join(df['department'].unique())}\n"
            
            summary += f"\nFirst few rows:\n{df.head().to_string(index=False)}"
            return summary
        
        else:
            return f"Unknown tool: {tool_name}"
    
    except Exception as e:
        return f"Error executing tool: {str(e)}"

def call_menu_agent_via_a2a(question: str, registry_url: str = None) -> str:
    """
    Call the Menu Agent via A2A to get menu information.
    This function looks up the menu agent in the registry and sends an A2A message.
    """
    if not A2A_AVAILABLE:
        return "A2A communication not available. Please install python_a2a library."
    
    try:
        # Look up menu agent in registry
        menu_agent_url = None
        target_agent_id = "menu-agent"
        
        if registry_url:
            try:
                # Try to find menu agent in registry
                response = requests.get(f"{registry_url}/list", timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    agents = data.get("agents", [])
                    # Find the most recent menu-agent
                    menu_agents = [a for a in agents if a.get("agent_id", "").startswith("menu-agent")]
                    if menu_agents:
                        # Get the most recent one (last in list or by some criteria)
                        menu_agent = menu_agents[-1]
                        menu_agent_url = menu_agent.get("agent_url")
                        target_agent_id = menu_agent.get("agent_id", "menu-agent")
                        safe_print(f"🌐 Found Menu Agent in registry: {target_agent_id} at {menu_agent_url}")
            except Exception as e:
                safe_print(f"⚠️ Registry lookup failed: {e}")
        
        if not menu_agent_url:
            # Fallback: try known IP (Agent A from deployment)
            menu_agent_url = "http://54.237.202.184:6000"
            safe_print(f"🏠 Using fallback Menu Agent URL: {menu_agent_url}")
        
        # Ensure URL has /a2a endpoint
        if not menu_agent_url.endswith('/a2a'):
            menu_agent_url = f"{menu_agent_url}/a2a"
        
        safe_print(f"📤 Calling Menu Agent via A2A: {question}")
        
        # Create A2A message
        client = A2AClient(menu_agent_url, timeout=30)
        a2a_message = Message(
            role=MessageRole.USER,
            content=TextContent(text=question),
            conversation_id=f"concierge-menu-request-{uuid.uuid4().hex[:8]}"
        )
        
        # Send message and get response
        response = client.send_message(a2a_message)
        safe_print(f"🛰️ Raw A2A response type: {type(response)}")
        safe_print(f"🛰️ Raw A2A response repr: {str(response)[:200]}...")
        
        # Extract response text robustly
        def _extract_text(resp):
            # Debug: log the response structure
            safe_print(f"[DEBUG] Response type: {type(resp)}")
            safe_print(f"[DEBUG] Response has 'parts' attr: {hasattr(resp, 'parts') if resp else False}")
            
            # python_a2a Message with parts
            if resp and hasattr(resp, 'parts'):
                try:
                    parts = getattr(resp, 'parts', None)
                    if parts and len(parts) > 0:
                        # Try accessing text directly
                        if hasattr(parts[0], 'text'):
                            return getattr(parts[0], 'text', '')
                        # Try as dict
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
                    # Also check if first is an object with text attribute
                    if hasattr(first, 'text'):
                        return getattr(first, 'text', '')
                if "text" in resp:
                    return resp.get("text")
            
            # Try to access as attribute (for Message objects)
            if resp and hasattr(resp, 'text'):
                try:
                    return getattr(resp, 'text', '')
                except:
                    pass
            
            # Fallback: convert to string and try to extract JSON
            try:
                resp_str = str(resp)
                # If it's a JSON string, try to parse it
                import json
                if resp_str.startswith('{') or resp_str.startswith('['):
                    try:
                        parsed = json.loads(resp_str)
                        if isinstance(parsed, dict):
                            parts = parsed.get("parts") or parsed.get("content")
                            if parts and isinstance(parts, list) and len(parts) > 0:
                                if isinstance(parts[0], dict) and "text" in parts[0]:
                                    return parts[0]["text"]
                    except:
                        pass
                return resp_str
            except Exception:
                return "Menu Agent responded but could not parse the response."
        
        response_text = _extract_text(response)
        safe_print(f"✅ Received response from Menu Agent (parsed): {response_text[:150]}...")
        return response_text or "Menu Agent responded but response format was unexpected."
            
    except Exception as e:
        error_msg = f"Error calling Menu Agent: {str(e)}"
        safe_print(f"❌ {error_msg}")
        return error_msg

def create_llm_agent_logic(config: Dict[str, Any]):
    """
    Creates an LLM-powered agent logic function based on the provided configuration.
    Uses Anthropic Claude for intelligent, context-aware responses.
    """
    
    # Initialize Anthropic client
    anthropic_client = None
    if ANTHROPIC_AVAILABLE and config.get("anthropic_api_key"):
        try:
            anthropic_client = Anthropic(api_key=config["anthropic_api_key"])
            safe_print(f"✅ Anthropic Claude initialized for {config['agent_name']}")
        except Exception as e:
            print(f"❌ Failed to initialize Anthropic: {e}")
            anthropic_client = None
    
    # Prepare system prompt (already formatted in get_agent_config)
    system_prompt = config["system_prompt"]
    
    # Get data tools if data is available
    agent_data = config.get("data")
    data_tools = create_data_tools(agent_data) if agent_data is not None else []
    
    # Step 6.2: Strengthen system prompt if data is available
    if agent_data is not None:
        data_rows = len(agent_data) if isinstance(agent_data, pd.DataFrame) else 0
        columns = list(agent_data.columns) if isinstance(agent_data, pd.DataFrame) else []
        
        system_prompt += f"\n\n{'='*60}"
        system_prompt += f"\nYOU ARE A DATA-BACKED AGENT WITH ACCESS TO A DATASET"
        system_prompt += f"\n{'='*60}"
        system_prompt += f"\n\nDATASET INFO:"
        system_prompt += f"\n- The dataset has EXACTLY {data_rows} rows"
        system_prompt += f"\n- Columns available: {', '.join(columns)}"
        system_prompt += f"\n\nIMPORTANT RULES - YOU MUST FOLLOW THESE:"
        system_prompt += f"\n1. If a question requires information from the dataset, you MUST use the provided tools."
        system_prompt += f"\n2. NEVER answer from memory when a tool can be used."
        system_prompt += f"\n3. Use tools for ANY question about: prices, counts, categories, averages, listings, min/max values, or any data analysis."
        system_prompt += f"\n4. After calling a tool, explain the result in plain language."
        system_prompt += f"\n5. If asked 'how many', 'what is the cheapest', 'most expensive', 'average', 'list all', etc. - you MUST use tools."
        system_prompt += f"\n6. Available tools: get_row_count (for counts), query_data (for filtering/analysis), get_data_summary (for overview)"
        system_prompt += f"\n\nEXAMPLES OF WHEN TO USE TOOLS:"
        system_prompt += f"\n- 'How many items?' → Use get_row_count"
        system_prompt += f"\n- 'What is the cheapest item?' → Use query_data with 'cheapest' or 'lowest price'"
        system_prompt += f"\n- 'What is the average price?' → Use query_data with 'average price'"
        system_prompt += f"\n- 'List all items' → Use query_data with 'all items'"
        system_prompt += f"\n\nREMEMBER: If you don't use the tools, your answer will be WRONG. Always use tools for data questions."
    
    # Step 3.3: Add A2A instructions for agents without data (like Concierge Agent)
    elif agent_data is None and "concierge" in config.get("agent_id", "").lower():
        system_prompt += f"\n\n{'='*60}"
        system_prompt += f"\nCRITICAL: YOU DO NOT HAVE ACCESS TO MENU DATA"
        system_prompt += f"\n{'='*60}"
        system_prompt += f"\n\nIMPORTANT RULES FOR FOOD/MENU QUESTIONS:"
        system_prompt += f"\n1. You do NOT have access to menu data, food prices, or restaurant information."
        system_prompt += f"\n2. If a user asks about food, prices, menus, restaurant options, or dining:"
        system_prompt += f"\n   - You MUST contact the Menu Agent via A2A (Agent-to-Agent) communication"
        system_prompt += f"\n   - Do NOT answer directly or make up information"
        system_prompt += f"\n   - Do NOT guess prices or menu items"
        system_prompt += f"\n3. When you receive the Menu Agent's response, summarize it for the user in a helpful way."
        system_prompt += f"\n4. Example questions that require A2A call:"
        system_prompt += f"\n   - 'What food options are available?'"
        system_prompt += f"\n   - 'What are the prices?'"
        system_prompt += f"\n   - 'I'm staying nearby. What food options and prices are available?'"
        system_prompt += f"\n   - 'What's on the menu?'"
        system_prompt += f"\n   - 'Tell me about restaurant options'"
        system_prompt += f"\n\nREMEMBER: If you answer food questions without calling the Menu Agent, your answer will be WRONG."
    
    def llm_agent_logic(message: str, conversation_id: str) -> str:
        """LLM-powered agent logic with fallback to basic responses"""
        safe_print(f"[DEBUG] llm_agent_logic invoked | agent_id={config.get('agent_id')} | agent_data_present={agent_data is not None} | message='{message}'")
        
        # Step 3.2: Detect food/menu questions and call Menu Agent via A2A
        # This applies to agents without data (like Concierge Agent)
        if agent_data is None:
            food_keywords = ['food', 'menu', 'restaurant', 'dining', 'price', 'prices', 'dish', 'dishes', 
                           'meal', 'meals', 'eat', 'eating', 'order', 'ordering', 'available', 'options']
            is_food_question = any(keyword in message.lower() for keyword in food_keywords)
            safe_print(f"[DEBUG] Food question? {is_food_question} | message='{message}'")
            
            # Force A2A for concierge agent; also trigger on detected food questions
            if is_food_question or ("concierge" in config.get("agent_id", "").lower()):
                try:
                    safe_print(f"🍽️ Detected food question, calling Menu Agent via A2A...")
                    registry_url = config.get("registry_url")
                    menu_response = call_menu_agent_via_a2a(message, registry_url)
                    safe_print(f"📥 Raw response from Menu Agent: {str(menu_response)[:150]}...")
                    
                    # If we already have a clear menu response (contains prices/items), return it directly for demo reliability
                    menu_response_lower = str(menu_response).lower()
                    menu_keywords = ["burger", "salad", "fries", "steak", "$", "price", "menu items", "items are", "available", "menu has"]
                    if any(token in menu_response_lower for token in menu_keywords):
                        safe_print(f"[DEBUG] Menu response contains menu keywords, returning directly")
                        return f"Here are the menu details I got from the Menu Agent:\n\n{menu_response}"
                    
                    # Otherwise, summarize via LLM if available
                    if anthropic_client:
                        try:
                            summary_prompt = f"""The user asked: "{message}"

I contacted the Menu Agent and received this response:
{menu_response}

Please provide a helpful, concise summary of the menu information for the user. Be friendly and conversational."""
                            
                            summary_response = anthropic_client.messages.create(
                                model=config["model"],
                                max_tokens=500,
                                system=system_prompt,
                                messages=[{"role": "user", "content": summary_prompt}]
                            )
                            
                            # Extract summary text
                            summary_text = ""
                            for block in summary_response.content:
                                if hasattr(block, 'type') and getattr(block, 'type', None) == "text":
                                    summary_text += getattr(block, 'text', '')
                                elif hasattr(block, 'text'):
                                    summary_text += getattr(block, 'text', '')
                            
                            return summary_text.strip() if summary_text else menu_response
                        except Exception as e:
                            safe_print(f"⚠️ Error summarizing Menu Agent response: {e}")
                            return f"I contacted the Menu Agent for you. Here's what they said:\n\n{menu_response}"
                    # No LLM available, return Menu Agent response directly
                    return f"I contacted the Menu Agent for you. Here's what they said:\n\n{menu_response}"
                except Exception as e:
                    safe_print(f"❌ Error during A2A flow: {e}")
                    return f"I tried to contact the Menu Agent but hit an error: {e}"
        
        # If LLM is available, use it for intelligent responses
        if anthropic_client:
            try:
                # Add current time context if time-related query
                context_info = ""
                if any(time_word in message.lower() for time_word in ['time', 'date', 'when']):
                    context_info = f"\n\nCurrent time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                
                messages = [
                        {
                            "role": "user", 
                            "content": message
                        }
                    ]
                
                # Make initial API call with tools if available
                # Force tool use for data-related questions via system prompt
                data_keywords = ['employee', 'salary', 'department', 'hr dataset', 'how many', 'employees', 'workforce',
                                'menu', 'item', 'price', 'cheapest', 'expensive', 'cost', 'dish', 'food', 'restaurant']
                is_data_question = any(keyword in message.lower() for keyword in data_keywords)
                
                # Don't use tool_choice - rely on strong system prompt to force tool use
                # Anthropic API doesn't support "any" or "required" - only "auto", "none", or specific tool dict
                
                # Build API call parameters
                api_params = {
                    "model": config["model"],
                    "max_tokens": 1000,
                    "system": system_prompt + context_info,
                    "messages": messages
                }
                
                # Only add tools and tool_choice if tools are available
                if data_tools:
                    api_params["tools"] = data_tools
                    # Don't set tool_choice - let the model decide based on system prompt
                
                response = anthropic_client.messages.create(**api_params)
                
                # Handle tool use if present
                max_iterations = 5  # Prevent infinite loops
                iteration = 0
                
                while iteration < max_iterations and getattr(response, 'stop_reason', None) == "tool_use":
                    iteration += 1
                    
                    # Check if response contains tool use
                    tool_use_blocks = []
                    for block in response.content:
                        block_type = getattr(block, 'type', None) if hasattr(block, 'type') else None
                        if block_type == "tool_use":
                            tool_use_blocks.append(block)
                    
                    if not tool_use_blocks:
                        break
                    
                    # Add assistant message with tool use
                    messages.append({
                        "role": "assistant",
                        "content": response.content
                    })
                    
                    # Execute tools and add results
                    tool_results = []
                    for tool_block in tool_use_blocks:
                        tool_name = getattr(tool_block, 'name', '')
                        tool_input = getattr(tool_block, 'input', {})
                        tool_id = getattr(tool_block, 'id', f"tool_{iteration}")
                        
                        # Step 6.4: Log tool call request
                        safe_print(f"📞 Tool call request: {tool_name} with input: {tool_input}")
                        
                        tool_result = execute_data_tool(tool_name, tool_input, agent_data)
                        
                        # Step 6.4: Log tool result
                        safe_print(f"✅ Tool result returned: {str(tool_result)[:100]}...")
                        
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": str(tool_result)
                        })
                    
                    messages.append({
                        "role": "user",
                        "content": tool_results
                    })
                    
                    # Continue conversation with tool results
                    # Build API call parameters for follow-up
                    followup_params = {
                        "model": config["model"],
                        "max_tokens": 1000,
                        "system": system_prompt + context_info,
                        "messages": messages
                    }
                    
                    if data_tools:
                        followup_params["tools"] = data_tools
                    
                    response = anthropic_client.messages.create(**followup_params)
                
                # Extract final text response
                text_content = ""
                for block in response.content:
                    if hasattr(block, 'type') and getattr(block, 'type', None) == "text":
                        text_content += getattr(block, 'text', '')
                    elif hasattr(block, 'text'):  # Fallback for text blocks
                        text_content += getattr(block, 'text', '')
                
                if text_content:
                    return text_content.strip()
                else:
                    return "I processed your request but couldn't generate a text response."
                
            except Exception as e:
                print(f"❌ LLM Error: {e}")
                # Fall back to basic response
                return f"Sorry, I'm having trouble processing that right now. Error: {str(e)}"
        
        # Fallback to basic responses if LLM not available
        else:
            return _basic_fallback_response(message, config)
    
    return llm_agent_logic

def _basic_fallback_response(message: str, config: Dict[str, Any]) -> str:
    """Basic fallback responses when LLM is not available"""
    msg = message.lower().strip()
    
    # Handle greetings
    if any(greeting in msg for greeting in ['hello', 'hi', 'hey']):
        return f"Hello! I'm {config['agent_name']}, but I need an Anthropic API key to provide intelligent responses. Please set ANTHROPIC_API_KEY environment variable."
    
    # Handle time requests
    elif 'time' in msg:
        current_time = datetime.now().strftime("%H:%M:%S")
        return f"The current time is {current_time}."
    
    # Handle basic calculations
    elif any(op in message for op in ['+', '-', '*', '/', '=']):
        try:
            calculation = message.replace('x', '*').replace('X', '*').replace('=', '').strip()
            result = eval(calculation)
            return f"Calculation result: {calculation} = {result}"
        except:
            return "Sorry, I couldn't calculate that. Please check your expression."
    
    # Default fallback
    else:
        return f"I'm {config['agent_name']}, but I need an Anthropic API key to provide intelligent responses. Please set ANTHROPIC_API_KEY environment variable and restart me."

# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Main function to start the LLM-powered modular agent"""
    safe_print(f"🤖 Starting {AGENT_CONFIG['agent_name']}")
    safe_print(f"📝 Specialization: {AGENT_CONFIG['specialization']}")
    safe_print(f"🎯 Domain: {AGENT_CONFIG['domain']}")
    safe_print(f"🛠️ Capabilities: {', '.join(AGENT_CONFIG['expertise'])}")
    if AGENT_CONFIG['registry_url']:
        safe_print(f"🌐 Registry: {AGENT_CONFIG['registry_url']}")
    
    # Load attached data (if any)
    data_path = os.getenv("DATA_PATH")
    agent_data = None

    # Temporary debug line for deployment validation
    print(f"DEBUG DATA_PATH seen by agent: {os.getenv('DATA_PATH')}", flush=True)

    if data_path:
        agent_data = load_agent_data(data_path)

    AGENT_CONFIG["data"] = agent_data
    
    # Check for Anthropic API key
    if not AGENT_CONFIG.get("anthropic_api_key"):
        safe_print("⚠️ Warning: ANTHROPIC_API_KEY not found in environment variables")
        print("   The agent will use basic fallback responses only")
        print("   Set ANTHROPIC_API_KEY to enable LLM capabilities")
    else:
        safe_print(f"🧠 LLM Model: {AGENT_CONFIG['model']}")
    
    # Create the LLM-powered agent logic based on configuration
    agent_logic = create_llm_agent_logic(AGENT_CONFIG)
    
    # Create and start the NANDA agent
    nanda = NANDA(
        agent_id=AGENT_CONFIG["agent_id"],
        agent_logic=agent_logic,
        port=PORT,
        registry_url=AGENT_CONFIG["registry_url"],
        public_url=AGENT_CONFIG["public_url"],
        enable_telemetry=False
    )
    
    safe_print(f"🚀 Agent URL: http://localhost:{PORT}/a2a")
    safe_print("💡 Try these messages:")
    print("   - 'Hello there'")
    print("   - 'Tell me about yourself'")
    print("   - 'What time is it?'")
    print("   - 'How can you help with Ubuntu?'")
    print("   - 'Explain Python virtual environments'")
    print("   - '5 + 3'")
    safe_print("\n🛑 Press Ctrl+C to stop")
    
    # Start the agent
    nanda.start()

def create_custom_agent(agent_name, specialization, domain, expertise_list, port=6000, anthropic_api_key=None, registry_url=None):
    """
    Helper function to quickly create a custom LLM-powered agent with different config
    
    Example usage:
        create_custom_agent(
            agent_name="Data Scientist", 
            specialization="analytical and precise AI assistant",
            domain="data science",
            expertise_list=["data analysis", "statistics", "machine learning", "Python"],
            port=6001,
            anthropic_api_key="sk-ant-xxxxx"
        )
    """
    custom_config = AGENT_CONFIG.copy()
    custom_config.update({
        "agent_id": agent_name.lower().replace(" ", "-"),
        "agent_name": agent_name,
        "specialization": specialization,
        "domain": domain,
        "expertise": expertise_list,
        "registry_url": registry_url,
        "anthropic_api_key": anthropic_api_key or os.getenv("ANTHROPIC_API_KEY"),
        "system_prompt": f"""You are {agent_name}, a {specialization} working in the domain of {domain}. 

You are part of the NANDA (Network of Autonomous Distributed Agents) system. You can communicate with other agents and help users with various tasks.

Your capabilities include:
{chr(10).join([f"- {expertise}" for expertise in expertise_list])}

Always be helpful, accurate, and concise in your responses. If you're unsure about something, say so honestly.

When someone asks about yourself, mention that you're part of the NANDA agent network and can communicate with other agents using the @agent_name syntax."""
    })
    
    agent_logic = create_llm_agent_logic(custom_config)
    
    nanda = NANDA(
        agent_id=custom_config["agent_id"],
        agent_logic=agent_logic,
        port=port,
        registry_url=custom_config["registry_url"],
        enable_telemetry=False
    )
    
    safe_print(f"🤖 Starting custom LLM agent: {agent_name}")
    safe_print(f"🚀 Agent URL: http://localhost:{port}/a2a")
    nanda.start()

if __name__ == "__main__":
    main()
