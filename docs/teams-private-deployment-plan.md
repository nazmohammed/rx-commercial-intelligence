# Riyadh Air — Teams Bot Private Deployment Plan

**Project:** RX Commercial Intelligence Bot (Teams) on private AKS
**Owner:** RX IT / Networking / Security
**Bot resource:** `azbotndapcomm` in `rg-neu-n-aks-01`

---

## Executive Summary

Deploy the RX Commercial Intelligence Teams bot with **zero direct public exposure of AKS**. The only public surface is an Application Gateway locked down to Microsoft's `AzureBotService` service tag. All AKS egress is forced through the existing Palo Alto NGFW for outbound inspection. This is the Microsoft-recommended pattern for regulated Teams bot deployments.

### Architecture

```
[Microsoft 365 / Microsoft Cloud]
  Teams Client ──► Bot Service ◄────────────┐
                       │ (1) inbound        │ (2) replies
                       │ HTTPS POST         │ from your bot
                       │ /api/messages      │
                       ▼                    │
                ┌───────────────┐            │
                │ App Gateway   │            │
                │ • Public FQDN │            │
                │ • NSG: only   │            │
                │   AzureBot-   │            │
                │   Service tag │            │
                └───────┬───────┘            │
                        │ private VNet       │
                        ▼                    │
                ┌───────────────┐            │
                │ AKS (private) │            │
                │  bot pod      │            │
                └───────┬───────┘            │
                        │ UDR 0.0.0.0/0      │
                        ▼                    │
                ┌───────────────┐            │
                │ Palo Alto NGFW│            │
                │ FQDN allow-   │────────────┘
                │ list to MS    │  outbound to Bot Service
                └───────────────┘  *.botframework.com
                                   smba.trafficmanager.net
                                   login.microsoftonline.com
```

---

## Phase 0 — Prerequisites & Confirmations

| # | Task | Owner | MS Learn Reference |
|---|------|-------|---------------------|
| 0.1 | Confirm AKS cluster is private (private API server, internal LB only) | RX IT — Platform | [Create a private AKS cluster](https://learn.microsoft.com/en-us/azure/aks/private-clusters) |
| 0.2 | Confirm Palo Alto VM-Series is deployed in hub VNet with trust + untrust NICs | RX Network | [PAN VM-Series in Azure](https://learn.microsoft.com/en-us/azure/architecture/reference-architectures/dmz/secure-vnet-hybrid) |
| 0.3 | Confirm hub-spoke topology with VNet peering (AKS spoke ↔ hub) | RX Network | [Hub-spoke topology](https://learn.microsoft.com/en-us/azure/architecture/networking/architecture/hub-spoke) |
| 0.4 | Reserve a public DNS FQDN for the bot endpoint (e.g. `bot.riyadhair.com`) | RX IT — DNS | n/a |
| 0.5 | Procure or generate a public TLS certificate for the FQDN | RX IT — Security | [App Gateway TLS termination](https://learn.microsoft.com/en-us/azure/application-gateway/ssl-overview) |
| 0.6 | Confirm bot container image is built, pushed to ACR, and deployable | Cx Dev | [Push images to ACR](https://learn.microsoft.com/en-us/azure/container-registry/container-registry-get-started-docker-cli) |
| 0.7 | Confirm Bot Service Microsoft App ID + secret/MI is in Key Vault and mounted to pod | RX IT — Platform | [Bot authentication](https://learn.microsoft.com/en-us/azure/bot-service/bot-builder-authentication) |

**Deliverable:** Sign-off checklist confirming all 7 items.
