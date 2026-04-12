# RX-Commercial-Intelligence

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
| **RX-Coordinator** | Code (Container Apps) | None (deterministic) | Routes Teams → Foundry agents, handles tool calls, formats Adaptive Cards |
| **RX-QueryEngine** | Foundry Prompt Agent | gpt-5.4-mini | Generates DAX from natural language, calls `execute_dax_query` tool |
| **RX-Analyst** | Foundry Prompt Agent | gpt-5.4-mini | Validates results, interprets with domain knowledge, flags anomalies |

## Data Flow

1. User asks in Teams: *"What's the load factor on RUH-LHR for Q1?"*
2. **RX-Coordinator** receives activity, sends question to **RX-QueryEngine**
3. **RX-QueryEngine** generates DAX, calls `execute_dax_query` tool
4. **RX-Coordinator** executes the DAX against PBI REST API, returns result to agent
5. **RX-QueryEngine** returns DAX + raw data
6. **RX-Coordinator** sends DAX + data + original question to **RX-Analyst**
7. **RX-Analyst** validates, interprets (e.g., "87% — 12 pts above network avg"), flags issues
8. **RX-Coordinator** parses response into Adaptive Card → Teams

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
│   │   ├── coordinator.py          # Routes → Foundry agents, handles tool calls
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

### Prerequisites
- Python 3.11+
- Azure subscription with AI Foundry project
- Power BI service principal with Dataset.Read.All
- Azure Bot registration + Teams channel

### Local Development

```bash
# Clone and setup
git clone https://github.com/nazmohammed/rx-commercial-intelligence.git
cd rx-commercial-intelligence
python -m venv .venv && .venv/Scripts/activate  # Windows
pip install -r requirements.txt

# Configure
cp .env.template .env
# Fill in all values in .env

# Create Foundry agents (one-time)
# 1. Create RX-QueryEngine prompt agent in AI Foundry with system_prompt.md
# 2. Register execute_dax_query as a function tool on the agent
# 3. Create RX-Analyst prompt agent with system_prompt.md
# 4. Copy agent IDs to .env

# Run
python -m src.app

# Test with Bot Framework Emulator or Dev Tunnel → Teams
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `BOT_APP_ID` | Entra ID app registration for the bot |
| `BOT_APP_PASSWORD` | Bot client secret |
| `FOUNDRY_PROJECT_ENDPOINT` | AI Foundry project endpoint URL |
| `FOUNDRY_QUERY_ENGINE_AGENT_ID` | Agent ID for RX-QueryEngine |
| `FOUNDRY_ANALYST_AGENT_ID` | Agent ID for RX-Analyst |
| `PBI_WORKSPACE_ID` | Power BI workspace (4435d932...) |
| `PBI_DATASET_ID` | Power BI dataset (b047fe92...) |
| `PBI_TENANT_ID` | Azure AD tenant for PBI service principal |
| `PBI_CLIENT_ID` | Service principal app ID |
| `PBI_CLIENT_SECRET` | Service principal secret |

## License

Proprietary — Riyadh Air Cx Commercial Insights Team
