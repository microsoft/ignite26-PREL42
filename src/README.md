# Source

Microsoft Agent Framework agents. All except the local Work IQ experiment are deployable as a
Foundry Hosted Agent:

| Agent | How it reaches its data |
| --- | --- |
| `agent-foundryiq-api` | Calls the knowledge base retrieval API from a custom Python tool |
| `agent-foundryiq-mcp` | Connects to the knowledge base through its Foundry IQ MCP endpoint |
| `agent-toolbox-foundryiq` | Uses a Foundry toolbox with the knowledge base, web search, and code interpreter |
| `agent-toolbox-foundryiq-workiq` | Uses a Foundry toolbox over a knowledge base with a Work IQ source |
| `agent-toolbox-workiq` | Uses a Work IQ toolbox for the caller's Microsoft 365 context |
| `agent-workiq-maf` | Local, single-user "Workmate" experiment using direct Work IQ MCP and delegated MSAL sign-in, without Toolbox |

## Try Work IQ without Toolbox

`agent-workiq-maf` uses the same app registration, delegated `WorkIQAgent.Ask` scope, and MCP endpoint
as [`workiq-mcp.ipynb`](../notebooks/workiq-mcp.ipynb). It exposes only the `ask` tool to the agent.
It does not use a Toolbox, a `RemoteA2A` connection, a client secret, or an OBO exchange.

Complete the [Work IQ admin setup](../docs/workiq-admin-setup.md) and configure the repository-root `.env`
with `WORK_IQ_SEARCH_ENTRA_APP_ID`, `WORK_IQ_SEARCH_ENTRA_TENANT_ID`, `FOUNDRY_PROJECT_ENDPOINT`, and
`AZURE_AI_MODEL_DEPLOYMENT_NAME`. Sign in to `azd` for the model connection, independently of the
Work IQ sign-in. The Work IQ user needs a Microsoft 365 Copilot license.

From the repository root in Windows PowerShell:

```powershell
uv run --project src\agent-workiq-maf python src\agent-workiq-maf\main.py "Summarize my recent emails about the Professional Claw Hammer. Who sent them, and what actions do they request?"
```

In the GitHub Codespaces terminal:

```bash
cd src/agent-workiq-maf
uv run python main.py "Summarize my recent emails about the Professional Claw Hammer. Who sent them, and what actions do they request?"
```

Sign in with the same account used in the Work IQ notebook when the browser opens. In GitHub Codespaces,
use the displayed device code instead. The command prints one answer and exits. Tokens stay in MSAL's
in-memory cache and are refreshed silently for each MCP request; if sign-in requires interaction again,
the command fails and asks you to restart.

This is a **local, single-user experiment**, not a hosted caller-authentication solution. It is deliberately
excluded from `azure.yaml` and postdeploy role assignments, and refuses to run in the Foundry hosting
environment. Do not expose it as a shared service or deploy an interactive user's credentials.
The Toolbox-based examples remain unchanged for comparison. A successful local call would demonstrate
the direct MCP path, not prove that hosted per-caller OBO works.

For offline checks, run `uv run python -m unittest -v test_main` from the `agent-workiq-maf` directory.
These cover the native MCP client against a mock HTTP transport, delegated-token refresh, sign-in
failure handling, and the hosted-execution guard. They do not establish live Work IQ access.

The notebooks are in [`notebooks/`](../notebooks/).
