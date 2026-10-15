"""Shared LLM helper for systems 02 and 03.

Works with any provider LiteLLM supports (Gemini, Groq, ...). Pick the model in .env:
    LLM_MODEL=gemini/gemini-3.8-flash      (needs GEMINI_API_KEY)
    LLM_MODEL=groq/llama-3.3-70b-versatile (needs GROQ_API_KEY)

Includes retry-with-backoff (the guide's fix for 429/503 errors).
"""
import json
import os
import re
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

import litellm  # noqa: E402  (after load_dotenv so keys are available)


def model_name() -> str:
    return os.getenv("LLM_MODEL", "gemini/gemini-3.8-flash")


def chat(system: str, user: str, retries: int = 5, temperature: float = 0.2) -> str:
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    for attempt in range(retries):
        try:
            resp = litellm.completion(
                model=model_name(), messages=messages, temperature=temperature
            )
            return resp.choices[0].message.content or ""
        except Exception as e:  # noqa: BLE001
            msg = str(e)
            # A daily quota will not recover in seconds - fail fast with a clear message.
            if "PerDay" in msg or "credit_balance" in msg or "insufficient_quota" in msg:
                raise RuntimeError(
                    "Daily quota / credits exhausted for "
                    f"{model_name()}. Switch LLM_MODEL in .env (e.g. a Groq model) or wait."
                ) from e
            transient = any(
                k in msg
                for k in ("429", "503", "500", "overloaded", "UNAVAILABLE", "timeout", "Timeout")
            )
            if not transient or attempt == retries - 1:
                raise
            wait = 3 * (2**attempt)
            print(f"[llm] transient error, retrying in {wait}s ({attempt + 1}/{retries})")
            time.sleep(wait)
    return ""


def parse_json(text: str) -> dict:
    """Extract the first JSON object from a model reply (handles ```json fences)."""
    text = re.sub(r"```(?:json)?", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON object in model reply: {text[:200]!r}")
    return json.loads(text[start : end + 1])


def chat_json(system: str, user: str, retries: int = 2) -> dict:
    """Ask for JSON and validate it; re-ask once or twice if the reply is malformed."""
    system = system + "\nRespond with ONLY a JSON object, no prose, no code fences."
    last = None
    for _ in range(retries + 1):
        try:
            return parse_json(chat(system, user))
        except (ValueError, json.JSONDecodeError) as e:
            last = e
    raise ValueError(f"Model did not return valid JSON: {last}")
