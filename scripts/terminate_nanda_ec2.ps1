# Terminate all EC2 instances tagged with Project = NANDA-Ecosystem-50 or NANDA-Ecosystem.
# Use for "Kill Cloud" after locking paper scope to local execution.
# Usage: .\terminate_nanda_ec2.ps1 [-Region us-east-1] [-WhatIf]

param(
    [string]$Region = "us-east-1",
    [switch]$WhatIf
)

$instanceIds = aws ec2 describe-instances `
    --region $Region `
    --filters "Name=tag:Project,Values=NANDA-Ecosystem-50,NANDA-Ecosystem" "Name=instance-state-name,Values=running,stopped,pending" `
    --query "Reservations[].Instances[].InstanceId" `
    --output text 2>$null

if (-not $instanceIds) {
    Write-Host "No NANDA ecosystem instances found in $Region (tag Project=NANDA-Ecosystem-50 or NANDA-Ecosystem)." -ForegroundColor Green
    exit 0
}

$ids = ($instanceIds -split "\s+") | Where-Object { $_ }
Write-Host "Found $($ids.Count) instance(s): $($ids -join ', ')" -ForegroundColor Yellow

if ($WhatIf) {
    Write-Host "WhatIf: would run: aws ec2 terminate-instances --region $Region --instance-ids $($ids -join ' ')" -ForegroundColor Cyan
    exit 0
}

Write-Host "Terminating (this cannot be undone)..." -ForegroundColor Red
aws ec2 terminate-instances --region $Region --instance-ids $ids
if ($LASTEXITCODE -eq 0) {
    Write-Host "Terminate requested. Instances will shut down in a few minutes." -ForegroundColor Green
} else {
    Write-Host "Terminate failed. Check AWS CLI and permissions." -ForegroundColor Red
    exit 1
}
