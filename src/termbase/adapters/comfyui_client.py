from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from time import sleep, time
from typing import Any
from uuid import uuid4

import httpx

from termbase.errors import ImageGenerationError
from termbase.models import GeneratedImageAsset, ImagePrompt


def populate_workflow_template(template: dict[str, Any], replacements: dict[str, object]) -> dict[str, Any]:
    def _replace(value: Any) -> Any:
        if isinstance(value, dict):
            return {key: _replace(inner_value) for key, inner_value in value.items()}
        if isinstance(value, list):
            return [_replace(inner_value) for inner_value in value]
        if isinstance(value, str):
            if value in replacements:
                return replacements[value]
            result = value
            for placeholder, replacement in replacements.items():
                if isinstance(replacement, (str, int, float)):
                    result = result.replace(placeholder, str(replacement))
            return result
        return value

    return _replace(deepcopy(template))


class ComfyUIClient:
    def __init__(self, base_url: str, timeout_sec: float = 600.0, poll_interval_sec: float = 2.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_sec = timeout_sec
        self.poll_interval_sec = poll_interval_sec

    def generate_image(
        self,
        workflow_template: dict[str, Any],
        image_prompt: ImagePrompt,
        output_path: Path,
        checkpoint_name: str,
        steps: int,
        cfg_scale: float,
    ) -> GeneratedImageAsset:
        replacements = {
            "__CHECKPOINT_NAME__": checkpoint_name,
            "__POSITIVE_PROMPT__": image_prompt.positive_prompt,
            "__NEGATIVE_PROMPT__": image_prompt.negative_prompt,
            "__WIDTH__": image_prompt.width,
            "__HEIGHT__": image_prompt.height,
            "__SEED__": image_prompt.seed,
            "__STEPS__": steps,
            "__CFG_SCALE__": cfg_scale,
            "__FILENAME_PREFIX__": image_prompt.filename_prefix,
            "__SCENE_TITLE__": image_prompt.title,
        }
        workflow = populate_workflow_template(workflow_template, replacements)
        prompt_id = self._queue_prompt(workflow)
        image_descriptor = self._wait_for_image(prompt_id)
        self._download_image(image_descriptor, output_path)
        return GeneratedImageAsset(
            scene_id=image_prompt.scene_id,
            title=image_prompt.title,
            prompt_id=prompt_id,
            filename_prefix=image_prompt.filename_prefix,
            local_path=output_path,
            reference_image_paths=[image_prompt.reference_image_path, image_prompt.supporting_reference_image_path],
            positive_prompt=image_prompt.positive_prompt,
            negative_prompt=image_prompt.negative_prompt,
            seed=image_prompt.seed,
            width=image_prompt.width,
            height=image_prompt.height,
            remote_filename=image_descriptor["filename"],
            remote_subfolder=image_descriptor.get("subfolder", ""),
            remote_type=image_descriptor.get("type", "output"),
        )

    def _queue_prompt(self, workflow: dict[str, Any]) -> str:
        payload = {"prompt": workflow, "client_id": f"termbase-{uuid4()}"}
        try:
            with httpx.Client(timeout=self.timeout_sec) as client:
                response = client.post(f"{self.base_url}/prompt", json=payload)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ImageGenerationError(f"ComfyUI prompt request failed: {exc}") from exc

        try:
            prompt_id = response.json()["prompt_id"]
        except (KeyError, TypeError, ValueError) as exc:
            raise ImageGenerationError("ComfyUI response did not contain prompt_id") from exc
        return prompt_id

    def _wait_for_image(self, prompt_id: str) -> dict[str, str]:
        deadline = time() + self.timeout_sec
        while time() < deadline:
            history = self._get_history(prompt_id)
            if prompt_id in history:
                outputs = history[prompt_id].get("outputs", {})
                image_descriptor = self._extract_first_image(outputs)
                if image_descriptor is not None:
                    return image_descriptor
            sleep(self.poll_interval_sec)
        raise ImageGenerationError(f"ComfyUI image generation timed out for prompt_id={prompt_id}")

    def _get_history(self, prompt_id: str) -> dict[str, Any]:
        try:
            with httpx.Client(timeout=self.timeout_sec) as client:
                response = client.get(f"{self.base_url}/history/{prompt_id}")
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as exc:
            raise ImageGenerationError(f"ComfyUI history request failed: {exc}") from exc

    def _extract_first_image(self, outputs: dict[str, Any]) -> dict[str, str] | None:
        for node_output in outputs.values():
            images = node_output.get("images")
            if images:
                first = images[0]
                return {
                    "filename": first["filename"],
                    "subfolder": first.get("subfolder", ""),
                    "type": first.get("type", "output"),
                }
        return None

    def _download_image(self, image_descriptor: dict[str, str], output_path: Path) -> None:
        params = {
            "filename": image_descriptor["filename"],
            "subfolder": image_descriptor.get("subfolder", ""),
            "type": image_descriptor.get("type", "output"),
        }
        try:
            with httpx.Client(timeout=self.timeout_sec) as client:
                response = client.get(f"{self.base_url}/view", params=params)
                response.raise_for_status()
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(response.content)
        except (httpx.HTTPError, OSError) as exc:
            raise ImageGenerationError(f"ComfyUI image download failed: {exc}") from exc