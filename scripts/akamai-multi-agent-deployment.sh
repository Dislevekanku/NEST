#!/bin/bash

# CONFIGURABLE Akamai Connected Cloud (Linode) Multi-Agent Deployment Script
# This script creates a Linode instance and deploys multiple fully configurable modular NANDA agents
# Usage: bash akamai-multi-agent-deployment.sh <ANTHROPIC_API_KEY> <AGENT_CONFIG_JSON> [REGISTRY_URL] [REGION] [INSTANCE_TYPE] [ROOT_PASSWORD]

set -e

# Parse arguments
ANTHROPIC_API_KEY="$1"
AGENT_CONFIG_JSON="$2"
REGISTRY_URL="${3:-http://registry.chat39.com:6900}"
REGION="${4:-us-east}"
INSTANCE_TYPE="${5:-g6-standard-2}"  # 4GB for multiple agents
ROOT_PASSWORD="${6:-}"

# Validation
if [ -z "$ANTHROPIC_API_KEY" ] || [ -z "$AGENT_CONFIG_JSON" ]; then
    echo "❌ Usage: $0 <ANTHROPIC_API_KEY> <AGENT_CONFIG_JSON> [REGISTRY_URL] [REGION] [INSTANCE_TYPE] [ROOT_PASSWORD]"
    echo ""
    echo "Example:"
    echo "  $0 sk-ant-xxxxx ./scripts/agent_configs/group-01-business-and-finance-experts.json \"http://registry.chat39.com:6900\" us-east g6-standard-2 \"SecurePassword123!\""
    echo ""
    echo "Parameters:"
    echo "  ANTHROPIC_API_KEY: Your Anthropic API key"
    echo "  AGENT_CONFIG_JSON: Path to JSON file or JSON string with agent configurations"
    echo "  REGISTRY_URL: Registry URL for agent discovery (default: http://registry.chat39.com:6900)"
    echo "  REGION: Linode region (default: us-east)"
    echo "  INSTANCE_TYPE: Linode plan type (default: g6-standard-2 for 4GB RAM)"
    echo "  ROOT_PASSWORD: Root password for the instance (will be generated if not provided)"
    echo ""
    echo "Common Linode regions: us-east, us-west, eu-west, ap-south"
    echo "Common instance types: g6-standard-1 (2GB), g6-standard-2 (4GB), g6-standard-4 (8GB)"
    exit 1
fi

# Parse and validate agent config
if [ -f "$AGENT_CONFIG_JSON" ]; then
    AGENTS_JSON=$(cat "$AGENT_CONFIG_JSON")
else
    AGENTS_JSON="$AGENT_CONFIG_JSON"
fi

AGENT_COUNT=$(echo "$AGENTS_JSON" | python3 -c "import json, sys; print(len(json.load(sys.stdin)))")
echo "Agents to deploy: $AGENT_COUNT"

# Validate instance type for agent count
if [ "$AGENT_COUNT" -gt 5 ] && [ "$INSTANCE_TYPE" = "g6-standard-1" ]; then
    echo "⚠️  WARNING: g6-standard-1 (2GB) may be insufficient for $AGENT_COUNT agents. Consider g6-standard-2 (4GB) or larger."
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Validate port uniqueness
echo "Validating port configuration..."
DUPLICATE_PORTS=$(echo "$AGENTS_JSON" | python3 -c "
import json, sys
from collections import Counter
agents = json.load(sys.stdin)
ports = [agent['port'] for agent in agents]
duplicates = [port for port, count in Counter(ports).items() if count > 1]
if duplicates:
    print(' '.join(map(str, duplicates)))
    sys.exit(1)
")

if [ $? -eq 1 ]; then
    echo "❌ Duplicate ports found: $DUPLICATE_PORTS"
    exit 1
fi

# Generate secure password if not provided
if [ -z "$ROOT_PASSWORD" ]; then
    ROOT_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
    echo "🔑 Generated root password: $ROOT_PASSWORD"
fi

# Configuration
FIREWALL_LABEL="nanda-nest-multi-agents"
SSH_KEY_LABEL="nanda-multi-agent-key"
IMAGE_ID="linode/ubuntu25.04"  # Ubuntu 25.04 LTS
DEPLOYMENT_ID=$(date +%Y%m%d-%H%M%S)

echo "🚀 Configurable Akamai Connected Cloud (Linode) Multi-Agent Deployment"
echo "======================================================================"
echo "Deployment ID: $DEPLOYMENT_ID"
echo "Agent Count: $AGENT_COUNT"
echo "Registry URL: $REGISTRY_URL"
echo "Region: $REGION"
echo "Instance Type: $INSTANCE_TYPE"
echo ""

# Check Linode CLI credentials
echo "[1/6] Checking Linode CLI credentials..."
if ! linode-cli --version >/dev/null 2>&1; then
    echo "❌ Linode CLI not installed. Install it: https://techdocs.akamai.com/cloud-computing/docs/install-and-configure-the-cli"
    exit 1
fi

CONFIG="$HOME/.config/linode-cli"
if [ ! -s "$CONFIG" ] && [ -z "$LINODE_CLI_TOKEN" ]; then
    echo "❌ Linode CLI not configured. Run 'linode-cli configure' first."
    exit 1
fi
echo "✅ Linode CLI credentials valid"

# Setup firewall
echo "[2/6] Setting up firewall..."
FIREWALL_ID=$(linode-cli firewalls list --text --no-headers --format="id,label" | grep "$FIREWALL_LABEL" | cut -f1 || echo "")
    # Get agent ports for firewall rules
AGENT_PORTS=$(echo "$AGENTS_JSON" | python3 -c "
import json, sys
agents = json.load(sys.stdin)
ports = [str(agent['port']) for agent in agents]
print(','.join(ports))
")
    
# Create inbound rules JSON for SSH and all agent ports
INBOUND_RULES='[{"protocol": "TCP", "ports": "22", "addresses": {"ipv4": ["0.0.0.0/0"]}, "action": "ACCEPT"}'
IFS=',' read -ra PORTS <<< "$AGENT_PORTS"
for PORT in "${PORTS[@]}"; do
    INBOUND_RULES+=', {"protocol": "TCP", "ports": "'$PORT'", "addresses": {"ipv4": ["0.0.0.0/0"]}, "action": "ACCEPT"}'
done
INBOUND_RULES+=']'

if [ -z "$FIREWALL_ID" ]; then
    echo "Creating firewall..."
    
    linode-cli firewalls create \
        --label "$FIREWALL_LABEL" \
        --rules.inbound_policy DROP \
        --rules.outbound_policy ACCEPT \
        --rules.inbound "$INBOUND_RULES"

    FIREWALL_ID=$(linode-cli firewalls list --text --no-headers --format="id,label" | grep "$FIREWALL_LABEL" | cut -f1 || echo "")
    echo "✅ Created firewall with ports: SSH, $AGENT_PORTS"
else
    echo "Using existing firewall..."
    # Add any missing agent ports
    linode-cli firewalls rules-update "$FIREWALL_ID" --inbound "$INBOUND_RULES" >/dev/null 2>&1
fi

echo "✅ Firewall: $FIREWALL_ID - $FIREWALL_LABEL"

# Setup SSH key
echo "[3/6] Setting up SSH key..."
if [ ! -f "${SSH_KEY_LABEL}.pub" ]; then
    echo "Generating SSH key pair..."
    ssh-keygen -t rsa -b 4096 -f "$SSH_KEY_LABEL" -N "" -C "nanda-multi-agent-$DEPLOYMENT_ID"
fi

# Create user data script with supervisor configuration
echo "[4/6] Creating improved user data script..."
cat > "user_data_multi_${DEPLOYMENT_ID}.sh" << EOF
#!/bin/bash
exec > /var/log/user-data.log 2>&1

echo "=== NANDA Multi-Agent Setup Started: $DEPLOYMENT_ID ==="
date

# Update system and install dependencies
apt-get update -y
apt-get install -y python3 python3-venv python3-pip git curl jq supervisor

# Create ubuntu user (Linode uses root by default)
useradd -m -s /bin/bash ubuntu
mkdir -p /home/ubuntu/.ssh
cp /root/.ssh/authorized_keys /home/ubuntu/.ssh/authorized_keys 2>/dev/null || true
chown -R ubuntu:ubuntu /home/ubuntu/.ssh
chmod 700 /home/ubuntu/.ssh
chmod 600 /home/ubuntu/.ssh/authorized_keys 2>/dev/null || true

# Setup project as ubuntu user
cd /home/ubuntu
sudo -u ubuntu git clone https://github.com/projnanda/NEST.git nanda-multi-agents-$DEPLOYMENT_ID
cd nanda-multi-agents-$DEPLOYMENT_ID

# Create virtual environment and install
sudo -u ubuntu python3 -m venv env
sudo -u ubuntu bash -c "source env/bin/activate && pip install --upgrade pip && pip install -e . && pip install anthropic"

# Get public IP using Linode metadata service
echo "Getting public IP address..."
for attempt in {1..10}; do
    # Linode metadata service
    TOKEN=\$(curl -s -X PUT -H "Metadata-Token-Expiry-Seconds: 3600" http://169.254.169.254/v1/token 2>/dev/null)
    if [ -n "\$TOKEN" ]; then
        NETWORK_INFO=\$(curl -s --connect-timeout 5 --max-time 10 -H "Metadata-Token: \$TOKEN" http://169.254.169.254/v1/network 2>/dev/null)
        # Extract IPv4 public IP from response like "ipv4.public: 45.79.145.23/32 ipv6.link_local: ..."
        PUBLIC_IP=\$(echo "\$NETWORK_INFO" | grep -o 'ipv4\\.public: [0-9]*\\.[0-9]*\\.[0-9]*\\.[0-9]*' | cut -d' ' -f2 | cut -d'/' -f1)
    fi
    
    # Fallback to external service if metadata service fails
    if [ -z "\$PUBLIC_IP" ]; then
        PUBLIC_IP=\$(curl -s --connect-timeout 5 --max-time 10 https://ipinfo.io/ip 2>/dev/null)
    fi
    
    if [ -n "\$PUBLIC_IP" ] && [[ \$PUBLIC_IP =~ ^[0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+\$ ]]; then
        echo "Retrieved public IP: \$PUBLIC_IP"
        break
    fi
    echo "Attempt \$attempt failed, retrying..."
    sleep 3
done

if [ -z "\$PUBLIC_IP" ]; then
    echo "ERROR: Could not retrieve public IP after 10 attempts"
    exit 1
fi

# Save agent configuration
cat > /tmp/agents_config.json << 'AGENTS_EOF'
$AGENTS_JSON
AGENTS_EOF

# Create supervisor configuration for each agent
echo "Creating supervisor configurations..."
mkdir -p /etc/supervisor/conf.d

while IFS= read -r agent_config; do
    AGENT_ID=\$(echo "\$agent_config" | jq -r '.agent_id')
    AGENT_NAME=\$(echo "\$agent_config" | jq -r '.agent_name')
    DOMAIN=\$(echo "\$agent_config" | jq -r '.domain')
    SPECIALIZATION=\$(echo "\$agent_config" | jq -r '.specialization')
    DESCRIPTION=\$(echo "\$agent_config" | jq -r '.description')
    CAPABILITIES=\$(echo "\$agent_config" | jq -r '.capabilities')
    PORT=\$(echo "\$agent_config" | jq -r '.port')
    
    echo "Configuring supervisor for agent: \$AGENT_ID"
    
    # Create supervisor configuration file
    cat > "/etc/supervisor/conf.d/agent_\$AGENT_ID.conf" << SUPERVISOR_EOF
[program:agent_\$AGENT_ID]
command=/home/ubuntu/nanda-multi-agents-$DEPLOYMENT_ID/env/bin/python examples/nanda_agent.py
directory=/home/ubuntu/nanda-multi-agents-$DEPLOYMENT_ID
user=ubuntu
autostart=true
autorestart=true
startretries=3
stderr_logfile=/var/log/agent_\$AGENT_ID.err.log
stdout_logfile=/var/log/agent_\$AGENT_ID.out.log
environment=
    ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY",
    AGENT_ID="\$AGENT_ID",
    AGENT_NAME="\$AGENT_NAME",
    AGENT_DOMAIN="\$DOMAIN",
    AGENT_SPECIALIZATION="\$SPECIALIZATION",
    AGENT_DESCRIPTION="\$DESCRIPTION",
    AGENT_CAPABILITIES="\$CAPABILITIES",
    REGISTRY_URL="$REGISTRY_URL",
    PUBLIC_URL="http://\$PUBLIC_IP:\$PORT",
    PORT="\$PORT"

SUPERVISOR_EOF

    echo "✅ Supervisor config created for agent \$AGENT_ID on port \$PORT"
    
done < <(cat /tmp/agents_config.json | jq -c '.[]')

# Start supervisor and wait for all agents
echo "Starting supervisor..."
systemctl enable supervisor
systemctl start supervisor
supervisorctl reread
supervisorctl update

# Wait for all agents to start
echo "Waiting for all agents to start..."
sleep 30

# Verify all agents are running
echo "Verifying agent status..."
supervisorctl status

echo "=== NANDA Multi-Agent Setup Complete: $DEPLOYMENT_ID ==="
echo "All agents managed by supervisor on: \$PUBLIC_IP"
EOF


echo "[5/6] Running Linode instance..."
# Check if instance already exists
INSTANCE_ID=$(linode-cli linodes list --label "nanda-multi-agent-$DEPLOYMENT_ID" --text --no-headers --format="id" | head -n1)
if [ ! -n "$INSTANCE_ID" ]; then
    # Launch Linode instance
    INSTANCE_ID=$(linode-cli linodes create \
        --type "$INSTANCE_TYPE" \
        --region "$REGION" \
        --image "$IMAGE_ID" \
        --label "nanda-multi-agent-$DEPLOYMENT_ID" \
        --tags "NANDA-NEST-Multi" \
        --root_pass "$ROOT_PASSWORD" \
        --authorized_keys "$(cat ${SSH_KEY_LABEL}.pub)" \
        --firewall_id "$FIREWALL_ID" \
        --text --no-headers --format="id")
fi
echo "✅ Instance id: $INSTANCE_ID"

# Wait for instance to be running
echo "Waiting for instance to be running..."
while true; do
    STATUS=$(linode-cli linodes view "$INSTANCE_ID" --text --no-headers --format="status")
    if [ "$STATUS" = "running" ]; then
        break
    fi
    echo "Instance status: $STATUS, waiting..."
    sleep 10
done

# Get public IP
PUBLIC_IP=$(linode-cli linodes view "$INSTANCE_ID" --text --no-headers --format="ipv4")
echo "Public IP: $PUBLIC_IP"

echo "[6/6] Deploying multi-agent system (this process may take several minutes)..."
# Copy the user data script and execute it
scp -i "$SSH_KEY_LABEL" -o StrictHostKeyChecking=no "user_data_multi_${DEPLOYMENT_ID}.sh" "root@$PUBLIC_IP:/tmp/"
ssh -i "$SSH_KEY_LABEL" -o StrictHostKeyChecking=no "root@$PUBLIC_IP" "chmod +x /tmp/user_data_multi_${DEPLOYMENT_ID}.sh && /tmp/user_data_multi_${DEPLOYMENT_ID}.sh"

# Cleanup
rm "user_data_multi_${DEPLOYMENT_ID}.sh"

# Health check all agents
echo ""
echo "🔍 Performing health checks..."
echo "$AGENTS_JSON" | python3 -c "
import json, sys
try:
    import requests
    agents = json.load(sys.stdin)
    for agent in agents:
        url = f'http://$PUBLIC_IP:{agent[\"port\"]}/health'
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f'✅ {agent[\"agent_id\"]}: Healthy')
            else:
                print(f'⚠️  {agent[\"agent_id\"]}: HTTP {response.status_code}')
        except Exception as e:
            print(f'❌ {agent[\"agent_id\"]}: {str(e)}')
except ImportError:
    print('Health check skipped (requests not available)')
" 2>/dev/null || echo "Health check skipped (requests not available)"

echo ""
echo "🎉 NANDA Multi-Agent Deployment Complete!"
echo "=========================================="
echo "Deployment ID: $DEPLOYMENT_ID"
echo "Instance ID: $INSTANCE_ID"
echo "Public IP: $PUBLIC_IP"
echo "Root Password: $ROOT_PASSWORD"

# Display agent URLs
echo ""
echo "🤖 Agent URLs:"
echo "$AGENTS_JSON" | python3 -c "
import json, sys
agents = json.load(sys.stdin)
for agent in agents:
    print(f\"  {agent['agent_id']}: http://$PUBLIC_IP:{agent['port']}/a2a\")
"

# Get actual agent IDs with hex suffixes from logs
echo ""
echo "Getting actual agent IDs (with hex suffixes)..."
ACTUAL_AGENT_IDS=""
sleep 10
for attempt in {1..3}; do
    ACTUAL_AGENT_IDS=$(ssh -i "${SSH_KEY_LABEL}" -o StrictHostKeyChecking=no ubuntu@$PUBLIC_IP \
        "grep 'Generated agent_id:' /var/log/agent_*.out.log 2>/dev/null | cut -d':' -f3 | tr -d ' '" 2>/dev/null || echo "")
    if [ -n "$ACTUAL_AGENT_IDS" ]; then
        break
    fi
    echo "Attempt $attempt: Waiting for agent logs..."
    sleep 5
done

if [ -n "$ACTUAL_AGENT_IDS" ]; then
    echo ""
    echo "🤖 Actual Agent IDs for A2A Communication:"
    echo "$ACTUAL_AGENT_IDS" | while read -r agent_id; do
        if [ -n "$agent_id" ]; then
            echo "  @$agent_id"
        fi
    done
    echo ""
    echo "📞 Use these in A2A messages:"
    echo "  Example: @[agent-id] your message here"
else
    echo ""
    echo "⚠️  Could not retrieve actual agent IDs from logs."
    echo "📞 Agent IDs will be: [base-id]-[6-char-hex]"
fi

echo ""
echo "🧪 Test an agent (direct communication):"
FIRST_PORT=$(echo "$AGENTS_JSON" | python3 -c "import json, sys; agents = json.load(sys.stdin); print(agents[0]['port']) if agents else print('6000')")
echo "curl -X POST http://$PUBLIC_IP:$FIRST_PORT/a2a \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -d '{\"content\":{\"text\":\"Hello! What can you help me with?\",\"type\":\"text\"},\"role\":\"user\",\"conversation_id\":\"test123\"}'"

echo ""
echo "🔐 SSH Access:"
echo "ssh -i ${SSH_KEY_LABEL} ubuntu@$PUBLIC_IP"
echo "ssh -i ${SSH_KEY_LABEL} root@$PUBLIC_IP"

echo ""
echo "📊 Monitor agents:"
echo "ssh -i ${SSH_KEY_LABEL} root@$PUBLIC_IP 'supervisorctl status'"

echo ""
echo "🔄 Restart all agents:"
echo "ssh -i ${SSH_KEY_LABEL} root@$PUBLIC_IP 'supervisorctl restart all'"

echo ""
echo "🛑 To terminate:"
echo "linode-cli linodes delete $INSTANCE_ID"