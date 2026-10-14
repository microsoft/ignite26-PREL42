# Skillable teardown action: delete the lab's Work IQ Entra application.
# create-workiq-entra.py names the app "PREL42-WorkIQ-<search service name>", and
# create-toolbox-workiq.py reuses it, so deleting it also removes the toolbox client secret.
# Run this before the resource group is deleted, because it looks up the Search service name.
$resourceGroupName = "@lab.CloudResourceGroup(PREL42-ResourceGroup).Name"
$searchServices = Get-AzResource -ResourceGroupName $resourceGroupName -ResourceType "Microsoft.Search/searchServices"

foreach ($search in $searchServices) {
    $displayName = "PREL42-WorkIQ-$($search.Name)"
    foreach ($app in (Get-AzADApplication -DisplayName $displayName)) {
        Remove-AzADApplication -ObjectId $app.Id
        Write-Output "Deleted Entra application: $displayName ($($app.AppId))"
    }
}
