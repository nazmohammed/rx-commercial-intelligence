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

---

## Phase 1 — Inbound Path (Bot Service → AKS)

### Task 1.1 — Deploy Application Gateway with WAF v2

| Step | Detail | Reference |
|------|--------|-----------|
| 1.1.1 | Deploy Application Gateway v2 (or AGIC if not present) in a dedicated subnet of the hub or AKS spoke VNet | [Quickstart: Direct web traffic with Application Gateway](https://learn.microsoft.com/en-us/azure/application-gateway/quick-create-portal) |
| 1.1.2 | Attach a public IP with a Standard SKU + a DNS label | [Application Gateway public IP](https://learn.microsoft.com/en-us/azure/application-gateway/configuration-frontend-ip) |
| 1.1.3 | Upload the public TLS cert (PFX) and configure HTTPS listener on port 443 | [TLS termination configuration](https://learn.microsoft.com/en-us/azure/application-gateway/ssl-overview) |
| 1.1.4 | Configure backend pool pointing to AKS internal load balancer private IP (or pod IPs via AGIC) | [Application Gateway backend pools](https://learn.microsoft.com/en-us/azure/application-gateway/application-gateway-components#backend-pools) |
| 1.1.5 | Configure health probe `/api/messages` (expect 401 / 405) | [Health monitoring overview](https://learn.microsoft.com/en-us/azure/application-gateway/application-gateway-probe-overview) |
| 1.1.6 | Enable WAF v2 in Prevention mode with OWASP 3.2 ruleset | [WAF v2 overview](https://learn.microsoft.com/en-us/azure/web-application-firewall/ag/ag-overview) |

### Task 1.2 — Lock down App Gateway subnet to Bot Service only

| Step | Detail | Reference |
|------|--------|-----------|
| 1.2.1 | Create NSG and attach to App Gateway subnet | [NSG overview](https://learn.microsoft.com/en-us/azure/virtual-network/network-security-groups-overview) |
| 1.2.2 | Add inbound rule: priority 100, ALLOW source `AzureBotService` service tag → port 443 | [Service tags reference](https://learn.microsoft.com/en-us/azure/virtual-network/service-tags-overview) |
| 1.2.3 | Add inbound rule: priority 110, ALLOW source `GatewayManager` → ports 65200-65535 (mandatory for App Gateway v2 control plane) | [App Gateway infrastructure config](https://learn.microsoft.com/en-us/azure/application-gateway/configuration-infrastructure#network-security-groups) |
| 1.2.4 | Add inbound rule: priority 120, ALLOW source `AzureLoadBalancer` → all ports | Same as 1.2.3 |
| 1.2.5 | Add inbound rule: priority 4000, DENY source `Internet` → all ports | NSG best practices |
| 1.2.6 | Enable NSG flow logs to Log Analytics | [NSG flow logs](https://learn.microsoft.com/en-us/azure/network-watcher/network-watcher-nsg-flow-logging-overview) |

### Task 1.3 — DNS

| Step | Detail | Reference |
|------|--------|-----------|
| 1.3.1 | Create public DNS A record `bot.riyadhair.com` → App Gateway public IP | [Azure DNS records](https://learn.microsoft.com/en-us/azure/dns/dns-zones-records) |
| 1.3.2 | Validate cert chain: `curl -vI https://bot.riyadhair.com/api/messages` from internet (should return 403 — not from Bot Service IP — but TLS handshake must succeed) | n/a |

**Deliverable:** App Gateway healthy, NSG locked to `AzureBotService`, DNS resolves, TLS valid.
