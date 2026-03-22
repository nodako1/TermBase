from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Sequence

import httpx

from termbase.errors import GeminiRequestError


class GeminiImageClient:
    def __init__(self, base_url: str, model: str, timeout_sec: float = 600.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_sec = timeout_sec

    def generate_image(
        self,
        prompt: str,
        reference_image_paths: Sequence[Path],
        aspect_ratio: str,
        image_size: str,
        seed: int,
    ) -> dict:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise GeminiRequestError("GEMINI_API_KEY is not set")

        contents = [
            {
                "parts": [
                    {"text": prompt},
                    *[self._image_part(path) for path in reference_image_paths],
                ]
            }
        ]
        generation_config: dict[str, object] = {
            "responseModalities": ["IMAGE"],
            "imageConfig": {
                "aspectRatio": aspect_ratio,
                "imageSize": image_size,
            },
        }
        if self._supports_seed():
            generation_config["seed"] = seed
        if self._supports_thinking_config():
            generation_config["thinkingConfig"] = {
                "thinkingLevel": "MINIMAL",
                "includeThoughts": False,
            }

        payload = {
            "contents": contents,
            "generationConfig": generation_config,
        }

        try:
            with httpx.Client(timeout=self.timeout_sec) as client:
                response = client.post(
                    f"{self.base_url}/models/{self.model}:generateContent",
                    params={"key": api_key},
                    headers={"Content-Type": "application/json"},
                    json=payload,
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise GeminiRequestError(self._build_http_error_message(exc)) from exc

        data = response.json()
        image_part = self._extract_image_part(data)
        return {
            "b64_json": image_part["inlineData"]["data"],
            "mime_type": image_part["inlineData"].get("mimeType", "image/png"),
            "response_id": data.get("responseId", ""),
        }

    def _image_part(self, path: Path) -> dict:
        try:
            encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        except OSError as exc:
            raise GeminiRequestError(f"failed to read reference image: {exc}") from exc
        return {
            "inlineData": {
                "mimeType": "image/png",
                "data": encoded,
            }
        }

    def _supports_seed(self) -> bool:
        return self.model == "gemini-3.1-flash-image-preview"

    def _supports_thinking_config(self) -> bool:
        return self.model == "gemini-3.1-flash-image-preview"

    def _extract_image_part(self, payload: dict) -> dict:
        try:
            candidates = payload["candidates"]
            for candidate in candidates:
                parts = candidate["content"]["parts"]
                for part in parts:
                    inline_data = part.get("inlineData")
                    if isinstance(inline_data, dict) and inline_data.get("data"):
                        return part
        except (KeyError, IndexError, TypeError) as exc:
            raise GeminiRequestError("Gemini image response was not valid") from exc

        finish_reason = ""
        finish_message = ""
        try:
            first_candidate = payload.get("candidates", [{}])[0]
            finish_reason = first_candidate.get("finishReason", "")
            finish_message = first_candidate.get("finishMessage", "")
        except (AttributeError, IndexError, TypeError):
            pass
        detail = f"Gemini returned no image output"
        if finish_reason or finish_message:
            detail = f"{detail}: {finish_reason} {finish_message}".strip()
        raise GeminiRequestError(detail)

    def _build_http_error_message(self, exc: httpx.HTTPError) -> str:
        response = getattr(exc, "response", None)
        if response is None:
            return f"Gemini image request failed: {exc}"

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
            return f"Gemini image request failed: {status} - {detail}"

        body = response.text.strip()
        if body:
            return f"Gemini image request failed: {status} - {body[:500]}"
        return f"Gemini image request failed: {status}"