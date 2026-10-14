# Skillable lifecycle action: sign in as the lab service principal and start the background deployment.
# Skillable stops lifecycle actions after ~600 seconds, so the long-running work happens in
# infra\deploy-background.ps1, which this script launches and does not wait for.
# Run lifecycle_github_repo_download.ps1 first so the repository is on the desktop.

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$repoRoot = "C:\Users\LabUser\Desktop\ignite26-PREL42"
$logFile = "C:\Users\LabUser\Desktop\lifecycle-log.txt"

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
# Optional Web IQ key for foundryiq-webiq.ipynb; leave empty until key distribution is decided.
$webIqKey = ""

$backgroundScript = Join-Path $repoRoot "infra\deploy-background.ps1"
if (-not (Test-Path $backgroundScript)) {
    Log "ERROR: Background script not found at: $backgroundScript"
    throw "Background script not found at: $backgroundScript"
}

# Keep the service principal's az session out of the lab user's default Azure CLI profile.
$env:AZURE_CONFIG_DIR = "C:\Users\LabUser\.azure-lab-setup"

Log "Logging in to Azure as the lab service principal..."
az login --service-principal -u $clientId -p $clientSecret --tenant $tenantId --subscription $subscriptionId --skip-subscription-discovery | Out-Null
az config set core.only_show_errors=yes --only-show-errors
az config set bicep.use_binary_from_path=false --only-show-errors

$labUserObjectId = az ad user show --id $labUserUpn --query id -o tsv
$spObjectId = az ad sp show --id $clientId --query id -o tsv
Log "Lab user object ID: $labUserObjectId"
Log "Service principal object ID: $spObjectId"

# The background process inherits these values; the az token cache stays in AZURE_CONFIG_DIR.
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
  -ArgumentList "-ExecutionPolicy Bypass -File `"$backgroundScript`"" `
  -WindowStyle Hidden

Log "=== Lifecycle script exiting (background process handles deployment) ==="
