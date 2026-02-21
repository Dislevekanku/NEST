# Exp1 paper-grade 50-agent scale run
# Set your deployed ecosystem public IP, or let the script fetch it via AWS CLI (if instance has tag Project=NANDA-Ecosystem-50 or NANDA-Ecosystem).

param(
    [string]$EcosystemIP = $env:ECOSYSTEM_IP,
    [string]$Region = "us-east-1"
)

if (-not $EcosystemIP) {
    $nestRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
    $getIpScript = Join-Path $nestRoot "scripts\get_ecosystem_ip.ps1"
    if (Test-Path $getIpScript) {
        $EcosystemIP = & $getIpScript -Region $Region
    }
}
if (-not $EcosystemIP) {
    Write-Host "Set ECOSYSTEM_IP to your deployed ecosystem public IP, or deploy with scripts\deploy_ecosystem_50.ps1 (tags instance so get_ecosystem_ip.ps1 can find it)."
    Write-Host "  PowerShell: `$env:ECOSYSTEM_IP = 'YOUR_IP'; .\run_scale_50.ps1"
    Write-Host "  Or: .\run_scale_50.ps1 -EcosystemIP YOUR_IP"
    exit 1
}

$env:ECOSYSTEM_IP = $EcosystemIP
Set-Location $PSScriptRoot
python run.py --scale-50
exit $LASTEXITCODE
