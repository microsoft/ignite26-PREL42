# Admin Setup — Work IQ

**Who this is for**: a tenant admin (Cloud Application Administrator or above). You are enabling a
developer to run the Work IQ notebooks and `agent-workiq-maf` against your tenant's Microsoft 365
work data.

**Time**: ~5 minutes. **Result**: a Work IQ Entra app that the notebooks sign in with and that Azure AI Search
trusts through a federated credential.

Work IQ always runs as the **signed-in user** and honors Microsoft 365 permissions and sensitivity
labels. There is no application-only mode. Work IQ usage is billed through **Copilot credits**: configure a
usage-based billing plan in Copilot Studio and assign each user to it. Users on a **Microsoft 365 Copilot
license** can also call the Work IQ gateway directly (propagation takes 15–30 minutes).

## Create the app

A Global Administrator enables the Work IQ API in the tenant once. Then run, as a Cloud Application
Administrator or an identity with the Microsoft Graph application permissions `Application.ReadWrite.All`,
`DelegatedPermissionGrant.ReadWrite.All`, and `Directory.Read.All`:

```bash
az ad sp create --id fdcc1f02-fc51-4226-8753-f668596af7f7   # Work IQ service principal, if missing
uv run python infra/create-workiq-entra.py --apply
```

The script creates a single-tenant public-client app that exposes `access_as_user`, grants tenant-wide admin
consent for `WorkIQAgent.Ask`, adds the federated credential for the Azure AI Search managed identity, and
writes `WORK_IQ_SEARCH_ENTRA_APP_ID`, `WORK_IQ_SEARCH_ENTRA_TENANT_ID`, and
`WORK_IQ_SEARCH_FEDERATED_CREDENTIAL_ID` to `.env`. The `workiq-*` notebooks use the same app for sign-in,
so no separate app registration is needed. Each direct Work IQ notebook reads the
`WORK_IQ_SEARCH_ENTRA_APP_ID` and `WORK_IQ_SEARCH_ENTRA_TENANT_ID` values directly and shows its own
MSAL browser sign-in code without shared authentication helpers.

## For the direct Work IQ MCP hosted agent

`agent-workiq-maf` uses a direct **`RemoteTool`** project connection targeting
`https://workiq.svc.cloud.microsoft/mcp`, with **OAuth identity passthrough** and the delegated scopes
`api://workiq.svc.cloud.microsoft/WorkIQAgent.Ask` and `offline_access`.
It does not use the `work_iq_preview` tool.

`infra/create-workiq-mcp.py` reuses the notebook app, grants admin consent, creates the
`work-iq-mcp-connection` OAuth2 connection, and registers the returned Microsoft Foundry callback URI
as a web redirect on the app. It creates a client secret only when creating the connection and sends
that secret directly to Microsoft Foundry, not to `.env` or the agent container.
The setup hooks run this helper for both self-deployment and Skillable provisioning.
For an existing lab, run it with the configured environment and the admin permissions above:

```powershell
uv run python infra\create-workiq-mcp.py --apply
```

Deploy the updated agent after the connection is ready. Each user authorizes Work IQ in the
Microsoft Foundry playground; Microsoft Foundry manages their delegated tokens and renewal.
The agent forwards trusted platform caller context to the model/tool service, not a client-supplied
Work IQ token or impersonated identity. Local testing keeps the notebook-style browser sign-in.
See [MCP authentication](https://learn.microsoft.com/azure/foundry/agents/how-to/mcp-authentication)
and the [local-to-hosted steps](../src/README.md#try-work-iq-through-direct-mcp).

## Which Entra app is which

One Work IQ Entra app (created by `infra/create-workiq-entra.py`, `WORK_IQ_SEARCH_ENTRA_*`) serves every Work IQ path:

| Path | How the app is used |
|---|---|
| `foundryiq-workiq.ipynb` | Azure AI Search calls Work IQ as the app through a federated credential (billed with Copilot credits) |
| Direct `workiq-*` notebooks | Interactive sign-in for `api://workiq.svc.cloud.microsoft/WorkIQAgent.Ask` |
| `agent-workiq-maf` | Local: notebook-style browser sign-in. Hosted: per-user OAuth identity passthrough through the direct MCP connection; the app secret stays in Microsoft Foundry, not the agent |

To test direct Work IQ MCP, follow the
[Agent Framework local-to-hosted steps](../src/README.md#try-work-iq-through-direct-mcp).
This reuses the notebook app. The hosted agent's
managed identity provides model access, not delegated Work IQ access; each user consents separately.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `403 Forbidden` with no scope message | User missing the Microsoft 365 Copilot license — assign and wait 15–30 min |
| `AADSTS65001: consent required` | Re-run step 6 (admin consent) |
| `401 Unauthorized` | Token `aud` must be `api://workiq.svc.cloud.microsoft` |
| `requires a signed-in user` from the hosted agent | Work IQ needs user context — invoke via the signed-in playground or the Teams digital worker, not an app identity |
| Empty / degraded responses | License just assigned; index not ready — wait 15–30 min |
