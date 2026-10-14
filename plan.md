# PREL42 porting plan

Goal: run the [iqdeepdive](https://github.com/microsoft/iqdeepdive) notebooks and agents inside the Skillable lab environment by reusing the Skillable infrastructure and lifecycle scripts from [aitour27-ILL344](https://github.com/microsoft/aitour27-ILL344-turning-data-into-agent-ready-knowledge-with-microsoft-iq) ("ILL344").

This repo: <https://github.com/microsoft/ignite26-PREL42>. Every repo URL copied from either source (clone commands, Codespaces/Dev Containers badges, zip download URL, README links) gets rewritten to it, and `cd iqdeepdive` / `aitour-ILL344` folder names become `ignite26-PREL42`.

## 1. How the two repos differ

| Area | iqdeepdive | ILL344 (works in Skillable) |
| --- | --- | --- |
| Content | 13 independent notebooks + 6 hosted agents (Contoso HR/health docs, Contoso DIY Fabric data) | 5 sequential notebooks (Caldova supply-chain data), no hosted agents |
| Bicep scope | `targetScope = 'subscription'`, creates its own RG | Resource-group scope; Skillable pre-creates the RG and runs `az deployment group create` |
| Bicep contents | AI account + project, model deployments, Search (`standard`), storage, App Insights / Log Analytics, Search + KB MCP project connections, optional Fabric F2 | AI account + project (name suffixed with a GUID to dodge soft-delete collisions), models, Search (`serverless` in North Central US), Fabric F16 with lab user + SP as admins, explicit RBAC for lab user (`principalType: 'User'`) and Search MI |
| Provisioning driver | `azd up` → `postprovision` hook (`uv run --locked ...`) → `azd deploy` → `postdeploy` hook | Skillable lifecycle `lifecycle_bicep_deployment.ps1` writes and launches `deploy-background.ps1` (must exit < 600 s); background script deploys Bicep, fetches keys, runs setup `.ps1` wrappers, logs to `Desktop\lifecycle-log.txt` |
| Setup-script auth | `AzureDeveloperCliCredential` everywhere | `DefaultAzureCredential` when `AZURE_CLIENT_ID`/`AZURE_CLIENT_SECRET` are set (Skillable SP), else azd; Search restore uses the admin key |
| Shared state | `.env` at repo root (scripts `load_dotenv` + `set_key`) | `.env` at repo root |
| Python tooling | `uv` with root `pyproject.toml`/`uv.lock` + `notebooks/requirements.txt`; per-agent `uv.lock` | `python -m venv .venv` + `pip install -r src/notebooks/requirements.txt` |
| Notebook auth | `AzureDeveloperCliCredential` (Search/OpenAI), `InteractiveBrowserCredential` (Fabric, Work IQ), MSAL public client (direct Work IQ) | API keys from `.env` (Search admin key, OpenAI key), `InteractiveBrowserCredential` for Fabric/Work IQ |
| Work IQ Entra app | `create-workiq-entra.py` → `WORK_IQ_SEARCH_ENTRA_*`; `create-toolbox-workiq.py` adds secret + RemoteA2A toolbox | `create-workiq-entra.py` (SP-aware, extra Graph replication retries) → `WORK_IQ_ENTRA_*`; `delete-workiq-entra.py` for teardown |
| Mail seeding | Manual (fixtures in `data/workiq-fixtures/`) | `seed-emails.ps1` sends 3 Caldova emails via Graph `Mail.Send` with the Skillable SP |
| Teardown | `azd down` | `lifecycle_teardown_cogservices.ps1` (purge accounts + backing ML workspace), `lifecycle_teardown_fabric.ps1`, `lifecycle_teardown_license.ps1` |

## 2. What to bring in

### From iqdeepdive (content)

| Bring | Notes |
| --- | --- |
| `notebooks/*.ipynb`, `notebooks/_shared.py`, `notebooks/requirements.txt` | See section 4 for which notebooks are in the lab path |
| `src/agent-foundryiq-api`, `src/agent-foundryiq-mcp`, `src/agent-toolbox-foundryiq`, `src/agent-toolbox-foundryiq-workiq`, `src/agent-toolbox-workiq`, `src/agent-workiq-maf` | Include `pyproject.toml`, `uv.lock`, `uv.toml`, `.agentignore` |
| `azure.yaml` | Agent services + hooks; rename project to `prel42-...` |
| `pyproject.toml`, `uv.lock` | Root environment for `infra/` scripts |
| `data/ai-search-data/`, `data/index-data/`, `data/ontologies/`, `data/semantic-models/`, `data/reports/`, `data/workiq-fixtures/` | Replaces `data/README.md` placeholder |
| `infra/core/**` Bicep modules | Already resource-group scoped, reuse as-is |
| `infra/create-search-indexes.py`, `create-toolbox-foundryiq.py`, `create-toolbox-workiq.py`, `create-lakehouse.py`, `create-fabric-graph.py`, `create-web-analytics-lakehouse.py`, `create-semantic-model.py`, `create-web-analytics-report.py`, `create-fabric-data-agent.py`, `setup-env.py`, `postdeploy.py`, `hooks/*` | Need the auth changes in section 3 |
| `.vscode/mcp.json`, `.vscode/settings.json`, `.agentignore`, `.env.sample`, `ATTRIBUTION.md` | `mcp.json` placeholders get filled by the background script |
| `.devcontainer/`, `.github/workflows/ci.yml` | Optional, for the "on your own" path; point the Codespaces and Dev Containers badges (currently `python-agentframework-demos`) at `microsoft/ignite26-PREL42` |
| Relevant parts of `AGENTS.md` | Merge the dev guidance, troubleshooting, and Fabric notes into this repo's agent instructions |

### From ILL344 (Skillable plumbing)

| Bring | Notes |
| --- | --- |
| `infra/lifecycle_bicep_deployment.ps1` | Foreground lifecycle action; rename paths, RG name, and the embedded background script |
| `infra/deploy-background.ps1` | Standalone copy of the embedded background script (keep the two in sync, or drop one) |
| `infra/lifecycle_github_repo_download.ps1` | Zip URL `https://api.github.com/repos/microsoft/ignite26-PREL42/zipball/main`; target folder `Desktop\ignite26-PREL42` |
| `infra/lifecycle_teardown_cogservices.ps1`, `lifecycle_teardown_fabric.ps1`, `lifecycle_teardown_license.ps1` | Update name patterns and template output names |
| `infra/seed-emails.ps1` | Swap Caldova emails for the 3 Contoso hammer fixtures |
| `infra/delete-workiq-entra.py` | Port to iqdeepdive env var names |
| SP-aware credential pattern from `create-workiq-entra.py` / `create-caldova-*.py` | Apply to every iqdeepdive setup script |
| `instructions/overview.md`, `instructions/summary.md` structure | Skillable `@lab.*` tokens, credential block, env/portal pre-checks |
| `deploy_yourself.md` structure | Self-deploy path |
| `delivery-resources/README.md` structure | Run of show, Skillable link slide |
| Notebook style rules in `AGENTS.md` | Optional, only if notebooks get the "mission" treatment |

### Leave behind

- ILL344: all Caldova data, `src/notebooks/part*.ipynb`, `restore.ipynb`, `create-knowledge.py`, `create-caldova-*.py`, `create-index-snapshots.py`, `scripts/*`, `setup-knowledge.ps1`, `setup-lakehouse.ps1` (replace with one wrapper, see 3.3), its `.github/` template tooling (this repo already has the Ignite equivalent).
- iqdeepdive: `infra/test-fabric-api-sdk.py`, `docs/workiq-admin-setup.md` and `docs/workiq-teams.md` (admin-only, could be linked instead).

### Included but not wired: Agent 365 autopilot (`src/agent-workiq-autopilot/`, `infra/a365/`)

**Decision:** copy the code in as-is. Do not add it to the Skillable lifecycle, Bicep, or the guided lab path yet. Waiting on a colleague to confirm Teams and Agent 365 availability in the Skillable tenant.

For reference, these are the blockers to resolve before wiring it later:

| Step | Blocker in Skillable |
| --- | --- |
| Container build | Not an `azure.yaml` service. It needs `az acr build` into a container registry (not in either Bicep) and a manual Foundry versions API call with the `activity` protocol. |
| Bot Service | `botservice.bicep` + `Microsoft.BotService` provider registration. Should be fine as the SP. |
| M365 publish | Creates a pending blueprint that an AI Administrator or Global Administrator must approve in the M365 admin center. The lab user is not an admin. Unknown whether the Skillable SP can approve through an API. |
| Bot ID wiring | Documented as portal-only (Teams Developer Portal); the API returns 403. This would be a manual attendee step, if the attendee can access that page. |
| Work IQ consent | Per-lab `oauth2PermissionGrant` for the digital worker's ServiceIdentity SP. Should be fine as the SP. |
| Teardown | Every lab leaves a blueprint, Entra apps, and a digital-worker identity in the shared tenant. Needs a cleanup script. |

Open questions for the colleague: (a) whether the Skillable E5 includes Teams, (b) whether blueprint approval can be done by the Skillable SP, (c) whether the lab user can open the Teams Developer Portal blueprint page.

## 3. What needs changing

### 3.1 Bicep: one resource-group-scoped `infra/main.bicep`

Convert iqdeepdive's `main.bicep` to `targetScope = 'resourceGroup'` (drop the `rg` resource and `scope: rg`) so it works for both Skillable (`az deployment group create`) and `azd` (set `AZURE_RESOURCE_GROUP`). Then layer in the ILL344 changes:

- [ ] Params: `principalType` default `'User'`; add `spPrincipalId`, `fabricAdminUpn` (already exists), `foundryDeploymentSuffix`, `resourcePrefix = 'prel42'`. Make `environmentName` optional (default `'prel42'`), since Skillable has no azd env.
- [ ] Foundry account/project names: add the GUID suffix from `foundryDeploymentSuffix` so a re-launched lab never collides with a soft-deleted account.
- [ ] Search: `serverless`. Update iqdeepdive's Search module to API `2026-09-01-preview`, set replicas/partitions/hostingMode to null when serverless, and set `semanticSearch: 'standard'`. Pin the Search location separately (ILL344 uses `northcentralus`) unless serverless is confirmed in `canadaeast`.
- [ ] Fabric: `fabricServicePrincipalId` ← `spPrincipalId` so the SP can create workspace items. Add a `fabricSkuName` param, default `F16`.
- [ ] RBAC for the Skillable SP (setup scripts now run as the SP, not the lab user):
  - Search Service Contributor + Search Index Data Contributor on Search (index restore, KB creation).
  - Azure AI User + Azure AI Project Manager on the project (toolbox creation in `create-toolbox-*.py`; Owner on the RG does not include these data actions).
- [ ] RBAC for the lab user: keep iqdeepdive's assignments (Azure AI User + Project Manager on project, Search roles, storage) and add ILL344's Azure AI User + Project Manager on the **account** and Search Index Data Reader.
- [ ] Search MI: keep both repos' roles (OpenAI User, Azure AI User, Cognitive Services User, Search Index Data Contributor) so Work IQ and model-backed KBs work.
- [ ] Keep iqdeepdive's project connections (`kb-mcp-connection`, `workiq-kb-mcp-connection`, `azure-ai-search-connection`, `storage-connection`, `appi-connection`).
- [ ] Outputs: keep iqdeepdive's full set (`setup-env.py` and `azure.yaml` depend on them). The Bicep cannot read `AZURE_AI_PROJECT_DEPLOYMENTS` in Skillable, so the fallback deployments list is what gets used; confirm `gpt-5.4` / `text-embedding-3-large` quota in the Skillable region.
- [ ] Region: `canadaeast` (verified for iqdeepdive, including hosted agents). Confirm F16 Fabric quota in `canadaeast` for the Skillable subscription.
- [ ] Remove ILL344's `deployIndexingStorage` (maintainer-only, iqdeepdive has its own storage module).

### 3.2 Setup scripts: run as the Skillable service principal

Every iqdeepdive script hard-codes `AzureDeveloperCliCredential`. Port the ILL344 pattern:

```python
if os.getenv("AZURE_CLIENT_ID") and os.getenv("AZURE_CLIENT_SECRET"):
    return DefaultAzureCredential()
return AzureDeveloperCliCredential(tenant_id=tenant_id)
```

- [ ] `create-search-indexes.py`, `create-toolbox-foundryiq.py`, `create-toolbox-workiq.py` (sync and async credentials), `create-lakehouse.py`, `create-fabric-graph.py`, `create-web-analytics-lakehouse.py`, `create-semantic-model.py`, `create-web-analytics-report.py`, `create-fabric-data-agent.py`, `postdeploy.py`.
- [ ] `create-workiq-entra.py`: take ILL344's version of the credential function, retry/replication handling, and per-lab display name, but keep iqdeepdive's `WORK_IQ_SEARCH_ENTRA_*` env names and the `AZURE_CLI_CLIENT_ID` pre-authorization (the notebooks need it).
- [ ] `create-toolbox-workiq.py`: guard the `azd env set` call so it does not fail when azd is absent; confirm the SP can create the client secret and grant delegated consent (Cloud Application Administrator should be enough; creating the Work IQ service principal `fdcc1f02-...` needs Global Admin once per tenant).
- [ ] `setup-env.py`: currently reads azd-provided env vars. Either have the background script export Bicep outputs as env vars before calling it (simplest), or add a `--from-deployment-json` option.
- [ ] Scripts that call `load_dotenv(".env")` are cwd-relative, so the background script must `Set-Location` to the repo root.
- [ ] Fabric with an SP: ILL344 proved lakehouse + ontology creation work as the SP. **Unverified**: Graph Model, Direct Lake semantic model, PBIR report, and Fabric Data Agent creation/publish with SP auth. Test each; if any refuse SPs, move that step to an attendee-run cell or a post-login script.
- [ ] Each Fabric script must add the lab user to the workspace (already done in `create-lakehouse.py` via `FABRIC_LAB_USER_UPN`/`FABRIC_LAB_USER_OID`; verify the later scripts reuse the same workspace from `.env`).

### 3.3 Skillable lifecycle scripts

- [ ] `lifecycle_bicep_deployment.ps1`: rename `aitour-ILL344` → `ignite26-PREL42`, `ILL344Final-ResourceGroup` → new RG name, pass `principalType=User`, `spPrincipalId`, `fabricAdminUpn`, `foundryDeploymentSuffix`, `location=canadaeast` (was `westus3`).
- [ ] Replace `setup-knowledge.ps1` + `setup-lakehouse.ps1` with a single `infra/setup-lab.ps1` that mirrors iqdeepdive's `postprovision` order, using the venv Python directly (no `uv run`):
  1. `python -m pip install uv`, then `uv sync --locked --all-groups` and `uv pip install --python .venv\Scripts\python.exe -r notebooks/requirements.txt`.
  2. Export Bicep outputs + `AZURE_CLIENT_ID/SECRET/TENANT_ID`, `FABRIC_TENANT_ID`, `FABRIC_LAB_USER_*` → run `setup-env.py`.
  3. `create-workiq-entra.py --apply` (non-fatal) → `create-search-indexes.py --include-workiq` → `create-toolbox-foundryiq.py` (twice: HR + Work IQ KB toolbox).
  4. `create-toolbox-workiq.py --apply` (non-fatal).
  5. Fabric chain (non-fatal, logged): lakehouse → graph → web analytics lakehouse → semantic model → report → data agent.
  6. `seed-emails.ps1`.
  7. Fill `.vscode/mcp.json` placeholders from `.env`.
  8. Create an azd environment (`azd env new prel42 --subscription ... --location canadaeast` + `azd env set` for every output) so `azd ai agent run` and `azd ai agent invoke` work for the attendee.
  9. `azd auth login --client-id ... --client-secret ... --tenant-id ...`, then `azd deploy` for each agent service in `azure.yaml`, then `postdeploy.py` (as the SP, which can write role assignments). Log out of azd afterward so the attendee signs in as themselves.
  10. Write `WEB_IQ_KEY` to `.env` if one is available (mechanism TBD, see decision 5).
- [ ] Ordering: Search + KB steps first so `foundryiq-*` notebooks are ready quickly; Fabric and agent deployment can run after. Log a clear "ready" line per stage to `lifecycle-log.txt`.
- [ ] Install azd + the `azure.ai.agents` extension on the VM (lifecycle or image).
- [ ] `seed-emails.ps1`: read the 3 files in `data/workiq-fixtures/` instead of inline Caldova HTML.
- [ ] Teardown:
  - `lifecycle_teardown_cogservices.ps1`: change the ML-workspace purge filter from `ill344-foundry-*` to the new account name pattern (`ai-account-*` or `prel42-*`).
  - `lifecycle_teardown_license.ps1`: update `@lab.CloudResourceTemplate(ILL344).Outputs[...]` names; add the lab user's account-scope roles.
  - Add `delete-workiq-entra.py` run (deletes the app, which also removes the toolbox client secret) and consider deleting the Fabric workspace before the capacity.

### 3.4 Notebooks

- [ ] Auth: keep `AzureDeveloperCliCredential`. Add an `azd auth login` step (Temporary Access Pass) at the start of `instructions/overview.md`; it also covers `azd ai agent run`/`invoke`.
- [ ] Windows: docs say `.venv/bin/python`; Skillable VM is Windows (`.venv\Scripts\python.exe`). `_shared.py` and data paths are already cross-platform.
- [ ] `foundryiq-workiq.ipynb` and the `workiq-*.ipynb` notebooks use interactive browser sign-in; confirm the lab user's Temporary Access Pass works for MSAL interactive flow on the VM.
- [ ] Prompts referencing "recent Teams chats" (agent invoke examples, `agent-toolbox-workiq`) should say "emails", since only mail is seeded.
- [ ] Clear outputs before committing.

### 3.5 Agents

- [ ] Local runs (`azd ai agent run` + `azd ai agent invoke --local`) need azd + the `azure.ai.agents` extension on the VM, an azd environment (see 3.3 step 8), Python 3.13 for the agent venvs, and the attendee signed in with `azd auth login`.
- [ ] Hosted runs: pre-deployed by the background script as the SP (3.3 step 9), because `postdeploy.py` writes role assignments the lab user likely cannot. Attendees run agents locally and also invoke the deployed versions.
- [ ] Confirm `azd ai agent invoke` against an SP-deployed agent works for the lab user (needs Azure AI User on the project, which they have).
- [ ] `agent-toolbox-foundryiq-workiq` only works when deployed (needs the hosted `x-agent-foundry-call-id`), so it is invoke-only in the lab.
- [ ] Confirm hosted-agent remote builds can reach PyPI from the Skillable subscription (`uv.toml` `system-certs = true` is already set).

### 3.6 Docs and README

- [ ] `README.md`: fill the Ignite template sections (description, 3 learning outcomes, technologies, owners) using the `help me initialize repo` workflow.
- [ ] `instructions/overview.md` + `instructions/summary.md`: Skillable flow adapted from ILL344, listing iqdeepdive env vars, the `azd auth login` step, the notebook order, and the agent exercises.
- [ ] `deploy_yourself.md` (or `docs/`): iqdeepdive's README deployment section (azd flags `ENABLE_FABRIC_CAPACITY`, `ENABLE_FABRIC_ITEMS`, `ENABLE_WORK_IQ_KB_TOOLBOX`, `ENABLE_WORK_IQ`, prerequisites, manual mail seeding).
- [ ] `infra/README.md`: how the Skillable lifecycle works and which scripts run in which order.
- [ ] Remove `docs/README.md` / `src/README.md` placeholders once filled.

## 4. Proposed lab path

| Order | Notebook / agent | Needs | In guided lab? |
| --- | --- | --- | --- |
| 1 | `foundryiq-basic.ipynb` | Search + models | Yes |
| 2 | `foundryiq-mcp.ipynb` | `contoso-company-kb-minimal` | Yes |
| 3 | `agent-foundryiq-mcp` / `agent-foundryiq-api` (local, then deployed) | azd env + login | Yes |
| 4 | `agent-toolbox-foundryiq` | Toolbox | Yes |
| 5 | `foundryiq-fabriciq-ontology.ipynb`, `fabriciq-ontology-mcp.ipynb` | Fabric lakehouse + ontology | Yes |
| 6 | `foundryiq-fabriciq-dataagent.ipynb`, `fabriciq-dataagent-mcp.ipynb`, `fabriciq-graph.ipynb` | Full Fabric chain | Yes if SP can create them, else self-paced |
| 7 | `foundryiq-workiq.ipynb` | Work IQ Entra app + Copilot credits | Yes |
| 8 | `workiq-api-concepts.ipynb`, `workiq-mcp.ipynb`, `workiq-tools-actions.ipynb`, `workiq-a2a.ipynb` | M365 Copilot license (Skillable `_Skillable-M365Copilot` group) | Self-paced |
| 9 | `agent-toolbox-workiq`, `agent-workiq-maf`, `agent-toolbox-foundryiq-workiq` | Work IQ toolbox, pre-deployed agents | Yes |
| 10 | `agent-workiq-autopilot` in Teams | Agent 365 publish + admin approval, Teams | Code included, not wired (see section 2) |
| 11 | `foundryiq-webiq.ipynb` | `WEB_IQ_KEY` | Yes, once key obtainment is sorted out |

## 5. Decisions

1. **Folder layout**: keep upstream paths (`notebooks/`, `src/agent-*`) so future iqdeepdive syncs are a straight copy.
2. **Search SKU**: `serverless`.
3. **Fabric SKU**: F16 (parameterized).
4. **Hosted agents**: both. Pre-deploy as the SP in the background script, and also have attendees run agents locally.
5. **Web IQ**: keep it. Ignite should be able to create keys; how attendees get one is still open (Skillable lab variable written to `.env`, or attendee pastes it in).
6. **Agent 365 autopilot**: code included, not wired (see section 2). Waiting on a colleague.
7. **Notebook auth**: `azd auth login` step at lab start, no notebook rewrites.
8. **Python tooling**: `pip install uv`, then `uv sync --locked`.
9. **Region**: `canadaeast` (verified for iqdeepdive). Search stays in `northcentralus` unless serverless is available in `canadaeast`.

## 6. Gaps found in review

Code changes (add to section 3 when executing):

- [ ] **Fabric workspace name collisions.** iqdeepdive defaults `FABRIC_WORKSPACE_NAME` to `ContosoDIYWorkspace`, but workspace names are unique per tenant and every Skillable lab shares one tenant. Use ILL344's pattern (`ContosoDIY-<8 hex>`) when running as the SP.
- [ ] **Hooks fire during `azd deploy`.** `azure.yaml`'s Windows hooks use `pwsh` (PowerShell 7), but ILL344 only relies on Windows PowerShell 5.1. Make sure `pwsh` is on the VM. The hook also needs `uv` on `PATH`, and then step 9 does not need a separate `postdeploy.py` call.
- [ ] **Sign azd out even on failure.** Wrap the SP `azd auth login` / `azd deploy` / `azd auth logout` in `try`/`finally` so a failed deploy never leaves the attendee's azd signed in as the SP.
- [ ] **Keep SP credentials out of `.env`.** `AZURE_CLIENT_ID`/`AZURE_CLIENT_SECRET` must stay process-scoped; `setup-env.py` and the Fabric scripts must not persist them.
- [ ] **ILL344 teardown is partly broken.** `lifecycle_teardown_license.ps1` reads `@lab.CloudResourceTemplate(ILL344).Outputs[AZURE_AIFOUNDRY_PROJECT_ID]` and `[searchMIPrincipalId]`, but neither output exists in ILL344's Bicep. Rewrite it against our own outputs, or confirm with Skillable whether a separate Cloud Resource Template is configured.
- [ ] **Attendees must not run `azd up` / `azd provision`.** The azd environment exists only for `azd ai agent` commands. Say so in the instructions.
- [ ] **Self-deploy with RG-scoped Bicep.** `azd` will prompt for a resource group. Document that in `deploy_yourself.md`, and keep iqdeepdive's `ENABLE_*` flags working in the hooks.

Things to verify (no code change until tested):

- [x] **Lakehouse data came from the GitHub API.** Resolved: the two dataset files are now in `data/lakehouse-data/` (embeddings removed, 150 KB), and `create-lakehouse.py` reads them locally. Verified the products, stores, and inventory are identical to the upstream download.
- [ ] **Serverless Search with the iqdeepdive knowledge sources.** ILL344 proved index, Fabric ontology, and Work IQ sources on serverless. Not yet proven: the Web IQ (MCP server) source, the Fabric Data Agent source, and the `contoso-company-kb-low` model-backed KB.
- [ ] **Fabric AI features in `canadaeast`.** The Data Agent and ontology use Fabric's Azure OpenAI integration. Check whether the Skillable tenant needs the cross-geo processing setting enabled for a Canada capacity.
- [ ] **Quota across concurrent labs.** If Skillable shares a subscription across labs, `gpt-5.4` (50K TPM) and `text-embedding-3-large` (30K TPM) per lab multiply quickly in `canadaeast`, as do F16 capacities. Confirm subscription-per-lab vs shared.
- [ ] **Setup duration.** Six remote agent builds plus six Fabric steps could take well over ILL344's runtime. Measure, then tell attendees in the instructions which notebooks are ready first and how to check `lifecycle-log.txt`.
- [ ] **Python on the VM.** iqdeepdive needs 3.12+ (agents 3.13). `uv` can download a managed Python, but confirm the VM can reach `python-build-standalone` downloads.

Outside this repo (needs Skillable / lab ops):

- [ ] New lab profile cloned from ILL344: resource group name, lifecycle actions, license groups, VM image (azd + extension, `pwsh`, `uv`).
- [ ] SP permissions: Cloud Application Administrator, `Mail.Send` application permission, Fabric "service principals can use Fabric APIs" tenant setting.
- [ ] A GitHub token for `lifecycle_github_repo_download.ps1` while the repo is private.
- [ ] Web IQ key distribution (decision 5) and the autopilot questions (section 2).

## 7. Execution order

1. **Port the code** (doable now, no Skillable needed): copy files, RG-scoped Bicep, SP-aware credentials, URL rewrites, new lifecycle/setup scripts, docs. **Done**, except the root `README.md` session metadata, which is left for the `help me initialize repo` workflow.
2. **Validate in our own subscription** in `canadaeast`: `azd up` with all flags, then simulate the Skillable path with an SP and `az deployment group create` + `setup-lab.ps1`.
3. **Validate in Skillable** once the lab profile exists, following section 8.

## 8. Validation steps

1. `az bicep build --file infra/main.bicep`.
2. Deploy to a test RG with `az deployment group create` using an SP, mirroring the lifecycle parameters.
3. Run `setup-lab.ps1` as the SP on a Windows VM and check `lifecycle-log.txt` for each stage.
4. Sign in as a test lab user, run every guided-path notebook, run the agents locally, and invoke the pre-deployed agents.
5. Run all teardown scripts and confirm no soft-deleted accounts, Fabric capacities, Entra apps, or role assignments remain.
6. Self-deploy path: `azd up` from a clean clone with all `ENABLE_*` flags on.
