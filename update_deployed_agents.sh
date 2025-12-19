#!/bin/bash
# Script to update deployed Menu Agent and Concierge Agent with latest code

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Updating Deployed Agents${NC}"
echo ""

# Menu Agent Configuration
MENU_AGENT_IP="54.237.202.184"
MENU_AGENT_KEY="${MENU_AGENT_KEY:-nanda-agent-key.pem}"  # Default key file
MENU_AGENT_DIR="/home/ubuntu/nanda-agent-menu-agent"
MENU_AGENT_USER="ubuntu"

# Concierge Agent Configuration
CONCIERGE_AGENT_IP="3.94.191.179"
CONCIERGE_AGENT_KEY="${CONCIERGE_AGENT_KEY:-nanda-agent-key.pem}"  # Default key file
CONCIERGE_AGENT_DIR="/home/ubuntu/nanda-agent-concierge-agent"
CONCIERGE_AGENT_USER="ubuntu"

# Check if key file exists
if [ ! -f "$MENU_AGENT_KEY" ] && [ ! -f "$CONCIERGE_AGENT_KEY" ]; then
    echo -e "${YELLOW}⚠️  Key file not found. Please set MENU_AGENT_KEY or CONCIERGE_AGENT_KEY environment variable${NC}"
    echo "Example: export MENU_AGENT_KEY=/path/to/key.pem"
    exit 1
fi

# Function to update an agent
update_agent() {
    local AGENT_NAME=$1
    local AGENT_IP=$2
    local AGENT_KEY=$3
    local AGENT_DIR=$4
    local AGENT_USER=$5
    
    echo -e "${YELLOW}📦 Updating ${AGENT_NAME} on ${AGENT_IP}...${NC}"
    
    ssh -i "$AGENT_KEY" -o StrictHostKeyChecking=no "${AGENT_USER}@${AGENT_IP}" << EOF
        set -e
        echo "Current directory: \$(pwd)"
        
        if [ ! -d "$AGENT_DIR" ]; then
            echo "❌ Directory $AGENT_DIR does not exist!"
            exit 1
        fi
        
        cd "$AGENT_DIR"
        echo "📂 Changed to: \$(pwd)"
        
        # Check if it's a git repository
        if [ ! -d ".git" ]; then
            echo "⚠️  Not a git repository. Skipping git pull."
            exit 0
        fi
        
        # Fetch latest changes
        echo "🔄 Fetching latest changes..."
        git fetch origin || echo "⚠️  Git fetch failed, continuing..."
        
        # Pull latest code
        echo "⬇️  Pulling latest code..."
        git pull origin main || git pull origin master || {
            echo "⚠️  Git pull failed. Trying to stash changes..."
            git stash
            git pull origin main || git pull origin master
        }
        
        # Install/update dependencies if needed
        if [ -f "requirements.txt" ]; then
            echo "📦 Updating Python dependencies..."
            pip install -q -r requirements.txt || echo "⚠️  Dependency update failed"
        fi
        
        if [ -f "setup.py" ]; then
            echo "📦 Installing package..."
            pip install -q -e . || echo "⚠️  Package install failed"
        fi
        
        echo "✅ ${AGENT_NAME} code updated successfully"
        
        # Check if agent is running with supervisor
        if command -v supervisorctl &> /dev/null; then
            echo "🔄 Restarting agent with supervisor..."
            supervisorctl restart nanda-agent || echo "⚠️  Supervisor restart failed, agent may need manual restart"
        else
            echo "ℹ️  Supervisor not found. Please restart the agent manually."
        fi
EOF
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ ${AGENT_NAME} updated successfully!${NC}"
    else
        echo -e "${RED}❌ Failed to update ${AGENT_NAME}${NC}"
        return 1
    fi
    echo ""
}

# Update Menu Agent
if [ -f "$MENU_AGENT_KEY" ]; then
    update_agent "Menu Agent" "$MENU_AGENT_IP" "$MENU_AGENT_KEY" "$MENU_AGENT_DIR" "$MENU_AGENT_USER"
else
    echo -e "${YELLOW}⚠️  Menu Agent key not found, skipping...${NC}"
fi

# Update Concierge Agent
if [ -f "$CONCIERGE_AGENT_KEY" ]; then
    update_agent "Concierge Agent" "$CONCIERGE_AGENT_IP" "$CONCIERGE_AGENT_KEY" "$CONCIERGE_AGENT_DIR" "$CONCIERGE_AGENT_USER"
else
    echo -e "${YELLOW}⚠️  Concierge Agent key not found, skipping...${NC}"
fi

echo -e "${GREEN}✨ Update process complete!${NC}"
echo ""
echo "🧪 Test the agents:"
echo "  Menu Agent: curl -X POST http://${MENU_AGENT_IP}:6000/a2a -H 'Content-Type: application/json' -d '{\"content\":{\"text\":\"Hello\",\"type\":\"text\"},\"role\":\"user\",\"conversation_id\":\"test\"}'"
echo "  Concierge A2A: curl -X POST http://${CONCIERGE_AGENT_IP}:6000/a2a -H 'Content-Type: application/json' -d '{\"content\":{\"text\":\"@menu-agent what'\''s on the menu?\",\"type\":\"text\"},\"role\":\"user\",\"conversation_id\":\"test\"}'"

