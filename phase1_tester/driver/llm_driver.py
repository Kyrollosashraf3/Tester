"""GPT-4o driver for generating buyer persona replies."""

import os
from typing import TYPE_CHECKING
 
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

from phase1_tester.persona.prompts import build_driver_messages

if TYPE_CHECKING:
    from phase1_tester.config.types import Turn


class LLMDriver:
    """Uses OpenAI GPT-4o to generate persona replies."""

    def __init__(self, model: str, api_key_env: str = "OPENAI_API_KEY"):
        self.model = model
        api_key = os.environ.get(api_key_env)
        if not api_key:
            raise ValueError(f"Missing {api_key_env} environment variable")
        self._client = OpenAI(api_key=api_key)

    def generate_reply(
        self,
        persona: dict,
        last_assistant: str,
        recent_turns: list["Turn"],
    ) -> str:
        """Generate the next user (buyer) message given persona and conversation."""
        messages = build_driver_messages(persona, last_assistant, recent_turns)
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=100,
            temperature=0.4,
        )
        content = resp.choices[0].message.content
        return (content or "").strip()
