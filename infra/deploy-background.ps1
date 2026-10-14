# Background deployment for the Skillable lab, launched by lifecycle_bicep_deployment.ps1.
# Deploys infra\main.bicep into the lab resource group, then runs infra\setup-lab.ps1.

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
$ErrorActionPreference = "Continue"

$repoRoot = $env:BG_REPO_ROOT
$logFile = $env:BG_LOG_FILE

function Log {
    param([string]$msg)
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $msg"
    Write-Host $line
    Add-Content -Path $logFile -Value $line -Encoding UTF8
}

Log "=== Background deploy script started ==="

$resourceGroupName = $env:BG_RESOURCE_GROUP
$location = "canadaeast"
$deploymentName = "prel42"
$foundryNameSuffix = [Guid]::NewGuid().ToString("N").Substring(0, 8)
$outputsFile = Join-Path $repoRoot "infra\deployment-outputs.json"
$deployErrorsFile = Join-Path $env:TEMP "prel42-deploy-stderr.txt"

try {
    Log "Starting Bicep deployment in $location..."
    $deploymentOutput = az deployment group create `
      --name $deploymentName `
      --resource-group $resourceGroupName `
      --template-file (Join-Path $repoRoot "infra\main.bicep") `
      --parameters location=$location `
      --parameters principalId=$env:BG_LAB_USER_OID `
      --parameters principalType=User `
      --parameters setupServicePrincipalId=$env:BG_SP_OBJECT_ID `
      --parameters foundryNameSuffix=$foundryNameSuffix `
      --parameters enableFabricCapacity=true `
      --parameters fabricSkuName=F16 `
      --parameters fabricAdminUpn=$env:BG_LAB_USER_UPN `
      --query properties.outputs -o json 2> $deployErrorsFile

    if ($LASTEXITCODE -ne 0) {
        Log "Deployment failed (exit code $LASTEXITCODE):"
        Get-Content $deployErrorsFile | Add-Content -Path $logFile -Encoding UTF8
        $opErrors = az deployment operation group list `
          --resource-group $resourceGroupName `
          --name $deploymentName `
          --query "[?properties.provisioningState=='Failed'].{Resource:properties.targetResource.resourceName, Type:properties.targetResource.resourceType, Error:properties.statusMessage.error}" `
          -o json 2>&1
        Log "Operation errors:"
        Add-Content -Path $logFile -Value $opErrors -Encoding UTF8
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
