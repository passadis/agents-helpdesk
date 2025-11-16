<!-- GitAds-Verify: 3TGJ6O5X187YUEZDHZ2R68LQXDFZDGZ7 -->

<p align="center">
  <a href="https://skillicons.dev">
    <img src="https://skillicons.dev/icons?i=azure,vscode,python,html,css,github,fastapi" />
  </a>
</p>

<h1 align="center">Agentic AI Helpdesk (FastAPI + Azure + M365)</h1

This project is a complete, event-driven, AI-powered helpdesk solution. It uses FastAPI for high-performance ingestion, Azure Service Bus for decoupling, and a Python worker to enrich requests with[...]  

<br/>

<details>
  <summary><strong>View Solution Architecture Flowchart</strong></summary>

  ```mermaid
  flowchart LR
    U["User submits Helpdesk Form<br/>(Title, Description, Category, Priority, ActionHint, RequesterEmail)"]
    U --> F[FastAPI /submit handler]

    F --> T["Save entity to<br/>Azure Table Storage<br/>(HelpdeskRequests)"]
    F --> Q[Send compact message<br/>to Service Bus queue 'm365']

    Q --> W[Worker process<br/>listens on 'm365']
    W --> R[Fetch full entity<br/>from Table Storage]

    R --> E["AI Enrichment<br/>(Azure OpenAI)"]
    E -->|enriched title/summary/urgency| TEAMS[Send MessageCard<br/>to Teams via Webhook]

    TEAMS --> A["Agent Framework<br/>decide_action(entity, enriched)"]

    A -->|notify-team| ACS[Send notification email<br/>via Azure Communication Services]
    A -->|create-task| PL[Create Planner task<br/>via Microsoft Graph]
    A -->|create-ticket| FLOW["Trigger Power Automate<br/>HTTP Flow (ticket)"]
    A -->|store-only| END["No further action<br/>(stored + Teams only)"]
  ```
 
</details>

<details> <summary><strong>View Screenshots</strong></summary>
  
![agentsbusscr1](https://github.com/user-attachments/assets/1708e213-d6c5-424d-8e76-26be0f7af47a)

![agentsbusscr2](https://github.com/user-attachments/assets/e83acf97-6ac3-4922-a942-6bcd680292ae)

</details

<br>

## 🚀 Features

  * **FastAPI Ingestion:** A high-performance, asynchronous API endpoint for form submission.
  * **Event-Driven:** Fully decoupled architecture using Azure Service Bus for resilience.
  * **AI Enrichment:** Uses Azure OpenAI to summarize, re-title, and assess the urgency of user requests.
  * **Agentic Actions:** Leverages the Microsoft Agent Framework to intelligently decide the next best action.
  * **M365 Integration:**
      * Posts notifications to **Microsoft Teams**.
      * Creates tasks in **Microsoft Planner** via Graph API.
      * Sends notification emails via **Azure Communication Services**.
      * Triggers **Power Automate** flows for custom ticketing.

-----

## 🔧 Prerequisites

Before you begin, you will need:

  * Python 3.10+
  * An **Azure Subscription**
  * An **Azure OpenAI** resource with a model deployed (e.g., `gpt-4o`)
  * A **Microsoft 365 Tenant** with admin permissions to:
      * Create App Registrations
      * Microsoft Teams (with a channel for notifications)
      * Microsoft Planner (with a plan and bucket)
      * Power Automate
  * An **Azure Communication Services** resource configured for email.

-----

## ⚙️ Configuration & Setup

### 1. Local Project Setup

First, clone the repository and set up your Python virtual environment.

```bash
# Clone the repository
git clone https://github.com/your-username/your-repo-name.git
cd your-repo-name

# Create a virtual environment (venv)
python -m venv .venv

# Activate the virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install the required packages
pip install -r requirements.txt
```

### 2. Create `.env` File

Create a file named `.env` in the root of the project. Copy the content below into it.

```dotenv
# Azure Storage
AZURE_TABLE_CONN_STR=
AZURE_TABLE_NAME=HelpdeskRequests

# Azure Service Bus
AZURE_SERVICEBUS_CONN_STR=
AZURE_SERVICEBUS_QUEUE_NAME=m365

# Teams
TEAMS_WEBHOOK_URL=

# Azure OpenAI / Agent Framework
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_DEPLOYMENT=
AZURE_AI_PROJECT_ENDPOINT=
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=

# Email via ACS
ACS_CONNECTION_STRING=
ACS_SENDER_ADDRESS=
NOTIFY_EMAILS=

# Planner via Graph
GRAPH_TENANT_ID=
GRAPH_CLIENT_ID=
GRAPH_CLIENT_SECRET=
PLANNER_PLAN_ID=
PLANNER_BUCKET_ID=

# Power Automate HTTP flow
POWER_AUTOMATE_FLOW_URL=
```

### 3. Get Configuration Values

#### Azure Storage & Service Bus

1. **Azure Storage:**
   * Create an Azure Storage Account.
   * Under **Access keys**, copy the **Connection string**.
   * Create a table named `HelpdeskRequests`.

2. **Azure Service Bus:**
   * Create a Service Bus Namespace.
   * Copy the **Primary Connection String**.
   * Create a queue named `m365`.

#### Microsoft Teams Webhook

1. Open Teams → go to the channel.
2. Select **Connectors** → **Incoming Webhook**.
3. Generate and copy the webhook URL.

#### Azure OpenAI

1. Open your Azure OpenAI resource.
2. Copy the endpoint and key.
3. Copy your model deployment name.

#### ACS Email

1. Create an ACS resource.
2. Configure Email → verified domain.
3. Copy connection string + sender address.

#### Microsoft Graph for Planner

1. Create an App Registration.
2. Copy:
   * Tenant ID
   * Client ID
3. Add Graph API permission:
   * `Tasks.ReadWrite.All`
4. Create a **Client Secret**.
5. Get:
   * `PLANNER_PLAN_ID`
   * `PLANNER_BUCKET_ID` via Graph Explorer.

#### Power Automate Flow

1. Create a flow with **When an HTTP request is received**.
2. Save → copy the generated endpoint URL.

-----

## ▶️ Running the Application

You need two terminals.

### Terminal 1 — FastAPI Web Server

```bash
uvicorn main:app --reload
```

### Terminal 2 — Worker

```bash
python worker.py
```

-----

## 📚 References

* Azure Service Bus messaging overview  
  https://learn.microsoft.com/azure/service-bus-messaging/service-bus-messaging-overview?wt.mc_id=MVP_365598

* Microsoft Agent Framework overview  
  https://learn.microsoft.com/agent-framework/overview/agent-framework-overview?wt.mc_id=MVP_365598

* Python Agent Tools  
  https://learn.microsoft.com/agent-framework/user-guide/agents/agent-tools?pivots=programming-language-python?wt.mc_id=MVP_365598

  ## GitAds Sponsored
[![Sponsored by GitAds](https://gitads.dev/v1/ad-serve?source=passadis/agents-helpdesk@github)](https://gitads.dev/v1/ad-track?source=passadis/agents-helpdesk@github)


