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

---

## Phase 2 — Outbound Path (AKS → Bot Service via Palo Alto NGFW)

> **Note:** RX uses Palo Alto VM-Series in the hub VNet. There is **no Azure Firewall** in this architecture. All AKS egress is forced through Palo Alto via UDR.

### Task 2.1 — Force AKS egress through Palo Alto

| Step | Detail | Reference |
|------|--------|-----------|
| 2.1.1 | Create Route Table on AKS subnet (or update existing) | [User-defined routes](https://learn.microsoft.com/en-us/azure/virtual-network/virtual-networks-udr-overview) |
| 2.1.2 | Add route: `0.0.0.0/0` → next-hop type `VirtualAppliance`, IP = Palo Alto trust-NIC private IP | [Egress with UDR](https://learn.microsoft.com/en-us/azure/aks/egress-outboundtype) |
| 2.1.3 | Set AKS cluster `outboundType=userDefinedRouting` if not already (one-time at cluster creation, or via redeploy) | [Outbound types](https://learn.microsoft.com/en-us/azure/aks/egress-outboundtype#outbound-type-of-userdefinedrouting) |
| 2.1.4 | Add bypass routes for Azure control plane (next-hop `Internet`): `AzureCloud`, `AzureContainerRegistry`, `AzureMonitor`, `AzureKeyVault` service tags so AKS nodes don't lose connectivity to control plane through PAN | [Required egress for AKS](https://learn.microsoft.com/en-us/azure/aks/limit-egress-traffic#required-network-rules-and-fqdn--application-rules-for-aks-clusters) |

### Task 2.2 — Palo Alto rules for Bot Service / Foundry / Power BI traffic

| Step | Detail | Reference |
|------|--------|-----------|
| 2.2.1 | Create Address Object: AKS pod CIDR + node CIDR (source) | PAN admin docs |
| 2.2.2 | Create FQDN Object Group `MS-BotService`: `*.botframework.com`, `smba.trafficmanager.net`, `*.skype.com`, `directline.botframework.com` | [Bot Service required URLs](https://learn.microsoft.com/en-us/azure/bot-service/bot-builder-howto-deploy-azure?view=azure-bot-service-4.0) |
| 2.2.3 | Create FQDN Object Group `MS-Identity`: `login.botframework.com`, `login.microsoftonline.com`, `login.microsoft.com`, `*.login.microsoftonline.com` | [Entra ID endpoints](https://learn.microsoft.com/en-us/entra/identity-platform/authentication-national-cloud) |
| 2.2.4 | Create FQDN Object Group `MS-Foundry`: `*.services.ai.azure.com`, `*.cognitiveservices.azure.com`, `*.openai.azure.com` | [AI Foundry networking](https://learn.microsoft.com/en-us/azure/ai-foundry/concepts/network-isolation) |
| 2.2.5 | Create FQDN Object Group `MS-PowerBI`: `api.powerbi.com`, `*.analysis.windows.net` | [Power BI URLs and IPs](https://learn.microsoft.com/en-us/power-bi/admin/power-bi-allow-list-urls) |
| 2.2.6 | Create FQDN Object Group `MS-Platform`: `*.azurecr.io`, `mcr.microsoft.com`, `*.vault.azure.net`, `*.applicationinsights.azure.com`, `*.monitor.azure.com`, `*.blob.core.windows.net` | [AKS required outbound FQDNs](https://learn.microsoft.com/en-us/azure/aks/limit-egress-traffic) |
| 2.2.7 | Security rule: source = AKS, destination = all 5 FQDN groups, app = `ssl, web-browsing, ms-azure, ms-teams`, action = Allow, log = enabled | PAN admin docs |
| 2.2.8 | Default rule for AKS source: action = Deny, log = enabled | PAN admin docs |
| 2.2.9 | SSL Decryption exclusion list (do NOT decrypt — preserves MS SDK cert pinning): `*.botframework.com`, `*.skype.com`, `smba.trafficmanager.net`, `*.microsoftonline.com`, `*.azurecr.io`, `*.vault.azure.net` | [Microsoft 365 SSL exemption guidance](https://learn.microsoft.com/en-us/microsoft-365/enterprise/microsoft-365-network-connectivity-principles?view=o365-worldwide#bp4) |
| 2.2.10 | Enable PAN traffic logging — forward to SIEM (Sentinel/Splunk) | PAN admin docs |

**Deliverable:** PAN config commit + traffic logs showing AKS → MS allow flows during smoke test.

---

## Phase 3 — Bot Service Configuration

### Task 3.1 — Configure Bot resource

| Step | Detail | Reference |
|------|--------|-----------|
| 3.1.1 | Set messaging endpoint on Bot resource: `https://bot.riyadhair.com/api/messages` | [Configure bot endpoint](https://learn.microsoft.com/en-us/azure/bot-service/bot-service-manage-overview?view=azure-bot-service-4.0) |
| 3.1.2 | Enable Microsoft Teams channel: `az bot msteams create -g rg-neu-n-aks-01 -n azbotndapcomm` | [Connect a bot to Microsoft Teams](https://learn.microsoft.com/en-us/azure/bot-service/channel-connect-teams) |
| 3.1.3 | Confirm Bot resource uses System-Assigned Managed Identity OR single-tenant App Registration (recommended: User-Assigned MI for prod) | [Bot identity types](https://learn.microsoft.com/en-us/azure/bot-service/bot-builder-authentication?view=azure-bot-service-4.0&tabs=userassigned) |
| 3.1.4 | If using App Registration: confirm App ID + secret in Key Vault, mounted to pod via CSI Secrets Store driver | [CSI Secrets Store on AKS](https://learn.microsoft.com/en-us/azure/aks/csi-secrets-store-driver) |
| 3.1.5 | Confirm pod env vars: `MicrosoftAppId`, `MicrosoftAppPassword` (or `MicrosoftAppType=UserAssignedMSI` + `MicrosoftAppTenantId`) | [Bot Framework auth env vars](https://learn.microsoft.com/en-us/azure/bot-service/bot-builder-authentication) |

**Deliverable:** Teams channel showing "Running" status in portal; bot endpoint validated.
