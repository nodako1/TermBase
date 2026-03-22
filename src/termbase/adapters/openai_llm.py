from __future__ import annotations

from contextlib import ExitStack
from datetime import datetime
import json
import os
from pathlib import Path
from typing import Sequence

import httpx

from termbase.errors import OpenAIRequestError


class OpenAIClient:
    def __init__(self, base_url: str, model: str, temperature: float = 0.3, timeout_sec: float = 120.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.timeout_sec = timeout_sec

    def _build_http_error_message(self, prefix: str, exc: httpx.HTTPError) -> str:
        response = getattr(exc, "response", None)
        if response is None:
            return f"{prefix}: {exc}"

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
            return f"{prefix}: {status} - {detail}"

        body = response.text.strip()
        if body:
            return f"{prefix}: {status} - {body[:500]}"

        return f"{prefix}: {status}"

    def _compose_image_instruction(self, prompt: str, negative_prompt: str) -> str:
        return (
            f"{prompt}\n"
            "Avoid the following in the final image:\n"
            f"{negative_prompt}"
        )

    def _serialize_json_payload(self, payload: dict) -> bytes:
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")

    def _build_chat_payload(self, messages: Sequence[dict[str, str]], include_response_format: bool = True) -> dict:
        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "messages": list(messages),
        }
        if include_response_format:
            payload["response_format"] = {"type": "json_object"}
        return payload

    def _build_minimized_messages(self, messages: Sequence[dict[str, str]]) -> list[dict[str, str]]:
        minimized_messages: list[dict[str, str]] = []
        for message in messages:
            content = " ".join(message["content"].split())
            minimized_messages.append(
                {
                    "role": message["role"],
                    "content": content[:240] + ("..." if len(content) > 240 else ""),
                }
            )
        return minimized_messages

    def _request_chat_completion(self, client: httpx.Client, api_key: str, payload: dict) -> httpx.Response:
        return client.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            content=self._serialize_json_payload(payload),
        )

    def _parse_chat_completion_response(self, response: httpx.Response) -> dict:
        try:
            content = response.json()["choices"][0]["message"]["content"]
            return json.loads(content)
        except (KeyError, IndexError, json.JSONDecodeError, TypeError) as exc:
            raise OpenAIRequestError("OpenAI response was not valid JSON") from exc

    def _should_retry_chat_without_response_format(self, exc: httpx.HTTPError) -> bool:
        response = getattr(exc, "response", None)
        if response is None or response.status_code != 400:
            return False
        body = response.text.lower()
        return "parse the json body" in body or "response_format" in body

    def write_debug_payload_bundle(self, messages: Sequence[dict[str, str]], output_dir: Path) -> Path:
        bundle_dir = output_dir / "openai_debug" / datetime.now().strftime("request_%Y%m%d_%H%M%S")
        bundle_dir.mkdir(parents=True, exist_ok=False)

        full_payload = self._build_chat_payload(messages, include_response_format=True)
        minimized_payload = self._build_chat_payload(self._build_minimized_messages(messages), include_response_format=True)

        (bundle_dir / "storyboard_full_payload.json").write_text(
            json.dumps(full_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (bundle_dir / "storyboard_minimized_payload.json").write_text(
            json.dumps(minimized_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return bundle_dir

    def debug_reproduce_json_from_messages(self, messages: Sequence[dict[str, str]], output_dir: Path) -> Path:
        bundle_dir = self.write_debug_payload_bundle(messages, output_dir)
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise OpenAIRequestError("OPENAI_API_KEY is not set")

        attempts = {
            "full": self._build_chat_payload(messages, include_response_format=True),
            "minimal": self._build_chat_payload(self._build_minimized_messages(messages), include_response_format=True),
        }

        with httpx.Client(timeout=self.timeout_sec) as client:
            for label, payload in attempts.items():
                result_path = bundle_dir / f"{label}_result.json"
                try:
                    response = self._request_chat_completion(client, api_key, payload)
                    response.raise_for_status()
                    body = response.json()
                    result = {
                        "ok": True,
                        "status_code": response.status_code,
                        "response_excerpt": json.dumps(body, ensure_ascii=False)[:2000],
                    }
                except httpx.HTTPError as exc:
                    result = {
                        "ok": False,
                        "error": self._build_http_error_message("OpenAI request failed", exc),
                    }
                result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

        return bundle_dir

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
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise OpenAIRequestError("OPENAI_API_KEY is not set")

        try:
            with httpx.Client(timeout=self.timeout_sec) as client:
                payload = self._build_chat_payload(messages, include_response_format=True)
                try:
                    response = self._request_chat_completion(client, api_key, payload)
                    response.raise_for_status()
                except httpx.HTTPError as exc:
                    if not self._should_retry_chat_without_response_format(exc):
                        raise
                    fallback_payload = self._build_chat_payload(messages, include_response_format=False)
                    response = self._request_chat_completion(client, api_key, fallback_payload)
                    response.raise_for_status()
        except httpx.HTTPError as exc:
            raise OpenAIRequestError(self._build_http_error_message("OpenAI request failed", exc)) from exc

        return self._parse_chat_completion_response(response)

    def generate_image(
        self,
        prompt: str,
        negative_prompt: str,
        width: int,
        height: int,
        reference_image_paths: Sequence[Path] | None = None,
    ) -> dict:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise OpenAIRequestError("OPENAI_API_KEY is not set")

        composed_prompt = self._compose_image_instruction(prompt, negative_prompt)

        try:
            with httpx.Client(timeout=self.timeout_sec) as client:
                if reference_image_paths:
                    response = self._post_image_edit(
                        client=client,
                        api_key=api_key,
                        prompt=composed_prompt,
                        width=width,
                        height=height,
                        reference_image_paths=reference_image_paths,
                    )
                else:
                    response = client.post(
                        f"{self.base_url}/images/generations",
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": self.model,
                            "prompt": composed_prompt,
                            "size": f"{width}x{height}",
                        },
                    )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise OpenAIRequestError(self._build_http_error_message("OpenAI image request failed", exc)) from exc

        try:
            return response.json()["data"][0]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise OpenAIRequestError("OpenAI image response was not valid") from exc

    def _post_image_edit(
        self,
        client: httpx.Client,
        api_key: str,
        prompt: str,
        width: int,
        height: int,
        reference_image_paths: Sequence[Path],
    ) -> httpx.Response:
        try:
            with ExitStack() as stack:
                files = []
                for path in reference_image_paths:
                    handle = stack.enter_context(path.open("rb"))
                    files.append(("image[]", (path.name, handle, "image/png")))

                return client.post(
                    f"{self.base_url}/images/edits",
                    headers={"Authorization": f"Bearer {api_key}"},
                    data={
                        "model": self.model,
                        "prompt": prompt,
                        "size": f"{width}x{height}",
                    },
                    files=files,
                )
        except OSError as exc:
            raise OpenAIRequestError(f"failed to open reference image: {exc}") from exc
