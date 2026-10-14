# Skillable teardown action: delete the lab's Fabric workspaces, then its Fabric capacity.
# Deleting the capacity releases regional quota; without this, capacities from ended lab sessions
# accumulate and block future deployments. Workspaces are deleted first because they are
# tenant-wide objects that outlive the capacity.
$resourceGroupName = "@lab.CloudResourceGroup(PREL42-ResourceGroup).Name"
$fabricApi = "https://api.fabric.microsoft.com/v1"
$fabricCapacities = Get-AzResource -ResourceGroupName $resourceGroupName -ResourceType "Microsoft.Fabric/capacities"

try {
    $accessToken = Get-AzAccessToken -ResourceUrl "https://api.fabric.microsoft.com"
    $token = $accessToken.Token
    if ($token -is [securestring]) {
        $token = [System.Net.NetworkCredential]::new("", $token).Password
    }
    $headers = @{ Authorization = "Bearer $token" }
    $capacities = (Invoke-RestMethod -Uri "$fabricApi/capacities" -Headers $headers).value
    $workspaces = (Invoke-RestMethod -Uri "$fabricApi/workspaces" -Headers $headers).value
    foreach ($fc in $fabricCapacities) {
        $capacity = $capacities | Where-Object { $_.displayName -eq $fc.Name } | Select-Object -First 1
        if (-not $capacity) { continue }
        foreach ($workspace in ($workspaces | Where-Object { $_.capacityId -eq $capacity.id })) {
            Invoke-RestMethod -Method DELETE -Uri "$fabricApi/workspaces/$($workspace.id)" -Headers $headers | Out-Null
            Write-Output "Deleted Fabric workspace: $($workspace.displayName)"
        }
    }
} catch {
    Write-Output "WARNING: Fabric workspace cleanup failed: $($_.Exception.Message)"
}

foreach ($fc in $fabricCapacities) {
    Remove-AzResource -ResourceId $fc.ResourceId -Force
    Write-Output "Deleted Fabric capacity: $($fc.Name)"
}
