# # app/services/agent.py

import os
import json

from agent_framework import ChatAgent
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

    agent = ChatAgent(
        name="HelpdeskRouter",
        chat_client=chat_client,
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
