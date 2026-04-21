# Cx IT Handoff Checklist — RX-Commercial-Intelligence

Use this checklist when Cx IT provisions the Azure Bot + App Registration
outside this repo. Complete all items, then return the requested values.

## Part 1 — Resources Cx IT Must Create

### Bot App Registration (Entra ID)
- [ ] Created Bot App Registration (display name: `RX-Coordinator-Bot`)
- [ ] Sign-in audience: **MultiTenant** *(or SingleTenant per org policy)*
- [ ] Generated client secret (or configured certificate)
- [ ] Stored secret in **Key Vault** as `bot-password` *(never in .env or code)*

**Share with project team:**
- `BOT_APP_ID` = `________________________________`
- Key Vault Secret URL = `https://<kv-name>.vault.azure.net/secrets/bot-password/`
- `MicrosoftAppType` = `MultiTenant` | `SingleTenant` | `UserAssignedMSI`
- Tenant ID (if SingleTenant or UserAssignedMSI) = `________________________________`

### Azure Bot Resource
- [ ] Created Azure Bot (name: `rx-coordinator-bot`, pricing tier: `S1` for prod / `F0` for dev)
- [ ] App Type matches the App Registration above
- [ ] Messaging endpoint set to: `https://<container-app-fqdn>/api/messages`
- [ ] **Microsoft Teams channel enabled** (Channels blade shows green)

### Container App MI Access

The Container App's managed identity (system-assigned or user-assigned) must be granted:

- [ ] **Azure AI Developer** role on the Foundry project (Azure Portal → Foundry resource → IAM)
- [ ] **Member** role on PBI Workspace `4435d932-4c62-46fd-ba3f-dd41a0d6d2f4`
      *(done in PBI Portal → Workspace access, not Azure CLI)*
- [ ] **Key Vault Secrets User** on the Key Vault holding `bot-password`
- [ ] Project-level membership added in Foundry Portal → Project → Users *(if tenant uses project RBAC)*

### Key Vault Secret Reference in Container App
- [ ] Container App's env var `BOT_APP_PASSWORD` configured as Key Vault reference:
      `@Microsoft.KeyVault(SecretUri=https://<kv-name>.vault.azure.net/secrets/bot-password/)`

---

## Part 2 — Values Set on the Container App

Once Part 1 is done, these env vars must exist on the Container App:

```
BOT_APP_ID=<from App Registration>
BOT_APP_PASSWORD=@Microsoft.KeyVault(SecretUri=...)
MicrosoftAppType=MultiTenant
MicrosoftAppTenantId=<only if SingleTenant/UserAssignedMSI>

FOUNDRY_PROJECT_ENDPOINT=https://<project>.services.ai.azure.com/api/projects/<name>
FOUNDRY_QUERY_ENGINE_AGENT_ID=asst_xxxxx
FOUNDRY_ANALYST_AGENT_ID=asst_yyyyy

PBI_WORKSPACE_ID=4435d932-4c62-46fd-ba3f-dd41a0d6d2f4
PBI_DATASET_ID=b047fe92-8b73-4f06-a2ae-e75b9b9363a0
```

---

## Part 3 — Teams App Upload

**Project team delivers** a signed Teams app package (`.zip`) to Cx IT.

- [ ] Teams admin uploads `.zip` via <https://admin.teams.microsoft.com> → **Teams apps → Manage apps → Upload new app**
- [ ] App assigned to the **Cx Commercial Insights** app permission policy
- [ ] App pinned via **App setup policy** for the Cx AD group *(optional but recommended)*

---

## Part 4 — End-to-End Validation

Cx IT + project team together:

- [ ] Open the bot in Teams → 1:1 chat works
- [ ] Ask a test question — verify response within 10–15 seconds
- [ ] Confirm RLS works: user A and user B see different data based on PBI access
- [ ] Review Container App logs for any 401/403/500 errors
- [ ] Application Insights traces show full pipeline (QueryEngine → PBI → Analyst)

---

## Common Issues Escalated to Cx IT

| Symptom | Who fixes | Action |
|---|---|---|
| 401 at `/api/messages` | Cx IT | Verify `BOT_APP_ID` matches App Registration; rotate secret if needed |
| Bot invisible in Teams | Cx IT | Confirm Teams channel enabled; re-run upload |
| PBI returns 403 | Cx IT | Add Container App MI to PBI Workspace as Member |
| Foundry "agent not found" | Project team | Verify agent IDs in env vars match portal |
| Secret expired | Cx IT | Rotate, update Key Vault — OR migrate to User-Assigned MI *(recommended)* |
