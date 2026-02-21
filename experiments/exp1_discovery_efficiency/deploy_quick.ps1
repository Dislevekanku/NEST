# NEST Quick Deployment Script (Windows PowerShell)
# Deploys 2 providers + 10 consumers for testing

param(
    [int]$ConsumerCount = 10,
    [switch]$ValidateOnly,
    [string]$Registry = "http://registry.chat39.com:6900"
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$NestRoot = (Get-Item $ScriptDir).Parent.Parent.FullName

Write-Host "=============================================="
Write-Host "NEST Quick Deployment"
Write-Host "=============================================="
Write-Host "NEST Root: $NestRoot"
Write-Host "Registry:  $Registry"
Write-Host "Consumers: $ConsumerCount"
Write-Host "=============================================="

# Check registry health
Write-Host "`nChecking registry health..."
try {
    $health = Invoke-RestMethod -Uri "$Registry/health" -TimeoutSec 5
    Write-Host "Registry: $($health.status)" -ForegroundColor Green
} catch {
    Write-Host "Registry unreachable!" -ForegroundColor Red
    exit 1
}

if ($ValidateOnly) {
    Write-Host "`nRunning validation only..."
    python "$ScriptDir\deploy_agents.py" --validate-only --registry $Registry
    exit 0
}

# Deploy agents
Write-Host "`nDeploying agents..."
$TotalAgents = 2 + $ConsumerCount  # 2 providers + N consumers

python "$ScriptDir\deploy_agents.py" `
    --mode local `
    --count $TotalAgents `
    --registry $Registry `
    --output "$ScriptDir\deploy_report.json"

Write-Host "`nDeployment complete. Check deploy_report.json for results."
