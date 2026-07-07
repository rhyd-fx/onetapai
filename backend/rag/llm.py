"""OpenRouter LLM client for coaching generation.

OpenRouter exposes an OpenAI-compatible API, so we use the `openai` SDK
pointed at OpenRouter's base URL. Model and key come from config/.env.
"""
from __future__ import annotations

import os
import sys

import openai

# Make the shared `config` module importable regardless of working directory
# (temporary shim until the backend is packaged with __init__.py files).
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import config


def get_llm_client() -> openai.OpenAI:
    """Return an OpenAI SDK client configured for OpenRouter."""
    return openai.OpenAI(
        api_key=config.require("OPENROUTER_API_KEY"),
        base_url=config.OPENROUTER_BASE_URL,
        default_headers={
            "HTTP-Referer": "http://localhost:3000",
            "X-Title": "OneTap AI",
        }
    )


def generate_coaching_response(
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.4,
) -> str:
    """Send chat messages to the OpenRouter model and return the reply text.

    `messages` is the OpenAI-style list of {"role", "content"} dicts, exactly
    as produced by `prompt_builder.build_coaching_prompt`.
    """
    client = get_llm_client()
    response = client.chat.completions.create(
        model=model or config.OPENROUTER_MODEL,
        messages=messages,
        temperature=temperature,
    )
    return response.choices[0].message.content or ""
