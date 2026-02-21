# Get public IP of the NANDA ecosystem EC2 instance via AWS CLI.
# Looks for running instances with tag Project=NANDA-Ecosystem-50 or NANDA-Ecosystem.
# Usage: .\get_ecosystem_ip.ps1 [-Region us-east-1]
#
# Raw AWS CLI one-liner (PowerShell):
#   aws ec2 describe-instances --region us-east-1 --filters "Name=instance-state-name,Values=running" "Name=tag:Project,Values=NANDA-Ecosystem-50,NANDA-Ecosystem" --query "Reservations[].Instances[].PublicIpAddress" --output text

param(
    [string]$Region = "us-east-1"
)

# Prefer 50-agent tag; filter returns running instances with Project = NANDA-Ecosystem-50 or NANDA-Ecosystem
$ip = aws ec2 describe-instances `
    --region $Region `
    --filters "Name=instance-state-name,Values=running" "Name=tag:Project,Values=NANDA-Ecosystem-50,NANDA-Ecosystem" `
    --query "Reservations[].Instances[].PublicIpAddress" `
    --output text 2>$null

# Take first non-empty (if multiple, use first)
if ($ip) {
    $ip = ($ip -split "\s+")[0]
}

if (-not $ip -or $ip -eq "None") {
    Write-Host "No running NANDA ecosystem instance found in $Region (tag Project=NANDA-Ecosystem-50 or NANDA-Ecosystem)." -ForegroundColor Yellow
    exit 1
}
Write-Output $ip
