# NEST - NANDA Sandbox and Testbed

A production-ready framework for deploying and managing specialized AI agents with seamless agent-to-agent communication and intelligent discovery.

**NEST** (NANDA Sandbox and Testbed) is part of Project NANDA (Networked AI Agents in Decentralized Architecture) - a comprehensive ecosystem for intelligent agent deployment and coordination.

## Key Features

- **Intelligent Agents**: Deploy specialized AI agents powered by multiple LLM providers (Anthropic Claude, OpenAI GPT, Google Gemini)
- **Data-Backed Agents**: Attach CSV or JSON datasets to agents for intelligent data-driven responses
- **A2A Communication**: Agents can find and communicate with each other using `@agent-id` syntax  
- **MCP Integration**: Discover and use tools from MCP servers via Smithery and NANDA registries
- **Cloud Deployment**: One-command deployment to AWS EC2 with automatic setup
- **Index Integration**: Automatic registration with NANDA agent Index
- **Scalable**: Deploy single agents or 10+ agents per instance
- **Production Ready**: Robust error handling, health checks, and monitoring

## Quick Start

### Deploy a Single Agent

```bash
bash scripts/aws-single-agent-deployment.sh \
  "agent-id" \                    # Unique identifier
  "your-api-key" \                # Anthropic Claude API key
  "Agent Name" \                  # Display name
  "domain" \                      # Field of expertise
  "specialization" \              # Role description
  "description" \                 # Detailed agent description
  "capabilities" \                # Comma-separated capabilities
  "smithery-api-key" \            # Smithery API key (optional)
  "registry-url" \                # Agent registry URL (optional)
  "mcp-registry-url" \            # MCP registry URL (optional)
  "port" \                        # Port number (default: 6000)
  "region" \                      # AWS region (default: us-east-1)
  "instance-type" \               # EC2 instance type (default: t3.micro)
  "data-path"                     # Data file path (optional, 14th parameter)
```

**Example (Basic Agent):**
```bash
bash scripts/aws-single-agent-deployment.sh \
  "furniture-expert" \
  "sk-ant-api03-..." \
  "Furniture Expert" \
  "furniture and interior design" \
  "knowledgeable furniture specialist" \
  "I help with furniture selection and interior design" \
  "furniture,interior design,decor" \
  "smithery-key-xxxxx" \
  "http://registry.chat39.com:6900" \
  "https://your-mcp-registry.ngrok-free.app" \
  "6000" \
  "us-east-1" \
  "t3.micro"
```

**Example (Data-Backed Agent with HR Dataset):**
```bash
bash scripts/aws-single-agent-deployment.sh \
  "hr-assistant" \
  "sk-ant-api03-..." \
  "HR Assistant" \
  "human resources" \
  "HR data specialist" \
  "I help answer questions about employee data, salaries, and department information" \
  "HR,employee data,payroll,benefits" \
  "smithery-key-xxxxx" \
  "http://registry.chat39.com:6900" \
  "https://your-mcp-registry.ngrok-free.app" \
  "6000" \
  "us-east-1" \
  "t3.micro" \
  "data/hr.csv"    # 14th parameter: DATA_PATH for data-backed responses
```

### Deploy Multiple Agents (10 per instance)

```bash
bash scripts/aws-multi-agent-deployment.sh \
  "your-api-key" \
  "scripts/agent_configs/group-01-business-and-finance-experts.json" \
  "smithery-key-xxxxx" \
  "http://registry.chat39.com:6900" \
  "https://your-mcp-registry.ngrok-free.app" \
  "us-east-1" \
  "t3.xlarge"
```

## Architecture

```
NEST/
├── nanda_core/                        # Core framework
│   ├── core/
│   │   ├── adapter.py                  # Main NANDA adapter
│   │   ├── agent_bridge.py             # A2A communication
│   │   ├── mcp_client.py               # MCP client integration
│   │   └── mcp_registry.py             # MCP registry management
│   ├── llm/                            # LLM provider abstractions
│   │   ├── anthropic.py                # Anthropic Claude
│   │   ├── openai.py                   # OpenAI GPT
│   │   └── gemini.py                   # Google Gemini
│   ├── deployment/                     # Deployment utilities
│   └── telemetry/                      # Monitoring & metrics
├── examples/
│   ├── nanda_agent.py                  # Main agent implementation
│   │                                   # Supports data loading, tool generation
│   ├── customer_support/               # Customer support agent example
│   └── team_manager/                   # Team management agent example
├── scripts/
│   ├── aws-single-agent-deployment.sh  # Single agent deployment
│   ├── aws-multi-agent-deployment.sh   # Multi-agent deployment
│   └── agent_configs/                  # Agent configuration files
│       ├── 100-agents-config.json      # 100 agent personalities
│       └── group-*.json                # Agent group configs
├── data/                               # Sample datasets
│   ├── hr.csv                          # Sample HR dataset
│   └── README.md                       # Data directory docs
└── README.md
```

## Agent Communication

### A2A Communication

Agents can communicate with each other using the `@agent-id` syntax:

```bash
# Test A2A communication
curl -X POST http://agent-ip:{PORT}/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "content": {
      "text": "@other-agent-id Can you help with this task?",
      "type": "text"
    },
    "role": "user",
    "conversation_id": "test123"
  }'
```

### MCP (Model Context Protocol) Integration

Agents can discover and execute tools from MCP servers using the `#registry:server-name` syntax:

**Smithery MCP Servers:**

```bash
# Query Smithery registry servers
curl -X POST http://agent-ip:{PORT}/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "content": {
      "text": "#smithery:@{mcp_server_name} get current weather in NYC",
      "type": "text"
    },
    "role": "user",
    "conversation_id": "mcp-test"
  }'
```

**NANDA MCP Servers:**

```bash
# Query NANDA registry servers
curl -X POST http://agent-ip:{PORT}/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "content": {
      "text": "#nanda:nanda-points get my current points balance",
      "type": "text"
    },
    "role": "user",
    "conversation_id": "nanda-test"
  }'
```

The agent will automatically:

1. Discover the MCP server from the appropriate registry
2. Connect to the server and get available tools
3. Use Claude to intelligently select and execute the right tools
4. Return formatted results

## Available Agent Groups

Pre-configured agent groups for quick deployment:

- **Business & Finance**: Financial analysts, investment advisors, business strategists
- **Technology & Engineering**: Software engineers, DevOps specialists, AI researchers  
- **Creative & Design**: Graphic designers, content creators, brand strategists
- **Healthcare & Life Sciences**: Medical researchers, health informatics specialists
- **Education & Research**: Academic researchers, curriculum developers
- **Media & Entertainment**: Journalists, content producers, social media managers
- **Environmental & Sustainability**: Climate scientists, sustainability consultants
- **Social Services**: Community organizers, social workers, policy analysts
- **Sports & Recreation**: Fitness trainers, sports analysts, nutrition experts
- **Travel & Hospitality**: Travel planners, hotel managers, tour guides.

## Prerequisites

**For AWS Deployment:**
- AWS CLI configured with credentials
- AWS account with EC2 permissions

**For Local Development:**
- Python 3.8+
- Anthropic API key (or OpenAI/Gemini key if using those providers)
- Optional: pandas (for CSV support) - installed automatically via `pip install -e .`

## Monitoring

Each deployed agent includes:
- **Health checks** on startup
- **Automatic registry registration**
- **Process management** with supervisor
- **Individual logs** for debugging
- **Performance metrics** collection

## Configuration

### Environment Variables

**Required:**
- `ANTHROPIC_API_KEY`: Your Anthropic Claude API key (or OpenAI/Gemini key depending on provider)

**Agent Configuration:**
- `AGENT_ID`: Unique agent identifier  
- `AGENT_NAME`: Display name for the agent
- `AGENT_DOMAIN`: Primary field of expertise
- `AGENT_SPECIALIZATION`: Role description
- `AGENT_DESCRIPTION`: Detailed agent description
- `AGENT_CAPABILITIES`: Comma-separated capabilities

**Registry & Communication:**
- `REGISTRY_URL`: NANDA agent registry endpoint
- `MCP_REGISTRY_URL`: MCP registry URL for NANDA MCP servers
- `SMITHERY_API_KEY`: Smithery API key for MCP server access
- `PUBLIC_URL`: Agent's public URL for A2A communication
- `PORT`: Port number for the agent server (default: 6000)

**Data & LLM:**
- `DATA_PATH`: Path to attached dataset (CSV or JSON file, or S3 URL)
- `LLM_PROVIDER`: LLM provider to use - `anthropic` (default), `openai`, or `gemini`

### Attached Data and `DATA_PATH`

NEST supports attaching datasets to agents via the `DATA_PATH` environment variable, enabling **data-backed agents** that can answer questions using real data from CSV or JSON files.

#### Features

- **Supported formats**: `.csv` (loaded as pandas DataFrame) and `.json` (loaded as Python dict/list)
- **Automatic tool generation**: When data is attached, the agent automatically gets tools like `get_row_count`, `query_data`, and `get_data_summary`
- **Intelligent tool use**: The agent intelligently uses these tools when questions require data analysis
- **S3 support**: Can load data from S3 URLs (e.g., `s3://bucket/path/data.csv`)

#### Local Development

**CSV Example:**
```bash
# Linux / Mac
DATA_PATH=data/hr.csv python examples/nanda_agent.py

# Windows PowerShell
$env:DATA_PATH="data/hr.csv"; python examples/nanda_agent.py
```

**JSON Example:**
```bash
DATA_PATH=data/products.json python examples/nanda_agent.py
```

The agent will:
- Load the file on startup
- Log the data shape/structure
- Make data tools available for queries
- Continue normally if loading fails (graceful degradation)

#### AWS Deployment

The deployment script accepts `DATA_PATH` as the **14th parameter** (optional):

```bash
bash scripts/aws-single-agent-deployment.sh \
  "hr-assistant" \
  "sk-ant-xxxxx" \
  "HR Assistant" \
  "human resources" \
  "HR data specialist" \
  "I help answer questions about employee data" \
  "HR,employee data,payroll" \
  "smithery-key-xxxxx" \
  "http://registry.chat39.com:6900" \
  "https://mcp-registry.ngrok-free.app" \
  "6000" \
  "us-east-1" \
  "t3.micro" \
  "data/hr.csv"    # 14th parameter: DATA_PATH
```

**S3 Example:**
```bash
# ... same parameters ...
  "s3://my-bucket/hr-data.csv"    # Load from S3
```

The script will:
- Download S3 files automatically if path starts with `s3://`
- Export `DATA_PATH` as environment variable on EC2
- Agent loads data on startup and makes it available via tools

#### How It Works

1. **Data Loading**: Agent reads `DATA_PATH` from environment on startup
2. **Tool Creation**: If data is loaded, agent automatically creates data query tools
3. **Intelligent Responses**: When users ask data-related questions, agent uses tools to query the dataset
4. **Transparent**: Agent explains results in natural language after tool execution

#### Example Use Cases

- **HR Agent**: Answer questions about employee data, salaries, departments
- **Product Catalog Agent**: Query product information, prices, availability
- **Knowledge Base Agent**: Search through structured knowledge data
- **Analytics Agent**: Perform data analysis and generate insights

See `DATA_SETUP_INSTRUCTIONS.md` for sample datasets and setup guides.

### Agent Personality Configuration

Agents are configured with:
- **Domain**: Primary area of expertise
- **Specialization**: Specific role and personality
- **Description**: Detailed background for system prompt
- **Capabilities**: List of specific skills and knowledge areas

## Testing

### Test Single Agent
```bash
curl -X POST http://agent-ip:{PORT}/a2a \
  -H "Content-Type: application/json" \
  -d '{"content":{"text":"Hello! What can you help me with?","type":"text"},"role":"user","conversation_id":"test123"}'
```

### Test Data-Backed Agent
```bash
# Ask a question that requires data
curl -X POST http://agent-ip:{PORT}/a2a \
  -H "Content-Type: application/json" \
  -d '{"content":{"text":"How many employees are in the Engineering department?","type":"text"},"role":"user","conversation_id":"test123"}'
```

The agent will automatically use data tools to query the attached dataset and return accurate results.

### Test A2A Communication
```bash
curl -X POST http://agent-a-ip:{PORT}/a2a \
  -H "Content-Type: application/json" \
  -d '{"content":{"text":"@agent-b-id Please help with this task","type":"text"},"role":"user","conversation_id":"test123"}'
```

### Test MCP Tool Access
```bash
# Query Smithery MCP server
curl -X POST http://agent-ip:{PORT}/a2a \
  -H "Content-Type: application/json" \
  -d '{"content":{"text":"#smithery:@weather-server get current weather in NYC","type":"text"},"role":"user","conversation_id":"test123"}'
```

## Production Deployment

For production use:

1. **Single Agent**: Use `t3.micro` for cost-effective single agent deployment
2. **Multi-Agent**: Use `t3.xlarge` or larger for 10+ agents per instance  
3. **High Availability**: Deploy across multiple AWS regions
4. **Monitoring**: Enable CloudWatch logs and metrics
5. **Security**: Use proper security groups and VPC configuration

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## Support

For issues and questions:
- Create an issue in this repository
- Check the documentation in `/scripts/README.md`
- Review example configurations in `/scripts/`

---

**Built by Project NANDA**  
[Visit Project NANDA](https://github.com/projnanda) | [NEST Repository](https://github.com/projnanda/NEST)