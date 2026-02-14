import os
import sys
import requests
from typing import Optional

def call_llm(system_prompt: str, user_prompt: str, model_name: str) -> Optional[str]:
    """
    Call an OpenAI-compatible LLM API.
    Returns the response content or None if API key is missing or error occurs.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    # Default to OpenRouter if model looks like one (has slash), or OpenAI otherwise.
    base_url = "https://api.openai.com/v1"
    if "openrouter" in model_name or "/" in model_name:
        base_url = "https://openrouter.ai/api/v1"

    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.7
    }

    try:
        response = requests.post(f"{base_url}/chat/completions", headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        result = response.json()
        return result['choices'][0]['message']['content']
    except Exception as e:
        print(f"Error calling LLM: {e}", file=sys.stderr)
        return None
