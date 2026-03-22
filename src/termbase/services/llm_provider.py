from __future__ import annotations

from typing import Protocol, Sequence

from termbase.adapters.gemini_llm import GeminiTextClient
from termbase.adapters.openai_llm import OpenAIClient
from termbase.models import AppConfig


class JsonLLMClient(Protocol):
    def generate_json_from_messages(
        self,
        messages: Sequence[dict[str, str]],
        response_json_schema: dict | None = None,
    ) -> dict: ...


def create_json_llm_client(config: AppConfig) -> JsonLLMClient:
    if config.llm_provider == "gemini":
        return GeminiTextClient(
            base_url=config.gemini_base_url,
            model=config.llm_model,
            temperature=config.llm_temperature,
        )

    return OpenAIClient(
        base_url=config.openai_base_url,
        model=config.llm_model,
        temperature=config.llm_temperature,
    )