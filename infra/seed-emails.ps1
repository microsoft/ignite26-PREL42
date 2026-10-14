<#
.SYNOPSIS
    Seeds the Work IQ sample emails into the lab user's mailbox via Microsoft Graph.
.DESCRIPTION
    Sends each fixture in data/workiq-fixtures/ from the lab user to themselves, using the
    service principal's app-only token. Requires the Mail.Send application permission (admin-consented).
    Each fixture starts with "From: <name>" and "Subject: <subject>" lines, then a blank line and the body.
.PARAMETER UserUpn
    The lab user's UPN (email) to send messages to/from.
.PARAMETER TenantId
    The Entra tenant ID for token acquisition. Defaults to AZURE_TENANT_ID.
.PARAMETER ClientId
    The service principal's app/client ID. Defaults to AZURE_CLIENT_ID.
.PARAMETER ClientSecret
    The service principal's client secret. Defaults to AZURE_CLIENT_SECRET, so it stays off the command line.
#>
param(
    [Parameter(Mandatory)][string]$UserUpn,
    [string]$TenantId = $env:AZURE_TENANT_ID,
    [string]$ClientId = $env:AZURE_CLIENT_ID,
    [string]$ClientSecret = $env:AZURE_CLIENT_SECRET
)

$ErrorActionPreference = "Stop"

function Log {
    param([string]$msg)
    # Write-Host keeps log lines out of function return values.
    Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $msg"
}

function Get-GraphToken {
    $body = @{
        grant_type    = "client_credentials"
        client_id     = $ClientId
        client_secret = $ClientSecret
        scope         = "https://graph.microsoft.com/.default"
    }
    $response = Invoke-RestMethod -Method POST `
        -Uri "https://login.microsoftonline.com/$TenantId/oauth2/v2.0/token" `
        -ContentType "application/x-www-form-urlencoded" `
        -Body $body
    return $response.access_token
}

function Send-LabMail {
    param(
        [string]$Token,
        [hashtable]$Mail
    )
    $headers = @{
        Authorization  = "Bearer $Token"
        "Content-Type" = "application/json; charset=utf-8"
    }
    $url = "https://graph.microsoft.com/v1.0/users/$UserUpn/sendMail"
    $payload = @{ message = $Mail; saveToSentItems = $false } | ConvertTo-Json -Depth 10
    for ($attempt = 1; $attempt -le 3; $attempt++) {
        try {
            Invoke-RestMethod -Method POST -Uri $url -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($payload)) -TimeoutSec 60
            return $true
        } catch {
            $errBody = ""
            if ($_.Exception.Response) {
                $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
                $errBody = $reader.ReadToEnd()
                $reader.Close()
            }
            Log "ERROR attempt $attempt ($($_.Exception.Response.StatusCode)): $errBody"
            if ($attempt -lt 3) {
                Start-Sleep -Seconds 5
            }
        }
    }
    return $false
}

function Read-Fixture {
    param([string]$Path)
    $lines = Get-Content -Path $Path -Encoding UTF8
    $sender = ($lines[0] -replace '^From:\s*', '').Trim()
    $subject = ($lines[1] -replace '^Subject:\s*', '').Trim()
    $body = ($lines | Select-Object -Skip 3) -join "`n"
    return @{
        subject      = $subject
        from         = @{ emailAddress = @{ name = $sender; address = $UserUpn } }
        toRecipients = @(@{ emailAddress = @{ name = "Me"; address = $UserUpn } })
        body         = @{ contentType = "Text"; content = $body }
    }
}

$fixtureDir = Join-Path (Split-Path -Parent $PSScriptRoot) "data\workiq-fixtures"
$fixtures = Get-ChildItem -Path $fixtureDir -Filter "*.txt" | Sort-Object Name
Log "Sending $($fixtures.Count) emails to mailbox: $UserUpn"

$token = Get-GraphToken
$failed = 0
foreach ($fixture in $fixtures) {
    $mail = Read-Fixture -Path $fixture.FullName
    if (Send-LabMail -Token $token -Mail $mail) {
        Log "Sent: $($mail.subject)"
    } else {
        Log "FAILED: $($mail.subject)"
        $failed++
    }
    Start-Sleep -Seconds 1
}

if ($failed -gt 0) {
    exit 1
}
Log "Email seeding complete!"
