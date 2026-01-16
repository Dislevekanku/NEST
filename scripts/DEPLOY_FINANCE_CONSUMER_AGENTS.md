# Deploy Finance Feed Agent and Consumer Agent to AWS

This guide explains how to deploy both the Finance Feed Agent and Consumer Agent to AWS EC2 instances.

## Quick Start

### Prerequisites

1. **AWS CLI configured** with credentials
2. **Anthropic API Key** - Required for both agents
3. **Git Bash** (for Windows) or bash shell (Linux/Mac)

### Step 1: Set Your Anthropic API Key

**Windows PowerShell:**
```powershell
$env:ANTHROPIC_API_KEY='sk-ant-your-api-key-here'
```

**Linux/Mac/Git Bash:**
```bash
export ANTHROPIC_API_KEY='sk-ant-your-api-key-here'
```

### Step 2: Navigate to NEST Directory

```bash
cd NEST
```

### Step 3: Run Deployment Script

**Using Git Bash (Windows):**
```bash
bash scripts/deploy_finance_consumer_agents.sh \
  "sk-ant-your-api-key-here" \
  "http://registry.chat39.com:6900" \
  "us-east-1" \
  "t3.micro"
```

**Linux/Mac:**
```bash
bash scripts/deploy_finance_consumer_agents.sh \
  "sk-ant-your-api-key-here" \
  "http://registry.chat39.com:6900" \
  "us-east-1" \
  "t3.micro"
```

## What the Script Does

1. ✅ Creates security group with ports: 6000 (Finance A2A), 6001 (Consumer A2A), 8000 (Finance Data Facts)
2. ✅ Creates/uses SSH key pair
3. ✅ Launches Finance Feed Agent EC2 instance
   - Installs dependencies (yfinance, flask, flask-cors, python-a2a)
   - Runs `examples/finance_feed_agent.py`
   - Configures environment variables (AGENT_ID, PUBLIC_URL, DATA_SERVER_PORT, etc.)
4. ✅ Launches Consumer Agent EC2 instance
   - Installs dependencies (python-a2a, requests)
   - Runs `examples/data_consumer_agent.py`
   - Configures environment variables (AGENT_ID, REGISTRY_URL, FINANCE_FEED_AGENT_URL, etc.)
5. ✅ Waits for both instances to be ready
6. ✅ Provides test commands and connection details

## Agent Configuration

### Finance Feed Agent

- **Agent ID:** `finance-feed-agent`
- **A2A Port:** 6000
- **Data Facts Port:** 8000
- **Environment Variables:**
  - `AGENT_ID=finance-feed-agent`
  - `AGENT_NAME=Finance Feed Agent`
  - `REGISTRY_URL=<your-registry-url>`
  - `PUBLIC_URL=http://<public-ip>:6000`
  - `PORT=6000`
  - `DATA_SERVER_PORT=8000`
  - `ANTHROPIC_API_KEY=<your-key>`

### Consumer Agent

- **Agent ID:** `data-consumer-agent`
- **A2A Port:** 6001
- **Environment Variables:**
  - `AGENT_ID=data-consumer-agent`
  - `AGENT_NAME=Data Consumer Agent`
  - `REGISTRY_URL=<your-registry-url>`
  - `PUBLIC_URL=http://<public-ip>:6001`
  - `PORT=6001`
  - `FINANCE_FEED_AGENT_URL=http://<finance-feed-ip>:6000` (fallback URL)
  - `ANTHROPIC_API_KEY=<your-key>`

## Testing After Deployment

After deployment, the script will display the public IPs. Use these commands to test:

### Test Finance Feed Agent A2A

```bash
curl -X POST http://<FINANCE_PUBLIC_IP>:6000/a2a \
  -H 'Content-Type: application/json' \
  -d '{"content":{"text":"what are the current stock prices?","type":"text"},"role":"user","conversation_id":"test123"}'
```

### Test Data Facts Endpoint

```bash
curl http://<FINANCE_PUBLIC_IP>:8000/data_facts/public_stock_ticker.json
```

### Test Stock Data Endpoint

```bash
curl http://<FINANCE_PUBLIC_IP>:8000/stock_data
```

### Test Consumer Agent A2A

```bash
curl -X POST http://<CONSUMER_PUBLIC_IP>:6001/a2a \
  -H 'Content-Type: application/json' \
  -d '{"content":{"text":"ask finance agent about stock prices","type":"text"},"role":"user","conversation_id":"test123"}'
```

## SSH Access

### Finance Feed Agent

```bash
ssh -i nanda-finance-consumer-key.pem ubuntu@<FINANCE_PUBLIC_IP>
```

### Consumer Agent

```bash
ssh -i nanda-finance-consumer-key.pem ubuntu@<CONSUMER_PUBLIC_IP>
```

## View Logs

### Finance Feed Agent Logs

```bash
ssh -i nanda-finance-consumer-key.pem ubuntu@<FINANCE_PUBLIC_IP> 'tail -f /home/ubuntu/finance_agent.log'
```

### Consumer Agent Logs

```bash
ssh -i nanda-finance-consumer-key.pem ubuntu@<CONSUMER_PUBLIC_IP> 'tail -f /home/ubuntu/consumer_agent.log'
```

### Deployment Logs

```bash
# Finance Feed Agent deployment log
ssh -i nanda-finance-consumer-key.pem ubuntu@<FINANCE_PUBLIC_IP> 'cat /var/log/user-data-finance.log'

# Consumer Agent deployment log
ssh -i nanda-finance-consumer-key.pem ubuntu@<CONSUMER_PUBLIC_IP> 'cat /var/log/user-data-consumer.log'
```

## Verify Registry Registration

After deployment, check if the Finance Feed Agent registered with the registry:

```bash
# Query registry for finance-feed-agent
curl http://registry.chat39.com:6900/list | jq '.[] | select(.agent_id | contains("finance-feed"))'
```

You should see:
```json
{
  "agent_id": "finance-feed-agent-xxxxxx",
  "agent_url": "http://<FINANCE_PUBLIC_IP>:6000/a2a",
  "data_facts_url": "http://<FINANCE_PUBLIC_IP>:8000/data_facts/public_stock_ticker.json"
}
```

## Restart Agents

If you need to restart the agents:

### Finance Feed Agent

```bash
ssh -i nanda-finance-consumer-key.pem ubuntu@<FINANCE_PUBLIC_IP> << 'EOF'
cd /home/ubuntu/nanda-finance-agent
source env/bin/activate
pkill -f finance_feed_agent.py
nohup python3 examples/finance_feed_agent.py > /home/ubuntu/finance_agent.log 2>&1 &
EOF
```

### Consumer Agent

```bash
ssh -i nanda-finance-consumer-key.pem ubuntu@<CONSUMER_PUBLIC_IP> << 'EOF'
cd /home/ubuntu/nanda-consumer-agent
source env/bin/activate
pkill -f data_consumer_agent.py
nohup python3 examples/data_consumer_agent.py > /home/ubuntu/consumer_agent.log 2>&1 &
EOF
```

## Terminate Instances

To stop and delete the EC2 instances:

```bash
aws ec2 terminate-instances --region us-east-1 --instance-ids <FINANCE_INSTANCE_ID> <CONSUMER_INSTANCE_ID>
```

## Troubleshooting

### Agents Not Starting

1. Check deployment logs:
   ```bash
   ssh -i nanda-finance-consumer-key.pem ubuntu@<IP> 'cat /var/log/user-data-*.log'
   ```

2. Check agent logs:
   ```bash
   ssh -i nanda-finance-consumer-key.pem ubuntu@<IP> 'cat /home/ubuntu/*_agent.log'
   ```

3. Check if processes are running:
   ```bash
   ssh -i nanda-finance-consumer-key.pem ubuntu@<IP> 'ps aux | grep -E "finance_feed_agent|data_consumer_agent"'
   ```

### Port Not Accessible

1. Check security group rules:
   ```bash
   aws ec2 describe-security-groups --group-names nanda-finance-consumer-agents --region us-east-1
   ```

2. Verify ports are open (6000, 6001, 8000)

### Registry Not Found

If the Consumer Agent cannot find the Finance Feed Agent in the registry:

1. Verify Finance Feed Agent is registered:
   ```bash
   curl http://registry.chat39.com:6900/list | jq '.[] | select(.agent_id | contains("finance"))'
   ```

2. Check Finance Feed Agent logs for registration errors:
   ```bash
   ssh -i nanda-finance-consumer-key.pem ubuntu@<FINANCE_IP> 'grep -i "registry\|register" /home/ubuntu/finance_agent.log'
   ```

3. Consumer Agent can still use the fallback URL (`FINANCE_FEED_AGENT_URL`) if registry fails

## Next Steps

After successful deployment:

1. ✅ Test A2A communication between agents
2. ✅ Test Data Facts discovery and access
3. ✅ Verify registry registration includes `data_facts_url`
4. ✅ Test end-to-end flow: Consumer Agent → Registry → Data Facts → Dataset
