# Local Development Guide

This guide walks a Cx Commercial Insights user through running the full
RX-Commercial-Intelligence pipeline on their laptop — **no bot, no Teams** —
against real Azure AI Foundry + real Power BI.

## Prerequisites

| Tool | Version | Install |
|---|---|---|
| Python | 3.11+ | <https://www.python.org/downloads/> |
| Git | any | <https://git-scm.com/> |
| VS Code | latest | <https://code.visualstudio.com/> |
| Azure CLI | latest | <https://aka.ms/installazurecliwindows> |

## Azure Access (must be granted before running)

Your Entra ID account needs:

| Resource | Role | Why |
|---|---|---|
| Azure AI Foundry project | `Azure AI Developer` | Invoke the two agents |
| PBI Workspace `4435d932…` | `Member` (min) | Query the dataset |
| PBI Dataset `b047fe92…` | `Build` permission | For `executeQueries` API |

`DefaultAzureCredential` will use your `az login` token for both Foundry and PBI — no service principal required for local dev.

## Setup

### 1. Clone and open in VS Code
```powershell
cd "C:\Users\<you>\Projects"
git clone https://github.com/nazmohammed/rx-commercial-intelligence.git
cd rx-commercial-intelligence
code .
```

### 2. Create venv & install dependencies
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
```
> If PowerShell blocks activation:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

### 3. Azure login
```powershell
az login
az account set --subscription "<subscription-id>"
```

### 4. Configure `.env`
```powershell
Copy-Item .env.template .env
code .env
```

Fill in at minimum:
```
FOUNDRY_PROJECT_ENDPOINT=https://<project>.services.ai.azure.com/api/projects/<name>
FOUNDRY_QUERY_ENGINE_AGENT_ID=asst_xxxxx
FOUNDRY_ANALYST_AGENT_ID=asst_yyyyy
PBI_WORKSPACE_ID=4435d932-4c62-46fd-ba3f-dd41a0d6d2f4
PBI_DATASET_ID=b047fe92-8b73-4f06-a2ae-e75b9b9363a0
```

Optional:
```
TEST_USER_UPN=first.last@riyadhair.com   # for PBI RLS impersonation
```

### 5. Validate setup
```powershell
python -m scripts.check_env
```

### 6. Run smoke tests (isolate failures)

Test PBI alone:
```powershell
python -m scripts.smoke_test_pbi
```

Test Foundry alone:
```powershell
python -m scripts.smoke_test_foundry
```

### 7. Run the full pipeline
```powershell
python -m scripts.run_local "What's the flown load factor on RUH-LHR for Q1 2025?"
```

Or interactively:
```powershell
python -m scripts.run_local
> Which top 5 routes grew revenue the most vs last year?
```

## Running via VS Code Debugger

Press **F5** and pick one of these launch configs:
- **Local CLI — run_local**
- **Smoke test — PBI**
- **Smoke test — Foundry**
- **Check env**

## Foundry Agents Setup (one-time, in Azure AI Foundry Portal)

Before `run_local` works, the two agents must exist in the portal:

### RX-QueryEngine (Prompt Agent)
- Model: `gpt-5.4-mini`
- Instructions: paste the full contents of
  `src/agents/query_engine/system_prompt.md`
- Tools → Add function tool → paste `EXECUTE_DAX_TOOL_DEFINITION` schema
  from `src/tools/pbi_execute_query.py`
- Save → copy **Agent ID** → `FOUNDRY_QUERY_ENGINE_AGENT_ID`

### RX-Analyst (Prompt Agent)
- Model: `gpt-5.4-mini`
- Instructions: paste the full contents of
  `src/agents/analyst/system_prompt.md`
- No tools
- Save → copy **Agent ID** → `FOUNDRY_ANALYST_AGENT_ID`

## Troubleshooting

| Symptom | Fix |
|---|---|
| `DefaultAzureCredential failed` | Re-run `az login` |
| `401 Unauthorized` from PBI | User lacks workspace/dataset access |
| `Agent not found` | Wrong `FOUNDRY_*_AGENT_ID` in `.env` |
| `ModuleNotFoundError: azure` | venv not activated |
| PowerShell execution policy error | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| Run stuck on `requires_action` | Tool name mismatch — portal function tool must be `execute_dax_query` (case-sensitive) |
