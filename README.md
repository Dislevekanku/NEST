# NEST - NANDA Sandbox and Testbed

A production-ready framework for deploying and managing specialized AI agents with seamless agent-to-agent communication and intelligent discovery.

**NEST** (NANDA Sandbox and Testbed) is part of Project NANDA (Networked AI Agents in Decentralized Architecture) - a comprehensive ecosystem for intelligent agent deployment and coordination.

## Key Features

- **Intelligent Agents**: Deploy specialized AI agents powered by Claude LLM
- **A2A Communication**: Agents can find and communicate with each other using `@agent-id` syntax  
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
  "registry-url" \                # Registry URL 
  "port" \                        # Port number 
  "region" \                      # AWS region 
  "instance-type"                 # EC2 instance type 
```

**Example:**
```bash
bash scripts/aws-single-agent-deployment.sh \
  "furniture-expert" \
  "sk-ant-api03-..." \
  "Furniture Expert" \
  "furniture and interior design" \
  "knowledgeable furniture specialist" \
  "I help with furniture selection and interior design" \
  "furniture,interior design,decor" \
  "http://registry.chat39.com:6900" \
  "6000" \
  "us-east-1" \
  "t3.micro"
```

### Deploy Multiple Agents (10 per instance)

```bash
bash scripts/aws-multi-agent-deployment.sh \
  "your-api-key" \
  "scripts/agent_configs/group-01-business-and-finance-experts.json" \
  "http://registry.chat39.com:6900" \
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
│   │   └── registry_client.py          # Registry integration
│   ├── discovery/                      # Agent discovery system
│   └── telemetry/                      # Monitoring & metrics
├── examples/
│   ├── nanda_agent.py                  # Main agent implementation
│   └── agent_configs.py                # Agent personalities
├── scripts/
│   ├── aws-single-agent-deployment.sh     # Single agent deployment
│   ├── aws-multi-agent-deployment.sh      # Multi-agent deployment
│   ├── deploy-agent.sh                    # Deploy to existing server
│   └── agent_configs/                     # Agent configuration files
│       ├── 100-agents-config.json            # 100 agent personalities
│       └── group-*.json                      # Agent group configs
└── README.md
```

## Agent Communication

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

- AWS CLI configured with credentials
- Anthropic API key
- Python 3.8+ (for local development)

## Monitoring

Each deployed agent includes:
- **Health checks** on startup
- **Automatic registry registration**
- **Process management** with supervisor
- **Individual logs** for debugging
- **Performance metrics** collection

## Configuration

### Environment Variables

- `ANTHROPIC_API_KEY`: Your Claude API key
- `AGENT_ID`: Unique agent identifier  
- `AGENT_NAME`: Display name for the agent
- `REGISTRY_URL`: NANDA registry endpoint
- `PUBLIC_URL`: Agent's public URL for A2A communication
- `PORT`: Port number for the agent server

### Attached Data and `DATA_PATH`

NEST supports attaching a local dataset to an agent via the `DATA_PATH` environment variable. The agent will load this file on startup and expose it through its configuration.

- **Supported formats**: `.csv` (via pandas DataFrame) and `.json` (via Python `json`)
- **Where it is used**: `examples/nanda_agent.py` reads `DATA_PATH`, loads the file, and assigns it to `AGENT_CONFIG["data"]`

**Local development**

- **CSV example**:
  - Create a data file under `data/`, for example `data/hr.csv` (see `DATA_SETUP_INSTRUCTIONS.md` for a ready-made HR dataset).
  - Start the agent with `DATA_PATH` set:

```bash
# Linux / Mac
DATA_PATH=data/hr.csv python examples/nanda_agent.py

# Windows PowerShell
$env:DATA_PATH="data/hr.csv"; python examples/nanda_agent.py
```

When `DATA_PATH` is set, the agent will attempt to load the file and log whether loading succeeded; if loading fails or `DATA_PATH` is unset, the agent will continue without attached data.

**AWS deployment**

The single-agent deployment script accepts an optional **12th parameter** that becomes the `DATA_PATH` environment variable on the EC2 instance (see `DATA_PATH_HOOK_CHANGES.md` for details):

```bash
bash scripts/aws-single-agent-deployment.sh \
  "hr-agent" \
  "sk-ant-xxxxx" \
  "HR Assistant" \
  "human resources" \
  "HR specialist" \
  "I help with HR questions and employee data" \
  "HR,employee data,payroll,benefits" \
  "http://registry.chat39.com:6900" \
  "6000" \
  "us-east-1" \
  "t3.small" \
  "data/hr.csv"    # 12th argument: DATA_PATH passed through to the agent
```

On the EC2 host the user-data script exports:

```bash
export DATA_PATH='$DATA_PATH'
```

so the running agent sees the same path via `os.getenv("DATA_PATH")` and loads the attached dataset at startup.

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

### Test A2A Communication
```bash
curl -X POST http://agent-a-ip:{PORT}/a2a \
  -H "Content-Type: application/json" \
  -d '{"content":{"text":"@agent-b-id Please help with this task","type":"text"},"role":"user","conversation_id":"test123"}'
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