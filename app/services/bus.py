# app/services/bus.py
import json
import os

from azure.servicebus import ServiceBusClient, ServiceBusMessage
from dotenv import load_dotenv

load_dotenv()

SB_CONN_STR = os.getenv("AZURE_SERVICEBUS_CONN_STR")
SB_QUEUE_NAME = os.getenv("AZURE_SERVICEBUS_QUEUE_NAME", "helpdesk-messages")


def send_helpdesk_message(entity: dict):
    """
    entity is the table entity we just stored.
    We'll send a slimmed-down message to Service Bus.
    """
    if not SB_CONN_STR:
        raise RuntimeError("AZURE_SERVICEBUS_CONN_STR not set")

    message_body = {
        "tablePartition": entity["PartitionKey"],
        "tableRow": entity["RowKey"],
        "title": entity.get("Title"),
        "category": entity.get("PartitionKey"),
        "priority": entity.get("Priority"),
        "actionHint": entity.get("ActionHint"),
        "requesterEmail": entity.get("RequesterEmail"),
    }

    sb_client = ServiceBusClient.from_connection_string(SB_CONN_STR, logging_enable=False)

    with sb_client:
        sender = sb_client.get_queue_sender(queue_name=SB_QUEUE_NAME)
        with sender:
            msg = ServiceBusMessage(json.dumps(message_body))
            sender.send_messages(msg)
