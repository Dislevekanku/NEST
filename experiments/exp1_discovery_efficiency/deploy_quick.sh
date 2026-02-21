#!/bin/bash
# NEST Quick Deployment Script (Linux/Mac)
# Deploys 2 providers + 10 consumers for testing

CONSUMER_COUNT=${1:-10}
REGISTRY=${2:-"http://registry.chat39.com:6900"}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=============================================="
echo "NEST Quick Deployment"
echo "=============================================="
echo "Script Dir: $SCRIPT_DIR"
echo "Registry:   $REGISTRY"
echo "Consumers:  $CONSUMER_COUNT"
echo "=============================================="

# Check registry health
echo -e "\nChecking registry health..."
HEALTH=$(curl -s --connect-timeout 5 "$REGISTRY/health" 2>/dev/null)
if [ $? -eq 0 ] && echo "$HEALTH" | grep -q "healthy"; then
    echo "Registry: healthy"
else
    echo "Registry unreachable!"
    exit 1
fi

# Deploy agents
echo -e "\nDeploying agents..."
TOTAL_AGENTS=$((2 + CONSUMER_COUNT))  # 2 providers + N consumers

python3 "$SCRIPT_DIR/deploy_agents.py" \
    --mode local \
    --count $TOTAL_AGENTS \
    --registry "$REGISTRY" \
    --output "$SCRIPT_DIR/deploy_report.json"

echo -e "\nDeployment complete. Check deploy_report.json for results."
