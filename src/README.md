# Source

Microsoft Agent Framework agents, each deployable as a Foundry Hosted Agent:

| Agent | How it reaches its data |
| --- | --- |
| `agent-foundryiq-mcp` | Connects to the knowledge base through its Foundry IQ MCP endpoint |
| `agent-workiq-maf` | Direct Work IQ MCP with local browser sign-in or hosted OAuth identity passthrough |

## Try Work IQ through direct MCP

`agent-workiq-maf` exposes the Responses protocol locally and in Microsoft Foundry.
Both modes use the same Work IQ MCP endpoint and allow only its read-only `ask` tool.
Local sign-in uses the same app registration and delegated `WorkIQAgent.Ask` scope as
[`workiq-mcp.ipynb`](../notebooks/workiq-mcp.ipynb). Hosted mode uses a direct MCP project connection
with **OAuth identity passthrough**. Neither mode uses RemoteA2A.

Complete the [Work IQ admin setup](../docs/workiq-admin-setup.md) and configure the repository-root `.env`
with `WORK_IQ_SEARCH_ENTRA_APP_ID`, `WORK_IQ_SEARCH_ENTRA_TENANT_ID`, `FOUNDRY_PROJECT_ENDPOINT`, and
`AZURE_AI_MODEL_DEPLOYMENT_NAME`. Sign in to `azd` for local model access and remote invocation.
The Work IQ user needs a Microsoft 365 Copilot license.

### Test locally first

From the repository root, start the agent and local playground:

```powershell
azd ai agent run agent-workiq-maf
```

Complete the Work IQ browser sign-in with your lab user account. The server becomes ready after
sign-in; if the playground opens before then, wait for the terminal to show
**Running on http://127.0.0.1:8088** before sending a message.
In the local playground, ask:

> Summarize my recent emails about the Professional Claw Hammer. Who sent them, and what actions do they request?

No custom token header or second terminal is needed for the local playground. The local agent keeps
MSAL's token cache in memory and silently renews the signed-in user's access token for each request.
If sign-in is revoked or requires interaction again, stop the agent with **Ctrl+C** and restart it.
Restart to change users, too.

This is a **single-user local development mode**: all headerless requests use the user who signed in
when the agent started. The server binds to loopback; do not share, expose, or make its port public.
In GitHub Codespaces, complete the device-code sign-in shown in the terminal and keep the port private.

For an optional command-line check, leave the server running and use a second terminal:

```powershell
uv run --project src\agent-workiq-maf python src\agent-workiq-maf\invoke.py --local "Summarize my recent emails about the Professional Claw Hammer. Who sent them, and what actions do they request?"
```

This client signs in separately, forwards its own Work IQ token in `x-client-workiq-access-token`,
checks the Responses completion status, and prints the answer. An explicit token takes precedence
over local sign-in.

### Then test in Microsoft Foundry

The setup hooks create the direct `work-iq-mcp-connection` OAuth connection. For an existing lab
that predates this connection, an administrator must run the following once from the repository root
with the configured lab environment and the permissions described in [admin setup](../docs/workiq-admin-setup.md):

```powershell
uv run python infra\create-workiq-mcp.py --apply
```

After a successful local call, stop the local server and deploy to the configured project:

```powershell
azd deploy agent-workiq-maf
azd ai agent show agent-workiq-maf
```

Open the **Playground URL**, sign in with your lab account, and ask the same email question.
If Work IQ requests authorization, select **Open consent**, sign in with that account, review the request,
and allow access. Return to the playground and send the question again if the consent turn has stopped.
Inspect **Traces** beneath the answer to see the direct Work IQ MCP call and returned context.

The hosted agent registers the MCP tool with `FoundryChatClient.get_mcp_tool`, referencing
`work-iq-mcp-connection`. Microsoft Foundry manages each user's OAuth consent, delegated tokens,
and renewal. The connection holds the app secret; the agent does not load it or receive a Work IQ token
in a custom header. Each request gets a fresh agent/client with the platform's trusted caller context.
The model uses managed identity; Work IQ uses the signed-in user's delegated identity.
See [MCP OAuth identity passthrough](https://learn.microsoft.com/azure/foundry/agents/how-to/mcp-authentication).

The caller needs **Foundry Agent Consumer** or an appropriate broader role. The standard playground flow
does not impersonate another user or require the custom `UserIdentityImpersonation/action` permission.
The hosting SDK is pinned to a consent-capable release compatible with the local MCP 1.x transport.

**Hosted mode does not use the local sign-in or its token cache.** It does not share one user's tokens
across callers, send tokens to the model, or fall back to application-only Work IQ access.
Do not capture `Authorization` or local
`x-client-workiq-access-token` headers in proxy or telemetry header logging.

The optional `invoke.py --remote` client uses ordinary Microsoft Foundry authentication. Complete
Work IQ authorization in the hosted playground before using it; it does not automate browser consent.

For offline checks, run `uv run python -m unittest -v test_main` from the `agent-workiq-maf` directory.
These check native Responses consent events, request-scoped agent cleanup, and local authentication.
They do not establish live Work IQ access. Verify a local answer first, then a hosted playground answer,
and repeat with two users to confirm identity separation.

The notebooks are in [`notebooks/`](../notebooks/).
