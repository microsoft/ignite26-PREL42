# AGENTS.md

Microsoft Ignite 2026 lab PREL42. The notebooks, agents, data, and setup scripts are ported from
[iqdeepdive](https://github.com/microsoft/iqdeepdive); keep them close to upstream so changes can be synced. For
Fabric, Agent Framework, and deployment troubleshooting notes, see the upstream
[AGENTS.md](https://github.com/microsoft/iqdeepdive/blob/main/AGENTS.md).

The same `infra/main.bicep` and setup scripts serve two paths: `azd up` for self-deployment, and the Skillable lab,
which runs them as a service principal (see `infra/README.md`). Keep both working.

## Upstream sources

Copied on 2026-10-14. Compare against these revisions when syncing:

| Upstream | Revision | What came from it |
| --- | --- | --- |
| [microsoft/iqdeepdive](https://github.com/microsoft/iqdeepdive) | [`b0445d1`](https://github.com/microsoft/iqdeepdive/commit/b0445d127e1817e4a7ae11adcc2beb5d451829b8) | Notebooks, agents, data, Bicep, setup scripts (its own upstreams are in its `ATTRIBUTION.md`) |
| [microsoft/aitour27-ILL344-...](https://github.com/microsoft/aitour27-ILL344-turning-data-into-agent-ready-knowledge-with-microsoft-iq) | [`130cbaf`](https://github.com/microsoft/aitour27-ILL344-turning-data-into-agent-ready-knowledge-with-microsoft-iq/commit/130cbafaa9d4aa0a0167948599badb14790d5c2e) | Skillable lifecycle, email seeding, teardown, lab instruction structure |
| [microsoft/ai-tour-26-zava-diy-dataset-plus-mcp](https://github.com/microsoft/ai-tour-26-zava-diy-dataset-plus-mcp) | [`726243b`](https://github.com/microsoft/ai-tour-26-zava-diy-dataset-plus-mcp/commit/726243b50fe0f8fc10e7d799c6c8e4c4773f12df) | `data/lakehouse-data/` (from `data/database/`, embeddings removed) |

## Rules

- Infrastructure dependencies go in the root `pyproject.toml`/`uv.lock`; each agent under `src/` has its own.
- Create credentials in `infra/` scripts with `infra/setup_credential.py`, not `AzureDeveloperCliCredential`.
- When changing `infra/hooks/postprovision.*`, mirror the change in `infra/setup-lab.ps1`.
- Skillable scripts run on Windows PowerShell 5.1: no PowerShell 7-only syntax.
- Every hosted-agent setting must be listed under that agent's `environmentVariables` in `azure.yaml`.
- Do not commit `.env`, credentials, or virtual environments.

## Validation

```bash
uv sync --locked --all-groups
uv run ruff check .
uv run python -m compileall -q infra src
az bicep build --file infra/main.bicep --stdout > /dev/null
```
