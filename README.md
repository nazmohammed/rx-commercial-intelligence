L# RX-Commercial-Intelligence

AI agent embedded in Microsoft Teams that enables Riyadh Air's Cx Commercial Insights team to instantly query KPIs, automatically detect revenue anomalies, and identify root causes — eliminating manual dashboard analysis or analyst support.

## Architecture

```
┌──────────────┐     ┌───────────────────────────────────────────────────┐
│  MS Teams    │────▶│  RX-Coordinator (Container Apps)                  │
│  User        │◀────│  M365 Agents SDK · /api/messages                  │
└──────────────┘     │                                                   │
                     │  1. Receive question                              │
                     │  2. Invoke RX-QueryEngine (Foundry Prompt Agent)  │
                     │  3. Handle execute_dax_query tool call locally    │
                     │  4. Invoke RX-Analyst (Foundry Prompt Agent)      │
                     │  5. Format → Adaptive Card → Teams               │
                     └──────────┬────────────────────────┬───────────────┘
                                │                        │
                     ┌──────────▼──────────┐  ┌─────────▼──────────┐
                     │  RX-QueryEngine     │  │  RX-Analyst        │
                     │  Foundry Prompt     │  │  Foundry Prompt    │
                     │  Agent              │  │  Agent             │
                     │  gpt-5.4-mini       │  │  gpt-5.4-mini     │
                     │                     │  │                    │
                     │  Generates DAX from │  │  Validates data,   │
                     │  natural language   │  │  interprets in     │
                     │  Calls tool →       │  │  commercial        │
                     │  execute_dax_query  │  │  context, flags    │
                     └─────────┬───────────┘  │  anomalies         │
                               │              └────────────────────┘
                     ┌─────────▼───────────┐
                     │  Power BI REST API   │
                     │  executeQueries      │
                     │                      │
                     │  Routes Insights -   │
                     │  Flyr Semantic Model │
                     │  Dataset: b047fe92   │
                     │  Workspace: 4435d932 │
                     └──────────────────────┘
```

## Agents

| Agent | Type | Model | Purpose |
|-------|------|-------|---------|
| **RX-Coordinator** | Code (Container Apps) | None (deterministic) | Routes Teams → Foundry agents, extracts DAX from markers, executes against PBI, formats Adaptive Cards |
| **RX-QueryEngine** | Foundry Prompt Agent | gpt-5.4-mini | Generates DAX from natural language and returns it between `=== DAX START === / === DAX END ===` markers |
| **RX-Analyst** | Foundry Prompt Agent | gpt-5.4-mini | Validates results, interprets with domain knowledge, flags anomalies |

Both Foundry agents are **pure Prompt Agents** — no function tools. The Coordinator performs all deterministic work (DAX parsing + PBI execution + RLS).

## Data Flow

1. User asks in Teams: *"What's the load factor on RUH-LHR for Q1?"*
2. **RX-Coordinator** receives activity, sends question to **RX-QueryEngine**
3. **RX-QueryEngine** generates DAX and returns it between `=== DAX START === / === DAX END ===` markers
4. **RX-Coordinator** parses the markers and executes the DAX against the PBI REST API (`impersonatedUser` for RLS)
5. **RX-Coordinator** sends the original question + DAX + raw JSON result to **RX-Analyst**
6. **RX-Analyst** validates, interprets (e.g., "87% — 12 pts above network avg"), flags issues
7. **RX-Coordinator** parses response into Adaptive Card → Teams

## Project Structure

```
rx-commercial-intelligence/
├── src/
│   ├── app.py                      # aiohttp entry point — /api/messages
│   ├── config.py                   # Environment config loader
│   ├── bot/
│   │   ├── bot_app.py              # Activity handlers (M365 Agents SDK)
│   │   ├── adaptive_cards.py       # Card templates
│   │   └── turn_state.py           # Conversation state
│   ├── orchestrator/
│   │   ├── coordinator.py          # Routes → Foundry agents, extracts + executes DAX
│   │   └── response_formatter.py   # Analyst markdown → Adaptive Card
│   ├── agents/
│   │   ├── query_engine/
│   │   │   ├── system_prompt.md    # Full system prompt for RX-QueryEngine
│   │   │   ├── agent_config.py     # Agent metadata
│   │   │   └── schema/
│   │   │       └── semantic_model.json
│   │   └── analyst/
│   │       ├── system_prompt.md    # Full system prompt for RX-Analyst
│   │       ├── agent_config.py     # Agent metadata
│   │       └── domain/
│   │           ├── kpi_definitions.json
│   │           └── route_benchmarks.json
│   ├── tools/
│   │   ├── pbi_auth.py             # Service principal token (MSAL)
│   │   └── pbi_execute_query.py    # DAX execution via PBI REST API
│   └── utils/
│       ├── logger.py               # Structured logging
│       └── error_handler.py        # Exception → user-friendly message
├── tests/
│   ├── test_pbi_tool.py
│   ├── test_coordinator.py
│   └── fixtures/
├── Dockerfile
├── requirements.txt
├── .env.template
└── docs/
    └── architecture.md
```

## Setup

> **👉 For Cx users running locally without Teams/Bot, follow the
> step-by-step [Local Development Guide](docs/local-dev.md).**
>
> **👉 For Teams + Azure Bot Service integration (production deployment),
> follow the [Teams Integration Guide](docs/teams-integration.md).**
>
> **👉 If Cx IT is provisioning the Bot + App Registration outside this repo,
> see the [Cx IT Handoff Checklist](docs/cx-it-handoff.md) and
> [Post-Provisioning Steps](docs/post-provisioning-steps.md).**

### Prerequisites
- Python 3.11+
- Azure subscription with AI Foundry project
- Power BI workspace + dataset access (`Member` + `Build`)
- Azure Bot registration + Teams channel *(production only)*

### Local Development (quick start)

```bash
git clone https://github.com/nazmohammed/rx-commercial-intelligence.git
cd rx-commercial-intelligence
python -m venv .venv && .venv/Scripts/activate  # Windows
pip install -r requirements-dev.txt

az login                                          # DefaultAzureCredential
cp .env.template .env                             # then fill in agent IDs

python -m scripts.check_env                       # validate config
python -m scripts.smoke_test_pbi                  # test PBI alone
python -m scripts.smoke_test_foundry              # test Foundry alone
python -m scripts.run_local "Your question here"  # full pipeline, no bot
```

Full walkthrough: [docs/local-dev.md](docs/local-dev.md)

### Environment Variables

| Variable | Description | Required for |
|----------|-------------|---|
| `FOUNDRY_PROJECT_ENDPOINT` | AI Foundry project endpoint URL | Local + Prod |
| `FOUNDRY_QUERY_ENGINE_AGENT_ID` | Agent ID for RX-QueryEngine | Local + Prod |
| `FOUNDRY_ANALYST_AGENT_ID` | Agent ID for RX-Analyst | Local + Prod |
| `PBI_WORKSPACE_ID` | Power BI workspace (`4435d932…`) | Local + Prod |
| `PBI_DATASET_ID` | Power BI dataset (`b047fe92…`) | Local + Prod |
| `TEST_USER_UPN` | UPN to impersonate for RLS | Local only |
| `BOT_APP_ID` | Entra ID app registration for the bot | Prod (Teams) |
| `BOT_APP_PASSWORD` | Bot client secret | Prod (Teams) |

> PBI and Foundry auth use `DefaultAzureCredential`. Locally this is your
> `az login` token; in production it's the Container App's managed identity.
> RLS is enforced via the `impersonatedUser` parameter on the PBI executeQueries API.

## License

Proprietary — Riyadh Air Cx Commercial Insights Team
