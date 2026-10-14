# Skillable teardown action: remove the lab user from the license groups.
# All role assignments are scoped to resources in the lab resource group, so they are removed with it.
$securityGroups = @("_Skillable-M365Copilot", "_Skillable-CopilotStudio", "_Skillable-E5", "_Skillable Events GHE w/ Copilot")

foreach ($secgrp in $securityGroups) {
    Remove-AzADGroupMember -GroupDisplayName $secgrp -MemberUserPrincipalName "@lab.CloudPortalCredential(User1).Username"
}
