# Deploy to your own Azure subscription

Use this guide to run the notebooks and agents outside the hosted lab, with your own Azure subscription and Microsoft 365 tenant.

## Azure account requirements

In order to run all of the examples, you will need a tenant with multiple licenses and permissions. However, even if you do not have all of these permissions, you may be able to run some of the examples.

* An Azure subscription with permission to create resources and role assignments
* Quota in one region for `gpt-5.4`, and `text-embedding-3-large`
* For Fabric IQ notebooks: A Fabric-capable tenant and a Fabric/Power BI license (or active Fabric trial), with permission to create an F2 capacity
* For Web IQ notebook: Access to the Web IQ portal to get the account's key
* For Work IQ notebooks and agents: Work IQ access for each caller (a Microsoft 365 Copilot license for the direct notebooks and agents, and a Copilot credits plan for Work IQ through Azure AI Search), a tenant enabled for Work IQ,
  and a Global Administrator for the one-time Entra app registration and admin consent
* For Work IQ through Azure AI Search: the Search service's managed identity must be in the same tenant as your subscription (`az search service show --query identity.tenantId`). A service whose identity belongs to another tenant, for example after a subscription tenant move, cannot authenticate to Azure OpenAI or Work IQ.

## Getting started

You have a few options for getting started with this repository.
The quickest way to get started is GitHub Codespaces, since it will setup everything for you, but you can also [set it up locally](#local-environment).

### GitHub Codespaces

You can run this repository virtually by using GitHub Codespaces. The button will open a web-based VS Code instance in your browser:

1. Open the repository (this may take several minutes):

    [![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/microsoft/ignite26-PREL42)

2. Open a terminal window
3. Continue with the steps to run the examples

### VS Code Dev Containers

A related option is VS Code Dev Containers, which will open the project in your local VS Code using the [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers):

1. Start Docker Desktop (install it if not already installed)
2. Open the project:

    [![Open in Dev Containers](https://img.shields.io/static/v1?style=for-the-badge&label=Dev%20Containers&message=Open&color=blue&logo=visualstudiocode)](https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/microsoft/ignite26-PREL42)

3. In the VS Code window that opens, once the project files show up (this may take several minutes), open a terminal window.
4. Continue with the steps to run the examples

### Local environment

1. Make sure the following tools are installed:

    * [Python 3.12+](https://www.python.org/downloads/)
    * [uv](https://docs.astral.sh/uv/getting-started/installation/)
    * [Azure Developer CLI](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd)
      with the `azure.ai.agents` and `azure.ai.connections` extensions available
    * Git

2. Clone the repository:

    ```shell
    git clone https://github.com/microsoft/ignite26-PREL42
    cd ignite26-PREL42
    ```

3. Install the dependencies:

    ```shell
    uv sync
    ```

## Deploying to Azure

1. Login to Azure:

    ```shell
    azd auth login
    ```

    For GitHub Codespaces users, if the previous command fails, try:

   ```shell
    azd auth login --use-device-code
    ```

2. Create an `azd` environment:

    ```shell
    azd env new
    ```

    It will prompt you for an environment name (like "prel42"), a subscription from your Azure
    account, and a location. Pick a location that supports Foundry hosted agents and `gpt-5.4`, such as
    `canadaeast`.

    The Bicep template deploys into a resource group. Name it, and azd will create it if it does not exist:

    ```shell
    azd env set AZURE_RESOURCE_GROUP rg-prel42
    ```

    Azure AI Search uses the `serverless` tier in `northcentralus` by default. To change either, set
    `AZURE_AI_SEARCH_SKU_NAME` (for example, `standard`) or `AZURE_AI_SEARCH_LOCATION`.

3. Every optional service is off by default. Enable the ones you have access to now, since they are
   read during provisioning:

    ```shell
    # Fabric IQ: Fabric capacity (F2 by default, set FABRIC_SKU_NAME to change), plus the lakehouse,
    # ontology, graph, semantic model, and Data Agent
    azd env set ENABLE_FABRIC_CAPACITY true
    azd env set ENABLE_FABRIC_ITEMS true

    # Work IQ Entra app and direct MCP OAuth connection, used by agent-workiq-maf
    # and the foundryiq-workiq.ipynb notebook
    azd env set ENABLE_WORK_IQ true
    ```

    Each flag has prerequisites described in its own section: [Fabric IQ](#enable-fabric-iq),
    [Work IQ retrieval for Azure AI Search](#enable-work-iq-retrieval-for-azure-ai-search), and
    [the direct Work IQ MCP agent](#enable-the-direct-work-iq-mcp-agent).
    You can also set any of these later and re-run `azd provision`.

    A Web IQ account is always created. After provisioning, get its key from the Web IQ portal, since it
    isn't available through Azure yet, and set `WEB_IQ_KEY` in `.env`.

    The Fabric scripts build portal links from `https://app.fabric.microsoft.com`. If your tenant uses a
    different Fabric host, set it in the same way, before you provision:

    ```shell
    azd env set FABRIC_PORTAL_BASE_URL https://<your-fabric-host>
    ```

    This only affects the links that are printed and written to `.env`, not which resources are created.

4. Provision the Azure resources:

    ```shell
    azd provision
    ```

5. Once the resources are provisioned, you should now see a local `.env` file with all the environment variables needed to run the scripts.
6. To delete the resources, run:

    ```shell
    azd down
    ```

### Enable Fabric IQ

The Fabric IQ notebooks need a Fabric workspace with a lakehouse,
ontology, product review graph, web analytics semantic model, and a published Fabric Data Agent. Fabric is
opt-in and controlled by two independent flags, one per layer:

* `ENABLE_FABRIC_CAPACITY` (default `false`) creates an F2 Fabric capacity in Bicep. Leave it `false` to
  use a workspace you already manage.
* `ENABLE_FABRIC_ITEMS` (default `false`) runs the postprovision steps that create the Fabric items: the
  lakehouse, ontology, product review graph, web analytics lakehouse, semantic model, Power BI report,
  Fabric Data Agent, and Fabric IQ toolbox. It requires either `FABRIC_CAPACITY_ID` or
  `FABRIC_WORKSPACE_ID` to be set, and fails early with a clear message when neither is present.

To create a capacity and all of the Fabric items:

```bash
azd env set ENABLE_FABRIC_CAPACITY true
azd env set ENABLE_FABRIC_ITEMS true
azd provision
```

To use a workspace you already manage, set `FABRIC_WORKSPACE_ID` in `.env` and create only the items:

```bash
azd env set ENABLE_FABRIC_ITEMS true
azd provision
```

To skip Fabric entirely, leave both flags unset.

The Fabric Data Agent is published over three complementary sources. The ontology owns product, category,
supplier, store, and inventory facts; the product review graph owns reviewers, reviews, features, and
feature-level sentiment; the Direct Lake semantic model owns website traffic and conversion measures. Product
SKU is the shared key between the ontology and the graph. Provisioning selects all seven semantic model tables
before publishing the Data Agent.

Provisioning writes the generated identifiers and portal links to `.env`:

| Variables | Fabric item |
| --- | --- |
| `FABRIC_ONTOLOGY_ID`, `FABRIC_ONTOLOGY_MCP_URL`, `FABRIC_ONTOLOGY_UI_URL` | Lakehouse ontology |
| `FABRIC_GRAPH_ID`, `FABRIC_GRAPH_UI_URL` | Product review Graph Model |
| `FABRIC_DATA_AGENT_ID`, `FABRIC_DATA_AGENT_MCP_URL` | Published Fabric Data Agent |
| `FABRIC_WEB_ANALYTICS_LAKEHOUSE_*` | Web analytics lakehouse |
| `FABRIC_WEB_ANALYTICS_SEMANTIC_MODEL_*` | Direct Lake semantic model |
| `FABRIC_WEB_ANALYTICS_REPORT_ID`, `FABRIC_WEB_ANALYTICS_REPORT_URL` | Power BI report |

### Enable Work IQ retrieval for Azure AI Search

The `foundryiq-workiq.ipynb` notebook uses a Work IQ knowledge source in
Azure AI Search. Azure AI Search authenticates to Work IQ as a customer-owned Microsoft Entra app through a
federated credential that trusts the Search service's managed identity. Work IQ usage is billed through
Copilot credits.

Prerequisites:

- A usage-based billing plan (Copilot credits) for Work IQ configured in Copilot Studio, with each user
  assigned to it.
- A Microsoft Entra Global Administrator who enables the Work IQ API in the tenant.
- An identity running `azd provision` with the Cloud Application Administrator role, or the Microsoft Graph
  application permissions `Application.ReadWrite.All`, `DelegatedPermissionGrant.ReadWrite.All`, and
  `Directory.Read.All`.

`infra/create-workiq-entra.py` runs from the postprovision hook when `ENABLE_WORK_IQ` is `true`.
It is used by the `foundryiq-workiq.ipynb` notebook and other callers that can pass the user assertion as
`query_work_iq_source_authorization` together with a Search-scoped user token as `query_source_authorization`.
Both are required: without the Search token, Work IQ results are withheld. The script creates or reuses a single-tenant Entra app that exposes `access_as_user`, grants tenant-wide admin consent
for `WorkIQAgent.Ask`, adds the federated credential for the Search identity (`SEARCH_SERVICE_PRINCIPAL_ID`),
and writes `WORK_IQ_SEARCH_ENTRA_APP_ID`, `WORK_IQ_SEARCH_ENTRA_TENANT_ID`, and `WORK_IQ_SEARCH_FEDERATED_CREDENTIAL_ID` to `.env`.
No client secret is created. See
[Create a Work IQ knowledge source](https://learn.microsoft.com/azure/search/agentic-knowledge-source-how-to-work-iq).

### Enable the direct Work IQ MCP agent

Work IQ setup is opt-in because its first run requires a Global Administrator and creates a tenant app
registration. Authenticate azd as that administrator, enable Work IQ, and rerun provisioning:

```bash
az ad sp create --id fdcc1f02-fc51-4226-8753-f668596af7f7
azd env set ENABLE_WORK_IQ true
azd provision
```

The postprovision helper first runs `infra/create-workiq-entra.py` (the shared Work IQ Entra app described
above). It then creates or reuses the Work IQ service principal, reuses that application, adds a client secret
and Foundry's returned callback URI to it, and creates the OAuth2 `RemoteTool` connection
`work-iq-mcp-connection` targeting `https://workiq.svc.cloud.microsoft/mcp`.
The generated client secret is sent directly to the connection and is not written to `.env`.
If `WORK_IQ_SEARCH_ENTRA_APP_ID` is not set, the helper creates its own application instead.

Admin consent allows the application to request `WorkIQAgent.Ask`; it does not authorize individual
users. On a caller's first Work IQ request, the agent returns an `oauth_consent_request` containing a
short-lived sign-in link. That user opens the link once and then retries the request. Each caller must
complete this delegated OAuth authorization with their own Microsoft 365 identity.

### Seed sample mailbox data

To test Work IQ with predictable content, sign in to Outlook as the test user and send the following
three fixture messages to that same user's email address:

* [Urgent: Professional Claw Hammer out of stock at Seattle store](../data/workiq-fixtures/urgent-professional-claw-hammer-out-of-stock.txt)
* [RE: Weekly inventory report - Seattle flagged](../data/workiq-fixtures/weekly-inventory-report-seattle-flagged.txt)
* [Customer escalation - hammer unavailable again](../data/workiq-fixtures/customer-escalation-hammer-unavailable.txt)

Use the subject and body from each fixture. Because Outlook cannot impersonate the named colleague,
prepend `Forwarded message from <name>, <role>` to the body rather than attempting to change the
sender. Verify that all three messages appear in the test user's Inbox, then try:

```text
Check my recent emails for messages about the Professional Claw Hammer. Summarize what colleagues
are saying and what actions have been requested.
```

Automated seeding through Microsoft Graph requires a dedicated Entra application with the
admin-consented `Mail.Send` application permission. That broad permission is not granted by this
project, so manual seeding is the recommended setup for a self-deployed test environment.

## Run the notebooks

Install the notebook kernel into the root environment:

```bash
uv sync --locked --all-groups
uv pip install --python .venv/bin/python -r notebooks/requirements.txt
```

Then open `notebooks/` in VS Code and select a notebook. Each one is independent, so you can run them in
any order, as long as you have the resources necessary.

Knowledge base notebooks, which build a Foundry IQ knowledge base over different kinds of knowledge source:

| Notebook | What it covers |
| --- | --- |
| `foundryiq-basic.ipynb` | Indexed knowledge sources over the sample HR and health documents |
| `foundryiq-webiq.ipynb` | Adds an MCP server knowledge source backed by Web IQ for web grounding. Requires `WEB_IQ_KEY` in `.env`. |
| `foundryiq-workiq.ipynb` | Adds a Work IQ knowledge source over the signed-in user's Microsoft 365 context |
| `foundryiq-fabriciq-ontology.ipynb` | Adds a Fabric ontology knowledge source, queried with a delegated user token |
| `foundryiq-fabriciq-dataagent.ipynb` | Adds a Fabric Data Agent knowledge source for analytical questions |

Endpoint notebooks, which skip the knowledge base and call a service endpoint directly:

| Notebook | What it covers |
| --- | --- |
| `foundryiq-mcp.ipynb` | Calls `knowledge_base_retrieve` on the `contoso-company-kb-minimal` MCP endpoint |
| `webiq-mcp.ipynb` | Inspects and calls the Web IQ MCP tools to search the web, images, and videos. Requires `WEB_IQ_KEY` in `.env`. |
| `fabriciq-ontology-mcp.ipynb` | Inspects and calls the tools on the Fabric ontology MCP endpoint |
| `fabriciq-dataagent-mcp.ipynb` | Inspects and calls the tools on the published Fabric Data Agent MCP endpoint |
| `fabriciq-graph.ipynb` | Sends GQL to the Fabric Graph `executeQuery` REST API |
| `workiq-mcp.ipynb` | Authenticates, lists tools, asks about work context, and discovers schemas and structured data through the read tools |
| `workiq-mcp-actions.ipynb` | Optional write-tool examples: inspect schemas, preview payloads, and approve individual mutations; writes are disabled by default |
| `workiq-a2a.ipynb` | Optionally discovers the Work IQ Agent Card and delegates an email-summary task over A2A |

When you run a notebook, select the `.venv/bin/python` virtual environment (`.venv\Scripts\python.exe` on Windows).

## Run and invoke the agents

Provisioning creates two knowledge bases over the same HR and health sources: `contoso-company-kb-low`
uses low reasoning effort and the configured Azure OpenAI model for query planning, while
`contoso-company-kb-minimal` uses minimal reasoning effort and is extractive, so it configures no model.
The notebooks create their own knowledge bases and are unaffected by these.

| Agent | How it reaches its data |
| --- | --- |
| `agent-foundryiq-api` | Calls the retrieval API on `contoso-company-kb-minimal` from a custom Python tool |
| `agent-foundryiq-mcp` | Connects to the same knowledge base through its Foundry IQ MCP endpoint |
| `agent-toolbox-foundryiq` | Uses a Foundry toolbox holding that knowledge base, web search, and code interpreter |
| `agent-workiq-maf` | Uses direct Work IQ MCP with local browser sign-in or hosted OAuth identity passthrough, without Toolbox |

Start any of the agents locally, and test them with either the local playground or CLI:

```bash
azd ai agent run agent-foundryiq-api
azd ai agent invoke --local "What benefits are available, and when do I need to enroll?"

azd ai agent run agent-foundryiq-mcp
azd ai agent invoke --local "What benefits are available, and when do I need to enroll?"

azd ai agent run agent-toolbox-foundryiq
azd ai agent invoke --local "What benefits are available, and when do I need to enroll?"

azd ai agent run agent-workiq-maf
azd ai agent invoke --local \
  "Check my recent emails for messages about the Professional Claw Hammer. Summarize what colleagues are saying and what actions have been requested."
```

You can also invoke the deployed versions. You may want to re-deploy before invoking, if you've made any changes:

```bash
azd deploy agent-foundryiq-api
azd ai agent invoke agent-foundryiq-api "What benefits are available, and when do I need to enroll?"

azd deploy agent-foundryiq-mcp
azd ai agent invoke agent-foundryiq-mcp "What benefits are available, and when do I need to enroll?"

azd deploy agent-toolbox-foundryiq
azd ai agent invoke agent-toolbox-foundryiq "What benefits are available, and when do I need to enroll?"

azd deploy agent-workiq-maf
azd ai agent show agent-workiq-maf
```

For `agent-workiq-maf`, complete the local Work IQ browser sign-in before using the local playground.
For the hosted version, open the **Playground URL** returned by `azd ai agent show`, ask the email
question, and complete Work IQ consent using the latest active **Open consent** button. Resend the
question if the consent turn has stopped. After authorization, you can also invoke it from the CLI:

```bash
azd ai agent invoke agent-workiq-maf \
  --new-session --new-conversation \
  "Check my recent emails for messages about the Professional Claw Hammer. Summarize what colleagues are saying and what actions have been requested."
```

Direct source deployment is used because the final agent requires no custom OS packages. Foundry's
remote build resolves each agent folder's `pyproject.toml` and `uv.lock`, avoiding an unnecessary
container registry and image-build path.

## Resources

The IQ workloads:

* [What is Foundry IQ?](https://learn.microsoft.com/azure/ai-foundry/agents/concepts/what-is-foundry-iq)
* [What is Fabric IQ?](https://learn.microsoft.com/fabric/iq/overview)
* [Work IQ MCP tool reference](https://learn.microsoft.com/microsoft-365/copilot/extensibility/work-iq/mcp/tool-reference)

Foundry IQ knowledge bases and agentic retrieval:

* [Agentic retrieval overview](https://learn.microsoft.com/azure/search/agentic-retrieval-overview)
* [What is a knowledge source?](https://learn.microsoft.com/azure/search/agentic-knowledge-source-overview)
* [Set the retrieval reasoning effort](https://learn.microsoft.com/azure/search/agentic-retrieval-how-to-set-retrieval-reasoning-effort), which explains the difference between the `low` and `minimal` knowledge bases created here
* [Query a knowledge base via API or MCP](https://learn.microsoft.com/azure/search/agentic-retrieval-how-to-retrieve)
* [Create a Work IQ knowledge source](https://learn.microsoft.com/azure/search/agentic-knowledge-source-how-to-work-iq)
* [Create a Fabric Ontology knowledge source](https://learn.microsoft.com/azure/search/agentic-knowledge-source-how-to-fabric-ontology)

Fabric items used by the Fabric IQ notebooks:

* [Fabric data agent concepts](https://learn.microsoft.com/fabric/data-science/concept-data-agent)
* [Direct Lake overview](https://learn.microsoft.com/fabric/fundamentals/direct-lake-overview)

Building and deploying the agents:

* [Microsoft Agent Framework](https://learn.microsoft.com/agent-framework/)
* [Azure Developer CLI](https://learn.microsoft.com/azure/developer/azure-developer-cli/)
* [Mastering Foundry Toolbox](https://github.com/microsoft-foundry/forgebook/blob/main/notebooks/mastering-foundry-toolbox.ipynb)
* [Model Context Protocol](https://modelcontextprotocol.io/)