# Infrastructure

`main.bicep` is resource-group scoped, so the same template serves both deployment paths:

- **Self-deployment with `azd`**: `azd up` provisions the template, runs `hooks/postprovision.*`, deploys the agents in `../azure.yaml`, and runs `hooks/postdeploy.*`. See [Deploy to your own Azure subscription](../docs/deploy-yourself.md).
- **Hosted Skillable lab**: the lifecycle scripts below deploy the template with `az deployment group create` and run the same setup scripts as the lab service principal.

## Bicep

| File | Creates |
| --- | --- |
| `main.bicep` | Entry point. Composes the modules and emits the outputs that `setup-env.py`, `azure.yaml`, and the setup scripts read |
| `core/ai/ai-project.bicep` | Foundry account and project, model deployments, monitoring, project connections, and role assignments for the user and the optional setup service principal |
| `core/search/azure_ai_search.bicep` | Azure AI Search (serverless by default) and its role assignments |
| `core/storage/storage.bicep` | Storage account and its project connection |
| `core/fabric/fabric-capacity.bicep` | Optional Fabric capacity |
| `core/webiq/webiq.bicep` | Web IQ grounding account. Its key comes from the Web IQ portal, not Azure |

## Setup scripts

The setup scripts run as the signed-in azd user, or as a service principal when `AZURE_CLIENT_ID` and `AZURE_CLIENT_SECRET` are set (see `setup_credential.py`). They share state through the repository root `.env` file, so run them from the repository root.

| Script | Purpose |
| --- | --- |
| `setup-env.py` | Writes the deployment outputs to `.env` |
| `create-workiq-entra.py` | Creates the Work IQ Entra app and federated credential that Azure AI Search uses |
| `create-search-indexes.py` | Restores the HR and health indexes and creates the agents' knowledge bases |
| `create-toolbox-foundryiq.py` | Creates the Foundry IQ toolboxes |
| `create-toolbox-workiq.py` | Creates the Work IQ OAuth connection and toolbox |
| `create-workiq-mcp.py` | Creates the direct Work IQ MCP OAuth connection for `agent-workiq-maf`, without a toolbox |
| `workiq_oauth.py` | Shares app registration, consent, and OAuth connection setup between the two Work IQ helpers |
| `create-lakehouse.py`, `create-fabric-graph.py`, `create-web-analytics-lakehouse.py`, `create-semantic-model.py`, `create-web-analytics-report.py`, `create-fabric-data-agent.py` | Create the Fabric items, in that order |
| `postdeploy.py` | Grants each deployed agent identity its Search and Foundry roles |
| `delete-workiq-entra.py` | Deletes the Work IQ Entra app (self-deployment cleanup) |

## Skillable lab lifecycle

Configure these as lifecycle actions in the lab profile, in this order.

| When | Script | What it does |
| --- | --- | --- |
| Start | `lifecycle_github_repo_download.ps1` | Downloads this repository to `Desktop\ignite26-PREL42`, with retries. Set `$token` to a read-only GitHub token while the repository is private |
| Start | `lifecycle_bicep_deployment.ps1` | Signs in as the lab service principal, writes `Desktop\deploy-background.ps1`, and launches it, then exits (Skillable's ~600 second limit) |
| Background | `Desktop\deploy-background.ps1` | Deploys `main.bicep` to the lab resource group's region with an F16 Fabric capacity, then runs `setup-lab.ps1` |
| Background | `setup-lab.ps1` | Installs Python dependencies with `uv`, writes `.env`, creates the knowledge bases and toolboxes, seeds the sample emails (`seed-emails.ps1`), creates the azd environment, deploys the hosted agents, and creates the Fabric items |
| Teardown | `lifecycle_teardown_workiq_entra.ps1` | Deletes the Work IQ Entra app. Run it before the resource group is deleted |
| Teardown | `lifecycle_teardown_fabric.ps1` | Deletes the Fabric workspaces on the lab capacity, then the capacity |
| Teardown | `lifecycle_teardown_cogservices.ps1` | Deletes and purges the Foundry account so its name and quota are released |
| Teardown | `lifecycle_teardown_license.ps1` | Removes the lab user from the license groups |

The scripts reference the resource group as `@lab.CloudResourceGroup(PREL42-ResourceGroup)`. Update that name if the lab profile uses a different one.

Progress is logged to `Desktop\lifecycle-log.txt`. Each stage logs `OK` or `FAILED`, and `setup-lab.ps1` logs `READY` or `NOT READY` for the Foundry IQ notebooks, the agents, and the Fabric IQ notebooks.

### Rerun a failed setup

`setup-lab.ps1` is safe to rerun on the lab VM. Set the service principal variables, then pass the saved deployment outputs:

```powershell
$env:AZURE_CLIENT_ID = "<app id>"
$env:AZURE_CLIENT_SECRET = "<secret>"
$env:AZURE_TENANT_ID = "<tenant id>"
$env:AZURE_SUBSCRIPTION_ID = "<subscription id>"
.\infra\setup-lab.ps1 -OutputsFile infra\deployment-outputs.json -LabUserUpn <upn> -LabUserObjectId <object id>
```

### Lab profile requirements

- VM: Python 3.10+, Visual Studio Code with the Python and Jupyter extensions, Azure CLI, Azure Developer CLI, and PowerShell 7 (`pwsh`, used by the azd deploy hooks).
- Service principal: Owner on the lab resource group, Cloud Application Administrator (Work IQ Entra app and consent), the admin-consented Microsoft Graph `Mail.Send` application permission (email seeding), and the Fabric tenant setting that allows service principals to use Fabric APIs.
- Lab user: Microsoft 365 Copilot and Copilot Studio licenses (the `_Skillable-*` groups) for Work IQ.
