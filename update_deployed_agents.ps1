# PowerShell script to update deployed Menu Agent and Concierge Agent with latest code

# Menu Agent Configuration - Use environment variables with defaults
$MenuAgentIP = $env:MENU_AGENT_IP
if (-not $MenuAgentIP) { $MenuAgentIP = "54.237.202.184" }
$MenuAgentKey = $env:MENU_AGENT_KEY
if (-not $MenuAgentKey) {
    $MenuAgentKey = $env:SSH_KEY_PATH
    if (-not $MenuAgentKey) { $MenuAgentKey = "nanda-agent-key.pem" }
}
$MenuAgentDir = $env:MENU_AGENT_DIR
if (-not $MenuAgentDir) { $MenuAgentDir = "/home/ubuntu/nanda-agent-menu-agent" }
$MenuAgentUser = $env:MENU_AGENT_USER
if (-not $MenuAgentUser) { $MenuAgentUser = "ubuntu" }
$MenuAgentBranch = $env:MENU_AGENT_BRANCH
if (-not $MenuAgentBranch) {
    $MenuAgentBranch = $env:GIT_BRANCH
    if (-not $MenuAgentBranch) { $MenuAgentBranch = "data-path" }
}

# Concierge Agent Configuration
$ConciergeAgentIP = $env:CONCIERGE_AGENT_IP
if (-not $ConciergeAgentIP) { $ConciergeAgentIP = "3.94.191.179" }
$ConciergeAgentKey = $env:CONCIERGE_AGENT_KEY
if (-not $ConciergeAgentKey) {
    $ConciergeAgentKey = $env:SSH_KEY_PATH
    if (-not $ConciergeAgentKey) { $ConciergeAgentKey = "nanda-agent-key.pem" }
}
$ConciergeAgentDir = $env:CONCIERGE_AGENT_DIR
if (-not $ConciergeAgentDir) { $ConciergeAgentDir = "/home/ubuntu/nanda-agent-concierge-agent" }
$ConciergeAgentUser = $env:CONCIERGE_AGENT_USER
if (-not $ConciergeAgentUser) { $ConciergeAgentUser = "ubuntu" }
$ConciergeAgentBranch = $env:CONCIERGE_AGENT_BRANCH
if (-not $ConciergeAgentBranch) {
    $ConciergeAgentBranch = $env:GIT_BRANCH
    if (-not $ConciergeAgentBranch) { $ConciergeAgentBranch = "data-path" }
}

function Update-Agent {
    param(
        [string]$AgentName,
        [string]$AgentIP,
        [string]$AgentKey,
        [string]$AgentDir,
        [string]$AgentUser,
        [string]$AgentBranch = "data-path"
    )
    
    Write-Host "Updating $AgentName on $AgentIP..." -ForegroundColor Yellow
    
    if (-not (Test-Path $AgentKey)) {
        Write-Host "WARNING: Key file not found: $AgentKey" -ForegroundColor Yellow
        Write-Host "  Set: `$env:MENU_AGENT_KEY or `$env:CONCIERGE_AGENT_KEY" -ForegroundColor Yellow
        return $false
    }
    
    # Build bash script - escape variables properly
    $bashScript = "set -e; "
    $bashScript += "echo 'Current directory: '`$(pwd); "
    $bashScript += "if [ ! -d '$AgentDir' ]; then echo 'ERROR: Directory $AgentDir does not exist!'; exit 1; fi; "
    $bashScript += "cd '$AgentDir'; "
    $bashScript += "echo 'Changed to: '`$(pwd); "
    $bashScript += "if [ ! -d '.git' ]; then echo 'WARNING: Not a git repository. Skipping git pull.'; exit 0; fi; "
    $bashScript += "echo 'Fetching latest changes...'; "
    $bashScript += "git fetch origin || echo 'WARNING: Git fetch failed, continuing...'; "
    $bashScript += "echo 'Pulling latest code from branch: $AgentBranch...'; "
    # Try multiple branch name variations
    $bashScript += "git pull origin $AgentBranch || git pull origin Data-Path || git pull origin main || git pull origin master || { "
    $bashScript += "echo 'WARNING: Git pull failed. Trying to stash changes...'; "
    $bashScript += "git stash; "
    $bashScript += "git pull origin $AgentBranch || git pull origin Data-Path || git pull origin main || git pull origin master; "
    $bashScript += "}; "
    $bashScript += "if [ -f 'requirements.txt' ]; then "
    $bashScript += "echo 'Updating Python dependencies...'; "
    $bashScript += "pip install -q -r requirements.txt || echo 'WARNING: Dependency update failed'; "
    $bashScript += "fi; "
    $bashScript += "if [ -f 'setup.py' ]; then "
    $bashScript += "echo 'Installing package...'; "
    $bashScript += "pip install -q -e . || echo 'WARNING: Package install failed'; "
    $bashScript += "fi; "
    $bashScript += "echo 'SUCCESS: $AgentName code updated successfully'; "
    $bashScript += "if command -v supervisorctl &> /dev/null; then "
    $bashScript += "echo 'Restarting agent with supervisor...'; "
    $bashScript += "supervisorctl restart nanda-agent || echo 'WARNING: Supervisor restart failed'; "
    $bashScript += "else "
    $bashScript += "echo 'INFO: Supervisor not found. Please restart manually.'; "
    $bashScript += "fi"
    
    try {
        ssh -i $AgentKey -o StrictHostKeyChecking=no "${AgentUser}@${AgentIP}" $bashScript
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "SUCCESS: $AgentName updated!" -ForegroundColor Green
            return $true
        } else {
            Write-Host "ERROR: Failed to update $AgentName" -ForegroundColor Red
            return $false
        }
    }
    catch {
        Write-Host "ERROR updating $AgentName : $_" -ForegroundColor Red
        return $false
    }
}

Write-Host "Updating Deployed Agents" -ForegroundColor Green
Write-Host ""

Update-Agent -AgentName "Menu Agent" -AgentIP $MenuAgentIP -AgentKey $MenuAgentKey -AgentDir $MenuAgentDir -AgentUser $MenuAgentUser -AgentBranch $MenuAgentBranch

Write-Host ""

Update-Agent -AgentName "Concierge Agent" -AgentIP $ConciergeAgentIP -AgentKey $ConciergeAgentKey -AgentDir $ConciergeAgentDir -AgentUser $ConciergeAgentUser -AgentBranch $ConciergeAgentBranch

Write-Host ""
Write-Host "Update process complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Test commands:" -ForegroundColor Cyan
Write-Host "  Menu Agent: Invoke-RestMethod -Uri http://${MenuAgentIP}:6000/a2a -Method Post -Body (@{content=@{text='Hello';type='text'};role='user';conversation_id='test'} | ConvertTo-Json) -ContentType 'application/json'"
Write-Host "  Concierge A2A: Invoke-RestMethod -Uri http://${ConciergeAgentIP}:6000/a2a -Method Post -Body (@{content=@{text='@menu-agent what is on the menu?';type='text'};role='user';conversation_id='test'} | ConvertTo-Json) -ContentType 'application/json'"
