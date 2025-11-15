# app/services/ai.py
import os
from dotenv import load_dotenv
import requests

load_dotenv()

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")


def enrich_helpdesk_entity(entity: dict) -> dict:
    """
    Returns a dict with nicer title/summary/urgency.
    If AI is not configured, it just falls back to the original.
    """
    base_result = {
        "title": entity.get("Title", "New request"),
        "summary": entity.get("Description", ""),
        "urgency": entity.get("Priority", "Normal"),
    }

    # no AI config? just return
    if not (AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_KEY and AZURE_OPENAI_DEPLOYMENT):
        return base_result

    prompt = (
        "You are helping an internal helpdesk. "
        "Given the following ticket fields, produce a short JSON with keys: title, summary, urgency.\n\n"
        f"Title: {entity.get('Title')}\n"
        f"Description: {entity.get('Description')}\n"
        f"Category: {entity.get('PartitionKey')}\n"
        f"Priority: {entity.get('Priority')}\n"
        f"ActionHint: {entity.get('ActionHint')}\n"
        "Return concise summary (max 40 words). Urgency should be Low, Normal, or High."
    )

    # Azure OpenAI chat completions style (2024-ish schema)
    url = f"{AZURE_OPENAI_ENDPOINT}openai/deployments/{AZURE_OPENAI_DEPLOYMENT}/chat/completions?api-version=2024-02-15-preview"
    headers = {
        "Content-Type": "application/json",
        "api-key": AZURE_OPENAI_KEY,
    }
    payload = {
        "messages": [
            {"role": "system", "content": "You strictly output JSON."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        # # content is expected to be JSON text
        import json
        # parsed = json.loads(content)
        # # merge over base_result
        # base_result.update(parsed)
        # Some models wrap JSON in ```json ... ``` – strip that if present
        text = content.strip()
        if text.startswith("```"):
            # remove ```json or ``` and trailing ```
            text = text.strip("`")
            # if there's a language tag like 'json\n', drop the first line
            if "\n" in text:
                lines = text.split("\n", 1)
                if lines[0].lower().startswith("json"):
                    text = lines[1]

        # Try to locate a JSON object in the text
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            json_str = text[start : end + 1]
        else:
            json_str = text  # best effort

        parsed = json.loads(json_str)
        base_result.update(parsed)
        
        
    except Exception as ex:
        # if AI fails, just return base
        print("AI enrichment failed:", ex)

    return base_result
