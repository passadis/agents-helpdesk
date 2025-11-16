# Azure Container Apps Secrets Configuration Template

This document provides a comprehensive list and template for all secret variables required to deploy the Agentic AI Helpdesk to Azure Container Apps.

## Overview

Azure Container Apps secrets are used to store sensitive configuration values securely. This template helps you prepare all required secrets before deployment.

## How to Use This Template

1. Copy this file or create a secure document
2. Fill in all the values with your actual Azure resource information
3. Use these values when running the `az containerapp create` commands
4. **DO NOT commit this file with actual values to source control**

## Required Secrets Checklist

### 1. Azure Storage Connection String
```
Secret Name: azure-table-conn-str
Description: Connection string for Azure Storage Account (Table Storage)
Format: DefaultEndpointsProtocol=https;AccountName=<name>;AccountKey=<key>;EndpointSuffix=core.windows.net

Your Value:
_______________________________________________
```

**How to obtain:**
1. Navigate to your Azure Storage Account in Azure Portal
2. Go to "Access keys" under Security + networking
3. Copy the entire "Connection string" value

---

### 2. Azure Service Bus Connection String
```
Secret Name: azure-servicebus-conn-str
Description: Connection string for Azure Service Bus namespace
Format: Endpoint=sb://<namespace>.servicebus.windows.net/;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=<key>

Your Value:
_______________________________________________
```

**How to obtain:**
1. Navigate to your Service Bus Namespace in Azure Portal
2. Go to "Shared access policies" under Settings
3. Click on "RootManageSharedAccessKey"
4. Copy the "Primary Connection String"

---

### 3. Microsoft Teams Webhook URL
```
Secret Name: teams-webhook-url
Description: Incoming webhook URL for Microsoft Teams channel
Format: https://outlook.office.com/webhook/<guid>@<guid>/IncomingWebhook/<guid>/<guid>

Your Value:
_______________________________________________
```

**How to obtain:**
1. Open Microsoft Teams and navigate to the desired channel
2. Click on the three dots (...) next to the channel name
3. Select "Connectors" → "Configure" → "Incoming Webhook"
4. Provide a name and optional image
5. Copy the generated webhook URL

---

### 4. Azure OpenAI API Key
```
Secret Name: azure-openai-api-key
Description: API key for Azure OpenAI resource
Format: <32-character-hex-string>

Your Value:
_______________________________________________
```

**How to obtain:**
1. Navigate to your Azure OpenAI resource in Azure Portal
2. Go to "Keys and Endpoint" under Resource Management
3. Copy "KEY 1" or "KEY 2"

---

### 5. Azure Communication Services Connection String
```
Secret Name: acs-connection-string
Description: Connection string for Azure Communication Services
Format: endpoint=https://<resource>.communication.azure.com/;accesskey=<key>

Your Value:
_______________________________________________
```

**How to obtain:**
1. Navigate to your Azure Communication Services resource in Azure Portal
2. Go to "Keys" under Settings
3. Copy the "Primary key connection string"

---

### 6. Microsoft Graph Client Secret
```
Secret Name: graph-client-secret
Description: Client secret for Microsoft Graph App Registration
Format: <string>~<guid>

Your Value:
_______________________________________________
```

**How to obtain:**
1. Navigate to Azure Active Directory → App registrations
2. Select your app registration
3. Go to "Certificates & secrets"
4. Under "Client secrets", create a new secret if needed
5. Copy the secret value (note: this is only shown once!)

---

### 7. Power Automate Flow URL
```
Secret Name: power-automate-flow-url
Description: HTTP endpoint URL for Power Automate flow
Format: https://prod-<region>.region.logic.azure.com:443/workflows/<guid>/triggers/manual/paths/invoke?api-version=...

Your Value:
_______________________________________________
```

**How to obtain:**
1. Open Power Automate (https://make.powerautomate.com)
2. Create or open a flow with "When an HTTP request is received" trigger
3. Save the flow to generate the HTTP POST URL
4. Copy the entire URL

---

## Non-Secret Environment Variables

These values are not sensitive but still required for configuration:

### Azure Table Storage
- **AZURE_TABLE_NAME**: `HelpdeskRequests` (or your custom table name)

### Azure Service Bus
- **AZURE_SERVICEBUS_QUEUE_NAME**: `m365` (or your custom queue name)

### Azure OpenAI
- **AZURE_OPENAI_ENDPOINT**: `https://<your-openai-resource>.openai.azure.com/`
- **AZURE_OPENAI_DEPLOYMENT**: `<your-deployment-name>` (e.g., `gpt-4o`)
- **AZURE_AI_PROJECT_ENDPOINT**: `<your-ai-project-endpoint>` (if using AI Foundry)
- **AZURE_OPENAI_CHAT_DEPLOYMENT_NAME**: `<your-chat-deployment-name>`

### Azure Communication Services
- **ACS_SENDER_ADDRESS**: `noreply@<your-domain>.azurecomm.net`
- **NOTIFY_EMAILS**: `admin@company.com,support@company.com` (comma-separated)

### Microsoft Graph
- **GRAPH_TENANT_ID**: `<your-tenant-id>` (Azure AD tenant ID)
- **GRAPH_CLIENT_ID**: `<your-client-id>` (App registration client ID)
- **PLANNER_PLAN_ID**: `<your-planner-plan-id>`
- **PLANNER_BUCKET_ID**: `<your-planner-bucket-id>`

---

## Validation Checklist

Before deploying, verify:

- [ ] All 7 secrets have been obtained and recorded
- [ ] All non-secret environment variables have been prepared
- [ ] Connection strings are complete and not truncated
- [ ] Azure OpenAI model deployment exists and matches the name
- [ ] Service Bus queue has been created
- [ ] Table Storage table has been created
- [ ] Teams webhook has been tested
- [ ] Microsoft Graph app has required permissions granted
- [ ] ACS sender address is verified and active
- [ ] This file with actual secrets is NOT committed to source control

---

## Security Best Practices

1. **Never commit secrets to Git** - Add this file to .gitignore if it contains real values
2. **Rotate secrets regularly** - Update secrets periodically for security
3. **Use managed identities** when possible - Reduces need for connection strings
4. **Limit access** - Only grant minimum required permissions
5. **Monitor usage** - Use Azure Monitor to track secret access
6. **Use Azure Key Vault** - Consider integrating with Key Vault for enhanced security

---

## Quick Copy Template for Azure CLI

Use this template when deploying with Azure CLI (replace <VALUE> with actual values):

```bash
# Web App Secrets
--secrets \
  azure-table-conn-str="<YOUR_AZURE_TABLE_CONNECTION_STRING>" \
  azure-servicebus-conn-str="<YOUR_AZURE_SERVICEBUS_CONNECTION_STRING>" \
  teams-webhook-url="<YOUR_TEAMS_WEBHOOK_URL>" \
  azure-openai-api-key="<YOUR_AZURE_OPENAI_API_KEY>" \
  acs-connection-string="<YOUR_ACS_CONNECTION_STRING>" \
  graph-client-secret="<YOUR_GRAPH_CLIENT_SECRET>" \
  power-automate-flow-url="<YOUR_POWER_AUTOMATE_FLOW_URL>"
```

---

## Troubleshooting

### Common Issues

**Problem:** Container fails to start
- **Check:** Verify all required secrets are set
- **Check:** Ensure connection strings are not truncated
- **Check:** View logs with `az containerapp logs show`

**Problem:** Cannot connect to Azure services
- **Check:** Verify network rules allow Container Apps IP ranges
- **Check:** Ensure service endpoints are correct
- **Check:** Verify credentials haven't expired

**Problem:** Teams webhook not working
- **Check:** Webhook URL is complete and not expired
- **Check:** Teams connector is still active in the channel
- **Check:** Message format is valid JSON

---

## Support

For more information:
- Main README: [README.md](README.md)
- Deployment Guide: [AZURE_DEPLOYMENT.md](AZURE_DEPLOYMENT.md)
- Azure Container Apps Documentation: https://learn.microsoft.com/azure/container-apps/
