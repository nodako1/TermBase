from __future__ import annotations

import json
import os
from typing import Sequence

import httpx

from termbase.errors import GeminiRequestError


class GeminiTextClient:
    def __init__(self, base_url: str, model: str, temperature: float = 0.3, timeout_sec: float = 120.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.timeout_sec = timeout_sec

    def _build_http_error_message(self, exc: httpx.HTTPError) -> str:
        response = getattr(exc, "response", None)
        if response is None:
            return f"Gemini request failed: {exc}"

        status = f"{response.status_code} {response.reason_phrase}".strip()
        detail: str | None = None
        try:
            payload = response.json()
            error = payload.get("error") if isinstance(payload, dict) else None
            if isinstance(error, dict):
                message = error.get("message")
                if isinstance(message, str) and message.strip():
                    detail = message.strip()
        except (ValueError, TypeError, json.JSONDecodeError):
            detail = None

        if detail:
            return f"Gemini request failed: {status} - {detail}"

        body = response.text.strip()
        if body:
            return f"Gemini request failed: {status} - {body[:500]}"
        return f"Gemini request failed: {status}"

    def _extract_system_instruction(self, messages: Sequence[dict[str, str]]) -> str | None:
        system_parts = [message["content"] for message in messages if message["role"] == "system"]
        if not system_parts:
            return None
        return "\n\n".join(system_parts)

    def _build_contents(self, messages: Sequence[dict[str, str]]) -> list[dict[str, object]]:
        contents: list[dict[str, object]] = []
        for message in messages:
            if message["role"] == "system":
                continue
            role = "model" if message["role"] == "assistant" else "user"
            contents.append(
                {
                    "role": role,
                    "parts": [{"text": message["content"]}],
                }
            )
        return contents

    def _extract_response_text(self, payload: dict) -> str:
        candidates = payload.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            raise GeminiRequestError("Gemini response did not contain candidates")
        content = candidates[0].get("content")
        if not isinstance(content, dict):
            raise GeminiRequestError("Gemini response did not contain content")
        parts = content.get("parts")
        if not isinstance(parts, list) or not parts:
            raise GeminiRequestError("Gemini response did not contain text parts")
        text_segments = [part.get("text", "") for part in parts if isinstance(part, dict)]
        text = "".join(segment for segment in text_segments if isinstance(segment, str)).strip()
        if not text:
            prompt_feedback = payload.get("promptFeedback")
            if isinstance(prompt_feedback, dict):
                block_reason = prompt_feedback.get("blockReasonMessage") or prompt_feedback.get("blockReason")
                if block_reason:
                    raise GeminiRequestError(f"Gemini blocked the request: {block_reason}")
            raise GeminiRequestError("Gemini response did not contain JSON text")
        return text

    def generate_json(self, system_prompt: str, user_prompt: str, response_json_schema: dict | None = None) -> dict:
        return self.generate_json_from_messages(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_json_schema=response_json_schema,
        )

    def generate_json_from_messages(
        self,
        messages: Sequence[dict[str, str]],
        response_json_schema: dict | None = None,
    ) -> dict:
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise GeminiRequestError("GEMINI_API_KEY or GOOGLE_API_KEY is not set")

        payload: dict[str, object] = {
            "contents": self._build_contents(messages),
            "generationConfig": {
                "temperature": self.temperature,
                "responseMimeType": "application/json",
            },
        }
        system_instruction = self._extract_system_instruction(messages)
        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}],
            }
        if response_json_schema is not None:
            payload["generationConfig"]["responseJsonSchema"] = response_json_schema

        try:
            with httpx.Client(timeout=self.timeout_sec) as client:
                response = client.post(
                    f"{self.base_url}/models/{self.model}:generateContent",
                    params={"key": api_key},
                    headers={"Content-Type": "application/json"},
                    content=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise GeminiRequestError(self._build_http_error_message(exc)) from exc

        response_payload = response.json()
        if isinstance(response_payload.get("parsed"), dict):
            return response_payload["parsed"]

        try:
            return json.loads(self._extract_response_text(response_payload))
        except json.JSONDecodeError as exc:
            raise GeminiRequestError("Gemini response was not valid JSON") from exc