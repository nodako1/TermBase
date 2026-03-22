from pathlib import Path

import httpx
import pytest

from termbase.adapters.openai_llm import OpenAIClient


def test_build_http_error_message_includes_openai_error_detail() -> None:
    client = OpenAIClient(base_url="https://api.openai.com/v1", model="gpt-image-1")
    request = httpx.Request("POST", "https://api.openai.com/v1/images/generations")
    response = httpx.Response(
        400,
        json={"error": {"message": "Billing hard limit has been reached."}},
        request=request,
    )
    exc = httpx.HTTPStatusError("400 Bad Request", request=request, response=response)

    message = client._build_http_error_message("OpenAI image request failed", exc)

    assert message == "OpenAI image request failed: 400 Bad Request - Billing hard limit has been reached."


def test_build_http_error_message_falls_back_to_response_text() -> None:
    client = OpenAIClient(base_url="https://api.openai.com/v1", model="gpt-image-1")
    request = httpx.Request("POST", "https://api.openai.com/v1/images/generations")
    response = httpx.Response(500, text="gateway timeout", request=request)
    exc = httpx.HTTPStatusError("500 Internal Server Error", request=request, response=response)

    message = client._build_http_error_message("OpenAI request failed", exc)

    assert message == "OpenAI request failed: 500 Internal Server Error - gateway timeout"


def test_generate_image_uses_edit_endpoint_when_reference_images_are_provided(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = OpenAIClient(base_url="https://api.openai.com/v1", model="gpt-image-1")
    reference = tmp_path / "teacher.png"
    support = tmp_path / "student.png"
    reference.write_bytes(b"teacher")
    support.write_bytes(b"student")

    captured: dict[str, object] = {}

    class DummyClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def post(self, url, headers=None, data=None, files=None, json=None):
            captured["url"] = url
            captured["headers"] = headers
            captured["data"] = data
            captured["files"] = files
            captured["json"] = json
            request = httpx.Request("POST", url)
            return httpx.Response(200, json={"data": [{"b64_json": "aGVsbG8="}]}, request=request)

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(httpx, "Client", DummyClient)

    result = client.generate_image(
        prompt="positive prompt",
        negative_prompt="negative prompt",
        width=1024,
        height=1536,
        reference_image_paths=[reference, support],
    )

    assert result["b64_json"] == "aGVsbG8="
    assert captured["url"] == "https://api.openai.com/v1/images/edits"
    assert captured["json"] is None
    assert captured["data"] == {
        "model": "gpt-image-1",
        "prompt": "positive prompt\nAvoid the following in the final image:\nnegative prompt",
        "size": "1024x1536",
    }
    assert [entry[0] for entry in captured["files"]] == ["image[]", "image[]"]


def test_generate_json_retries_without_response_format_on_400(monkeypatch: pytest.MonkeyPatch) -> None:
    client = OpenAIClient(base_url="https://api.openai.com/v1", model="gpt-5.4")
    calls: list[dict[str, object]] = []

    class DummyClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def post(self, url, headers=None, content=None, data=None, files=None, json=None):
            payload = __import__("json").loads(content.decode("utf-8"))
            calls.append(payload)
            request = httpx.Request("POST", url)
            if len(calls) == 1:
                return httpx.Response(
                    400,
                    json={"error": {"message": "We could not parse the JSON body of your request."}},
                    request=request,
                )
            return httpx.Response(
                200,
                json={"choices": [{"message": {"content": '{"summary":"ok","scenes":[]}'}}]},
                request=request,
            )

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(httpx, "Client", DummyClient)

    result = client.generate_json_from_messages(
        messages=[
            {"role": "system", "content": "Return JSON only."},
            {"role": "user", "content": "{}"},
        ]
    )

    assert result["summary"] == "ok"
    assert "response_format" in calls[0]
    assert "response_format" not in calls[1]


def test_write_debug_payload_bundle_creates_full_and_minimized_payloads(tmp_path: Path) -> None:
    client = OpenAIClient(base_url="https://api.openai.com/v1", model="gpt-5.4")

    bundle_dir = client.write_debug_payload_bundle(
        messages=[
            {"role": "system", "content": "Return JSON only."},
            {"role": "user", "content": "A" * 400},
        ],
        output_dir=tmp_path,
    )

    assert (bundle_dir / "storyboard_full_payload.json").exists()
    assert (bundle_dir / "storyboard_minimized_payload.json").exists()
