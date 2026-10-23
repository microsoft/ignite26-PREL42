# Source

Microsoft Agent Framework agents, each deployable as a Foundry Hosted Agent:

| Agent | How it reaches its data |
| --- | --- |
| `agent-foundryiq-api` | Calls the knowledge base retrieval API from a custom Python tool |
| `agent-foundryiq-mcp` | Connects to the knowledge base through its Foundry IQ MCP endpoint |
| `agent-toolbox-foundryiq` | Uses a Foundry toolbox with the knowledge base, web search, and code interpreter |
| `agent-toolbox-foundryiq-workiq` | Uses a Foundry toolbox over a knowledge base with a Work IQ source |
| `agent-toolbox-workiq` | Uses a Work IQ toolbox for the caller's Microsoft 365 context |
| `agent-workiq-maf` | Direct Work IQ MCP with local browser sign-in or a forwarded hosted caller token, without Toolbox |

## Try Work IQ without Toolbox

`agent-workiq-maf` runs the **same Responses server locally and in Microsoft Foundry**.
Local sign-in and the optional test client use the same app registration and delegated `WorkIQAgent.Ask` scope as
[`workiq-mcp.ipynb`](../notebooks/workiq-mcp.ipynb). The server calls the Work IQ MCP gateway directly
and exposes only a read-only `ask_work_iq` tool to the model. It does not use Toolbox or RemoteA2A.

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

After a successful local call, stop the local server and deploy to the configured project:

```powershell
azd deploy agent-workiq-maf
uv run --project src\agent-workiq-maf python src\agent-workiq-maf\invoke.py --remote "Summarize my recent emails about the Professional Claw Hammer. Who sent them, and what actions do they request?"
```

The remote client authenticates to Microsoft Foundry separately with the `azd` identity and sends
the delegated Work IQ token in the same `x-client-*` header. It derives `x-ms-user-identity` from
MSAL's authenticated ID-token claims so that Microsoft Foundry isolates the represented user's state.
The invoking identity needs **Foundry Agent Consumer** (or an appropriate broader role) and the custom
`Microsoft.CognitiveServices/accounts/AIServices/agents/endpoints/UserIdentityImpersonation/action`
data action. The custom action is not included in built-in roles; an administrator must grant it.
The existing postdeploy hook grants the hosted agent's own model-access roles, not this caller permission.

Microsoft Foundry forwards `x-client-*` headers to the container on Responses protocol 2.0.0.
The server reads the token from `ResponseContext.client_headers`, uses it only for that request,
and creates a separate direct MCP session for each tool call. The model uses managed identity
in Microsoft Foundry and `AzureDeveloperCliCredential` locally.

See [Use on-behalf-of flow with hosted agents](https://learn.microsoft.com/azure/foundry/agents/how-to/use-on-behalf-of-flow)
for the token-forwarding contract and
[Delegate the end-user identity](https://learn.microsoft.com/azure/foundry/agents/concepts/hosted-agent-permissions#delegate-the-end-user-identity)
for caller permissions. This lab test client acquires its downstream token interactively, like the
notebook; it does not need an OBO exchange or a client secret. A production middle tier would
acquire the delegated Work IQ token through its own supported authentication/OBO flow.

**Hosted mode does not use the local sign-in or its token cache.** It never signs in interactively,
shares a local user's tokens across callers, sends tokens to the model, or falls back to
application-only Work IQ access. Missing hosted tokens and background execution are rejected.
Expired forwarded tokens require a new invocation with a fresh token; Microsoft Foundry does not exchange
or refresh a forwarded token. The standard **hosted** playground cannot test this direct-auth path
without a caller-supplied Work IQ token header. A working local playground does not establish hosted
playground compatibility. Toolbox examples remain unchanged for comparison.
Do not capture `Authorization` or `x-client-workiq-access-token` in proxy or telemetry header logging.

For offline checks, run `uv run python -m unittest -v test_main` from the `agent-workiq-maf` directory.
These do not establish live Work IQ access or prove that deployment and per-user header forwarding
work in a particular project. Verify a local answer first, then the deployed answer, and repeat
with two users to confirm identity separation.

The notebooks are in [`notebooks/`](../notebooks/).
