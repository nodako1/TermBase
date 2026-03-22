from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from pydantic import ValidationError

from termbase.errors import ConfigValidationError
from termbase.models import AppConfig


EXTERNAL_STORAGE_ROOT = Path("/Volumes/T7Shield/koichi-home")


def _normalize_legacy_fields(data: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(data)
    if "opening_template" not in normalized and "catchphrase" in normalized:
        normalized["opening_template"] = normalized["catchphrase"]
    if "catchphrase" in normalized:
        normalized.pop("catchphrase")
    return normalized


def load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError as exc:
        raise ConfigValidationError(f"config file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigValidationError(f"invalid JSON in config file: {path}: {exc}") from exc


def validate_against_schema(data: dict[str, Any], schema_path: Path) -> None:
    schema = load_json(schema_path)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda error: list(error.path))
    if not errors:
        return

    messages = []
    for error in errors:
        json_path = ".".join(str(part) for part in error.path) or "$"
        messages.append(f"{json_path}: {error.message}")
    joined = "\n".join(messages)
    raise ConfigValidationError(f"config schema validation failed:\n{joined}")


def _resolve_config_path(path_value: Path, config_path: Path) -> Path:
    expanded = path_value.expanduser()
    if expanded.is_absolute():
        return expanded.resolve(strict=False)
    return (config_path.parent / expanded).resolve(strict=False)


def load_config(config_path: Path, schema_path: Path) -> AppConfig:
    config_path = config_path.expanduser().resolve(strict=False)
    raw_data = _normalize_legacy_fields(load_json(config_path))
    validate_against_schema(raw_data, schema_path)
    try:
        config = AppConfig.model_validate(raw_data)
    except ValidationError as exc:
        raise ConfigValidationError(str(exc)) from exc

    if config.scene_count < 10 or config.scene_count > 15:
        raise ConfigValidationError("scene_count must be between 10 and 15")

    min_duration = config.scene_count * 5
    if config.target_duration_sec < min_duration:
        raise ConfigValidationError(
            f"target_duration_sec is too short for scene_count; minimum recommended is {min_duration}"
        )

    config.character_reference_root_dir = _resolve_config_path(config.character_reference_root_dir, config_path)
    if config.image_workflow_path:
        config.image_workflow_path = _resolve_config_path(config.image_workflow_path, config_path)
        if not config.image_workflow_path.exists():
            raise ConfigValidationError(f"image_workflow_path not found: {config.image_workflow_path}")
    if config.voice_backend == "google-cloud-tts" and not config.google_application_credentials_path:
        raise ConfigValidationError("google_application_credentials_path is required for google-cloud-tts")
    if config.google_application_credentials_path:
        config.google_application_credentials_path = _resolve_config_path(
            config.google_application_credentials_path,
            config_path,
        )
        if config.voice_backend == "google-cloud-tts" and not config.google_application_credentials_path.exists():
            raise ConfigValidationError(
                f"google_application_credentials_path not found: {config.google_application_credentials_path}"
            )
    if config.overlay_font_path:
        config.overlay_font_path = _resolve_config_path(config.overlay_font_path, config_path)
        if not config.overlay_font_path.exists():
            raise ConfigValidationError(f"overlay_font_path not found: {config.overlay_font_path}")

    resolved_output_dir = config.output_dir.expanduser().resolve(strict=False)
    resolved_storage_root = EXTERNAL_STORAGE_ROOT.expanduser().resolve(strict=False)
    if not resolved_output_dir.is_absolute():
        raise ConfigValidationError("output_dir must be an absolute path")
    if resolved_output_dir != resolved_storage_root and resolved_storage_root not in resolved_output_dir.parents:
        raise ConfigValidationError(
            f"output_dir must be under external storage root: {resolved_storage_root}"
        )
    config.output_dir = resolved_output_dir

    return config
