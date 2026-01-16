#!/bin/bash

# Deploy Finance Feed Agent and Consumer Agent to AWS EC2
# This script deploys both agents to separate EC2 instances

set -e

# Parse arguments
ANTHROPIC_API_KEY="$1"
REGISTRY_URL="${2:-http://registry.chat39.com:6900}"
REGION="${3:-us-east-1}"
INSTANCE_TYPE="${4:-t3.micro}"

# Validate inputs
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "❌ Usage: $0 <ANTHROPIC_API_KEY> [REGISTRY_URL] [REGION] [INSTANCE_TYPE]"
    echo ""
    echo "Example:"
    echo "  $0 sk-ant-xxxxx \"http://registry.chat39.com:6900\" us-east-1 t3.micro"
    exit 1
fi

echo "🚀 Deploying Finance Feed Agent and Consumer Agent to AWS"
echo "=========================================================="
echo "Registry URL: $REGISTRY_URL"
echo "Region: $REGION"
echo "Instance Type: $INSTANCE_TYPE"
echo ""

# Configuration
SECURITY_GROUP_NAME="nanda-finance-consumer-agents"
SECURITY_GROUP_ID="${SECURITY_GROUP_ID:-}"  # Can be provided via environment variable
KEY_NAME="nanda-finance-consumer-key"
AMI_ID="ami-0866a3c8686eaeeba"  # Ubuntu 22.04 LTS
DEPLOYMENT_ID=$(date +%Y%m%d-%H%M%S)

# Check AWS credentials
echo "[1/7] Checking AWS credentials..."
if ! aws sts get-caller-identity >/dev/null 2>&1; then
    echo "⚠️  Warning: AWS credentials check failed, but continuing anyway..."
    echo "   (Credentials may still work for EC2 operations)"
else
    echo "✅ AWS credentials valid"
fi

# Setup security group
echo "[2/7] Setting up security group..."
# If SECURITY_GROUP_ID is provided via environment variable, use it
if [ -n "$SECURITY_GROUP_ID" ]; then
    echo "✅ Using provided security group: $SECURITY_GROUP_ID"
else
    # Try to find existing security group by name, or use default
if aws ec2 describe-security-groups --group-names "$SECURITY_GROUP_NAME" --region "$REGION" >/dev/null 2>&1; then
    SECURITY_GROUP_ID=$(aws ec2 describe-security-groups \
        --group-names "$SECURITY_GROUP_NAME" \
        --region "$REGION" \
        --query 'SecurityGroups[0].GroupId' \
        --output text 2>/dev/null || echo "")
fi

# If not found, try to create it (may fail if no permissions)
if [ -z "$SECURITY_GROUP_ID" ]; then
    if aws ec2 create-security-group \
        --group-name "$SECURITY_GROUP_NAME" \
        --description "Security group for Finance Feed and Consumer agents" \
        --region "$REGION" \
        --query 'GroupId' \
        --output text 2>/dev/null > /tmp/sg_id; then
        SECURITY_GROUP_ID=$(cat /tmp/sg_id)
        rm /tmp/sg_id
        
        # Open SSH port (may also fail if no permissions)
        aws ec2 authorize-security-group-ingress \
            --group-id "$SECURITY_GROUP_ID" \
            --protocol tcp \
            --port 22 \
            --cidr 0.0.0.0/0 \
            --region "$REGION" 2>/dev/null || echo "⚠️  Could not authorize SSH port (may already be open)"
    else
        echo "⚠️  Could not create or find security group. Trying default security group..."
        # Try to get default security group (last resort)
        SECURITY_GROUP_ID=$(aws ec2 describe-security-groups \
            --filters "Name=group-name,Values=default" \
            --region "$REGION" \
            --query 'SecurityGroups[0].GroupId' \
            --output text 2>/dev/null || echo "")
        
        if [ -z "$SECURITY_GROUP_ID" ]; then
            echo "❌ Could not determine security group."
            echo ""
            echo "Please provide SECURITY_GROUP_ID environment variable:"
            echo "   export SECURITY_GROUP_ID='sg-xxxxxxxxxxxxx'"
            echo "   # Then run the deployment script again"
            echo ""
            echo "Or ask your AWS administrator to:"
            echo "   1. Create a security group named '$SECURITY_GROUP_NAME'"
            echo "   2. Open ports: 22 (SSH), 6000, 6001, 8000"
            echo "   3. Provide you with the security group ID"
            exit 1
        fi
        echo "⚠️  Using default security group: $SECURITY_GROUP_ID"
        echo "   Make sure ports 22, 6000, 6001, and 8000 are open!"
    fi
    fi
fi

# Open ports for both agents
# Finance Feed Agent: 6000 (A2A), 8000 (Data Facts)
# Consumer Agent: 6001 (A2A)
for PORT in 6000 6001 8000; do
    aws ec2 authorize-security-group-ingress \
        --group-id "$SECURITY_GROUP_ID" \
        --protocol tcp \
        --port "$PORT" \
        --cidr 0.0.0.0/0 \
        --region "$REGION" 2>/dev/null || echo "Port $PORT already open"
done

echo "✅ Security group: $SECURITY_GROUP_ID"

# Setup key pair
echo "[3/7] Setting up key pair..."
if [ ! -f "${KEY_NAME}.pem" ]; then
    echo "Creating key pair..."
    aws ec2 create-key-pair \
        --key-name "$KEY_NAME" \
        --region "$REGION" \
        --query 'KeyMaterial' \
        --output text > "${KEY_NAME}.pem"
    chmod 600 "${KEY_NAME}.pem"
fi
echo "✅ Key pair: $KEY_NAME"

# =============================================================================
# DEPLOY FINANCE FEED AGENT
# =============================================================================

echo "[4/7] Creating Finance Feed Agent deployment script..."

cat > "user_data_finance_feed_${DEPLOYMENT_ID}.sh" << 'FINANCE_EOF'
#!/bin/bash
exec > /var/log/user-data-finance.log 2>&1

echo "=== Finance Feed Agent Setup Started ==="
date

# Update system and install dependencies
apt-get update -y
apt-get install -y python3 python3-venv python3-pip git curl unzip

# Setup project
cd /home/ubuntu
sudo -u ubuntu git clone https://github.com/projnanda/NEST.git nanda-finance-agent
cd nanda-finance-agent
# Try multiple branches to find the files
sudo -u ubuntu git checkout data-path || sudo -u ubuntu git checkout main || sudo -u ubuntu git checkout feature/mcp-tooling || sudo -u ubuntu git checkout master || true
# Verify files exist
if [ ! -f "examples/finance_feed_agent.py" ]; then
    echo "WARNING: finance_feed_agent.py not found. Trying to find it..."
    sudo -u ubuntu find . -name "finance_feed_agent.py" -type f 2>/dev/null | head -5
    # Try checking out all branches
    for branch in $(sudo -u ubuntu git branch -a | grep -v HEAD | sed 's|remotes/origin/||' | sort -u); do
        echo "Checking branch: $branch"
        sudo -u ubuntu git checkout "$branch" 2>/dev/null && break || continue
    done
fi
cd ..
cd nanda-finance-agent

# Create virtual environment
sudo -u ubuntu python3 -m venv env
sudo -u ubuntu bash -c "source env/bin/activate && pip install --upgrade pip && pip install -e . && pip install anthropic yfinance flask flask-cors python-a2a requests"

# Get public IP
echo "Getting public IP address..."
for attempt in {1..5}; do
    TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600" --connect-timeout 5 --max-time 10)
    if [ -n "$TOKEN" ]; then
        PUBLIC_IP=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" --connect-timeout 5 --max-time 10 http://169.254.169.254/latest/meta-data/public-ipv4)
        if [ -n "$PUBLIC_IP" ] && [[ $PUBLIC_IP =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
            echo "Retrieved public IP: $PUBLIC_IP"
            break
        fi
    fi
    echo "Attempt $attempt failed, retrying..."
    sleep 3
done

if [ -z "$PUBLIC_IP" ]; then
    echo "ERROR: Could not retrieve public IP"
    exit 1
fi

# Set environment variables
export AGENT_ID='finance-feed-agent'
export AGENT_NAME='Finance Feed Agent'
export REGISTRY_URL='REGISTRY_URL_PLACEHOLDER'
export PUBLIC_URL="http://$PUBLIC_IP:6000"
export PORT='6000'
export DATA_SERVER_PORT='8000'
export ANTHROPIC_API_KEY='ANTHROPIC_API_KEY_PLACEHOLDER'

# Start finance feed agent
cd /home/ubuntu/nanda-finance-agent
sudo -u ubuntu bash -c "source env/bin/activate && nohup python3 examples/finance_feed_agent.py > /home/ubuntu/finance_agent.log 2>&1 &"

# Wait a moment for agent to start
sleep 10

echo "=== Finance Feed Agent Setup Complete ==="
echo "Agent running at: http://$PUBLIC_IP:6000/a2a"
echo "Data Facts at: http://$PUBLIC_IP:8000/data_facts/public_stock_ticker.json"
echo "Stock Data at: http://$PUBLIC_IP:8000/stock_data"

FINANCE_EOF

# Replace placeholders in finance feed user data
sed -i "s|REGISTRY_URL_PLACEHOLDER|$REGISTRY_URL|g" "user_data_finance_feed_${DEPLOYMENT_ID}.sh"
sed -i "s|ANTHROPIC_API_KEY_PLACEHOLDER|$ANTHROPIC_API_KEY|g" "user_data_finance_feed_${DEPLOYMENT_ID}.sh"

# Launch Finance Feed Agent instance
echo "[5/7] Launching Finance Feed Agent EC2 instance..."
FINANCE_INSTANCE_ID=$(aws ec2 run-instances \
    --image-id "$AMI_ID" \
    --count 1 \
    --instance-type "$INSTANCE_TYPE" \
    --key-name "$KEY_NAME" \
    --security-group-ids "$SECURITY_GROUP_ID" \
    --region "$REGION" \
    --user-data "file://user_data_finance_feed_${DEPLOYMENT_ID}.sh" \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=nanda-finance-feed-agent-$DEPLOYMENT_ID},{Key=Project,Value=NANDA-Finance-Agent},{Key=DeploymentId,Value=$DEPLOYMENT_ID}]" \
    --query 'Instances[0].InstanceId' \
    --output text)

echo "✅ Finance Feed Agent instance launched: $FINANCE_INSTANCE_ID"

# Wait for Finance Feed Agent instance
aws ec2 wait instance-running --region "$REGION" --instance-ids "$FINANCE_INSTANCE_ID"
FINANCE_PUBLIC_IP=$(aws ec2 describe-instances --region "$REGION" --instance-ids "$FINANCE_INSTANCE_ID" --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)

echo "Finance Feed Agent Public IP: $FINANCE_PUBLIC_IP"
echo "Waiting 60 seconds for Finance Feed Agent deployment..."
sleep 60

# =============================================================================
# DEPLOY CONSUMER AGENT
# =============================================================================

echo "[6/7] Creating Consumer Agent deployment script..."

cat > "user_data_consumer_${DEPLOYMENT_ID}.sh" << 'CONSUMER_EOF'
#!/bin/bash
exec > /var/log/user-data-consumer.log 2>&1

echo "=== Consumer Agent Setup Started ==="
date

# Update system and install dependencies
apt-get update -y
apt-get install -y python3 python3-venv python3-pip git curl unzip

# Setup project
cd /home/ubuntu
sudo -u ubuntu git clone https://github.com/projnanda/NEST.git nanda-consumer-agent
cd nanda-consumer-agent
# Try multiple branches to find the files
sudo -u ubuntu git checkout data-path || sudo -u ubuntu git checkout main || sudo -u ubuntu git checkout feature/mcp-tooling || sudo -u ubuntu git checkout master || true
# Verify files exist
if [ ! -f "examples/data_consumer_agent.py" ]; then
    echo "WARNING: data_consumer_agent.py not found. Trying to find it..."
    sudo -u ubuntu find . -name "data_consumer_agent.py" -type f 2>/dev/null | head -5
    # Try checking out all branches
    for branch in $(sudo -u ubuntu git branch -a | grep -v HEAD | sed 's|remotes/origin/||' | sort -u); do
        echo "Checking branch: $branch"
        sudo -u ubuntu git checkout "$branch" 2>/dev/null && break || continue
    done
fi
cd ..
cd nanda-consumer-agent

# Create virtual environment
sudo -u ubuntu python3 -m venv env
sudo -u ubuntu bash -c "source env/bin/activate && pip install --upgrade pip && pip install -e . && pip install anthropic python-a2a requests"

# Get public IP
echo "Getting public IP address..."
for attempt in {1..5}; do
    TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600" --connect-timeout 5 --max-time 10)
    if [ -n "$TOKEN" ]; then
        PUBLIC_IP=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" --connect-timeout 5 --max-time 10 http://169.254.169.254/latest/meta-data/public-ipv4)
        if [ -n "$PUBLIC_IP" ] && [[ $PUBLIC_IP =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
            echo "Retrieved public IP: $PUBLIC_IP"
            break
        fi
    fi
    echo "Attempt $attempt failed, retrying..."
    sleep 3
done

if [ -z "$PUBLIC_IP" ]; then
    echo "ERROR: Could not retrieve public IP"
    exit 1
fi

# Set environment variables
export AGENT_ID='data-consumer-agent'
export AGENT_NAME='Data Consumer Agent'
export REGISTRY_URL='REGISTRY_URL_PLACEHOLDER'
export PUBLIC_URL="http://$PUBLIC_IP:6001"
export PORT='6001'
export ANTHROPIC_API_KEY='ANTHROPIC_API_KEY_PLACEHOLDER'
export FINANCE_FEED_AGENT_URL="http://FINANCE_FEED_IP_PLACEHOLDER:6000"

# Start consumer agent
cd /home/ubuntu/nanda-consumer-agent
sudo -u ubuntu bash -c "source env/bin/activate && nohup python3 examples/data_consumer_agent.py > /home/ubuntu/consumer_agent.log 2>&1 &"

# Wait a moment for agent to start
sleep 10

echo "=== Consumer Agent Setup Complete ==="
echo "Agent running at: http://$PUBLIC_IP:6001/a2a"

CONSUMER_EOF

# Replace placeholders in consumer user data
sed -i "s|REGISTRY_URL_PLACEHOLDER|$REGISTRY_URL|g" "user_data_consumer_${DEPLOYMENT_ID}.sh"
sed -i "s|ANTHROPIC_API_KEY_PLACEHOLDER|$ANTHROPIC_API_KEY|g" "user_data_consumer_${DEPLOYMENT_ID}.sh"
sed -i "s|FINANCE_FEED_IP_PLACEHOLDER|$FINANCE_PUBLIC_IP|g" "user_data_consumer_${DEPLOYMENT_ID}.sh"

# Launch Consumer Agent instance
echo "[7/7] Launching Consumer Agent EC2 instance..."
CONSUMER_INSTANCE_ID=$(aws ec2 run-instances \
    --image-id "$AMI_ID" \
    --count 1 \
    --instance-type "$INSTANCE_TYPE" \
    --key-name "$KEY_NAME" \
    --security-group-ids "$SECURITY_GROUP_ID" \
    --region "$REGION" \
    --user-data "file://user_data_consumer_${DEPLOYMENT_ID}.sh" \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=nanda-consumer-agent-$DEPLOYMENT_ID},{Key=Project,Value=NANDA-Consumer-Agent},{Key=DeploymentId,Value=$DEPLOYMENT_ID}]" \
    --query 'Instances[0].InstanceId' \
    --output text)

echo "✅ Consumer Agent instance launched: $CONSUMER_INSTANCE_ID"

# Wait for Consumer Agent instance
aws ec2 wait instance-running --region "$REGION" --instance-ids "$CONSUMER_INSTANCE_ID"
CONSUMER_PUBLIC_IP=$(aws ec2 describe-instances --region "$REGION" --instance-ids "$CONSUMER_INSTANCE_ID" --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)

echo "Consumer Agent Public IP: $CONSUMER_PUBLIC_IP"
echo "Waiting 60 seconds for Consumer Agent deployment..."
sleep 60

# Cleanup
rm "user_data_finance_feed_${DEPLOYMENT_ID}.sh"
rm "user_data_consumer_${DEPLOYMENT_ID}.sh"

# Summary
echo ""
echo "🎉 Deployment Complete!"
echo "======================"
echo ""
echo "Finance Feed Agent:"
echo "  Instance ID: $FINANCE_INSTANCE_ID"
echo "  Public IP: $FINANCE_PUBLIC_IP"
echo "  A2A Endpoint: http://$FINANCE_PUBLIC_IP:6000/a2a"
echo "  Data Facts: http://$FINANCE_PUBLIC_IP:8000/data_facts/public_stock_ticker.json"
echo "  Stock Data: http://$FINANCE_PUBLIC_IP:8000/stock_data"
echo ""
echo "Consumer Agent:"
echo "  Instance ID: $CONSUMER_INSTANCE_ID"
echo "  Public IP: $CONSUMER_PUBLIC_IP"
echo "  A2A Endpoint: http://$CONSUMER_PUBLIC_IP:6001/a2a"
echo ""
echo "Key File: ${KEY_NAME}.pem"
echo ""
echo "Test Commands:"
echo "  # Test Finance Feed Agent A2A:"
echo "  curl -X POST http://$FINANCE_PUBLIC_IP:6000/a2a \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"content\":{\"text\":\"what are the current stock prices?\",\"type\":\"text\"},\"role\":\"user\",\"conversation_id\":\"test123\"}'"
echo ""
echo "  # Test Data Facts:"
echo "  curl http://$FINANCE_PUBLIC_IP:8000/data_facts/public_stock_ticker.json"
echo ""
echo "  # Test Consumer Agent A2A:"
echo "  curl -X POST http://$CONSUMER_PUBLIC_IP:6001/a2a \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"content\":{\"text\":\"ask finance agent about stock prices\",\"type\":\"text\"},\"role\":\"user\",\"conversation_id\":\"test123\"}'"
echo ""
echo "SSH Access:"
echo "  Finance Feed Agent: ssh -i ${KEY_NAME}.pem ubuntu@$FINANCE_PUBLIC_IP"
echo "  Consumer Agent: ssh -i ${KEY_NAME}.pem ubuntu@$CONSUMER_PUBLIC_IP"
echo ""
echo "Check Logs:"
echo "  Finance Feed Agent: ssh -i ${KEY_NAME}.pem ubuntu@$FINANCE_PUBLIC_IP 'tail -f /home/ubuntu/finance_agent.log'"
echo "  Consumer Agent: ssh -i ${KEY_NAME}.pem ubuntu@$CONSUMER_PUBLIC_IP 'tail -f /home/ubuntu/consumer_agent.log'"
echo ""
echo "Terminate Instances:"
echo "  aws ec2 terminate-instances --region $REGION --instance-ids $FINANCE_INSTANCE_ID $CONSUMER_INSTANCE_ID"
