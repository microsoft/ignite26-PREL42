<#
.SYNOPSIS
    Prepares the Skillable lab after infra\main.bicep is deployed.
.DESCRIPTION
    Mirrors infra\hooks\postprovision.ps1, but runs as the lab service principal (AZURE_CLIENT_ID,
    AZURE_CLIENT_SECRET, AZURE_TENANT_ID, and AZURE_SUBSCRIPTION_ID must be set) and without an azd
    environment during provisioning. Stages run in the order attendees need them, and every stage logs
    "OK" or "FAILED" to the log file. Safe to rerun.
.PARAMETER OutputsFile
    JSON file with the Bicep deployment outputs (az deployment group create --query properties.outputs).
#>
param(
    [Parameter(Mandatory)][string]$OutputsFile,
    [Parameter(Mandatory)][string]$LabUserUpn,
    [Parameter(Mandatory)][string]$LabUserObjectId,
    [string]$WebIqKey = "",
    [string]$LogFile = "C:\Users\LabUser\Desktop\lifecycle-log.txt"
)

# Native tools write progress to stderr, which "Stop" would turn into terminating errors.
$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUNBUFFERED = "1"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"

function Log {
    param([string]$msg)
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $msg"
    Write-Host $line
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
}

function Invoke-Step {
    param([string]$Name, [scriptblock]$Command)
    Log "--- $Name"
    & $Command 2>&1 | ForEach-Object { Add-Content -Path $LogFile -Value "$_" -Encoding UTF8 }
    if ($LASTEXITCODE -eq 0) {
        Log "OK: $Name"
        return $true
    }
    Log "FAILED (exit $LASTEXITCODE): $Name"
    return $false
}

foreach ($name in "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET", "AZURE_TENANT_ID", "AZURE_SUBSCRIPTION_ID") {
    if (-not [Environment]::GetEnvironmentVariable($name)) {
        Log "ERROR: $name must be set before running setup-lab.ps1."
        exit 1
    }
}

Log "=== Lab setup started ==="

# Expose the Bicep outputs as environment variables, the same way azd does for its hooks.
$outputs = Get-Content -Path $OutputsFile -Raw | ConvertFrom-Json
foreach ($output in $outputs.PSObject.Properties) {
    [Environment]::SetEnvironmentVariable($output.Name, [string]$output.Value.value, "Process")
}
$env:FABRIC_LAB_USER_UPN = $LabUserUpn
$env:FABRIC_LAB_USER_OID = $LabUserObjectId

$azdEnvReady = $false
$agentsReady = $false

# Stage 1: Python environment
$null = Invoke-Step "Install uv" { python -m pip install --upgrade uv --disable-pip-version-check }
if (-not (Invoke-Step "Install Python dependencies" { python -m uv sync --locked --all-groups })) {
    Log "=== Lab setup FAILED: cannot continue without Python dependencies ==="
    exit 1
}
$null = Invoke-Step "Install notebook dependencies" { python -m uv pip install --python $python -r notebooks\requirements.txt }

# Stage 2: .env for the notebooks and agents
if (-not (Invoke-Step "Write .env" { & $python infra\setup-env.py })) {
    Log "=== Lab setup FAILED: .env could not be written ==="
    exit 1
}
if ($WebIqKey) {
    $env:WEB_IQ_KEY = $WebIqKey
    $null = Invoke-Step "Write WEB_IQ_KEY" { & $python -c "import os; from dotenv import set_key; set_key('.env', 'WEB_IQ_KEY', os.environ['WEB_IQ_KEY'], quote_mode='never')" }
}

# Stage 3: Foundry IQ knowledge bases and toolboxes
$workIqReady = Invoke-Step "Work IQ Entra app" { & $python infra\create-workiq-entra.py --apply }
if ($workIqReady) {
    $searchReady = Invoke-Step "Search indexes and knowledge bases (with Work IQ)" { & $python infra\create-search-indexes.py --include-workiq }
} else {
    $searchReady = Invoke-Step "Search indexes and knowledge bases" { & $python infra\create-search-indexes.py }
}
if ($searchReady) {
    $null = Invoke-Step "Foundry IQ toolbox" { & $python infra\create-toolbox-foundryiq.py }
    if ($workIqReady) {
        $null = Invoke-Step "Work IQ knowledge-base toolbox" {
            & $python infra\create-toolbox-foundryiq.py `
                --toolbox-name workiq-knowledge-tools `
                --knowledge-base-name multisource-workiq-knowledge-base `
                --connection-name workiq-kb-mcp-connection `
                --knowledge-base-description "Retrieve the signed-in user's Microsoft 365 work context through Foundry IQ." `
                --toolbox-description "Foundry IQ knowledge-base tools backed by a Work IQ knowledge source."
        }
    }
}
if ($workIqReady) {
    $null = Invoke-Step "Work IQ connection and toolbox" { & $python infra\create-toolbox-workiq.py --apply }
}
if ($searchReady) { Log "READY: Foundry IQ notebooks" } else { Log "NOT READY: Foundry IQ notebooks" }

# Stage 4: Work IQ sample emails (seed-emails.ps1 reads the service principal from the environment)
$null = Invoke-Step "Seed sample emails" {
    powershell -ExecutionPolicy Bypass -File infra\seed-emails.ps1 -UserUpn $LabUserUpn
}

# Stage 5: azd environment for the attendee, then hosted agents deployed as the service principal
$azdEnvReady = Invoke-Step "Create azd environment" {
    azd env new prel42 --subscription $env:AZURE_SUBSCRIPTION_ID --location $env:AZURE_LOCATION --no-prompt
    azd env select prel42
    $values = [ordered]@{}
    foreach ($output in $outputs.PSObject.Properties) {
        $values[$output.Name] = [string]$output.Value.value
    }
    foreach ($line in Get-Content .env) {
        if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)=(.*)$') {
            $values[$Matches[1]] = $Matches[2]
        }
    }
    foreach ($key in $values.Keys) {
        # Windows PowerShell drops empty native arguments, so skip unset values.
        if ($values[$key]) {
            azd env set $key $values[$key]
        }
    }
}
$null = Invoke-Step "Install azd AI agents extension (lab user)" { azd extension install azure.ai.agents }

if ($azdEnvReady) {
    # A separate azd config directory keeps the service principal sign-in away from the attendee's azd sign-in.
    $attendeeAzdConfigDir = $env:AZD_CONFIG_DIR
    $env:AZD_CONFIG_DIR = Join-Path $env:TEMP "azd-lab-setup"
    try {
        $null = Invoke-Step "Sign azd in as the service principal" {
            azd auth login --client-id $env:AZURE_CLIENT_ID --client-secret $env:AZURE_CLIENT_SECRET --tenant-id $env:AZURE_TENANT_ID
        }
        $null = Invoke-Step "Install azd AI agents extension (setup)" { azd extension install azure.ai.agents }
        # The postdeploy hook grants each deployed agent identity its Search and Foundry roles.
        $agentsReady = Invoke-Step "Deploy hosted agents" { azd deploy --no-prompt }
    }
    finally {
        azd auth logout 2>&1 | Out-Null
        Remove-Item $env:AZD_CONFIG_DIR -Recurse -Force -ErrorAction SilentlyContinue
        $env:AZD_CONFIG_DIR = $attendeeAzdConfigDir
    }
}
if ($agentsReady) { Log "READY: Agents" } else { Log "NOT READY: Hosted agents (local runs may still work)" }

# Stage 6: Fabric IQ items, slowest last. Each step depends on the one before it.
$fabricSteps = @(
    @("Fabric lakehouse and ontology", "infra\create-lakehouse.py"),
    @("Fabric product review graph", "infra\create-fabric-graph.py"),
    @("Fabric web analytics lakehouse", "infra\create-web-analytics-lakehouse.py"),
    @("Fabric web analytics semantic model", "infra\create-semantic-model.py"),
    @("Fabric web analytics report", "infra\create-web-analytics-report.py"),
    @("Fabric data agent", "infra\create-fabric-data-agent.py")
)
$fabricReady = $true
foreach ($step in $fabricSteps) {
    $stepScript = $step[1]
    if (-not (Invoke-Step $step[0] { & $python $stepScript })) {
        Log "Skipping the remaining Fabric steps."
        $fabricReady = $false
        break
    }
}
if ($fabricReady) { Log "READY: Fabric IQ notebooks" } else { Log "NOT READY: Fabric IQ notebooks" }

# Stage 7: fill the MCP server placeholders now that the Fabric IDs exist
$null = Invoke-Step "Fill .vscode\mcp.json" {
    $envValues = @{}
    foreach ($line in Get-Content .env) {
        if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)=(.*)$') {
            $envValues[$Matches[1]] = $Matches[2].Trim("'`"")
        }
    }
    $mcpPath = ".vscode\mcp.json"
    $mcpJson = Get-Content $mcpPath -Raw
    foreach ($name in "AZURE_AI_SEARCH_SERVICE_NAME", "FABRIC_WORKSPACE_ID", "FABRIC_ONTOLOGY_ID") {
        if ($envValues[$name]) {
            $mcpJson = $mcpJson -replace "\{$name\}", $envValues[$name]
        }
    }
    Set-Content $mcpPath $mcpJson -NoNewline
    $global:LASTEXITCODE = 0
}

Log "=== Lab setup completed ==="
