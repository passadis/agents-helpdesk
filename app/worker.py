# app/worker.py
import json
import os
import time
import asyncio
from dotenv import load_dotenv
from azure.servicebus import ServiceBusClient

from .services.storage import get_helpdesk_request
from .services.ai import enrich_helpdesk_entity
from .services.teams import send_to_teams

# NEW: import the actions
from .services.helpdesk_actions import send_email_via_acs, create_planner_task, trigger_flow
from .services.agent import decide_action

load_dotenv()

SB_CONN_STR = os.getenv("AZURE_SERVICEBUS_CONN_STR")
SB_QUEUE_NAME = os.getenv("AZURE_SERVICEBUS_QUEUE_NAME", "m365")

if not SB_CONN_STR:
    raise RuntimeError("AZURE_SERVICEBUS_CONN_STR not set")


def process_message(message_body: dict):
    partition = message_body.get("tablePartition")
    row = message_body.get("tableRow")

    entity = None
    if partition and row:
        entity = get_helpdesk_request(partition, row)

    print("---- New helpdesk message ----")
    print("Queue payload:", message_body)

    if not entity:
        print("Could not fetch entity from Table Storage.")
        print("------------------------------")
        return

    print("Fetched full entity from Table Storage.")

    # 1) AI enrichment (safe fallback)
    enriched = enrich_helpdesk_entity(entity)
    print("Enriched view:", enriched)

    # 2) Send to Teams
    send_to_teams(enriched, entity)

    # 3) Decide next action via Agent Framework
    try:
        action_result = asyncio.run(decide_action(entity))
        action = (action_result or {}).get("action") or entity.get("ActionHint") or "notify-team"
    except Exception as ex:
        print("Agent decision failed:", ex)
        action = entity.get("ActionHint") or "notify-team"

    print("Agent decided action:", action)

    # 4) Execute action
    if action == "notify-team":
        send_email_via_acs(entity, enriched)
    elif action == "create-task":
        create_planner_task(entity)
    elif action == "create-ticket":
        trigger_flow(entity)
    elif action == "store-only":
        print("No downstream action requested.")
    else:
        print(f"Unknown action '{action}', skipping.")

    print("------------------------------")


def main():
    sb_client = ServiceBusClient.from_connection_string(SB_CONN_STR, logging_enable=False)
    print(f"Listening on queue '{SB_QUEUE_NAME}' ... Ctrl+C to stop.")

    with sb_client:
        receiver = sb_client.get_queue_receiver(queue_name=SB_QUEUE_NAME)
        with receiver:
            while True:
                messages = receiver.receive_messages(max_message_count=5, max_wait_time=5)
                if not messages:
                    time.sleep(1)
                    continue

                for msg in messages:
                    try:
                        body = json.loads(str(msg))
                        process_message(body)
                        receiver.complete_message(msg)
                    except Exception as ex:
                        print("Error processing message:", ex)
                        receiver.abandon_message(msg)


if __name__ == "__main__":
    main()
