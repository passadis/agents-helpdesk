"""Actions module for helpdesk agent.

This module defines functions to execute downstream actions based on the
decision returned by the Microsoft Agent Framework. The functions
interact with Azure Communication Services to send email notifications,
Microsoft Graph to create Planner tasks, and Power Automate HTTP flows
to raise support tickets.

Each function reads configuration from environment variables so that
you can configure credentials and endpoints without changing code.

Environment variables used:

* Email actions (Azure Communication Services)
    - `ACS_CONNECTION_STRING`: connection string for the ACS resource
    - `ACS_SENDER_ADDRESS`: email address configured as the sender
    - `NOTIFY_EMAILS`: comma‑separated list of recipient email addresses

* Planner actions (Microsoft Graph)
    - `GRAPH_TENANT_ID`: Azure AD tenant ID
    - `GRAPH_CLIENT_ID`: client ID for an app registration with Graph
    - `GRAPH_CLIENT_SECRET`: client secret for the app registration
    - `PLANNER_PLAN_ID`: ID of the Planner plan in which to create tasks
    - `PLANNER_BUCKET_ID`: ID of the bucket within the plan
    - `PLANNER_ASSIGNEE_ID` (optional): Azure AD object ID of the user to
      assign the task to; if unset, no assignment will be made

* Ticket actions (Power Automate)
    - `POWER_AUTOMATE_FLOW_URL`: URL of the HTTP triggered flow

All functions log exceptions but do not raise them, to ensure the
worker can continue processing subsequent messages even if an action
fails.
"""

from __future__ import annotations

import json
import os
from typing import Dict, Any, Optional

import requests
from dotenv import load_dotenv

try:
    from azure.communication.email import EmailClient  # type: ignore
except ImportError:
    # If the library isn't installed, we'll fall back later
    EmailClient = None  # type: ignore

try:
    import msal  # type: ignore
except ImportError:
    msal = None  # type: ignore

# Load environment variables from .env if present
load_dotenv()


def send_email_via_acs(entity: Dict[str, Any], enriched: Dict[str, Any]) -> None:
    """Send a notification email using Azure Communication Services.

    This function builds a simple email message summarising the
    request. It pulls the recipients, sender and connection string
    from environment variables. If ACS is not configured or the
    required library is unavailable, the function logs a message and
    returns without attempting to send an email.

    Args:
        entity: The full entity dictionary fetched from Table Storage.
        enriched: A dictionary returned from the AI enrichment agent
            containing keys like `title`, `summary`, and `urgency`.
    """
    connection_string = os.getenv("ACS_CONNECTION_STRING")
    sender = os.getenv("ACS_SENDER_ADDRESS")
    recipients_str = os.getenv("NOTIFY_EMAILS")
    if not (connection_string and sender and recipients_str and EmailClient):
        print(
            "ACS email configuration is incomplete or azure-communication-email is not installed; skipping email send."
        )
        return

    recipients = []
    for addr in recipients_str.split(","):
        addr = addr.strip()
        if addr:
            recipients.append({"address": addr})

    subject = f"Helpdesk request: {enriched.get('title', entity.get('Title'))}"
    plain_text = (
        f"Summary: {enriched.get('summary', entity.get('Description'))}\n"
        f"Priority: {enriched.get('urgency', entity.get('Priority'))}\n"
        f"Category: {entity.get('PartitionKey')}\n"
        f"Requester: {entity.get('RequesterEmail') or 'n/a'}"
    )
    html_body = (
        f"<p><strong>Summary:</strong> {enriched.get('summary', entity.get('Description'))}</p>"
        f"<p><strong>Priority:</strong> {enriched.get('urgency', entity.get('Priority'))}</p>"
        f"<p><strong>Category:</strong> {entity.get('PartitionKey')}</p>"
        f"<p><strong>Requester:</strong> {entity.get('RequesterEmail') or 'n/a'}</p>"
    )

    message: Dict[str, Any] = {
        "content": {
            "subject": subject,
            "plainText": plain_text,
            "html": html_body,
        },
        "recipients": {"to": recipients},
        "senderAddress": sender,
    }

    try:
        client = EmailClient.from_connection_string(connection_string)  # type: ignore
        poller = client.begin_send(message)  # type: ignore[attr-defined]
        result = poller.result()  # wait for completion
        print(f"📧 Email sent via ACS. Message ID: {getattr(result, 'id', 'unknown')}")
    except Exception as ex:
        print(f"Failed to send email via ACS: {ex}")


def _get_graph_access_token() -> Optional[str]:
    """Acquire an application token for Microsoft Graph using MSAL.

    Returns None if MSAL is unavailable or if any required environment
    variables are missing.
    """
    tenant_id = os.getenv("GRAPH_TENANT_ID")
    client_id = os.getenv("GRAPH_CLIENT_ID")
    client_secret = os.getenv("GRAPH_CLIENT_SECRET")
    if not (msal and tenant_id and client_id and client_secret):
        print(
            "Graph authentication is not configured or msal is not installed; skipping access token acquisition."
        )
        return None
    authority = f"https://login.microsoftonline.com/{tenant_id}"
    app = msal.ConfidentialClientApplication(
        client_id=client_id,
        client_credential=client_secret,
        authority=authority,
    )
    scopes = ["https://graph.microsoft.com/.default"]
    result = app.acquire_token_for_client(scopes=scopes)
    access_token = result.get("access_token")
    if not access_token:
        print(
            f"Failed to acquire Graph token: {result.get('error_description') or 'unknown error'}"
        )
    return access_token


def create_planner_task(entity: Dict[str, Any]) -> None:
    """Create a Planner task in Microsoft Graph for the helpdesk request.

    This function builds a minimal task with the plan and bucket IDs
    specified in the environment. It optionally assigns the task to a
    user if `PLANNER_ASSIGNEE_ID` is set. If Graph authentication is
    not configured or the MSAL library is missing, the function logs
    a message and returns.

    Args:
        entity: The full entity dictionary fetched from Table Storage.
    """
    plan_id = os.getenv("PLANNER_PLAN_ID")
    bucket_id = os.getenv("PLANNER_BUCKET_ID")
    if not (plan_id and bucket_id):
        print("Planner configuration (plan and bucket IDs) is missing; skipping task creation.")
        return
    token = _get_graph_access_token()
    if not token:
        return

    body: Dict[str, Any] = {
        "planId": plan_id,
        "bucketId": bucket_id,
        "title": entity.get("Title", "New helpdesk request"),
    }
    assignee_id = os.getenv("PLANNER_ASSIGNEE_ID")
    if assignee_id:
        # Add the assignments object, using a simple order hint
        body["assignments"] = {
            assignee_id: {
                "@odata.type": "#microsoft.graph.plannerAssignment",
                "orderHint": " !",
            }
        }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    try:
        response = requests.post(
            "https://graph.microsoft.com/v1.0/planner/tasks",
            headers=headers,
            data=json.dumps(body),
            timeout=10,
        )
        if response.status_code >= 200 and response.status_code < 300:
            print(f"✅ Created Planner task: {response.json().get('id')}")
        else:
            print(
                f"Failed to create Planner task (status {response.status_code}): {response.text}"
            )
    except Exception as ex:
        print(f"Error calling Graph API to create Planner task: {ex}")


def trigger_flow(entity: Dict[str, Any]) -> None:
    """Send the helpdesk request to a Power Automate HTTP flow.

    The function posts the entire entity as JSON to the flow URL.
    If the flow URL is not set, the function logs a message and returns.

    Args:
        entity: The full entity dictionary fetched from Table Storage.
    """
    flow_url = os.getenv("POWER_AUTOMATE_FLOW_URL")
    if not flow_url:
        print("Power Automate flow URL is not configured; skipping ticket creation.")
        return
    try:
        # It's safe to send the raw entity; the flow can parse what it needs
        response = requests.post(flow_url, json=entity, timeout=10)
        if response.status_code >= 200 and response.status_code < 300:
            print("✅ Sent request to Power Automate flow.")
        else:
            print(
                f"Failed to trigger Power Automate flow (status {response.status_code}): {response.text}"
            )
    except Exception as ex:
        print(f"Error triggering Power Automate flow: {ex}")