from __future__ import annotations

import os
from pathlib import Path

from termbase.errors import ImagenRequestError


class ImagenClient:
    def __init__(self, model: str) -> None:
        self.model = model

    def generate_image(
        self,
        prompt: str,
        negative_prompt: str,
        output_path: Path,
        aspect_ratio: str,
        image_size: str,
    ) -> None:
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ImagenRequestError("GEMINI_API_KEY or GOOGLE_API_KEY is not set")

        try:
            from google import genai
            from google.genai import errors as genai_errors
            from google.genai import types
        except ImportError as exc:
            raise ImagenRequestError("google-genai is not installed") from exc

        try:
            with genai.Client(api_key=api_key) as client:
                response = client.models.generate_images(
                    model=self.model,
                    prompt=prompt,
                    config=types.GenerateImagesConfig(
                        number_of_images=1,
                        aspect_ratio=aspect_ratio,
                        image_size=image_size,
                        output_mime_type="image/png",
                        language="en",
                        negative_prompt=negative_prompt,
                        enhance_prompt=True,
                    ),
                )
        except genai_errors.APIError as exc:
            raise ImagenRequestError(f"Imagen request failed: {exc.message}") from exc
        except Exception as exc:  # noqa: BLE001
            raise ImagenRequestError(f"Imagen request failed: {exc}") from exc

        generated_images = getattr(response, "generated_images", None)
        if not generated_images:
            raise ImagenRequestError("Imagen response did not contain generated images")

        image = generated_images[0].image
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            image.save(output_path)
        except OSError as exc:
            raise ImagenRequestError(f"failed to write Imagen image output: {exc}") from exc