from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4
import base64

from termbase.adapters.comfyui_client import ComfyUIClient
from termbase.adapters.gemini_image import GeminiImageClient
from termbase.adapters.imagen_client import ImagenClient
from termbase.errors import ImageGenerationError
from termbase.adapters.openai_llm import OpenAIClient
from termbase.errors import ConfigValidationError
from termbase.models import AppConfig, GeneratedImageAsset, ImagePrompt


def _load_workflow_template(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _normalize_openai_image_size(width: int, height: int) -> tuple[int, int]:
    if height > width:
        return (1024, 1536)
    if width > height:
        return (1536, 1024)
    return (1024, 1024)


def _normalize_gemini_image_config(width: int, height: int) -> tuple[str, str, tuple[int, int]]:
    if height == width:
        aspect_ratio = "1:1"
        dimensions_by_size = {
            "512": (512, 512),
            "1K": (1024, 1024),
            "2K": (2048, 2048),
            "4K": (4096, 4096),
        }
    elif height > width:
        aspect_ratio = "9:16"
        dimensions_by_size = {
            "512": (384, 688),
            "1K": (768, 1376),
            "2K": (1536, 2752),
            "4K": (3072, 5504),
        }
    else:
        aspect_ratio = "16:9"
        dimensions_by_size = {
            "512": (688, 384),
            "1K": (1376, 768),
            "2K": (2752, 1536),
            "4K": (5504, 3072),
        }

    longest_edge = max(width, height)
    if longest_edge <= 768:
        image_size = "512"
    elif longest_edge <= 1536:
        image_size = "1K"
    elif longest_edge <= 3072:
        image_size = "2K"
    else:
        image_size = "4K"
    return aspect_ratio, image_size, dimensions_by_size[image_size]


def _normalize_gemini_seed(seed: int) -> int:
    return seed % 2147483647


def _generate_images_via_gemini(
    config: AppConfig,
    image_prompts: list[ImagePrompt],
    run_directory: Path,
) -> list[GeneratedImageAsset]:
    images_directory = run_directory / "images"
    client = GeminiImageClient(
        base_url=config.gemini_base_url,
        model=config.gemini_image_model,
        timeout_sec=600.0,
    )
    assets: list[GeneratedImageAsset] = []
    for image_prompt in image_prompts:
        aspect_ratio, image_size, normalized_dimensions = _normalize_gemini_image_config(
            image_prompt.width,
            image_prompt.height,
        )
        normalized_seed = _normalize_gemini_seed(image_prompt.seed)
        output_path = images_directory / f"{image_prompt.filename_prefix}.png"
        reference_image_paths = [image_prompt.reference_image_path, image_prompt.supporting_reference_image_path]
        generated = client.generate_image(
            prompt=image_prompt.positive_prompt,
            reference_image_paths=reference_image_paths,
            aspect_ratio=aspect_ratio,
            image_size=image_size,
            seed=normalized_seed,
        )
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(base64.b64decode(generated["b64_json"]))
        except (OSError, ValueError) as exc:
            raise ImageGenerationError(f"failed to write Gemini image output: {exc}") from exc

        assets.append(
            GeneratedImageAsset(
                scene_id=image_prompt.scene_id,
                title=image_prompt.title,
                prompt_id=generated["response_id"] or f"gemini-{uuid4()}",
                filename_prefix=image_prompt.filename_prefix,
                local_path=output_path,
                reference_image_paths=reference_image_paths,
                positive_prompt=image_prompt.positive_prompt,
                negative_prompt=image_prompt.negative_prompt,
                seed=normalized_seed,
                width=normalized_dimensions[0],
                height=normalized_dimensions[1],
                remote_filename=output_path.name,
                remote_type="gemini",
            )
        )
    return assets


def _generate_images_via_imagen(
    config: AppConfig,
    image_prompts: list[ImagePrompt],
    run_directory: Path,
) -> list[GeneratedImageAsset]:
    images_directory = run_directory / "images"
    client = ImagenClient(model=config.imagen_model)
    assets: list[GeneratedImageAsset] = []

    for image_prompt in image_prompts:
        aspect_ratio, image_size, normalized_dimensions = _normalize_gemini_image_config(
            image_prompt.width,
            image_prompt.height,
        )
        output_path = images_directory / f"{image_prompt.filename_prefix}.png"
        client.generate_image(
            prompt=image_prompt.positive_prompt,
            negative_prompt=image_prompt.negative_prompt,
            output_path=output_path,
            aspect_ratio=aspect_ratio,
            image_size=image_size,
        )
        assets.append(
            GeneratedImageAsset(
                scene_id=image_prompt.scene_id,
                title=image_prompt.title,
                prompt_id=f"imagen-{uuid4()}",
                filename_prefix=image_prompt.filename_prefix,
                local_path=output_path,
                reference_image_paths=[],
                positive_prompt=image_prompt.positive_prompt,
                negative_prompt=image_prompt.negative_prompt,
                seed=image_prompt.seed,
                width=normalized_dimensions[0],
                height=normalized_dimensions[1],
                remote_filename=output_path.name,
                remote_type="imagen",
            )
        )
    return assets


def _generate_images_via_openai(
    config: AppConfig,
    image_prompts: list[ImagePrompt],
    run_directory: Path,
) -> list[GeneratedImageAsset]:
    images_directory = run_directory / "images"
    client = OpenAIClient(
        base_url=config.openai_base_url,
        model=config.openai_image_model,
        temperature=config.llm_temperature,
        timeout_sec=600.0,
    )
    assets: list[GeneratedImageAsset] = []
    for image_prompt in image_prompts:
        width, height = _normalize_openai_image_size(image_prompt.width, image_prompt.height)
        output_path = images_directory / f"{image_prompt.filename_prefix}.png"
        reference_image_paths = [image_prompt.reference_image_path, image_prompt.supporting_reference_image_path]
        generated = client.generate_image(
            prompt=image_prompt.positive_prompt,
            negative_prompt=image_prompt.negative_prompt,
            width=width,
            height=height,
            reference_image_paths=reference_image_paths,
        )
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(base64.b64decode(generated["b64_json"]))
        except (OSError, ValueError) as exc:
            raise ImageGenerationError(f"failed to write OpenAI image output: {exc}") from exc

        assets.append(
            GeneratedImageAsset(
                scene_id=image_prompt.scene_id,
                title=image_prompt.title,
                prompt_id=f"openai-{uuid4()}",
                filename_prefix=image_prompt.filename_prefix,
                local_path=output_path,
                reference_image_paths=reference_image_paths,
                positive_prompt=image_prompt.positive_prompt,
                negative_prompt=image_prompt.negative_prompt,
                seed=image_prompt.seed,
                width=width,
                height=height,
                remote_filename=output_path.name,
                remote_type="openai",
            )
        )
    return assets


def generate_images(config: AppConfig, image_prompts: list[ImagePrompt], run_directory: Path) -> list[GeneratedImageAsset]:
    if config.image_backend == "openai":
        return _generate_images_via_openai(config, image_prompts, run_directory)

    if config.image_backend == "gemini":
        return _generate_images_via_gemini(config, image_prompts, run_directory)

    if config.image_backend == "imagen":
        return _generate_images_via_imagen(config, image_prompts, run_directory)

    if not config.image_workflow_path:
        raise ConfigValidationError("image_workflow_path is required for image generation")

    workflow_template = _load_workflow_template(config.image_workflow_path)
    client = ComfyUIClient(
        base_url=config.comfyui_base_url,
        timeout_sec=config.comfyui_timeout_sec,
        poll_interval_sec=config.comfyui_poll_interval_sec,
    )

    images_directory = run_directory / "images"
    assets: list[GeneratedImageAsset] = []
    for image_prompt in image_prompts:
        output_path = images_directory / f"{image_prompt.filename_prefix}.png"
        asset = client.generate_image(
            workflow_template=workflow_template,
            image_prompt=image_prompt,
            output_path=output_path,
            checkpoint_name=config.comfyui_checkpoint_name,
            steps=config.comfyui_steps,
            cfg_scale=config.comfyui_cfg_scale,
        )
        assets.append(asset)
    return assets