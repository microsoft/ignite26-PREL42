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

### Check the environment setup

Your Azure resources, search indexes, Fabric items, hosted agents, and sample emails are already created for you.

1. In Visual Studio Code, select **Terminal > New Terminal**.
2. Wait a few seconds for the Python virtual environment to be activated in the terminal.
3. Run this command to show the MCP server URLs that setup saved for you:

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
6. Return to the **GitHub Copilot** app. On the next screen, do not select any folder; select **Continue**. You will use the app only for chat; you will use VS Code for interacting with the lab folder.
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
4. If a dialog invites you to try Web IQ in a playground, select **Skip**.
5. You are already on the profile management page. Scroll to the bottom of the page. Under **Authentication > API Keys**, select **Create API key**, enter any name, and select **Create**. Copy the new key.

Then save the key so the notebooks can use it:

1. In Visual Studio Code, open the **.env** file in the lab folder.
2. Add a new line at the end of the file with **WEB_IQ_KEY=**, and paste the key after the equals sign. For example: **WEB_IQ_KEY=your-key**.
3. Save the file.

## Call Web IQ from a notebook

1. Open **notebooks/webiq-mcp.ipynb**.
2. If the lab kernel isn't already selected, select **Select Kernel > Python Environments**, and choose the **ignite26-prel42** environment with the path **.venv\Scripts\python.exe**.
3. Run each cell. You call the Web IQ MCP endpoint directly to search the web, images, and videos.

> [!Hint] **Troubleshooting:** If code cells get stuck and keep spinning, try these remediation steps:
>
> First, confirm that the selected kernel is the lab's **.venv\Scripts\python.exe**. After each recovery step below, reselect the lab kernel if needed and rerun the cells from the top of the notebook:
>
> 1. Select **Restart** from the notebook toolbar at the top. If that doesn't work:
> 2. Select **Developer: Reload Window** from the VS Code command palette. If that doesn't work:
> 3. Close VS Code completely and restart it. Reopen the lab folder and notebook. If cells still get stuck, let a proctor know.

## Use Web IQ in the GitHub Copilot app

1. In the GitHub Copilot app, select **Customize**, and then select **Add > MCP Server...**.
2. Enter these values:
    - **Server name**: +++web-iq+++
    - **Server type**: HTTP
    - **URL**: +++https://api.microsoft.ai/v3/mcp+++
3. Select **Add header**, and enter the name +++x-apikey+++. Switch to Visual Studio Code, copy the **WEB_IQ_KEY** value from **.env**, and then switch back to the app and paste it as the header value.
4. Switch to the **Installed** tab. Under **MCP Servers**, confirm that **web-iq** is toggled on and has a green check mark.

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
5. Return to the workspace and open **ContosoDIYReviewGraph**. Explore the graph's node and edge types. Look for **Product**, **Reviewer**, **Review**, and **Feature**, and see how the relationships connect reviews to products and features. In the **Components** pane, expand **Edges > MENTIONS** to see the **sentiment**, **confidence**, and **evidenceExcerpt** property names. You are inspecting the graph's schema, not previewing property values; you don't need to select the individual properties. These properties describe the sentiment of a review's mention of a particular feature, adding feature-level sentiment context to the product catalog. You will query the graph's data in **notebooks/fabriciq-graph.ipynb**.
6. Return to the workspace and open the **ContosoWebAnalytics** semantic model. Explore the relationship diagram. In the **Data** pane on the right, expand **Sessions** to see fields such as **Converted** and **RevenueAmount**, and expand **Channels** to see **Channel** and **ChannelGroup**. Follow the relationship line between these tables in the diagram to see how sessions connect to marketing channels. You are inspecting the model's structure, not previewing data rows.
7. Return to the workspace and open **ContosoDIYDataAgent**. Review its configured data sources: the ontology, review graph, and web analytics semantic model. The data agent brings these sources together so you can ask analytical questions in natural language.

## Call Fabric IQ from notebooks

When you open each notebook, if the lab kernel isn't already selected, select **Select Kernel > Python Environments**, and choose the **ignite26-prel42** environment with the path **.venv\Scripts\python.exe**.

1. Open **notebooks/fabriciq-ontology-mcp.ipynb** and run each cell. You call the ontology's MCP endpoint directly.
2. Open **notebooks/fabriciq-graph.ipynb** and run each cell. You query the product review graph with GQL over the Fabric REST API.
3. Open **notebooks/fabriciq-dataagent-mcp.ipynb** and run each cell. You call the Fabric data agent's MCP endpoint for analytical questions.

> [!Hint] **Troubleshooting:** If code cells get stuck and keep spinning, try these remediation steps:
>
> First, confirm that the selected kernel is the lab's **.venv\Scripts\python.exe**. After each recovery step below, reselect the lab kernel if needed and rerun the cells from the top of the notebook:
>
> 1. Select **Restart** from the notebook toolbar at the top. If that doesn't work:
> 2. Select **Developer: Reload Window** from the VS Code command palette. If that doesn't work:
> 3. Close VS Code completely and restart it. Reopen the lab folder and notebook. If cells still get stuck, let a proctor know.

## Use Fabric IQ in the GitHub Copilot app

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
4. Switch to the **Installed** tab. Under **MCP Servers**, find **fabric-iq-ontology** and select **Sign in**. A Microsoft Entra sign-in page opens in the browser. Sign in with:

    - **Username**: +++@lab.CloudPortalCredential(User1).Username+++
    - **Temporary Access Pass**: +++@lab.CloudPortalCredential(User1).AccessToken+++

    At the **Enter Temporary Access Pass** screen, enter the pass above and select **Sign in**. Then return to the GitHub Copilot app.

5. On the **Installed** tab, find **fabric-iq-data-agent**, select **Sign in**, and complete the sign-in in the browser the same way.
6. Confirm that both servers are toggled on and each has a green check mark. If sign-in still fails, let a proctor know.

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

In each notebook, if the lab kernel isn't already selected, select **Select Kernel > Python Environments**, and choose the **ignite26-prel42** environment with the path **.venv\Scripts\python.exe**.

1. Open **notebooks/workiq-mcp.ipynb** and run each cell. You sign in, list the tools, ask about the sample emails, discover resource paths and schemas, fetch structured email data, and discover agents.
2. Open **notebooks/workiq-mcp-actions.ipynb** and run the **Step 1** and **Step 2** cells to sign in and inspect the write tools and their schemas. The remaining action cells change real data in your lab mailbox and calendar without input prompts, so run them one at a time and check the result in Outlook after each:

    1. Run the **Step 3** cell to create the restock-review event. In Outlook, open **Calendar** and go to tomorrow. Find **Contoso Seattle: Professional Claw Hammer restock review**, a 30-minute event at 15:00 UTC (Outlook shows it in your local time zone), and open it to see the agenda built from the sample emails.
    2. Run the **Step 4** cell to update the event. Refresh the calendar and confirm that the subject changed to **Contoso Seattle: HTHM001600 restock and transfer coordination** and that the event is now 45 minutes long.
    3. Run the **Step 5** cell to delete the event. Refresh the calendar and confirm that the event is gone.
    4. Run the **Step 6** cell to send the follow-up email. In Outlook, open your **Inbox** and find **Contoso Seattle: HTHM001600 restock follow-up**. It can take a minute to arrive. You can also find it in **Sent Items**.

3. Open **notebooks/workiq-a2a.ipynb** to discover Work IQ as a remote agent and delegate an email-summary task through A2A.

> [!Hint] **Troubleshooting:** If code cells get stuck and keep spinning, try these remediation steps:
>
> First, confirm that the selected kernel is the lab's **.venv\Scripts\python.exe**. After each recovery step below, reselect the lab kernel if needed and rerun the setup and sign-in cells. In **workiq-mcp-actions.ipynb**, rerun only **Step 1** and **Step 2**, then check Outlook before retrying an action; don't repeat actions that already completed. If the restart lost state needed by an action, ask a proctor for help:
>
> 1. Select **Restart** from the notebook toolbar at the top. If that doesn't work:
> 2. Select **Developer: Reload Window** from the VS Code command palette. If that doesn't work:
> 3. Close VS Code completely and restart it. Reopen the lab folder and notebook. If cells still get stuck, let a proctor know.

## Use Work IQ in the GitHub Copilot app

Work IQ is available as a plugin, so you install it instead of adding the MCP server yourself.

1. In the GitHub Copilot app, select **Customize**, and then select **Browse**.
2. Search for +++workiq+++.
3. Under **Plugins**, find **WorkIQ** from Microsoft ("Find answers across Microsoft 365 emails, meetings, documents, and Teams messages"), and select **Install**.
4. Select **New** and ask:

    +++Check my recent emails for messages about the Professional Claw Hammer. Summarize what colleagues are saying and what actions have been requested.+++

5. If the chat shows **Extension "workiq" needs you to sign in to MCP server "workiq"**, select **Sign in**. Before you sign in, the agent may answer that it can't check your emails; that's expected.
6. A Microsoft Entra sign-in page opens in the browser. Sign in with:

    - **Username**: +++@lab.CloudPortalCredential(User1).Username+++
    - **Temporary Access Pass**: +++@lab.CloudPortalCredential(User1).AccessToken+++

    At the **Enter Temporary Access Pass** screen, enter the pass above and select **Sign in**.

7. Return to the GitHub Copilot app and send the same question again:

    +++Check my recent emails for messages about the Professional Claw Hammer. Summarize what colleagues are saying and what actions have been requested.+++

    Confirm that Work IQ returns a summary of the sample emails. If sign-in still fails or the chat reports that the MCP server is not configured, let a proctor know.

===

# Exercise: Foundry IQ

Foundry IQ knowledge bases combine knowledge sources, such as search indexes, Fabric IQ, Work IQ, and Web IQ, and use agentic retrieval to plan queries across them and return grounded answers with citations.

## Inspect the indexed documents before running code

Foundry IQ knowledge bases run on Azure AI Search. Your search service already has two indexes of HR and health documents. Look at what's indexed and compare it with the original files before you build knowledge bases over them.

1. In the Azure portal, search for +++search-+++ in the top search bar, and open the Azure AI Search service in your resource group.
2. Select **Search management > Indexes**. Note the two indexes, **hrdocs** and **healthdocs**, and their document counts. Each document is a chunk of a source file.
3. Open **hrdocs**, and then open **Search explorer**. In the search text box, enter +++vacation+++ and select **Search**. Inspect a result's **snippet**, **blob_path**, and **snippet_parent_id** fields.
4. In File Explorer, open **Desktop > ignite26-PREL42 > data > ai-search-data > hrdocs**. Open **Contoso_DIY_Company_Overview.md** in Visual Studio Code and find the **Vacation Perks** table.

**Compare the records:** Find the chunk in Search explorer whose **blob_path** matches the file, and check that it contains the same vacation tiers. How many weeks does a senior employee get? Keep the file open: the first notebook asks this question, and you can check whether the answer cites this source.

## Call Foundry IQ from notebooks

In each notebook, if the lab kernel isn't already selected, select **Select Kernel > Python Environments**, and choose the **ignite26-prel42** environment with the path **.venv\Scripts\python.exe**.

1. Open **notebooks/foundryiq-basic.ipynb** and run each cell. You upload a file to a file knowledge source, then build a multi-source knowledge base over the HR and health indexes and query it with agentic retrieval. Review the activity log and references for the vacation question.
2. Open **notebooks/foundryiq-mcp.ipynb** and run each cell. You call a knowledge base through its MCP endpoint.
3. Open **notebooks/foundryiq-fabriciq-ontology.ipynb** and run each cell. You add the Fabric IQ ontology as a knowledge source.
4. Open **notebooks/foundryiq-fabriciq-dataagent.ipynb** and run each cell. You add the Fabric data agent as a knowledge source for analytical questions.
5. Open **notebooks/foundryiq-workiq.ipynb** and run each cell. You add a Work IQ knowledge source, so a knowledge base can search your emails alongside the HR documents.
6. Open **notebooks/foundryiq-webiq.ipynb** and run each cell. You add a Web IQ knowledge source, so answers combine the HR documents with web results.

> [!Hint] **Troubleshooting:** If code cells get stuck and keep spinning, try these remediation steps:
>
> First, confirm that the selected kernel is the lab's **.venv\Scripts\python.exe**. After each recovery step below, reselect the lab kernel if needed and rerun the cells from the top of the notebook:
>
> 1. Select **Restart** from the notebook toolbar at the top. If that doesn't work:
> 2. Select **Developer: Reload Window** from the VS Code command palette. If that doesn't work:
> 3. Close VS Code completely and restart it. Reopen the lab folder and notebook. If cells still get stuck, let a proctor know.

## Verify what you built in the browser

1. Return to your Azure AI Search service. Select **Agentic retrieval > Knowledge bases** and refresh the list.
2. Find the knowledge bases the notebooks created: **file-docs-knowledge-base**, **multisource-search-knowledge-base**, **multisource-fabric-ontology-knowledge-base**, **multisource-fabric-data-agent-knowledge-base**, **multisource-workiq-entra-knowledge-base**, and **multisource-web-knowledge-base**. Setup also created **contoso-company-kb-low** and **contoso-company-kb-minimal**; the hosted agents and the Foundry IQ MCP endpoint use **contoso-company-kb-minimal**.
3. Open **multisource-search-knowledge-base** and inspect its knowledge sources: **hrdocs-knowledge-source** and **healthdocs-knowledge-source**. Then open one of the other **multisource-** knowledge bases and see that it combines the same two sources with a Fabric IQ, Work IQ, or Web IQ source.
4. Select **Agentic retrieval > Knowledge sources**. Compare **file-docs-knowledge-source**, which the service indexed for you from the uploaded file, with **hrdocs-knowledge-source**, which points to the index you inspected earlier.
5. Compare one cited vacation claim from the notebook with **Contoso_DIY_Company_Overview.md**. A **blob_path** is citation metadata and might not be a directly accessible link.

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

# Exercise: Foundry Hosted Agents

In this exercise, you explore two Microsoft Agent Framework apps: one connects to a Foundry IQ knowledge base through its MCP endpoint, and one connects directly to Work IQ through MCP for your Microsoft 365 context. Both are deployed as Foundry Hosted Agents. Explore both agents' code, run them locally, and try both hosted versions in the Microsoft Foundry playground.

| Agent | How it reaches its data |
| --- | --- |
| **agent-foundryiq-mcp** | Connects to a Foundry IQ knowledge base through its MCP endpoint, plus local tools for enrollment dates |
| **agent-workiq-maf** | Connects directly to Work IQ MCP; uses local browser sign-in or hosted OAuth identity passthrough |

## Agent 1: Foundry IQ through MCP

### Explore the code

1. Open **src\agent-foundryiq-mcp\main.py** in Visual Studio Code.
2. Find where the agent builds the knowledge base MCP endpoint and connects to it through **MCPStreamableHTTPTool**, allowing only the **knowledge_base_retrieve** tool. The agent authenticates to Azure AI Search with its own identity: your Azure Developer CLI sign-in locally, and its managed identity when hosted.
3. Find the **get_enrollment_deadline_info** and **get_current_date** tools, and the instructions that tell the model to ground answers in the knowledge base and use these tools for benefits deadlines.

### Run locally

1. In the Visual Studio Code terminal, start the agent:

    +++azd ai agent run agent-foundryiq-mcp+++

2. Wait for a local playground to open in the browser. Then ask:

    +++What benefits does Contoso offer, and when do I need to enroll?+++

3. Stop the local agent with **Ctrl+C** in the terminal where you started it.

### Try the hosted version

1. Get the agent's deployment details:

    +++azd ai agent show agent-foundryiq-mcp+++

2. Open the **Playground URL** from the output. This opens the agent in the Microsoft Foundry playground. If prompted to sign in, use:

    - **Username**: +++@lab.CloudPortalCredential(User1).Username+++
    - **Temporary Access Pass**: +++@lab.CloudPortalCredential(User1).AccessToken+++

3. Ask the same question:

    +++What benefits does Contoso offer, and when do I need to enroll?+++

4. After the agent responds, select **Traces** beneath its answer. In the **Trajectories** tab, expand the agent run and select the **Execute Tool** entry for **knowledge_base_retrieve**. In **Input + Output**, inspect the queries the agent sent and the document content returned. Then find the tool call for **get_enrollment_deadline_info** and compare its dates with the answer.

## Agent 2: Work IQ through direct MCP

### Explore the code

1. Open **src\agent-workiq-maf\main.py** in Visual Studio Code.
2. Find the **ask_work_iq** tool. For local runs, it connects directly to **https://workiq.svc.cloud.microsoft/mcp** through **MCPStreamableHTTPTool**, allowing only the read-only **ask** operation.
3. Find **create_hosted_agent**. For hosted runs, it registers the same MCP endpoint through **FoundryChatClient.get_mcp_tool**, using **work-iq-mcp-connection** for per-user OAuth identity passthrough.
4. Open **src\agent-workiq-maf\workiq_auth.py**. Find the **PublicClientApplication** and the delegated **WorkIQAgent.Ask** scope. Local sign-in uses the same app registration and browser authentication pattern as the Work IQ notebook. In hosted mode, Microsoft Foundry manages authorization through the MCP connection instead.

### Run locally

1. In the Visual Studio Code terminal, from the lab repository root, start the agent:

    +++azd ai agent run agent-workiq-maf+++

2. A Work IQ sign-in window opens before the agent starts listening. Select the same lab account you used for the Work IQ notebook. If prompted to sign in again, use:

    - **Username**: +++@lab.CloudPortalCredential(User1).Username+++
    - **Temporary Access Pass**: +++@lab.CloudPortalCredential(User1).AccessToken+++

    At the **Enter Temporary Access Pass** screen, enter the pass above and select **Sign in**. Complete any requested consent. This sign-in is separate from your Azure Developer CLI sign-in for model access.

    > [!Help] **Sign-in window:** If the sign-in window is hidden, minimize the other windows **inside the lab virtual machine** until you find it. Keep the outer browser hosting the Skillable lab open.

3. Wait for the terminal to show **Running on http://127.0.0.1:8088**. The local playground opens in the browser. If it opened earlier, wait for the agent to start before sending a message.
4. In the local playground, ask:

    +++Check my recent emails for messages about the Professional Claw Hammer. Summarize what colleagues are saying and what actions have been requested.+++

5. Review the answer and its sources. Confirm that it refers to messages in your lab mailbox.
6. Stop the local agent with **Ctrl+C** in the terminal where you started it.

> [!Help] **Local sign-in is single-user:** The local agent keeps its token cache in memory and renews tokens for the user who signed in at startup. Do not share or expose the local port. To change users, or if sign-in expires or is revoked, stop and restart the agent and sign in again.

### Try the hosted version

1. Get the deployed agent's details:

    +++azd ai agent show agent-workiq-maf+++

2. Open the **Playground URL** from the output. This opens the agent in the Microsoft Foundry playground. If prompted to sign in, use:

    - **Username**: +++@lab.CloudPortalCredential(User1).Username+++
    - **Temporary Access Pass**: +++@lab.CloudPortalCredential(User1).AccessToken+++

3. In the hosted playground, ask:

    +++Check my recent emails for messages about the Professional Claw Hammer. Summarize what colleagues are saying and what actions have been requested.+++

4. If Work IQ requests authorization, select **Open consent** on the most recent active consent request.

    > [!Hint] **Multiple consent buttons:** If the chat shows multiple consent buttons, do not reopen links from earlier attempts.

    Select the same lab account. If prompted to sign in again, use:

    - **Username**: +++@lab.CloudPortalCredential(User1).Username+++
    - **Temporary Access Pass**: +++@lab.CloudPortalCredential(User1).AccessToken+++

    At the **Enter Temporary Access Pass** screen, enter the pass above and select **Sign in**. Review the consent request, check **I have verified this request and trust the source** if prompted, and select **Allow access**.

5. Close the consent window and return to the hosted playground. If the agent has not continued, send the email question again. Local browser sign-in and hosted MCP authorization are separate; Microsoft Foundry manages the hosted connection for your signed-in identity.

    > [!Hint] **Consent window error:** If a consent window displays **Authentication failed** with **Code ... not found**, close that window and retry the email question in the playground. Do not assume authorization succeeded or failed from the popup alone: confirm that the agent can return your mailbox results. If the request still fails or repeatedly asks for consent, let a proctor know.

6. Review the answer and compare it with the local result. Once the agent returns your mailbox answer, you do not need to select any remaining consent buttons.
7. Select **Traces** beneath the answer. In **Trajectories**, expand the run and select the Work IQ MCP tool call. In **Input + Output**, inspect the request and returned work context.

===

# Summary

You built context-aware AI with Microsoft IQ:

- A Web IQ knowledge source that grounds answers in current web content.
- Fabric IQ knowledge sources over a Fabric ontology and a Fabric data agent.
- A Work IQ knowledge source over your Microsoft 365 email.
- Foundry IQ knowledge bases with agentic retrieval over indexed documents, called through the retrieval API and MCP.
- MCP servers for each IQ in the GitHub Copilot app.
- Microsoft Agent Framework agents using MCP for Foundry IQ and Work IQ, tested locally and in the Microsoft Foundry hosted playground.

## Continue learning

- [Microsoft Web IQ documentation](https://learn.microsoft.com/en-us/web-iq/)
- [What is Foundry IQ?](https://learn.microsoft.com/azure/ai-foundry/agents/concepts/what-is-foundry-iq)
- [What is Fabric IQ?](https://learn.microsoft.com/fabric/iq/overview)
- [Work IQ MCP tool reference](https://learn.microsoft.com/microsoft-365/copilot/extensibility/work-iq/mcp/tool-reference)
- [Agentic retrieval overview](https://learn.microsoft.com/azure/search/agentic-retrieval-overview)
- [Create a Work IQ knowledge source](https://learn.microsoft.com/azure/search/agentic-knowledge-source-how-to-work-iq)
- [Create a Fabric Ontology knowledge source](https://learn.microsoft.com/azure/search/agentic-knowledge-source-how-to-fabric-ontology)
- [Microsoft Agent Framework](https://learn.microsoft.com/agent-framework/)

## Try it on your own

Everything in this lab is in the [session repository](https://github.com/microsoft/ignite26-PREL42). To run it in your own Azure subscription, follow [Deploy to your own Azure subscription](https://github.com/microsoft/ignite26-PREL42/blob/main/docs/deploy-yourself.md).
