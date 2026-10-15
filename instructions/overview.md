@lab.Title

## Before you begin

<details>
<summary><strong>Lab credentials (select to expand when you need to sign in)</strong></summary>

### Sign in to the virtual machine (Windows)

- **User name**: +++@lab.VirtualMachine(Win11-Pro-Base).Username+++
- **Password**: +++@lab.VirtualMachine(Win11-Pro-Base).Password+++

### Sign in to Azure and Microsoft 365

Use these credentials for the Azure portal, Microsoft Fabric, Outlook, and any browser sign-in prompt from a notebook or agent:

- **Username**: +++@lab.CloudPortalCredential(User1).Username+++
- **Temporary Access Pass**: +++@lab.CloudPortalCredential(User1).AccessToken+++

</details>

## Overview

In this lab, you build context-aware AI with Microsoft IQ. You create Foundry IQ knowledge bases with agentic retrieval, extend them with Fabric IQ (structured business data in Microsoft Fabric) and Work IQ (the signed-in user's Microsoft 365 context), and call them from Microsoft Agent Framework agents that run locally and as Foundry hosted agents.

The scenario is Contoso, a DIY retailer: HR and benefits documents in Azure AI Search, product, store, and inventory data in Fabric, and inventory emails in your mailbox.

## Get started

### Sign in to Windows

Sign in to the virtual machine with the credentials above.

### Open the lab folder in Visual Studio Code

1. Open Visual Studio Code.
2. Select **File > Open Folder**, go to **Desktop**, select the **ignite26-PREL42** folder, and then select **Select Folder**.
3. When asked whether you trust the authors of the files, select **Yes, I trust the authors**.

### Check the environment setup

Your Azure resources, search indexes, Fabric items, hosted agents, and sample emails are created for you in the background when the lab starts. The Fabric items finish last.

1. Open **Desktop > lifecycle-log.txt**.
2. Look for these lines:
    - `READY: Foundry IQ notebooks`: you can start the first notebooks.
    - `READY: Agents`: the hosted agents are deployed.
    - `READY: Fabric IQ notebooks`: the Fabric notebooks are ready.

    If a line says `NOT READY`, let a proctor know. You can keep working on the parts that are ready.

3. Open the **.env** file in the lab folder and check that it includes `AZURE_AI_SEARCH_SERVICE_ENDPOINT`, `AZURE_OPENAI_ENDPOINT`, and `FOUNDRY_PROJECT_ENDPOINT`. After the Fabric setup completes, it also includes `FABRIC_WORKSPACE_ID` and `FABRIC_ONTOLOGY_ID`.

### Sign in to the Azure Developer CLI

The notebooks and agents use your Azure Developer CLI sign-in.

1. In Visual Studio Code, open a terminal with **Terminal > New Terminal**.
2. Run:

    +++azd auth login+++

3. In the browser window that opens, sign in with your lab **Username** and **Temporary Access Pass**.

> [!IMPORTANT]
> Don't run `azd up`, `azd provision`, or `azd deploy`. Everything is already provisioned and deployed for you.

### Select the notebook kernel

When you open a notebook, select **Select Kernel > Python Environments**, and then select the **.venv** environment in the lab folder (`.venv\Scripts\python.exe`).

## Part 1: Foundry IQ knowledge bases

1. Open **notebooks/foundryiq-basic.ipynb** and run each cell. You build a multi-source knowledge base over the HR and health indexes and query it with agentic retrieval.
2. Open **notebooks/foundryiq-mcp.ipynb** and run each cell. You call a knowledge base through its MCP endpoint.

## Part 2: Agents grounded in Foundry IQ

Each agent in the **src/** folder is a Microsoft Agent Framework app. Try one locally, then call its deployed version.

1. In the terminal, start the agent locally:

    +++azd ai agent run agent-foundryiq-mcp+++

2. Open a second terminal and send it a question:

    +++azd ai agent invoke --local "What benefits are available, and when do I need to enroll?"+++

3. Stop the local agent with **Ctrl+C**, and then call the hosted version of the same agent:

    +++azd ai agent invoke agent-foundryiq-mcp "What benefits are available, and when do I need to enroll?"+++

4. Repeat with **agent-foundryiq-api** (a custom retrieval tool instead of MCP) and **agent-toolbox-foundryiq** (a Foundry toolbox with the knowledge base, web search, and code interpreter). Compare the code in each agent's **main.py**.

## Part 3: Fabric IQ

Wait for `READY: Fabric IQ notebooks` in the log file.

1. Open **notebooks/foundryiq-fabriciq-ontology.ipynb**. You add a Fabric ontology knowledge source over Contoso's product, store, and inventory data.
2. Open **notebooks/fabriciq-ontology-mcp.ipynb** to call the ontology's MCP endpoint directly.
3. Open **notebooks/foundryiq-fabriciq-dataagent.ipynb**. You add a Fabric Data Agent knowledge source for analytical questions.
4. Optional: try **notebooks/fabriciq-dataagent-mcp.ipynb** and **notebooks/fabriciq-graph.ipynb**.

When a notebook opens a browser sign-in, use your lab credentials.

## Part 4: Work IQ

Your mailbox has three emails about an out-of-stock Professional Claw Hammer. Open Outlook in the browser to see them.

1. Open **notebooks/foundryiq-workiq.ipynb**. You add a Work IQ knowledge source so the knowledge base can search your emails alongside the HR documents.
2. Call the Work IQ agents:

    +++azd ai agent invoke agent-toolbox-workiq --new-session --new-conversation "Check my recent emails for messages about the Professional Claw Hammer. Summarize what colleagues are saying and what actions have been requested."+++

    The first time, the agent replies with a sign-in link. Open it, sign in with your lab credentials, and then run the command again.

3. Try **agent-toolbox-foundryiq-workiq**, which reaches Work IQ through a knowledge base:

    +++azd ai agent invoke agent-toolbox-foundryiq-workiq --new-session --new-conversation "Search my recent emails for Professional Claw Hammer and summarize requested actions. Use the knowledge base and its Work IQ source."+++

## Part 5: Web IQ

If your **.env** file includes `WEB_IQ_KEY`, open **notebooks/foundryiq-webiq.ipynb** to add web grounding through Web IQ.

## Keep going

If you have time left, explore the Work IQ API notebooks: **workiq-api-concepts.ipynb**, **workiq-mcp.ipynb**, **workiq-tools-actions.ipynb**, and **workiq-a2a.ipynb**.

Select **Next** to review what you built.

# Outline

Organize notebooks into folders

# Slides: Microsoft IQ intro (with demo of IQ working in a Copilot)

# Setup VS Code & GitHub Copilot App

Only open the repo in VS Code
Dont open the repo in GitHub Copilot App

Say hi to the agent? Ask for SF restaurant tips.

# Slides: Web IQ (AB)

# Exercise: Web IQ

* Notebook
* Use as MCP server in App

# Slides: Fabric IQ (PF)

# Fabric IQ

* Notebooks
* Use as MCP server in App

# Slides: Work IQ (PF)

# Work IQ

* Notebooks
* Use as MCP server in App

# Slides: Foundry IQ (PF)

# Foundry IQ

* Notebooks
* Use as MCP server in App

# Slides: Foundry hosted agents (PF)

# Foundry hosted agents

* Local playground
* Hosted playground
