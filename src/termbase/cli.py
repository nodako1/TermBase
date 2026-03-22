from __future__ import annotations

from pathlib import Path

import typer

from termbase.adapters.openai_llm import OpenAIClient
from termbase.config import load_config
from termbase.errors import ConfigValidationError, TermBaseError
from termbase.services.audio_generation_engine import generate_audio
from termbase.services.character_reference_manager import validate_character_references
from termbase.services.image_generation_engine import generate_images
from termbase.services.prompt_builder import build_image_prompts
from termbase.services.scenario_engine import build_storyboard_messages, generate_storyboard
from termbase.writers.output_writer import (
    load_image_prompts_output,
    load_storyboard_output,
    overwrite_image_prompts,
    write_audio_outputs,
    write_image_outputs,
    write_script_outputs,
)

app = typer.Typer(add_completion=False, no_args_is_help=True)


def _schema_path() -> Path:
    return Path("config/project.schema.json")


def _handle_error(exc: TermBaseError) -> None:
    typer.secho(str(exc), fg=typer.colors.RED, err=True)
    raise typer.Exit(code=exc.exit_code) from exc


@app.command("validate-config")
def validate_config_command(config: Path = typer.Option(..., exists=True, dir_okay=False, file_okay=True)) -> None:
    try:
        load_config(config, _schema_path())
    except TermBaseError as exc:
        _handle_error(exc)
    typer.echo("config validation passed")


@app.command("validate-assets")
def validate_assets_command(
    character_root: Path = typer.Option(..., exists=True, dir_okay=True, file_okay=False)
) -> None:
    try:
        validate_character_references(character_root)
    except TermBaseError as exc:
        _handle_error(exc)
    typer.echo("asset validation passed")


def _generate(config_path: Path) -> None:
    try:
        config = load_config(config_path, _schema_path())
        references = validate_character_references(config.character_reference_root_dir)
        storyboard = generate_storyboard(config, references)
        image_prompts = build_image_prompts(config, storyboard, references)
        result = write_script_outputs(config, storyboard, image_prompts)
    except TermBaseError as exc:
        _handle_error(exc)

    typer.echo(f"run_id: {result.run_id}")
    typer.echo(f"storyboard: {result.storyboard_path}")
    typer.echo(f"metadata: {result.metadata_path}")
    typer.echo(f"image_prompts: {result.image_prompts_path}")


@app.command("generate")
def generate_command(config: Path = typer.Option(..., exists=True, dir_okay=False, file_okay=True)) -> None:
    _generate(config)


@app.command("generate-script")
def generate_script_command(config: Path = typer.Option(..., exists=True, dir_okay=False, file_okay=True)) -> None:
    _generate(config)


@app.command("generate-images")
def generate_images_command(config: Path = typer.Option(..., exists=True, dir_okay=False, file_okay=True)) -> None:
    try:
        loaded_config = load_config(config, _schema_path())
        references = validate_character_references(loaded_config.character_reference_root_dir)
        storyboard = generate_storyboard(loaded_config, references)
        image_prompts = build_image_prompts(loaded_config, storyboard, references)
        script_result = write_script_outputs(loaded_config, storyboard, image_prompts)
        image_assets = generate_images(loaded_config, image_prompts, script_result.run_directory)
        image_result = write_image_outputs(script_result.run_directory, image_assets)
    except TermBaseError as exc:
        _handle_error(exc)

    typer.echo(f"run_id: {script_result.run_id}")
    typer.echo(f"storyboard: {script_result.storyboard_path}")
    typer.echo(f"image_prompts: {script_result.image_prompts_path}")
    typer.echo(f"images: {image_result.images_directory}")
    typer.echo(f"image_manifest: {image_result.manifest_path}")


@app.command("generate-images-from-run")
def generate_images_from_run_command(
    config: Path = typer.Option(..., exists=True, dir_okay=False, file_okay=True),
    run_dir: Path = typer.Option(..., exists=True, dir_okay=True, file_okay=False),
) -> None:
    try:
        loaded_config = load_config(config, _schema_path())
        references = validate_character_references(loaded_config.character_reference_root_dir)
        storyboard = load_storyboard_output(run_dir / "scripts" / "storyboard.json")
        image_prompts = build_image_prompts(loaded_config, storyboard, references)
        script_result = write_script_outputs(loaded_config, storyboard, image_prompts)
        image_assets = generate_images(loaded_config, image_prompts, script_result.run_directory)
        image_result = write_image_outputs(script_result.run_directory, image_assets)
    except TermBaseError as exc:
        _handle_error(exc)

    typer.echo(f"source_storyboard: {run_dir / 'scripts' / 'storyboard.json'}")
    typer.echo(f"run_id: {script_result.run_id}")
    typer.echo(f"storyboard: {script_result.storyboard_path}")
    typer.echo(f"image_prompts: {script_result.image_prompts_path}")
    typer.echo(f"images: {image_result.images_directory}")
    typer.echo(f"image_manifest: {image_result.manifest_path}")


@app.command("regenerate-image-prompts")
def regenerate_image_prompts_command(
    config: Path = typer.Option(..., exists=True, dir_okay=False, file_okay=True),
    run_dir: Path = typer.Option(..., exists=True, dir_okay=True, file_okay=False),
) -> None:
    try:
        loaded_config = load_config(config, _schema_path())
        references = validate_character_references(loaded_config.character_reference_root_dir)
        storyboard = load_storyboard_output(run_dir / "scripts" / "storyboard.json")
        image_prompts = build_image_prompts(loaded_config, storyboard, references)
        image_prompts_path = overwrite_image_prompts(run_dir, image_prompts)
    except TermBaseError as exc:
        _handle_error(exc)

    typer.echo(f"storyboard: {run_dir / 'scripts' / 'storyboard.json'}")
    typer.echo(f"image_prompts: {image_prompts_path}")


@app.command("generate-audio")
def generate_audio_command(
    config: Path = typer.Option(..., exists=True, dir_okay=False, file_okay=True),
    run_dir: Path = typer.Option(..., exists=True, dir_okay=True, file_okay=False),
) -> None:
    try:
        loaded_config = load_config(config, _schema_path())
        storyboard = load_storyboard_output(run_dir / "scripts" / "storyboard.json")
        assets = generate_audio(loaded_config, storyboard, run_dir)
        result = write_audio_outputs(run_dir, assets)
    except TermBaseError as exc:
        _handle_error(exc)

    typer.echo(f"audio_directory: {result.audio_directory}")
    typer.echo(f"audio_manifest: {result.manifest_path}")


@app.command("debug-openai-storyboard-request")
def debug_openai_storyboard_request_command(
    config: Path = typer.Option(..., exists=True, dir_okay=False, file_okay=True),
) -> None:
    try:
        loaded_config = load_config(config, _schema_path())
        if loaded_config.llm_provider != "openai":
            raise ConfigValidationError("debug-openai-storyboard-request can only be used when llm_provider is openai")
        references = validate_character_references(loaded_config.character_reference_root_dir)
        messages = build_storyboard_messages(loaded_config, references)
        client = OpenAIClient(
            base_url=loaded_config.openai_base_url,
            model=loaded_config.llm_model,
            temperature=loaded_config.llm_temperature,
        )
        bundle_dir = client.debug_reproduce_json_from_messages(messages, loaded_config.output_dir)
    except TermBaseError as exc:
        _handle_error(exc)

    typer.echo(f"debug_bundle: {bundle_dir}")
