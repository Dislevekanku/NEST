# Copy nanda_core + experiments/ecosystem to the running instance and start the server.
# Use when the cloned branch lacked nanda_core or experiments/ecosystem.
# Prereq: .pem permissions fixed (icacls ... /inheritance:r /grant:r "%USERNAME%:R")
# Usage: .\fix_ecosystem_on_instance.ps1 -InstanceIP "18.234.53.227" [-KeyPath "..\nanda-ecosystem-key.pem"]

param(
    [Parameter(Mandatory=$true)]
    [string]$InstanceIP,
    [string]$KeyPath = (Join-Path $PSScriptRoot "..\nanda-ecosystem-key.pem"),
    [string]$Region = "us-east-1"
)

$NestRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$EcoDir = Join-Path $NestRoot "experiments\ecosystem"
$NandaCoreDir = Join-Path $NestRoot "nanda_core"
if (-not (Test-Path (Join-Path $EcoDir "run_ecosystem.py"))) {
    Write-Host "Not found: $EcoDir\run_ecosystem.py" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path (Join-Path $NandaCoreDir "dataset\server.py"))) {
    Write-Host "Not found: $NandaCoreDir\dataset\server.py" -ForegroundColor Red
    exit 1
}

$key = (Resolve-Path $KeyPath).Path
Write-Host "Ensuring remote directories exist..."
ssh -i $key -o StrictHostKeyChecking=accept-new ubuntu@$InstanceIP "mkdir -p /home/ubuntu/nanda-ecosystem/experiments /home/ubuntu/nanda-ecosystem/nanda_core" 2>&1
Write-Host "Copying nanda_core (required for run_ecosystem) to ubuntu@${InstanceIP} ..."
scp -i $key -r "$NandaCoreDir" "ubuntu@${InstanceIP}:/home/ubuntu/nanda-ecosystem/" 2>&1
if ($LASTEXITCODE -ne 0) { Write-Host "SCP nanda_core failed." -ForegroundColor Red; exit 1 }
Write-Host "Copying experiments/ecosystem to ubuntu@${InstanceIP} ..."
scp -i $key -r "$EcoDir" "ubuntu@${InstanceIP}:/home/ubuntu/nanda-ecosystem/experiments/" 2>&1
if ($LASTEXITCODE -ne 0) { Write-Host "SCP experiments/ecosystem failed." -ForegroundColor Red; exit 1 }
Write-Host "Starting ecosystem on instance..."
# Single-line command to avoid CRLF issues when PowerShell sends to bash
$startCmd = "cd /home/ubuntu/nanda-ecosystem && source env/bin/activate && export REGISTRY_URL='http://registry.chat39.com:6900' DATA_SERVER_PORT='8000' PUBLIC_URL='http://" + $InstanceIP + ":8000' CONFIG_PATH='/home/ubuntu/nanda-ecosystem/experiments/ecosystem/config_50_agents.json' && nohup python3 experiments/ecosystem/run_ecosystem.py >> /home/ubuntu/ecosystem.log 2>&1 & sleep 4 && curl -s -m 5 http://localhost:8000/health || true"
ssh -i $key ubuntu@$InstanceIP $startCmd
Write-Host ""
Write-Host "If you see {\"status\":\"ok\",...} above, the server is running. Then run:" -ForegroundColor Green
Write-Host "  `$env:ECOSYSTEM_IP = `"$InstanceIP`"; cd experiments\exp1_discovery_efficiency; .\run_scale_50.ps1"
