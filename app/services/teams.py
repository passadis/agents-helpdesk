# app/services/teams.py
import os
import requests
from dotenv import load_dotenv

load_dotenv()

TEAMS_WEBHOOK_URL = os.getenv("TEAMS_WEBHOOK_URL")


def send_to_teams(enriched: dict, entity: dict):
    """
    enriched: dict from AI (title, summary, urgency)
    entity: full table entity (for extra fields)
    """
    if not TEAMS_WEBHOOK_URL:
        print("TEAMS_WEBHOOK_URL not set – skipping Teams send.")
        return

    title = enriched.get("title", "New helpdesk request")
    summary = enriched.get("summary", "")
    urgency = enriched.get("urgency", entity.get("Priority", "Normal"))
    category = entity.get("PartitionKey")
    action_hint = entity.get("ActionHint") or "n/a"
    requester = entity.get("RequesterEmail") or "n/a"

    color = "0078D4"  # Teams blue
    if urgency.lower() == "high":
      color = "FF0000"

    payload = {
        "@type": "MessageCard",
        "@context": "https://schema.org/extensions",
        "summary": title,
        "themeColor": color,
        "title": f"📨 {title}",
        "sections": [
            {
                "activityTitle": f"Category: **{category}** | Priority: **{urgency}**",
                "facts": [
                    {"name": "Action hint", "value": action_hint},
                    {"name": "Requester", "value": requester},
                ],
                "text": summary,
            }
        ],
        "potentialAction": [
            {
                "@type": "OpenUri",
                "name": "View in Storage (placeholder)",
                "targets": [
                    {"os": "default", "uri": "https://portal.azure.com/"}  # You can change this
                ],
            }
        ],
    }

    try:
        resp = requests.post(TEAMS_WEBHOOK_URL, json=payload, timeout=10)
        resp.raise_for_status()
        print("✅ Sent to Teams.")
    except Exception as ex:
        print("Failed to send to Teams:", ex)
