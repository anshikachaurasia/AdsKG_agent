"""One small function to call an OpenAI model and measure tokens + time.

The API key is read from the .env file in the project folder (OPENAI_API_KEY=...).
"""
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

PROJECT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT / ".env")

_client = None


def get_client():
    global _client
    if _client is None:
        _client = OpenAI()   # reads OPENAI_API_KEY from the environment
    return _client


def ask(model, system, user, reasoning_effort=None):
    """Send one system + user message. Returns (answer_text, usage_dict)."""
    start = time.time()
    extra = {"reasoning_effort": reasoning_effort} if reasoning_effort else {}
    response = get_client().chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        **extra,
    )
    usage = {
        "tokens_in": response.usage.prompt_tokens,
        "tokens_out": response.usage.completion_tokens,
        "llm_seconds": round(time.time() - start, 2),
    }
    return response.choices[0].message.content, usage
