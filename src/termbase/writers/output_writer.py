from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

from termbase.errors import OutputWriteError
from termbase.models import (
    AudioGenerationResult,
    AppConfig,
    GeneratedImageAsset,
    GeneratedAudioAsset,
    ImageGenerationResult,
    ImagePrompt,
    OverlayCompositeAsset,
    OverlayCompositeResult,
    ScriptGenerationResult,
    Storyboard,
)


def generate_run_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _cleanup_old_runs(output_dir: Path, keep_count: int = 5) -> None:
    run_directories = sorted(
        [path for path in output_dir.iterdir() if path.is_dir() and path.name.startswith("run_")],
        key=lambda path: path.name,
        reverse=True,
    )
    for obsolete_run in run_directories[keep_count:]:
        shutil.rmtree(obsolete_run)


def write_script_outputs(
    config: AppConfig,
    storyboard: Storyboard,
    image_prompts: list[ImagePrompt],
) -> ScriptGenerationResult:
    run_id = generate_run_id()
    root_dir = config.output_dir / f"run_{run_id}"
    scripts_dir = root_dir / "scripts"
    logs_dir = root_dir / "logs"

    try:
        scripts_dir.mkdir(parents=True, exist_ok=False)
        logs_dir.mkdir(parents=True, exist_ok=False)
    except OSError as exc:
        raise OutputWriteError(f"failed to create output directories: {exc}") from exc

    storyboard_path = scripts_dir / "storyboard.json"
    metadata_path = scripts_dir / "metadata.json"
    image_prompts_path = scripts_dir / "image_prompts.json"
    log_path = logs_dir / "run.log"

    character_root_dir = config.character_reference_root_dir.expanduser().resolve(strict=False)

    metadata = {
        "run_id": run_id,
        "term": config.term,
        "status": "script_generated",
        "models": {
            "llm_provider": config.llm_provider,
            "llm": config.llm_model,
            "llm_temperature": config.llm_temperature,
        },
        "settings": {
            "scene_count": config.scene_count,
            "target_duration_sec": config.target_duration_sec,
            "aspect_ratio": config.image_aspect_ratio,
            "tone": config.tone,
            "output_dir": str(config.output_dir),
            "image_width": config.image_width,
            "image_height": config.image_height,
        },
        "templates": {
            "opening_template": config.opening_template,
            "ending_template": config.ending_template,
        },
        "generation_inputs": {
            "additional_instructions": config.additional_instructions,
            "retry_count": config.retry_count,
        },
        "character_references": {
            "root_directory": str(character_root_dir),
            "roles": {
                "teacher": {"directory": str(character_root_dir / "teacher"), "required_count": 10},
                "student": {"directory": str(character_root_dir / "student"), "required_count": 10},
            },
        },
        "character_design_profiles": config.character_design_profiles.model_dump(),
        "voice_models": config.voice_models.model_dump(),
        "google_tts_voice_tunings": config.google_tts_voice_tunings.model_dump(),
        "google_tts_section_speaking_rates": config.google_tts_section_speaking_rates.model_dump(),
        "image_backend": {
            "provider": config.image_backend,
            "image_prompt_use_llm": config.image_prompt_use_llm,
            "openai_image_model": config.openai_image_model,
            "gemini_base_url": config.gemini_base_url,
            "gemini_image_model": config.gemini_image_model,
            "imagen_model": config.imagen_model,
            "comfyui_base_url": config.comfyui_base_url,
            "checkpoint_name": config.comfyui_checkpoint_name,
            "steps": config.comfyui_steps,
            "cfg_scale": config.comfyui_cfg_scale,
            "workflow_path": str(config.image_workflow_path) if config.image_workflow_path else None,
        },
        "llm_prompt_log": storyboard.llm_prompt_log,
        "image_prompt_artifacts": {
            "file": str(image_prompts_path),
            "count": len(image_prompts),
        },
        "scenes": [scene.model_dump(mode="json") for scene in storyboard.scenes],
    }

    try:
        storyboard_payload = storyboard.model_dump(mode="json")
        image_prompt_payload = [prompt.model_dump(mode="json") for prompt in image_prompts]
        storyboard_path.write_text(json.dumps(storyboard_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        image_prompts_path.write_text(json.dumps(image_prompt_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        log_path.write_text(f"INFO run_id={run_id} phase=script_generation status=success\n", encoding="utf-8")
        _cleanup_old_runs(config.output_dir, keep_count=5)
    except OSError as exc:
        raise OutputWriteError(f"failed to write outputs: {exc}") from exc
    except Exception as exc:
        raise OutputWriteError(f"failed to cleanup old output runs: {exc}") from exc

    return ScriptGenerationResult(
        run_id=run_id,
        run_directory=root_dir,
        storyboard_path=storyboard_path,
        metadata_path=metadata_path,
        image_prompts_path=image_prompts_path,
        storyboard=storyboard,
    )


def write_image_outputs(run_directory: Path, assets: list[GeneratedImageAsset]) -> ImageGenerationResult:
    images_directory = run_directory / "images"
    manifest_path = images_directory / "image_generation.json"
    metadata_path = run_directory / "scripts" / "metadata.json"

    try:
        images_directory.mkdir(parents=True, exist_ok=True)
        payload = [asset.model_dump(mode="json") for asset in assets]
        manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        if metadata_path.exists():
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            metadata["status"] = "image_generated"
            metadata["image_generation"] = {
                "count": len(assets),
                "images_directory": str(images_directory),
                "manifest_path": str(manifest_path),
                "reference_mode": "reference_pngs_sent_to_backend_when_supported",
                "provider": assets[0].remote_type if assets else None,
                "files": [str(asset.local_path) for asset in assets],
            }
            metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as exc:
        raise OutputWriteError(f"failed to write image outputs: {exc}") from exc

    return ImageGenerationResult(
        run_directory=run_directory,
        images_directory=images_directory,
        manifest_path=manifest_path,
        assets=assets,
    )


def load_storyboard_output(storyboard_path: Path) -> Storyboard:
    try:
        payload = json.loads(storyboard_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise OutputWriteError(f"failed to read storyboard output: {exc}") from exc
    return Storyboard.model_validate(payload)


def load_image_prompts_output(image_prompts_path: Path) -> list[ImagePrompt]:
    try:
        payload = json.loads(image_prompts_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise OutputWriteError(f"failed to read image prompt output: {exc}") from exc
    return [ImagePrompt.model_validate(item) for item in payload]


def overwrite_image_prompts(run_directory: Path, image_prompts: list[ImagePrompt]) -> Path:
    image_prompts_path = run_directory / "scripts" / "image_prompts.json"
    metadata_path = run_directory / "scripts" / "metadata.json"

    try:
        payload = [prompt.model_dump(mode="json") for prompt in image_prompts]
        image_prompts_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        if metadata_path.exists():
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            metadata["image_prompt_artifacts"] = {
                "file": str(image_prompts_path),
                "count": len(image_prompts),
            }
            metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as exc:
        raise OutputWriteError(f"failed to overwrite image prompts: {exc}") from exc

    return image_prompts_path


def write_overlay_outputs(run_directory: Path, assets: list[OverlayCompositeAsset]) -> OverlayCompositeResult:
    output_directory = run_directory / "images" / "composited"
    manifest_path = run_directory / "images" / "overlay_composition.json"
    metadata_path = run_directory / "scripts" / "metadata.json"

    try:
        output_directory.mkdir(parents=True, exist_ok=True)
        payload = [asset.model_dump(mode="json") for asset in assets]
        manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        if metadata_path.exists():
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            metadata["overlay_generation"] = {
                "count": len(assets),
                "output_directory": str(output_directory),
                "manifest_path": str(manifest_path),
                "files": [str(asset.output_path) for asset in assets],
            }
            metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as exc:
        raise OutputWriteError(f"failed to write overlay outputs: {exc}") from exc

    return OverlayCompositeResult(
        run_directory=run_directory,
        output_directory=output_directory,
        manifest_path=manifest_path,
        assets=assets,
    )


def write_audio_outputs(run_directory: Path, assets: list[GeneratedAudioAsset]) -> AudioGenerationResult:
    audio_directory = run_directory / "audio"
    manifest_path = audio_directory / "audio_generation.json"
    metadata_path = run_directory / "scripts" / "metadata.json"

    try:
        audio_directory.mkdir(parents=True, exist_ok=True)
        payload = [asset.model_dump(mode="json") for asset in assets]
        manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        if metadata_path.exists():
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            voices_by_role = {asset.speaker_role: asset.voice_name for asset in assets}
            metadata["status"] = "audio_generated"
            metadata["voice_models"] = voices_by_role
            metadata["audio_generation"] = {
                "count": len(assets),
                "audio_directory": str(audio_directory),
                "manifest_path": str(manifest_path),
                "audio_encoding": assets[0].audio_encoding if assets else None,
                "voices_by_role": voices_by_role,
                "files": [str(asset.local_path) for asset in assets],
            }
            metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as exc:
        raise OutputWriteError(f"failed to write audio outputs: {exc}") from exc

    return AudioGenerationResult(
        run_directory=run_directory,
        audio_directory=audio_directory,
        manifest_path=manifest_path,
        assets=assets,
    )
