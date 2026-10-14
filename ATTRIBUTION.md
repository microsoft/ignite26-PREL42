# Attribution

This repository is ported from two public Microsoft repositories:

| Upstream | Revision used | Retained material | License |
| --- | --- | --- | --- |
| [microsoft/iqdeepdive](https://github.com/microsoft/iqdeepdive) | [`b0445d127e1817e4a7ae11adcc2beb5d451829b8`](https://github.com/microsoft/iqdeepdive/commit/b0445d127e1817e4a7ae11adcc2beb5d451829b8) | Notebooks, agents, sample data, Bicep, and setup scripts | [MIT](LICENSE) |
| [microsoft/aitour27-ILL344-turning-data-into-agent-ready-knowledge-with-microsoft-iq](https://github.com/microsoft/aitour27-ILL344-turning-data-into-agent-ready-knowledge-with-microsoft-iq) | [`130cbafaa9d4aa0a0167948599badb14790d5c2e`](https://github.com/microsoft/aitour27-ILL344-turning-data-into-agent-ready-knowledge-with-microsoft-iq/commit/130cbafaa9d4aa0a0167948599badb14790d5c2e) | Skillable lifecycle, email seeding, and teardown scripts, service principal credential handling, and lab instruction structure | Code under [MIT](LICENSE); documentation under [CC BY-SA 4.0](LICENSE-DOCS) |

The Fabric lakehouse sample data in `data/lakehouse-data/` is copied from a third repository, with the unused
`image_embedding` and `description_embedding` fields removed:

| Upstream | Revision used | Retained material | License |
| --- | --- | --- | --- |
| [microsoft/ai-tour-26-zava-diy-dataset-plus-mcp](https://github.com/microsoft/ai-tour-26-zava-diy-dataset-plus-mcp) | [`726243b50fe0f8fc10e7d799c6c8e4c4773f12df`](https://github.com/microsoft/ai-tour-26-zava-diy-dataset-plus-mcp/commit/726243b50fe0f8fc10e7d799c6c8e4c4773f12df) | `data/database/product_data.json` and `data/database/reference_data.json` | [MIT](https://github.com/microsoft/ai-tour-26-zava-diy-dataset-plus-mcp/blob/main/LICENSE) |

iqdeepdive in turn incorporates and adapts material from these public Microsoft repositories:

| Upstream | Revision used | Retained material | License |
| --- | --- | --- | --- |
| [microsoft/Build26-LAB532-from-data-to-context-agent-ready-knowledge-with-foundry-iq](https://github.com/microsoft/Build26-LAB532-from-data-to-context-agent-ready-knowledge-with-foundry-iq) | [`d12d7b7bf893ad0328fd1db798c240ee172476b8`](https://github.com/microsoft/Build26-LAB532-from-data-to-context-agent-ready-knowledge-with-foundry-iq/commit/d12d7b7bf893ad0328fd1db798c240ee172476b8) | Five notebooks, sample data, Fabric setup, and supporting infrastructure | Code under [MIT](LICENSE); documentation and notebook content under [CC BY-SA 4.0](LICENSE-DOCS) |
| [Azure-Samples/foundry-hosted-agentframework-demos](https://github.com/Azure-Samples/foundry-hosted-agentframework-demos) | [`126c8a04ed63da0398e90a12ddf237c1d0800d9a`](https://github.com/Azure-Samples/foundry-hosted-agentframework-demos/commit/126c8a04ed63da0398e90a12ddf237c1d0800d9a) | HR hosted agents, toolbox creation, HR Search data/setup, and Foundry infrastructure patterns | [MIT](LICENSE) |
| [Azure-Samples/azure-search-openai-demo](https://github.com/Azure-Samples/azure-search-openai-demo) | [`c7e6ca02484bed3e4fc3830196443514aa661ce5`](https://github.com/Azure-Samples/azure-search-openai-demo/commit/c7e6ca02484bed3e4fc3830196443514aa661ce5) | Microsoft Graph application registration, client secret, delegated consent, and redirect URI update patterns | [MIT](LICENSE) |

The unified deployment configuration, dependency manifests, checks, repository documentation, and the
Fabric IQ toolbox agent
were adapted for this repository. Earlier staged agents, the multi-agent workflow, evaluations,
red-team and load-test material, and upstream organization-specific process files were not included.
