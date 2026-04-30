# Container Apps Pivot — Plan & Decision Doc

> **Status:** PLAN ONLY — no code changes yet. Awaiting review/approval before any commit modifies running code.
>
> **Branch:** `feat/container-apps-pivot`
> **Author:** Cx Dev (Noor)
> **Last updated:** 2026-04-30

---

## 1. Why this pivot

The original plan deployed a Teams bot on AKS, but RX cyber requires zero public exposure of Bot Service. Rather than wait for the Teams private-deployment cyber approvals (tracked in [`rx-teams-bot-deployment-plan`](https://github.com/nazmohammed/rx-teams-bot-deployment-plan)), we deliver the **same agent experience** to the RX commercial team via a simple internal web app on Azure Container Apps.

Same backend, same agents, same outputs — just a different front door.

---

## 2. Hard guarantees (non-negotiable)

| Guarantee | What this means |
|---|---|
| **No backend changes** | `src/orchestrator/coordinator.py`, `src/orchestrator/response_formatter.py`, `src/tools/pbi_*`, all Foundry Prompt Agent prompts and registrations remain **untouched**. |
| **Same DAX + same agent behavior** | The pipeline RX-QueryEngine → DAX → RX-Analyst → Adaptive Card is identical. |
| **No new identity infrastructure** | Zero app registrations from RX IT. Container Apps **Easy Auth** (built-in Microsoft identity provider) handles sign-in. |
| **Internal only** | Container Apps environment with `internal=true`. No public IP, no Front Door, no custom DNS, no custom TLS cert. Microsoft auto-generated URL is enough. |
| **Egress through existing Palo Alto NGFW** | Same FQDN allow-list already approved (Foundry, Power BI, Entra ID). |
| **Single Container App, two containers** | One ingress, one billable unit, one log stream. Frontend nginx reverse-proxies `/api/*` to backend on `localhost`. |

---

## 3. Target architecture (final)

```
RX user (corp laptop on RX network or Zscaler ZTNA)
   │ Browser
   ▼
https://rxcommercial.<random>.<region>.azurecontainerapps.io
   │ (auto-generated URL, MS-managed TLS, internal-only)
   │
   ▼ Container Apps Easy Auth (Microsoft provider — toggle by RX IT)
   │   • If unauthenticated → redirect to login.microsoftonline.com
   │   • After SSO → injects identity headers:
   │       X-MS-CLIENT-PRINCIPAL-NAME = <user UPN>
   │       X-MS-CLIENT-PRINCIPAL-ID   = <user oid>
   │
   ▼
Container App "rx-commercial"  (single app, two containers, internal=true)
  ┌────────────────────────────────────────────────────┐
  │  frontend container (nginx, port 80)               │
  │    /              → React SPA                      │
  │    /api/*         → http://localhost:8000          │
  │                                                    │
  │  backend container (FastAPI, port 8000)            │
  │    Reads X-MS-CLIENT-PRINCIPAL-NAME → upn          │
  │    Wraps EXISTING coordinator.process(q, upn)      │
  │    Returns existing Adaptive Card JSON             │
  └────────────────────────────────────────────────────┘
   │ outbound through Palo Alto (existing rules)
   ▼
Foundry Prompt Agents · Power BI XMLA · Entra ID
```

---

## 4. What stays UNTOUCHED (the working backend)

These files and resources are **read-only** for this pivot:

| Path / Resource | Why untouched |
|---|---|
| `src/orchestrator/coordinator.py` | Already accepts `user_principal_name`. FastAPI will pass UPN straight through. |
| `src/orchestrator/response_formatter.py` | Pure parsing logic. |
| `src/tools/pbi_execute_query.py` | Already does RLS impersonation via UPN. |
| `src/tools/pbi_auth.py` | Token acquisition for Power BI. |
| `src/agents/query_engine/system_prompt.md` | Foundry prompt — unchanged. |
| `src/agents/analyst/system_prompt.md` | Foundry prompt — unchanged. |
| `src/agents/*/agent_config.py` | Agent registration helpers — unchanged. |
| Foundry Prompt Agent registrations in the portal | No changes. |
| Power BI dataset, RLS roles, `Routes Insights - Flyr` model | No changes. |
| `scripts/smoke_test_foundry.py` | Continues to pass — proves the agent path is healthy. |

> **If any commit on this branch modifies any of the above, it is a defect.**

---

## 5. What changes (front-door only)

### 5.1 New code

| Path | Purpose |
|---|---|
| `src/api/__init__.py` | Marker |
| `src/api/main.py` | FastAPI app entrypoint (uvicorn target) |
| `src/api/routes/__init__.py` | Marker |
| `src/api/routes/chat.py` | `POST /api/chat` — wraps `coordinator.process()` |
| `src/api/middleware/__init__.py` | Marker |
| `src/api/middleware/easy_auth.py` | Reads `X-MS-CLIENT-PRINCIPAL-NAME` header → UPN |
| `frontend/` | New directory: Vite + React + TS + Tailwind |
| `frontend/src/main.tsx` | React entrypoint |
| `frontend/src/App.tsx` | Top-level layout |
| `frontend/src/components/Header.tsx` | RX logo + title + user avatar (from `/.auth/me`) |
| `frontend/src/components/InputBar.tsx` | Sticky bottom prompt input |
| `frontend/src/components/OutputCard.tsx` | Adaptive Card renderer, RX themed |
| `frontend/src/components/FAQCard.tsx` | Suggested-question chip |
| `frontend/src/components/LoadingCard.tsx` | 4-step skeleton (QueryEngine → DAX → Analyst → Render) |
| `frontend/src/api/client.ts` | `fetch` wrapper for `/api/chat` |
| `frontend/public/riyadh-air-logo.svg` | Brand asset (placeholder until provided) |
| `frontend/tailwind.config.js` | RX brand colors |
| `frontend/nginx.conf` | Static + reverse proxy to localhost:8000 |
| `Dockerfile.frontend` | Multi-stage Vite build → nginx |
| `Dockerfile.backend` | Renamed from existing `Dockerfile`, runs uvicorn |
| `infra/main.bicep` | Container Apps Environment (internal=true) + single Container App with two containers |
| `azure.yaml` | Updated services |

### 5.2 Modified files (minimal, surgical)

| File | Change | Risk |
|---|---|---|
| `requirements.txt` | Add `fastapi`, `uvicorn`. Bot SDK packages can stay (unused, harmless) for now. | None. |
| `Dockerfile` | Renamed to `Dockerfile.backend`, entrypoint changes from bot to `uvicorn src.api.main:app`. Old bot file untouched on disk. | Backend module unchanged; only invocation path. |
| `.env.template` | Add `FRONTEND_ORIGIN` (for CORS during local dev). No bot-specific keys removed (not blocking anything). | None. |
| `azure.yaml` | Service name + Dockerfile path. | Affects only `azd` deploy target. |

### 5.3 Files we do NOT delete in this pivot

- `src/bot/` — left in place for now. If it bothers anyone, we delete in a later cleanup PR after Container Apps is in production for 30 days.
- `scripts/smoke_test_foundry.py` — keep as a backend health probe.
- `infra/main.bicep` (existing AKS bits) — superseded but kept as reference until cutover.

> **Principle:** additive over destructive. We add the new path, prove it works, then remove the old path in a separate, low-risk PR.

---

## 6. Authentication flow (Easy Auth — zero app registrations from us)

```
1. Browser opens https://rxcommercial.<random>...azurecontainerapps.io
2. Easy Auth (Container Apps built-in) sees no session cookie
   → redirects to login.microsoftonline.com (RX tenant)
3. User signs in with corporate account (silent SSO if already logged in)
4. Returns to app with auth cookie set by Easy Auth
5. React calls fetch('/api/chat', { method: 'POST', body: ... })
   → No MSAL.js needed. Browser includes auth cookie automatically.
6. Easy Auth validates cookie, injects headers:
     X-MS-CLIENT-PRINCIPAL-NAME = noor.albidewe@vendor.riyadhair.com
     X-MS-CLIENT-PRINCIPAL-ID   = <oid>
7. Frontend nginx reverse-proxies to localhost:8000 (preserves headers)
8. FastAPI middleware reads X-MS-CLIENT-PRINCIPAL-NAME → upn
9. coordinator.process(question, state, user_principal_name=upn)
10. Power BI executeQueries with impersonatedUser.userName=upn → RLS applied
11. Adaptive Card JSON returned → React renders with RX theme
```

**RX IT involvement:** one toggle.
- Container App → "Authentication" blade → "Add identity provider" → Microsoft → Create → Save.
- Azure auto-creates the underlying app registration silently in their tenant. Nothing for us to copy or paste.

**Code involvement:** ~10 lines.
- Backend reads one HTTP header.
- Frontend has no auth code at all.

---

## 7. Frontend layout (matches the supplied wireframe)

```
┌──────────────────────────────────────────────────────────────┐
│ [RX Logo]   Commercial Agent                       [N M]      │  Header (sticky)
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────────────┐  ┌──────────┐  ┌──────────┐     │
│  │ Output 1 (latest answer)│  │ FAQ      │  │ FAQ      │     │
│  │ — Adaptive Card RX-themed│  │ chip 1  │  │ chip 2   │     │
│  ├─────────────────────────┤  └──────────┘  └──────────┘     │
│  │ Output 2                │  ┌──────────┐  ┌──────────┐     │
│  ├─────────────────────────┤  │ FAQ      │  │ FAQ      │     │
│  │ Output 3                │  │ chip 3   │  │ chip 4   │     │
│  └─────────────────────────┘  └──────────┘  └──────────┘     │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│ Type your question…                                  [Send]  │  Input (sticky bottom)
└──────────────────────────────────────────────────────────────┘
```

**Theme:**
- Primary: RX deep purple `#5B2C8B`
- Background: cream `#F4EDE2`
- Text: near-black `#1A1A1A`
- Accent / success / warn / error: standard Tailwind palette

**Behaviour:**
- Suggested-question chips populate the input on click (don't auto-send).
- Outputs stream newest-on-top.
- Loading card shows 4 deterministic steps with checkmarks as they complete.
- Each output card has "Copy DAX" and "Copy summary" buttons.

---

## 8. Detailed commit plan (this branch)

> Each commit is independently reviewable. Nothing destructive until commit 14.

| # | Commit message | Files touched | Risk |
|---|---|---|---|
| 1 | `docs: add Container Apps pivot plan and decision doc` | `docs/container-apps-pivot.md` (THIS FILE) | None — doc only |
| 2 | `refactor: extract card builders to src/api/cards (no behavior change)` | `src/api/cards/__init__.py`, `src/api/cards/insight_card.py`, `src/api/cards/error_card.py` | Low — pure copy from `src/bot/adaptive_cards.py`, no callers changed yet |
| 3 | `feat(api): add FastAPI backend skeleton (uvicorn entrypoint)` | `src/api/main.py`, `src/api/__init__.py` | None — new module, no callers |
| 4 | `feat(api): add Easy Auth middleware (reads X-MS-CLIENT-PRINCIPAL-NAME)` | `src/api/middleware/easy_auth.py` | None — new module |
| 5 | `feat(api): add /api/chat endpoint wrapping coordinator.process` | `src/api/routes/chat.py` | None — calls existing coordinator unchanged |
| 6 | `chore: add fastapi + uvicorn to requirements.txt` | `requirements.txt` | None — additive |
| 7 | `feat(frontend): scaffold Vite + React + TS + Tailwind` | `frontend/package.json`, `frontend/vite.config.ts`, `frontend/tsconfig.json`, `frontend/index.html`, `frontend/src/main.tsx`, `frontend/src/App.tsx` | None — new dir |
| 8 | `feat(frontend): add Header with RX logo and user avatar` | `frontend/src/components/Header.tsx`, logo asset | None |
| 9 | `feat(frontend): add InputBar component` | `frontend/src/components/InputBar.tsx` | None |
| 10 | `feat(frontend): add OutputCard with adaptivecards renderer + RX theme` | `frontend/src/components/OutputCard.tsx` | None |
| 11 | `feat(frontend): add FAQ suggested-question chips` | `frontend/src/components/FAQCard.tsx`, default FAQ list | None |
| 12 | `feat(frontend): add LoadingCard with 4-step progress` | `frontend/src/components/LoadingCard.tsx` | None |
| 13 | `feat(frontend): wire API client to /api/chat` | `frontend/src/api/client.ts`, `frontend/src/App.tsx` | None |
| 14 | `style(frontend): apply Tailwind RX brand theme` | `frontend/tailwind.config.js`, `frontend/src/index.css` | None |
| 15 | `build: add Dockerfile.frontend (nginx) and rename Dockerfile → Dockerfile.backend` | `Dockerfile.frontend`, `Dockerfile.backend`, `frontend/nginx.conf` | **First risk surface — entrypoint changes for backend image** |
| 16 | `infra: add Container Apps Bicep (single app, two containers, internal=true)` | `infra/containerapps.bicep` (NEW; existing AKS bicep untouched) | None — new file |
| 17 | `chore: update azure.yaml + .env.template for Container Apps service` | `azure.yaml`, `.env.template` | Low |

**Total: 17 commits.** Branch is fully reviewable end-to-end before any deploy.

---

## 9. RX IT involvement (final list)

| When | Action | Time |
|---|---|---|
| Pre-deploy | Confirm Container Apps Environment can be created in existing AKS spoke VNet (or new spoke) | 1 hour discussion |
| Deploy | Run `azd up` (or apply Bicep) — creates Container Apps Environment + the app | 5 min |
| Deploy | In Azure Portal: Container App → Authentication → Add Microsoft identity provider → Create → Save | 2 min |
| Deploy | Confirm the Container App URL is reachable from RX corporate network | 5 min |
| Validation | Open URL in browser → SSO → ask test question → verify Power BI RLS works | 10 min |

**Total RX IT effort: < 30 minutes including discussion.** Zero scripts, zero copy/paste of GUIDs.

---

## 10. Rollback / kill switch

- This branch only adds files (and renames one Dockerfile). Reverting to `main` removes everything.
- Existing AKS bot deployment (if it ever lands) is independent — not modified.
- Coordinator + agents path is unchanged, so the existing smoke test continues to be the source of truth for backend health.

---

## 11. Approval checklist (review gates)

- [ ] Plan reviewed and approved by user
- [ ] Branch `feat/container-apps-pivot` created
- [ ] Commit 1 (this doc) merged or visible on branch
- [ ] User explicitly says "go" before any commit beyond #1
- [ ] After commit 17, user reviews the branch end-to-end
- [ ] PR opened to `main` only after explicit approval

---

## 12. What I will NOT do without explicit approval

- ❌ Modify `src/orchestrator/`, `src/agents/`, `src/tools/`
- ❌ Touch any Foundry Prompt Agent prompt or registration
- ❌ Delete `src/bot/` (defer to a later cleanup PR)
- ❌ Open a PR to `main`
- ❌ Run `azd up` or any deploy
- ❌ Change anything about Power BI, RLS, or DAX

---

**Next step:** review this doc, then reply "go" to proceed with commits 2–17.
