@lab.Title

## Overview

In this lab, you give AI agents context with Microsoft IQ: Web IQ for the web, Fabric IQ for structured business data, Work IQ for your Microsoft 365 work, and Foundry IQ knowledge bases that bring them together. For Web IQ, Fabric IQ, and Work IQ, you first call them from Python notebooks; for every IQ, you add it as an MCP server in the GitHub Copilot app. In the Foundry IQ exercise, you bring them all together as knowledge sources in a Foundry IQ knowledge base. You finish by running Microsoft Agent Framework agents locally and as Foundry hosted agents.

The scenario is Contoso, a DIY retailer: HR and benefits documents in Azure AI Search, product, store, and inventory data in Fabric, and inventory emails in your mailbox.

## Sign in to Windows

Sign in to the virtual machine with these credentials:

- **User name**: +++@lab.VirtualMachine(ILL344-Win11).Username+++
- **Password**: +++@lab.VirtualMachine(ILL344-Win11).Password+++

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

    ++https://github.com/enterprises/skillable-events/sso++

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

First, get your Web IQ key by running this in the Visual Studio Code terminal:

+++Get-Content .env | Select-String "WEB_IQ_KEY"+++

## Call Web IQ from a notebook

1. Open **notebooks/webiq-mcp.ipynb**.
2. Select **Select Kernel > Python Environments**, and then select the **.venv** environment in the lab folder if it isn't already selected.
3. Run each cell. You call the Web IQ MCP endpoint directly to search the web, search the news, and read a web page.

## Use Web IQ in the GitHub Copilot app

1. In the GitHub Copilot app, select **Customize**, and then select **Add > MCP Server...**.
2. Enter these values:
    - **Server name**: +++web-iq+++
    - **Server type**: HTTP
    - **URL**: +++https://api.microsoft.ai/v3/mcp+++
3. Select **Add header**, and enter the name +++x-apikey+++ and the **WEB_IQ_KEY** value that the command above showed.
4. Select **Add server**, and check that the server is turned on in the **MCP Servers** list.

Then select **New** and ask:

+++Use Web IQ to find recent news about mental health benefits trends for employers.+++

===

# Exercise: Fabric IQ

Fabric IQ gives agents structured business data from Microsoft Fabric. Your Fabric workspace has a Contoso DIY lakehouse, an ontology over products, stores, suppliers, and inventory, a product review graph, a web analytics semantic model, and a published Fabric data agent.

## Call Fabric IQ from notebooks

When you open each notebook, select **Select Kernel > Python Environments**, and then select the **.venv** environment in the lab folder if it isn't already selected. When a notebook opens a browser sign-in, use your lab credentials.

1. Open **notebooks/fabriciq-ontology-mcp.ipynb** and run each cell. You call the ontology's MCP endpoint directly.
2. Open **notebooks/fabriciq-graph.ipynb** and run each cell. You query the product review graph with GQL over the Fabric REST API.
3. Open **notebooks/fabriciq-dataagent-mcp.ipynb** and run each cell. You call the Fabric data agent's MCP endpoint for analytical questions.

## Use Fabric IQ in the GitHub Copilot app

Add two MCP servers, one for the ontology and one for the data agent. Both sign you in with your Microsoft Entra account, so they don't need headers.

To get their URLs, run this in the Visual Studio Code terminal:

+++Get-Content .env | Select-String "FABRIC_.*_MCP_URL"+++

1. In the GitHub Copilot app, select **Customize**, and then select **Add > MCP Server...**.
2. Enter these values, and then select **Add server**:
    - **Server name**: +++fabric-iq-ontology+++
    - **Server type**: HTTP
    - **URL**: the **FABRIC_ONTOLOGY_MCP_URL** value, everything after the **=**
3. Select **Add > MCP Server...** again, enter these values, and then select **Add server**:
    - **Server name**: +++fabric-iq-data-agent+++
    - **Server type**: HTTP
    - **URL**: the **FABRIC_DATA_AGENT_MCP_URL** value, everything after the **=**
4. Check that both servers are turned on in the **MCP Servers** list. When prompted, sign in with your lab credentials.

Then select **New** and ask:

+++How many Professional Claw Hammers does each store have in stock?+++

+++Which marketing channel has the highest conversion rate in the web analytics data?+++

===

# Exercise: Work IQ

Work IQ gives agents your Microsoft 365 work context: email, meetings, files, chats, and people. It always uses your own permissions.

Your mailbox has three emails about an out-of-stock Professional Claw Hammer. Open Outlook in the browser to see them.

## Call Work IQ from notebooks

In each notebook, select **Select Kernel > Python Environments > .venv** if it isn't already selected. When a notebook opens a browser sign-in, use your lab credentials.

1. Open **notebooks/workiq-api-concepts.ipynb** and run each cell. You learn the Work IQ API concepts and ask about your own work context.
2. Open **notebooks/workiq-mcp.ipynb** and run each cell. You call Work IQ as a tool through its MCP server.
3. Optional: try **notebooks/workiq-tools-actions.ipynb** and **notebooks/workiq-a2a.ipynb**.

## Use Work IQ in the GitHub Copilot app

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

In each notebook, select **Select Kernel > Python Environments > .venv** if it isn't already selected. When a notebook opens a browser sign-in, use your lab credentials.

1. Open **notebooks/foundryiq-basic.ipynb** and run each cell. You build a multi-source knowledge base over the HR and health indexes and query it with agentic retrieval.
2. Open **notebooks/foundryiq-mcp.ipynb** and run each cell. You call a knowledge base through its MCP endpoint.
3. Open **notebooks/foundryiq-fabriciq-ontology.ipynb** and run each cell. You add the Fabric IQ ontology as a knowledge source.
4. Open **notebooks/foundryiq-fabriciq-dataagent.ipynb** and run each cell. You add the Fabric data agent as a knowledge source for analytical questions.
5. Open **notebooks/foundryiq-workiq.ipynb** and run each cell. You add a Work IQ knowledge source, so a knowledge base can search your emails alongside the HR documents.
6. Open **notebooks/foundryiq-webiq.ipynb** and run each cell. You add a Web IQ knowledge source, so answers combine the HR documents with web results.

## Use Foundry IQ in the GitHub Copilot app

The knowledge base MCP endpoint uses a Search query key, so first copy one from the Azure portal:

1. Go back to the Azure portal in the browser.
2. Search for +++search-+++ in the top search bar, and open the Azure AI Search service in your resource group.
3. Select **Settings > Keys**, and copy a key under **Manage query keys**.

Then get the knowledge base's MCP URL by running this in the Visual Studio Code terminal:

+++Get-Content .env | Select-String "FOUNDRY_IQ_MCP_URL"+++

Then add the MCP server:

1. In the GitHub Copilot app, select **Customize**, and then select **Add > MCP Server...**.
2. Enter these values:
    - **Server name**: +++foundry-iq+++
    - **Server type**: HTTP
    - **URL**: the **FOUNDRY_IQ_MCP_URL** value, everything after the **=**
3. Select **Add header**, and enter the name +++api-key+++ and the query key you copied.
4. Select **Add server**, and check that the server is turned on in the **MCP Servers** list.

Then select **New** and ask:

+++What benefits are available, and when do I need to enroll?+++

===

# Exercise: Foundry hosted agents

Each agent in the **src/** folder is a Microsoft Agent Framework app that uses Foundry IQ, Work IQ, or both. The agents are already deployed as Foundry hosted agents. You run one locally first, and then try the hosted version.

| Agent | How it reaches its data |
| --- | --- |
| **agent-foundryiq-mcp** | Connects to a knowledge base through its Foundry IQ MCP endpoint |
| **agent-foundryiq-api** | Calls the knowledge base retrieval API from a custom Python tool |
| **agent-toolbox-foundryiq** | Uses a Foundry toolbox with the knowledge base, web search, and code interpreter |
| **agent-toolbox-workiq** | Uses a Work IQ toolbox for your Microsoft 365 context |
| **agent-toolbox-foundryiq-workiq** | Uses a Foundry toolbox over a knowledge base with a Work IQ source |

## Run an agent locally

1. In the Visual Studio Code terminal, start the agent:

    +++azd ai agent run agent-foundryiq-mcp+++

2. Open the local playground link that the command prints, and ask:

    +++What benefits are available, and when do I need to enroll?+++

    You can also open a second terminal and send the question from the command line:

    +++azd ai agent invoke --local "What benefits are available, and when do I need to enroll?"+++

3. Open **src/agent-foundryiq-mcp/main.py** to see how the agent connects to the knowledge base.
4. Stop the agent with **Ctrl+C**.

## Try the hosted agents

1. Call the hosted version of the same agent:

    +++azd ai agent invoke agent-foundryiq-mcp "What benefits are available, and when do I need to enroll?"+++

2. Open the hosted playground. Get the agent's details:

    +++azd ai agent show agent-foundryiq-mcp+++

    Open the **Playground URL** from the output, sign in with your lab credentials if prompted, and ask the same question.
3. Try a Work IQ agent in its hosted playground:

    +++azd ai agent show agent-toolbox-workiq+++

    Open the **Playground URL** from the output, and ask:

    +++Check my recent emails for messages about the Professional Claw Hammer. Summarize what colleagues are saying and what actions have been requested.+++

    The first time, the agent asks you to sign in to the Work IQ connection. Select **Open consent**, sign in with your lab credentials, check **I have verified this request and trust the source**, and select **Allow access**. If the window then shows an "Authentication failed" message, close it.

    After you've signed in, start a new chat and ask the question again.

4. Optional: compare **agent-foundryiq-api** and **agent-toolbox-foundryiq**, locally and hosted.

Select **Next** to review what you built.

===

# Summary

You built context-aware AI with Microsoft IQ:

- A Web IQ knowledge source that grounds answers in current web content.
- Fabric IQ knowledge sources over a Fabric ontology and a Fabric data agent.
- A Work IQ knowledge source over your Microsoft 365 email.
- Foundry IQ knowledge bases with agentic retrieval over indexed documents, called through the retrieval API and MCP.
- MCP servers for each IQ in the GitHub Copilot app.
- Microsoft Agent Framework agents that use those knowledge bases, run locally and as Foundry hosted agents.

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
