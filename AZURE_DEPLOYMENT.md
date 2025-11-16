# Azure Container Apps Deployment Guide

This guide provides step-by-step instructions for deploying the Agentic AI Helpdesk solution to Azure Container Apps.

## Architecture Overview

The solution consists of two container apps that work together:
1. **Web App (FastAPI)**: Handles HTTP requests and form submissions
2. **Worker App**: Processes messages from Azure Service Bus queue

Both apps share the same Docker image but run different commands.

## Prerequisites

- Azure CLI installed and configured
- Docker installed locally (for testing)
- Azure subscription with appropriate permissions
- All Azure resources already created (see main README.md):
  - Azure Storage Account (with Table Storage)
  - Azure Service Bus (with queue)
  - Azure OpenAI
  - Azure Communication Services
  - Microsoft Graph App Registration
  - Microsoft Teams webhook
  - Power Automate flow (optional)

## Step 1: Build and Push Docker Image

### 1.1 Build the Docker Image Locally (Optional - for testing)

```bash
docker build -t agents-helpdesk:latest .
```

### 1.2 Test Locally (Optional)

Create a `.env` file with your configuration, then:

**Option A: Using docker-compose (recommended for local testing)**
```bash
# Start both web and worker containers
docker-compose up

# Or run in detached mode
docker-compose up -d

# View logs
docker-compose logs -f

# Stop containers
docker-compose down
```

**Option B: Using docker run**
```bash
# Test the web app
docker run -p 8000:8000 --env-file .env agents-helpdesk:latest

# Test the worker (in another terminal)
docker run --env-file .env agents-helpdesk:latest python -m app.worker
```

### 1.3 Create Azure Container Registry (if not exists)

```bash
# Set variables
RESOURCE_GROUP="rg-helpdesk-prod"
LOCATION="eastus"
ACR_NAME="acrhelpdesk"  # Must be globally unique

# Create resource group
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create container registry
az acr create \
  --resource-group $RESOURCE_GROUP \
  --name $ACR_NAME \
  --sku Basic \
  --admin-enabled true
```

### 1.4 Build and Push to ACR

```bash
# Login to ACR
az acr login --name $ACR_NAME

# Build and push using ACR
az acr build \
  --registry $ACR_NAME \
  --image agents-helpdesk:latest \
  --image agents-helpdesk:v1.0.0 \
  .
```

## Step 2: Create Azure Container Apps Environment

```bash
# Set variables
ENVIRONMENT_NAME="env-helpdesk-prod"

# Install Container Apps extension
az extension add --name containerapp --upgrade

# Create Container Apps environment
az containerapp env create \
  --name $ENVIRONMENT_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION
```

## Step 3: Configure Secrets in Azure

All sensitive configuration values should be stored as secrets in Azure Container Apps.

### 3.1 Retrieve ACR Credentials

```bash
ACR_LOGIN_SERVER=$(az acr show --name $ACR_NAME --query loginServer --output tsv)
ACR_USERNAME=$(az acr credential show --name $ACR_NAME --query username --output tsv)
ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query passwords[0].value --output tsv)
```

### 3.2 Create Container Apps with Secrets

The following secrets need to be configured. Replace the placeholder values with your actual values.

## Step 4: Deploy Web App

```bash
APP_NAME="app-helpdesk-web"

az containerapp create \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --environment $ENVIRONMENT_NAME \
  --image $ACR_LOGIN_SERVER/agents-helpdesk:latest \
  --registry-server $ACR_LOGIN_SERVER \
  --registry-username $ACR_USERNAME \
  --registry-password $ACR_PASSWORD \
  --target-port 8000 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 3 \
  --cpu 0.5 \
  --memory 1.0Gi \
  --secrets \
    azure-table-conn-str="<YOUR_AZURE_TABLE_CONNECTION_STRING>" \
    azure-servicebus-conn-str="<YOUR_AZURE_SERVICEBUS_CONNECTION_STRING>" \
    teams-webhook-url="<YOUR_TEAMS_WEBHOOK_URL>" \
    azure-openai-api-key="<YOUR_AZURE_OPENAI_API_KEY>" \
    acs-connection-string="<YOUR_ACS_CONNECTION_STRING>" \
    graph-client-secret="<YOUR_GRAPH_CLIENT_SECRET>" \
    power-automate-flow-url="<YOUR_POWER_AUTOMATE_FLOW_URL>" \
  --env-vars \
    "AZURE_TABLE_CONN_STR=secretref:azure-table-conn-str" \
    "AZURE_TABLE_NAME=HelpdeskRequests" \
    "AZURE_SERVICEBUS_CONN_STR=secretref:azure-servicebus-conn-str" \
    "AZURE_SERVICEBUS_QUEUE_NAME=m365" \
    "TEAMS_WEBHOOK_URL=secretref:teams-webhook-url" \
    "AZURE_OPENAI_ENDPOINT=<YOUR_AZURE_OPENAI_ENDPOINT>" \
    "AZURE_OPENAI_API_KEY=secretref:azure-openai-api-key" \
    "AZURE_OPENAI_DEPLOYMENT=<YOUR_AZURE_OPENAI_DEPLOYMENT>" \
    "AZURE_AI_PROJECT_ENDPOINT=<YOUR_AZURE_AI_PROJECT_ENDPOINT>" \
    "AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=<YOUR_AZURE_OPENAI_CHAT_DEPLOYMENT_NAME>" \
    "ACS_CONNECTION_STRING=secretref:acs-connection-string" \
    "ACS_SENDER_ADDRESS=<YOUR_ACS_SENDER_ADDRESS>" \
    "NOTIFY_EMAILS=<YOUR_NOTIFY_EMAILS>" \
    "GRAPH_TENANT_ID=<YOUR_GRAPH_TENANT_ID>" \
    "GRAPH_CLIENT_ID=<YOUR_GRAPH_CLIENT_ID>" \
    "GRAPH_CLIENT_SECRET=secretref:graph-client-secret" \
    "PLANNER_PLAN_ID=<YOUR_PLANNER_PLAN_ID>" \
    "PLANNER_BUCKET_ID=<YOUR_PLANNER_BUCKET_ID>" \
    "POWER_AUTOMATE_FLOW_URL=secretref:power-automate-flow-url"
```

## Step 5: Deploy Worker App

```bash
WORKER_NAME="app-helpdesk-worker"

az containerapp create \
  --name $WORKER_NAME \
  --resource-group $RESOURCE_GROUP \
  --environment $ENVIRONMENT_NAME \
  --image $ACR_LOGIN_SERVER/agents-helpdesk:latest \
  --registry-server $ACR_LOGIN_SERVER \
  --registry-username $ACR_USERNAME \
  --registry-password $ACR_PASSWORD \
  --ingress internal \
  --min-replicas 1 \
  --max-replicas 1 \
  --cpu 0.5 \
  --memory 1.0Gi \
  --command "python" "-m" "app.worker" \
  --secrets \
    azure-table-conn-str="<YOUR_AZURE_TABLE_CONNECTION_STRING>" \
    azure-servicebus-conn-str="<YOUR_AZURE_SERVICEBUS_CONNECTION_STRING>" \
    teams-webhook-url="<YOUR_TEAMS_WEBHOOK_URL>" \
    azure-openai-api-key="<YOUR_AZURE_OPENAI_API_KEY>" \
    acs-connection-string="<YOUR_ACS_CONNECTION_STRING>" \
    graph-client-secret="<YOUR_GRAPH_CLIENT_SECRET>" \
    power-automate-flow-url="<YOUR_POWER_AUTOMATE_FLOW_URL>" \
  --env-vars \
    "AZURE_TABLE_CONN_STR=secretref:azure-table-conn-str" \
    "AZURE_TABLE_NAME=HelpdeskRequests" \
    "AZURE_SERVICEBUS_CONN_STR=secretref:azure-servicebus-conn-str" \
    "AZURE_SERVICEBUS_QUEUE_NAME=m365" \
    "TEAMS_WEBHOOK_URL=secretref:teams-webhook-url" \
    "AZURE_OPENAI_ENDPOINT=<YOUR_AZURE_OPENAI_ENDPOINT>" \
    "AZURE_OPENAI_API_KEY=secretref:azure-openai-api-key" \
    "AZURE_OPENAI_DEPLOYMENT=<YOUR_AZURE_OPENAI_DEPLOYMENT>" \
    "AZURE_AI_PROJECT_ENDPOINT=<YOUR_AZURE_AI_PROJECT_ENDPOINT>" \
    "AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=<YOUR_AZURE_OPENAI_CHAT_DEPLOYMENT_NAME>" \
    "ACS_CONNECTION_STRING=secretref:acs-connection-string" \
    "ACS_SENDER_ADDRESS=<YOUR_ACS_SENDER_ADDRESS>" \
    "NOTIFY_EMAILS=<YOUR_NOTIFY_EMAILS>" \
    "GRAPH_TENANT_ID=<YOUR_GRAPH_TENANT_ID>" \
    "GRAPH_CLIENT_ID=<YOUR_GRAPH_CLIENT_ID>" \
    "GRAPH_CLIENT_SECRET=secretref:graph-client-secret" \
    "PLANNER_PLAN_ID=<YOUR_PLANNER_PLAN_ID>" \
    "PLANNER_BUCKET_ID=<YOUR_PLANNER_BUCKET_ID>" \
    "POWER_AUTOMATE_FLOW_URL=secretref:power-automate-flow-url"
```

## Step 6: Get the Application URL

```bash
az containerapp show \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --query properties.configuration.ingress.fqdn \
  --output tsv
```

Visit the URL to access your helpdesk application!

## Required Secret Variables Reference

Below is a comprehensive list of all secret variables required for Azure Container Apps deployment:

### Secrets (Sensitive - Store in Azure Container Apps Secrets)

1. **azure-table-conn-str**: Azure Storage Account connection string
   - Example: `DefaultEndpointsProtocol=https;AccountName=...;AccountKey=...`

2. **azure-servicebus-conn-str**: Azure Service Bus connection string
   - Example: `Endpoint=sb://...;SharedAccessKeyName=...;SharedAccessKey=...`

3. **teams-webhook-url**: Microsoft Teams incoming webhook URL
   - Example: `https://outlook.office.com/webhook/...`

4. **azure-openai-api-key**: Azure OpenAI API key
   - Example: `abc123def456...`

5. **acs-connection-string**: Azure Communication Services connection string
   - Example: `endpoint=https://...;accesskey=...`

6. **graph-client-secret**: Microsoft Graph App Registration client secret
   - Example: `ABC~123...`

7. **power-automate-flow-url**: Power Automate HTTP flow endpoint URL
   - Example: `https://prod-xx.region.logic.azure.com:443/workflows/...`

### Non-Secret Environment Variables

1. **AZURE_TABLE_NAME**: Table Storage table name (default: `HelpdeskRequests`)
2. **AZURE_SERVICEBUS_QUEUE_NAME**: Service Bus queue name (default: `m365`)
3. **AZURE_OPENAI_ENDPOINT**: Azure OpenAI endpoint URL
4. **AZURE_OPENAI_DEPLOYMENT**: Azure OpenAI model deployment name
5. **AZURE_AI_PROJECT_ENDPOINT**: Azure AI project endpoint
6. **AZURE_OPENAI_CHAT_DEPLOYMENT_NAME**: Chat model deployment name
7. **ACS_SENDER_ADDRESS**: Email sender address (e.g., `noreply@yourdomain.com`)
8. **NOTIFY_EMAILS**: Comma-separated list of notification email addresses
9. **GRAPH_TENANT_ID**: Azure AD tenant ID
10. **GRAPH_CLIENT_ID**: Microsoft Graph App Registration client ID
11. **PLANNER_PLAN_ID**: Microsoft Planner plan ID
12. **PLANNER_BUCKET_ID**: Microsoft Planner bucket ID

## Updating the Application

To update the application after code changes:

```bash
# Build and push new image
az acr build \
  --registry $ACR_NAME \
  --image agents-helpdesk:latest \
  --image agents-helpdesk:v1.0.1 \
  .

# Update web app
az containerapp update \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --image $ACR_LOGIN_SERVER/agents-helpdesk:latest

# Update worker app
az containerapp update \
  --name $WORKER_NAME \
  --resource-group $RESOURCE_GROUP \
  --image $ACR_LOGIN_SERVER/agents-helpdesk:latest
```

## Monitoring and Troubleshooting

### View Logs

```bash
# Web app logs
az containerapp logs show \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --follow

# Worker app logs
az containerapp logs show \
  --name $WORKER_NAME \
  --resource-group $RESOURCE_GROUP \
  --follow
```

### Scale Applications

```bash
# Scale web app
az containerapp update \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --min-replicas 2 \
  --max-replicas 5

# Worker should typically run with min=max=1 to avoid duplicate processing
az containerapp update \
  --name $WORKER_NAME \
  --resource-group $RESOURCE_GROUP \
  --min-replicas 1 \
  --max-replicas 1
```

## Cost Optimization

- Use consumption-based pricing for Container Apps
- Consider scaling web app to 0 replicas during off-hours if appropriate
- Worker app should run at least 1 replica to process queue messages
- Use Azure Monitor to track resource usage and optimize accordingly

## Security Best Practices

1. **Never commit secrets to source control** - Use Azure Container Apps secrets
2. **Enable managed identity** if possible for Azure service authentication
3. **Use Azure Key Vault** for additional secret management if needed
4. **Restrict ingress** to only necessary endpoints
5. **Keep the base Docker image updated** for security patches
6. **Review and rotate secrets regularly**

## Additional Resources

- [Azure Container Apps Documentation](https://learn.microsoft.com/azure/container-apps/)
- [Azure Container Registry Documentation](https://learn.microsoft.com/azure/container-registry/)
- [Container Apps Secrets Management](https://learn.microsoft.com/azure/container-apps/manage-secrets)
