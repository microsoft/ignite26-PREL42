@lab.Title

## Overview

In this lab, you give AI agents context with Microsoft IQ: Web IQ for the web, Fabric IQ for structured business data, Work IQ for your Microsoft 365 work, and Foundry IQ knowledge bases that bring them together. For Web IQ, Fabric IQ, and Work IQ, you first call them from Python notebooks; for every IQ, you add it as an MCP server in the GitHub Copilot app. In the Foundry IQ exercise, you bring them all together as knowledge sources in a Foundry IQ knowledge base. You finish by running Microsoft Agent Framework agents locally and as Foundry hosted agents.

The scenario is Contoso, a DIY retailer: HR and benefits documents in Azure AI Search, product, store, and inventory data in Fabric, and inventory emails in your mailbox.

## Sign in to Windows

Sign in to the virtual machine with these credentials:

- **User name**: +++@lab.VirtualMachine(ILL344:Win11).Username+++
- **Password**: +++@lab.VirtualMachine(ILL344:Win11).Password+++

## Set up Visual Studio Code

### Open the lab folder

1. Open Visual Studio Code.
2. Select **File > Open Folder**, go to **Desktop**, select the **ignite26-PREL42** folder, and then select **Select Folder**.
3. A **Restricted Mode** banner appears at the top of the window. Select **Manage** in that banner, and then select **Trust** to trust the folder.

### Check the environment setup

Your Azure resources, search indexes, Fabric items, hosted agents, and sample emails are already created for you.

1. In Visual Studio Code, open a terminal with **Terminal > New Terminal**.
2. Run this command to show the MCP server URLs that setup saved for you:

    +++Get-Content .env | Select-String "MCP_URL"+++

    You should see three lines: **FOUNDRY_IQ_MCP_URL**, **FABRIC_ONTOLOGY_MCP_URL**, and **FABRIC_DATA_AGENT_MCP_URL**. If any are missing, let a proctor know.

### Sign in to the Azure portal

1. Open the browser and go to +++https://portal.azure.com+++.
2. Sign in with your lab credentials:
   - **Username**: +++@lab.CloudPortalCredential(User1).Username+++
   - **Temporary Access Pass**: +++@lab.CloudPortalCredential(User1).AccessToken+++

Keep the browser open. The next sign-ins reuse this session.

### Sign in to the Azure Developer CLI

The notebooks and agents will use your Azure Developer CLI sign-in.

1. In the Visual Studio Code terminal, run:

    +++azd auth login+++

2. In the browser window that opens, select your lab account.

## Sign in to GitHub

1. In the browser, sign in in the GitHub enterprise organization for Skillable:

    +++https://github.com/enterprises/skillable-events/sso+++

You will be signed into a special account created for the lab environment, not your actual GitHub account.

## Set up the GitHub Copilot app

In the exercises, you will connect GitHub Copilot app to each IQ so you can query it from a chat.

1. Open the **GitHub Copilot** app.
2. Select **Sign in to GitHub**.
3. When the browser opens, select the lab GitHub account.
4. Paste the 8-digit code from the app screen.
5. Select **Authorize GitHub**.
6. On the next screen, do not select any folder, simply select **Continue**. You will use the app only for chat; you will use VS Code for interacting with the lab folder.
7. Send a message to the agent in the chat box, such as:

    +++What are some good restaurants near Moscone Center in San Francisco?+++

===

# Exercise: Web IQ

Web IQ grounds answers in current web content.

## Get your Web IQ key

A Web IQ resource was created for you in your resource group. Get its API key from the Web IQ portal:

1. In the browser, go to +++https://webiq.microsoft.ai/profiles+++.
2. In the sign-in prompt, select your lab account.
3. In **Select an Azure Resource**, select your lab subscription for **Azure subscription**, and then select the resource that starts with **webiq-** for **Resource**. Select **Finish**.
4. Select **Profile Management** in the left menu. Under **Authentication > API Keys**, select the copy icon next to the **default** key.

Then save the key so the notebooks can use it:

1. In Visual Studio Code, open the **.env** file in the lab folder.
2. Add a new line at the end of the file with **WEB_IQ_KEY=**, and paste the key after the equals sign. For example: **WEB_IQ_KEY=your-key**.
3. Save the file.

## Call Web IQ from a notebook

1. Open **notebooks/webiq-mcp.ipynb**.
2. Select **Select Kernel**, and choose the **ignite26-prel42** environment with the path **.venv\Scripts\python.exe** if it isn't already selected.
3. Run each cell. You call the Web IQ MCP endpoint directly to search the web, images, and videos.

**⚠️ Troubleshooting:** If code cells get stuck and keep spinning, try these remediation steps:

1. Select **Restart** from the notebook toolbar at the top. If that doesn't work:
2. Select **Developer: Reload Window** from the VS Code command palette. If that doesn't work:
3. Close VS Code completely and restart it.

## Use Web IQ in the GitHub Copilot app

1. In the GitHub Copilot app, select **Customize**, and then select **Add > MCP Server...**.
2. Enter these values:
    - **Server name**: +++web-iq+++
    - **Server type**: HTTP
    - **URL**: +++https://api.microsoft.ai/v3/mcp+++
3. Select **Add header**, and enter the name +++x-apikey+++. Switch to Visual Studio Code, copy the **WEB_IQ_KEY** value from **.env**, and then switch back to the app and paste it as the header value.
4. Select **Add server**, and then switch to the **Installed** tab. Under **MCP Servers**, confirm that the server is toggled on and has a green check mark.

Then select **New** and ask:

+++Use Web IQ to search the web for recent trends in mental health benefits for employers.+++

===

# Exercise: Fabric IQ

Fabric IQ gives agents structured business data from Microsoft Fabric. Your Fabric workspace has a Contoso DIY lakehouse, an ontology over products, stores, suppliers, and inventory, a product review graph, a web analytics semantic model, and a published Fabric data agent.

## Explore your Fabric workspace

Before calling Fabric IQ from code, explore the data and relationships in the Fabric portal. These items are already created for you; you don't need to create or edit them.

1. In the browser, go to +++https://app.fabric.microsoft.com+++ and sign in with your lab credentials.
2. Select **Workspaces**, and open the workspace whose name starts with **ContosoDIY-**.
3. Open **ContosoDIYLakehouse**. Under **Tables**, select a few tables to preview their rows. Look at the products, stores, and inventory data that you will ask about later.
4. Return to the workspace and open **ContosoDIYOntology**. Explore the **Product**, **Category**, **Store**, **Inventory**, and **Supplier** entities. Inspect their properties and relationships: how does the ontology connect a product to the stores that stock it?
5. Return to the workspace and open **ContosoDIYReviewGraph**. Explore the graph's node and edge types. Look for **Product**, **Reviewer**, **Review**, and **Feature**, and see how the relationships connect reviews to products and features. In the **Components** pane, expand **Edges > MENTIONS** to see the **sentiment**, **confidence**, and **evidenceExcerpt** properties. These properties describe the sentiment of a review's mention of a particular feature, adding feature-level sentiment context to the product catalog.
6. Return to the workspace and open the **ContosoWebAnalytics** semantic model. Explore the relationship diagram. In the **Data** pane on the right, expand **Sessions** to see fields such as **Converted** and **RevenueAmount**, and expand **Channels** to see **Channel** and **ChannelGroup**. Follow the relationship line between these tables in the diagram to see how sessions connect to marketing channels. You are inspecting the model's structure, not previewing data rows.
7. Return to the workspace and open **ContosoDIYDataAgent**. Review its configured data sources: the ontology, review graph, and web analytics semantic model. The data agent brings these sources together so you can ask analytical questions in natural language.

## Call Fabric IQ from notebooks

When you open each notebook, select **Select Kernel**, and choose the **ignite26-prel42** environment with the path **.venv\Scripts\python.exe** if it isn't already selected.

1. Open **notebooks/fabriciq-ontology-mcp.ipynb** and run each cell. You call the ontology's MCP endpoint directly.
2. Open **notebooks/fabriciq-graph.ipynb** and run each cell. You query the product review graph with GQL over the Fabric REST API.
3. Open **notebooks/fabriciq-dataagent-mcp.ipynb** and run each cell. You call the Fabric data agent's MCP endpoint for analytical questions.

**⚠️ Troubleshooting:** If code cells get stuck and keep spinning, try these remediation steps:

1. Select **Restart** from the notebook toolbar at the top. If that doesn't work:
2. Select **Developer: Reload Window** from the VS Code command palette. If that doesn't work:
3. Close VS Code completely and restart it.

## Use Fabric IQ in the GitHub Copilot app

**⚠️ Known issue:** Fabric IQ MCP servers currently cannot sign in to the GitHub Copilot app on Windows because of a Microsoft Entra authentication issue. We are tracking the issue in [GitHub issue #14](https://github.com/microsoft/ignite26-PREL42/issues/14).

Add two MCP servers, one for the ontology and one for the data agent. Both sign you in with your Microsoft Entra account, so they don't need headers.

In Visual Studio Code, open the **.env** file in the lab folder and find **FABRIC_ONTOLOGY_MCP_URL** and **FABRIC_DATA_AGENT_MCP_URL**. Keep the file open so you can switch back to it when each URL is needed.

1. In the GitHub Copilot app, select **Customize**, and then select **Add > MCP Server...**.
2. Enter these values, and then select **Add server**:
    - **Server name**: +++fabric-iq-ontology+++
    - **Server type**: HTTP
    - **URL**: switch to Visual Studio Code, copy the complete **FABRIC_ONTOLOGY_MCP_URL** value from **.env**, and switch back to the app to paste it. Copy only the URL after the first **=**, without surrounding quotes.
3. Select **Add > MCP Server...** again, enter these values, and then select **Add server**:
    - **Server name**: +++fabric-iq-data-agent+++
    - **Server type**: HTTP
    - **URL**: switch to Visual Studio Code, copy the complete **FABRIC_DATA_AGENT_MCP_URL** value from **.env**, and switch back to the app to paste it. Copy only the URL after the first **=**, without surrounding quotes.
4. Switch to the **Installed** tab. Under **MCP Servers**, confirm that both servers are toggled on and each has a green check mark. When prompted, sign in with your lab credentials.

Then select **New** and ask:

+++How many Professional Claw Hammers does each store have in stock?+++

+++Which marketing channel has the highest conversion rate in the web analytics data?+++

===

# Exercise: Work IQ

Work IQ gives agents your Microsoft 365 work context: email, meetings, files, chats, and people. It always uses your own permissions.

## Explore your sample emails

Your mailbox has three emails about an out-of-stock Professional Claw Hammer. Read them before asking Work IQ about them.

1. In the browser, go to +++https://outlook.office.com+++ and sign in with your lab credentials if prompted.
2. Open your **Inbox** and find the three sample emails about the **Professional Claw Hammer**.
3. Open each email and read the inventory updates, customer concerns, and requested actions. You will use Work IQ to summarize this context later in the exercise.

## Call Work IQ from notebooks

In each notebook, select **Select Kernel**, and choose the **ignite26-prel42** environment with the path **.venv\Scripts\python.exe** if it isn't already selected.

1. Open **notebooks/workiq-mcp.ipynb** and run each cell. You sign in, list the tools, ask about the sample emails, discover resource paths and schemas, fetch structured email data, and discover agents.
2. Open **notebooks/workiq-mcp-actions.ipynb** to explore the write tools, inspect schemas, and preview create, update, delete, and send-mail operations. Writes are disabled by default.

    **⚠️ Known issue:** Work IQ MCP actions currently do not work in the Skillable lab. The lab advertises only read operations, and calendar write-schema requests are denied. Skip this step for now, including its schema-discovery cell, which can fail even when writes are disabled. We are tracking the issue in [GitHub issue #15](https://github.com/microsoft/ignite26-PREL42/issues/15).

3. Open **notebooks/workiq-a2a.ipynb** to discover Work IQ as a remote agent and delegate an email-summary task through A2A.

**⚠️ Troubleshooting:** If code cells get stuck and keep spinning, try these remediation steps:

1. Select **Restart** from the notebook toolbar at the top. If that doesn't work:
2. Select **Developer: Reload Window** from the VS Code command palette. If that doesn't work:
3. Close VS Code completely and restart it.

## Use Work IQ in the GitHub Copilot app

**⚠️ Known issue:** The WorkIQ plugin currently cannot authenticate in the GitHub Copilot app on the Skillable Windows machine. We are tracking this issue in [GitHub issue #16](https://github.com/microsoft/ignite26-PREL42/issues/16).

Work IQ is available as a plugin, so you install it instead of adding the MCP server yourself.

1. In the GitHub Copilot app, select **Customize**, and then select **Browse**.
2. Search for +++workiq+++.
3. Under **Plugins**, find **WorkIQ** from Microsoft ("Find answers across Microsoft 365 emails, meetings, documents, and Teams messages"), and select **Install**.
4. When prompted, sign in with your lab credentials.

Then select **New** and ask:

+++Check my recent emails for messages about the Professional Claw Hammer. Summarize what colleagues are saying and what actions have been requested.+++

===

# Exercise: Foundry IQ

Foundry IQ knowledge bases combine knowledge sources, such as search indexes, Fabric IQ, Work IQ, and Web IQ, and use agentic retrieval to plan queries across them and return grounded answers with citations.

## Call Foundry IQ from notebooks

In each notebook, select **Select Kernel**, and choose the **ignite26-prel42** environment with the path **.venv\Scripts\python.exe** if it isn't already selected.

1. Open **notebooks/foundryiq-basic.ipynb** and run each cell. You build a multi-source knowledge base over the HR and health indexes and query it with agentic retrieval.
2. Open **notebooks/foundryiq-mcp.ipynb** and run each cell. You call a knowledge base through its MCP endpoint.
3. Open **notebooks/foundryiq-fabriciq-ontology.ipynb** and run each cell. You add the Fabric IQ ontology as a knowledge source.
4. Open **notebooks/foundryiq-fabriciq-dataagent.ipynb** and run each cell. You add the Fabric data agent as a knowledge source for analytical questions.
5. Open **notebooks/foundryiq-workiq.ipynb** and run each cell. You add a Work IQ knowledge source, so a knowledge base can search your emails alongside the HR documents.
6. Open **notebooks/foundryiq-webiq.ipynb** and run each cell. You add a Web IQ knowledge source, so answers combine the HR documents with web results.

**⚠️ Troubleshooting:** If code cells get stuck and keep spinning, try these remediation steps:

1. Select **Restart** from the notebook toolbar at the top. If that doesn't work:
2. Select **Developer: Reload Window** from the VS Code command palette. If that doesn't work:
3. Close VS Code completely and restart it.

## Use Foundry IQ in the GitHub Copilot app

The knowledge base MCP endpoint uses a Search query key. First find the key in the Azure portal:

1. Go back to the Azure portal in the browser.
2. Search for +++search-+++ in the top search bar, and open the Azure AI Search service in your resource group.
3. Select **Security + networking > Keys**, and locate a key under **Manage query keys**. Keep this page open.

In Visual Studio Code, open the **.env** file in the lab folder and find **FOUNDRY_IQ_MCP_URL**. Keep the file open. You will switch between the app, Visual Studio Code, and the portal to copy and paste each value when it is needed.

Then add the MCP server:

1. In the GitHub Copilot app, select **Customize**, and then select **Add > MCP Server...**.
2. Enter these values:
    - **Server name**: +++foundry-iq+++
    - **Server type**: HTTP
    - **URL**: switch to Visual Studio Code, copy the complete **FOUNDRY_IQ_MCP_URL** value from **.env**, and switch back to the app to paste it. Copy only the URL after the first **=**, without surrounding quotes.
3. Select **Add header**, and enter the name +++api-key+++. Switch to the Azure portal's **Keys** page, copy a key under **Manage query keys**, and switch back to the app to paste it as the header value.
4. Select **Add server**, and then switch to the **Installed** tab. Under **MCP Servers**, confirm that the server is toggled on and has a green check mark.

Then select **New** and ask:

+++What benefits does Contoso offer, and when do I need to enroll?+++

===

# Exercise: Foundry hosted agents

In this exercise, you explore two Microsoft Agent Framework apps that connect to Foundry toolboxes through MCP: one for a Foundry IQ knowledge base, and one for Work IQ Microsoft 365 context. Both are already deployed as Foundry hosted agents. Explore both agents' code, run the Foundry IQ agent locally, and try both hosted versions. Skip the local Work IQ run because of the known consent issue described below.

| Agent | How it reaches its data |
| --- | --- |
| **agent-toolbox-foundryiq** | Uses a Foundry toolbox with a Foundry IQ knowledge base, web search, and code interpreter |
| **agent-toolbox-workiq** | Uses a Foundry toolbox connected to Work IQ for your Microsoft 365 context |

## Agent 1: Foundry IQ through a Foundry toolbox

### Explore the code

1. Open **src/agent-toolbox-foundryiq/main.py** in Visual Studio Code.
2. Find where the agent connects to the Foundry toolbox's MCP endpoint using **FoundryToolbox**. Inspect the instructions that tell the model to use the knowledge base for company questions, web search for current information, and code interpreter for calculations.

### Run locally

1. In the Visual Studio Code terminal, start the agent:

    +++azd ai agent run agent-toolbox-foundryiq+++

2. Wait for a local playground to open in the browser. Then ask:

    +++What benefits does Contoso offer, and when do I need to enroll?+++

3. Stop the local agent with **Ctrl+C** in the terminal where you started it.

### Try the hosted version

1. Get the agent's deployment details:

    +++azd ai agent show agent-toolbox-foundryiq+++

2. Open the **Playground URL** from the output and sign in with your lab credentials if prompted.
3. Ask the same question:

    +++What benefits does Contoso offer, and when do I need to enroll?+++

4. After the agent responds, select **Traces** beneath its answer. In the **Trajectories** tab, expand the agent run and select the **Execute Tool** entry for knowledge base retrieval. In **Input + Output**, inspect the queries the agent sent and the document content returned.

## Agent 2: Work IQ through a Foundry toolbox

### Explore the code

1. Open **src/agent-toolbox-workiq/main.py** in Visual Studio Code.
2. Find where the agent connects to the **work-iq-tools** Foundry toolbox and instructs the model to use Work IQ for questions about your Microsoft 365 context.

### Run locally

> **Known issue:** Work IQ consent fails in the local playground, and a subsequent chat can report that the MCP server failed to initialize. See [issue #18](https://github.com/microsoft/ignite26-PREL42/issues/18).

1. In the Visual Studio Code terminal, start the agent:

    +++azd ai agent run agent-toolbox-workiq+++

2. Wait for a local playground to open in the browser. Then ask:

    +++Check my recent emails for messages about the Professional Claw Hammer. Summarize what colleagues are saying and what actions have been requested.+++

3. If the agent asks you to sign in to the Work IQ connection, select **Open consent**, sign in with your lab credentials, check **I have verified this request and trust the source**, and select **Allow access**. If consent fails or the MCP server cannot initialize, continue with the hosted version after stopping the local agent.
4. Stop the local agent with **Ctrl+C** in the terminal where you started it.

### Try the hosted version

> **Known issue:** After Work IQ consent, the popup can show **Authentication failed** with **Code ... not found**, while the playground shows **Sign in successful** followed by **MCP server failed to initialize**. Completing consent and starting a **new chat** has been verified to work for the hosted agent. Follow the steps below. See [issue #17](https://github.com/microsoft/ignite26-PREL42/issues/17).

1. Get the agent's deployment details:

    +++azd ai agent show agent-toolbox-workiq+++

2. Open the **Playground URL** from the output and sign in with your lab credentials if prompted. Ask:

    +++Check my recent emails for messages about the Professional Claw Hammer. Summarize what colleagues are saying and what actions have been requested.+++

3. If the agent requests Work IQ consent, select **Open consent**, sign in with your lab credentials, check **I have verified this request and trust the source**, and select **Allow access**.

4. After completing consent, close the consent window, even if it shows the **Code ... not found** error described above. In the hosted playground, start a **new chat** and ask the email question again. If the new chat still fails, the workaround has not succeeded; let your instructor know.

5. After the agent answers the email question, select **Traces** beneath its answer. In the **Trajectories** tab, expand the agent run and select the **Execute Tool** entry for the Work IQ call. In **Input + Output**, inspect the request and the returned work context.

===

# Summary

You built context-aware AI with Microsoft IQ:

- A Web IQ knowledge source that grounds answers in current web content.
- Fabric IQ knowledge sources over a Fabric ontology and a Fabric data agent.
- A Work IQ knowledge source over your Microsoft 365 email.
- Foundry IQ knowledge bases with agentic retrieval over indexed documents, called through the retrieval API and MCP.
- MCP servers for each IQ in the GitHub Copilot app.
- Microsoft Agent Framework agents that connect through MCP to Foundry toolboxes for Foundry IQ and Work IQ, with a local Foundry IQ run and both agents explored as Foundry hosted agents.

## Continue learning

- [What is Foundry IQ?](https://learn.microsoft.com/azure/ai-foundry/agents/concepts/what-is-foundry-iq)
- [What is Fabric IQ?](https://learn.microsoft.com/fabric/iq/overview)
- [Work IQ MCP tool reference](https://learn.microsoft.com/microsoft-365/copilot/extensibility/work-iq/mcp/tool-reference)
- [Agentic retrieval overview](https://learn.microsoft.com/azure/search/agentic-retrieval-overview)
- [Create a Work IQ knowledge source](https://learn.microsoft.com/azure/search/agentic-knowledge-source-how-to-work-iq)
- [Create a Fabric Ontology knowledge source](https://learn.microsoft.com/azure/search/agentic-knowledge-source-how-to-fabric-ontology)
- [Microsoft Agent Framework](https://learn.microsoft.com/agent-framework/)

## Try it on your own

Everything in this lab is in the [session repository](https://github.com/microsoft/ignite26-PREL42). To run it in your own Azure subscription, follow [Deploy to your own Azure subscription](https://github.com/microsoft/ignite26-PREL42/blob/main/docs/deploy-yourself.md).
