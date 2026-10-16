# Lifecycle — Write a self-contained background script that handles everything
# after az login: deploy, fetch outputs, run setup.
# This lets the Skillable lifecycle action exit quickly (< 600s).
# Run the repo download LCA first so the repository is at $repoRoot.

$repoRoot = "C:\Users\LabUser\Desktop\ignite26-PREL42"
$bgScriptPath = "C:\Users\LabUser\Desktop\deploy-background.ps1"
$logFile = "C:\Users\LabUser\Desktop\lifecycle-log.txt"

$bgScript = @'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
$ErrorActionPreference = "Continue"
$logFile = $env:BG_LOG_FILE
function Log {
    param([string]$msg)
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $msg"
    Write-Host $line
    Add-Content -Path $logFile -Value $line -Encoding UTF8
}

Log "=== Background deploy script started ==="

$repoRoot = $env:BG_REPO_ROOT
$resourceGroupName = $env:BG_RESOURCE_GROUP
$outputsFile = Join-Path $repoRoot "infra\deployment-outputs.json"
$deployErrorsFile = Join-Path $env:TEMP "prel42-deploy-stderr.txt"

try {
    az config set core.only_show_errors=yes --only-show-errors
    az config set bicep.use_binary_from_path=false --only-show-errors

    # Deploy to the lab resource group's region, which the Skillable profile sets.
    $location = az group show --name $resourceGroupName --query location -o tsv
    if ([string]::IsNullOrWhiteSpace($location)) {
        Log "ERROR: Could not read location of resource group $resourceGroupName"
        Log "=== Background deploy script FAILED ==="
        exit 1
    }
    Log "Resource group $resourceGroupName is in $location"

    $suffix = [Guid]::NewGuid().ToString("N").Substring(0, 8)
    $deploymentName = "prel42-$suffix"

    Log "Starting Bicep deployment $deploymentName..."
    $deploymentOutput = az deployment group create `
      --name $deploymentName `
      --resource-group $resourceGroupName `
      --template-file (Join-Path $repoRoot "infra\main.bicep") `
      --parameters location=$location `
      --parameters principalId=$env:BG_LAB_USER_OID `
      --parameters principalType=User `
      --parameters setupServicePrincipalId=$env:BG_SP_OBJECT_ID `
      --parameters foundryNameSuffix=$suffix `
      --parameters enableFabricCapacity=true `
      --parameters fabricSkuName=F16 `
      --parameters fabricAdminUpn=$env:BG_LAB_USER_UPN `
      --query properties.outputs -o json 2> $deployErrorsFile

    if ($LASTEXITCODE -ne 0) {
        Log "Deployment failed (exit code $LASTEXITCODE):"
        Get-Content $deployErrorsFile | Add-Content -Path $logFile -Encoding UTF8
        $exists = az deployment group show --resource-group $resourceGroupName --name $deploymentName --query name -o tsv 2>$null
        if ($exists) {
            $opErrors = az deployment operation group list `
              --resource-group $resourceGroupName `
              --name $deploymentName `
              --query "[?properties.provisioningState=='Failed'].{Resource:properties.targetResource.resourceName, Type:properties.targetResource.resourceType, Error:properties.statusMessage.error}" `
              -o json 2>&1
            Log "Operation errors:"
            Add-Content -Path $logFile -Value $opErrors -Encoding UTF8
        } else {
            Log "Deployment was never created in Azure (validation or CLI error above)."
        }
        Log "=== Background deploy script FAILED ==="
        exit 1
    }
    Log "Deployment succeeded."
    Set-Content -Path $outputsFile -Value $deploymentOutput -Encoding UTF8

    # The setup scripts authenticate as the service principal through these variables.
    $env:AZURE_CLIENT_ID = $env:BG_CLIENT_ID
    $env:AZURE_CLIENT_SECRET = $env:BG_CLIENT_SECRET
    $env:AZURE_TENANT_ID = $env:BG_TENANT_ID
    $env:AZURE_SUBSCRIPTION_ID = $env:BG_SUBSCRIPTION_ID

    & (Join-Path $repoRoot "infra\setup-lab.ps1") `
      -OutputsFile $outputsFile `
      -LabUserUpn $env:BG_LAB_USER_UPN `
      -LabUserObjectId $env:BG_LAB_USER_OID `
      -WebIqKey $env:BG_WEB_IQ_KEY `
      -LogFile $logFile
}
finally {
    az logout 2>&1 | Out-Null
    if ($env:AZURE_CONFIG_DIR -and (Test-Path $env:AZURE_CONFIG_DIR)) {
        Remove-Item $env:AZURE_CONFIG_DIR -Recurse -Force -ErrorAction SilentlyContinue
    }
    Log "=== Background deploy script finished ==="
}
'@

# Write the background script to disk
Set-Content -Path $bgScriptPath -Value $bgScript -Encoding UTF8

# --- Quick inline work that must finish within ~600s ---

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
function Log {
    param([string]$msg)
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $msg"
    Write-Host $line
    Add-Content -Path $logFile -Value $line -Encoding UTF8
}
Log "=== Lifecycle script started ==="

$clientId = "@lab.CloudSubscription.AppId"
$clientSecret = "@lab.CloudSubscription.AppSecret"
$tenantId = "@lab.CloudSubscription.TenantId"
$subscriptionId = "@lab.CloudSubscription.Id"
$resourceGroupName = "@lab.CloudResourceGroup(PREL42-ResourceGroup).Name"
$labUserUpn = "@lab.CloudPortalCredential(User1).Username"
# Web IQ key for the Web IQ exercise and foundryiq-webiq.ipynb, from the Web IQ portal.
$webIqKey = ""

$bicepFilePath = Join-Path $repoRoot "infra\main.bicep"
if (-not (Test-Path $bicepFilePath)) {
    Log "ERROR: Bicep file not found at: $bicepFilePath"
    throw "Bicep file not found at: $bicepFilePath"
}

# Keep the service principal's az session out of the lab user's default Azure CLI profile.
$env:AZURE_CONFIG_DIR = "C:\Users\LabUser\.azure-lab-setup"

Log "Logging in to Azure..."
az login --service-principal -u $clientId -p $clientSecret --tenant $tenantId --subscription $subscriptionId --skip-subscription-discovery | Out-Null
az config set core.only_show_errors=yes --only-show-errors
az config set bicep.use_binary_from_path=false --only-show-errors

$labUserObjectId = az ad user show --id $labUserUpn --query id -o tsv
# Bicep adds the service principal as a Fabric capacity admin and grants it setup roles.
$spObjectId = az ad sp show --id $clientId --query id -o tsv
Log "Lab user object ID: $labUserObjectId"
Log "SP Object ID: $spObjectId"

# Pass values to background script via environment variables
# (the az CLI session is cached in AZURE_CONFIG_DIR, which the background process inherits)
$env:BG_REPO_ROOT = $repoRoot
$env:BG_LOG_FILE = $logFile
$env:BG_SUBSCRIPTION_ID = $subscriptionId
$env:BG_RESOURCE_GROUP = $resourceGroupName
$env:BG_LAB_USER_OID = $labUserObjectId
$env:BG_LAB_USER_UPN = $labUserUpn
$env:BG_SP_OBJECT_ID = $spObjectId
$env:BG_CLIENT_ID = $clientId
$env:BG_CLIENT_SECRET = $clientSecret
$env:BG_TENANT_ID = $tenantId
$env:BG_WEB_IQ_KEY = $webIqKey

Log "Launching background deploy process..."
Start-Process -FilePath "powershell.exe" `
  -ArgumentList "-ExecutionPolicy Bypass -File `"$bgScriptPath`"" `
  -WindowStyle Hidden

Log "=== Lifecycle script exiting (background process handles deployment) ==="
