import base64

import httpx
import pytest

from termbase.adapters.gemini_image import GeminiImageClient


def test_generate_image_posts_reference_images_and_extracts_inline_image(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = GeminiImageClient(
        base_url="https://generativelanguage.googleapis.com/v1beta",
        model="gemini-3.1-flash-image-preview",
    )
    teacher = tmp_path / "teacher.png"
    student = tmp_path / "student.png"
    teacher.write_bytes(b"teacher-bytes")
    student.write_bytes(b"student-bytes")

    captured: dict[str, object] = {}

    class DummyClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def post(self, url, params=None, headers=None, json=None):
            captured["url"] = url
            captured["params"] = params
            captured["headers"] = headers
            captured["json"] = json
            request = httpx.Request("POST", url)
            return httpx.Response(
                200,
                json={
                    "responseId": "gemini-response-1",
                    "candidates": [
                        {
                            "content": {
                                "parts": [
                                    {
                                        "inlineData": {
                                            "mimeType": "image/png",
                                            "data": "aGVsbG8=",
                                        }
                                    }
                                ]
                            }
                        }
                    ],
                },
                request=request,
            )

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(httpx, "Client", DummyClient)

    result = client.generate_image(
        prompt="draw this scene",
        reference_image_paths=[teacher, student],
        aspect_ratio="9:16",
        image_size="1K",
        seed=123,
    )

    assert result == {
        "b64_json": "aGVsbG8=",
        "mime_type": "image/png",
        "response_id": "gemini-response-1",
    }
    assert captured["url"] == "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image-preview:generateContent"
    assert captured["params"] == {"key": "test-key"}
    payload = captured["json"]
    assert payload["generationConfig"]["responseModalities"] == ["IMAGE"]
    assert payload["generationConfig"]["imageConfig"] == {"aspectRatio": "9:16", "imageSize": "1K"}
    parts = payload["contents"][0]["parts"]
    assert parts[0] == {"text": "draw this scene"}
    assert parts[1]["inlineData"]["data"] == base64.b64encode(b"teacher-bytes").decode("ascii")
    assert parts[2]["inlineData"]["data"] == base64.b64encode(b"student-bytes").decode("ascii")