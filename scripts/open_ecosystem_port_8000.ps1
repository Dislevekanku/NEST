# Open port 8000 on the security group of the NANDA ecosystem instance.
# Run this if scale-50 fails with "Connection timed out" to 18.234.53.227:8000.
# Usage: .\open_ecosystem_port_8000.ps1 [-Region us-east-1]

param(
    [string]$Region = "us-east-1"
)

# Find running ecosystem instance (by tag)
$instanceId = aws ec2 describe-instances `
    --region $Region `
    --filters "Name=instance-state-name,Values=running" "Name=tag:Project,Values=NANDA-Ecosystem-50,NANDA-Ecosystem" `
    --query "Reservations[].Instances[].InstanceId" --output text 2>$null
if (-not $instanceId) {
    Write-Host "No running NANDA ecosystem instance found in $Region." -ForegroundColor Red
    exit 1
}
$instanceId = ($instanceId -split "\s+")[0]

# Get security group ID(s) for this instance
$sgIds = aws ec2 describe-instances --region $Region --instance-ids $instanceId `
    --query "Reservations[0].Instances[0].SecurityGroups[].GroupId" --output text 2>$null
if (-not $sgIds) {
    Write-Host "Could not get security groups for instance $instanceId" -ForegroundColor Red
    exit 1
}

foreach ($sgId in ($sgIds -split "\s+")) {
    if (-not $sgId) { continue }
    Write-Host "Adding inbound rule: port 8000, 0.0.0.0/0 to security group $sgId ..."
    $err = aws ec2 authorize-security-group-ingress `
        --group-id $sgId `
        --protocol tcp `
        --port 8000 `
        --cidr 0.0.0.0/0 `
        --region $Region 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  Done. Port 8000 is now open." -ForegroundColor Green
    } else {
        if ($err -match "already exists") {
            Write-Host "  Rule already exists for $sgId (port 8000 already open)." -ForegroundColor Yellow
        } else {
            Write-Host "  $err" -ForegroundColor Red
        }
    }
}
Write-Host ""
Write-Host "Retry the experiment:"
Write-Host '  $env:ECOSYSTEM_IP = (.\get_ecosystem_ip.ps1); cd experiments\exp1_discovery_efficiency; .\run_scale_50.ps1'
