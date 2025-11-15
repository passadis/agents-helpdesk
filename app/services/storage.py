# app/services/storage.py
import uuid
from datetime import datetime, timezone
import os

from azure.data.tables import TableServiceClient
from dotenv import load_dotenv

# load env once
load_dotenv()

TABLE_CONN_STR = os.getenv("AZURE_TABLE_CONN_STR")
TABLE_NAME = os.getenv("AZURE_TABLE_NAME", "HelpdeskRequests")


def get_table_client():
    if not TABLE_CONN_STR:
        raise RuntimeError("AZURE_TABLE_CONN_STR not set")
    service = TableServiceClient.from_connection_string(TABLE_CONN_STR)
    # create table if not exists
    try:
        service.create_table_if_not_exists(TABLE_NAME)
    except Exception:
        # it's okay if it already exists
        pass
    return service.get_table_client(TABLE_NAME)


def save_helpdesk_request(payload: dict) -> dict:
    """
    payload keys expected:
      title, description, category, priority, actionHint, requesterEmail
    returns the entity we stored (including PartitionKey/RowKey)
    """
    table_client = get_table_client()

    partition_key = payload.get("category", "Uncategorized")
    row_key = str(uuid.uuid4())

    entity = {
        "PartitionKey": partition_key,
        "RowKey": row_key,
        "Title": payload.get("title"),
        "Description": payload.get("description"),
        "Priority": payload.get("priority"),
        "ActionHint": payload.get("actionHint") or "",
        "RequesterEmail": payload.get("requesterEmail") or "",
        "CreatedAt": datetime.now(timezone.utc).isoformat(),
    }

    table_client.create_entity(entity=entity)
    return entity


def get_helpdesk_request(partition_key: str, row_key: str) -> dict | None:
    table_client = get_table_client()
    try:
        entity = table_client.get_entity(partition_key=partition_key, row_key=row_key)
        return entity
    except Exception:
        return None
