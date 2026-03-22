from pathlib import Path

from PIL import Image

from termbase.services.overlay_compositor import compose_overlays
from termbase.testsupport import load_storyboard_fixture, load_test_config
from termbase.services.prompt_builder import build_image_prompts
from termbase.services.character_reference_manager import validate_character_references


def test_compose_overlays_creates_composited_pngs(tmp_path: Path) -> None:
    config = load_test_config("config/project.sample.json")
    references = validate_character_references(config.character_reference_root_dir)
    storyboard = load_storyboard_fixture()
    image_prompts = build_image_prompts(config, storyboard, references)

    run_directory = tmp_path / "run_20260321_000000"
    images_directory = run_directory / "images"
    images_directory.mkdir(parents=True)

    for prompt in image_prompts:
        Image.new("RGBA", (832, 1216), (240, 240, 240, 255)).save(images_directory / f"{prompt.filename_prefix}.png")

    assets = compose_overlays(config, image_prompts, run_directory)

    assert len(assets) == len(image_prompts)
    assert assets[0].output_path.exists()
    assert assets[0].speech_bubble_text