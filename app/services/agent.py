# # app/services/agent.py
# import os
# import json
# import asyncio

# from agent_framework import ChatAgent
# from agent_framework.azure import AzureAIAgentClient
# from azure.core.credentials import AzureKeyCredential

# async def decide_action(entity: dict) -> dict:
#     """
#     Given a helpdesk entity, return a JSON-like dict with an 'action' field
#     (notify-team, create-task, create-ticket, or store-only) decided by the agent.
#     """
#     endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
#     api_key = os.getenv("AZURE_OPENAI_KEY")
#     deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")

#     # If any of the required environment variables are missing, just return the actionHint
#     if not (endpoint and api_key and deployment):
#         action_hint = entity.get("ActionHint") or "notify-team"
#         return {"action": action_hint}

#     client = AzureAIAgentClient(
#         endpoint=endpoint,
#         api_key=api_key,
#         deployment_name=deployment,
#     )

#     # Instructions to the agent: classify the request and return JSON
#     instructions = (
#         "You are a helpdesk routing agent. Based on the category, priority, and "
#         "ActionHint provided, decide which action to perform. "
#         "Valid actions: notify-team, create-task, create-ticket, store-only. "
#         "Respond ONLY with JSON of the form {\"action\": \"<action>\"}."
#     )

#     agent = ChatAgent(chat_client=client, instructions=instructions)

#     # Compose the prompt from the entity fields
#     prompt = (
#         f"Category: {entity.get('PartitionKey')}\n"
#         f"Priority: {entity.get('Priority')}\n"
#         f"ActionHint: {entity.get('ActionHint') or 'notify-team'}\n"
#     )

#     # Run the agent asynchronously
#     result = await agent.run(prompt)

#     try:
#         # Parse the agent's JSON response
#         return json.loads(result.text.strip())
#     except Exception:
#         # Fallback if parsing fails
#         return {"action": entity.get("ActionHint") or "notify-team"}
# app/services/agent.py
# app/services/agent.py
import os
import json

from agent_framework import RawAgent
from agent_framework.azure import AzureOpenAIChatClient


async def decide_action(entity: dict) -> dict:
    """
    Given a helpdesk entity, return a JSON-like dict with an 'action' field
    (notify-team, create-task, create-ticket, or store-only) decided by the agent.
    """

    # We'll use this only to decide whether to enable the agent at all
    model_id = os.getenv("AZURE_OPENAI_DEPLOYMENT")

    # If the model id is missing, just fall back to ActionHint
    if not model_id:
        action_hint = entity.get("ActionHint") or "notify-team"
        return {"action": action_hint}

    # NOTE: AzureOpenAIChatClient reads endpoint & credentials from environment.
    # Make sure you have the standard env vars set:
    #   AZURE_OPENAI_ENDPOINT
    #   AZURE_OPENAI_API_KEY
    #   AZURE_OPENAI_CHAT_DEPLOYMENT_NAME (or similar for model_id)
    chat_client = AzureOpenAIChatClient()

    instructions = (
        "You are a helpdesk routing agent. Your job is to decide the action type.\n"
        "Based on the Category, Priority, and ActionHint provided:\n"
        "- If ActionHint is 'notify-team', return: {\"action\": \"notify-team\"}\n"
        "- If ActionHint is 'create-task', return: {\"action\": \"create-task\"}\n"
        "- If ActionHint is 'create-ticket', return: {\"action\": \"create-ticket\"}\n"
        "- If ActionHint is 'store-only', return: {\"action\": \"store-only\"}\n\n"
        "You must respond with ONLY valid JSON. No explanations, no markdown, just JSON."
    )

    agent = RawAgent(
        name="HelpdeskRouter",
        client=chat_client,
        instructions=instructions
    )

    action_hint = entity.get('ActionHint') or 'notify-team'
    prompt = (
        f"Determine the action for this helpdesk request:\n"
        f"Category: {entity.get('PartitionKey')}\n"
        f"Priority: {entity.get('Priority')}\n"
        f"ActionHint: {action_hint}\n\n"
        f"Return JSON with the action field."
    )

    try:
        result = await agent.run(prompt)
        raw = result.text.strip()
        
        # Debug: print what the agent actually returned
        print(f"🤖 Agent raw response: '{raw}'")
        
        # Sometimes agents wrap JSON in markdown code blocks, so handle that
        if raw.startswith("```"):
            # Extract JSON from markdown code block
            lines = raw.split("\n")
            raw = "\n".join(lines[1:-1]) if len(lines) > 2 else raw
            raw = raw.replace("```json", "").replace("```", "").strip()
        
        parsed = json.loads(raw)
        print(f"✅ Agent parsed decision: {parsed}")
        return parsed
    except json.JSONDecodeError as ex:
        print(f"❌ Agent returned invalid JSON: '{raw}'. Error: {ex}")
        print(f"📋 Falling back to ActionHint: {action_hint}")
        return {"action": action_hint}
    except Exception as ex:
        print(f"❌ Agent decision failed: {ex}")
        print(f"📋 Falling back to ActionHint: {action_hint}")
        return {"action": action_hint}
