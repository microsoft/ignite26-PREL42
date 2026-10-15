# Source

Microsoft Agent Framework agents, each deployable as a Microsoft Foundry hosted agent:

| Agent | How it reaches its data |
| --- | --- |
| `agent-foundryiq-api` | Calls the knowledge base retrieval API from a custom Python tool |
| `agent-foundryiq-mcp` | Connects to the knowledge base through its Foundry IQ MCP endpoint |
| `agent-toolbox-foundryiq` | Uses a Foundry toolbox with the knowledge base, web search, and code interpreter |
| `agent-toolbox-foundryiq-workiq` | Uses a Foundry toolbox over a knowledge base with a Work IQ source |
| `agent-toolbox-workiq` | Uses a Work IQ toolbox for the caller's Microsoft 365 context |
| `agent-workiq-maf` | Uses the Work IQ toolbox as a "Workmate" assistant |

The notebooks are in [`notebooks/`](../notebooks/).
