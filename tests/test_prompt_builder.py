from pathlib import Path

from termbase.services.character_reference_manager import validate_character_references
from termbase.services.prompt_builder import PROMPT_STRATEGY_VERSION, build_image_prompts
from termbase.services.scenario_engine import _validate_storyboard_quality
from termbase.testsupport import load_storyboard_fixture, load_test_config


def test_build_image_prompts_creates_one_prompt_per_scene() -> None:
    config = load_test_config("config/project.json")
    config.image_prompt_use_llm = False
    references = validate_character_references(Path("assets/character_refs"))
    storyboard = load_storyboard_fixture()
    config.term = storyboard.term

    _validate_storyboard_quality(config, storyboard)
    prompts = build_image_prompts(config, storyboard, references)

    assert len(prompts) == len(storyboard.scenes)
    assert prompts[0].reference_image_path.is_absolute()
    assert prompts[0].supporting_reference_image_path.is_absolute()
    assert prompts[0].seed >= 0
    assert prompts[0].width == 832
    assert prompts[0].height == 1216
    assert prompts[0].speech_bubble.text
    assert prompts[0].speech_bubble.placement == "top-right"
    assert prompts[0].speech_bubble.text == storyboard.scenes[0].speech_bubble_text
    assert prompts[0].overlay_layout_notes
    assert prompts[1].graph_overlay is not None
    assert PROMPT_STRATEGY_VERSION in prompts[0].positive_prompt
    assert "exact identity anchor" in prompts[0].positive_prompt
    assert "Primary student design profile" in prompts[0].positive_prompt
    assert config.character_design_profiles.student in prompts[0].positive_prompt
    assert "Speech bubble rendering instruction" in prompts[0].positive_prompt
    assert "Bubble text must be exactly" in prompts[0].positive_prompt
    assert "Graph rendering instruction" in prompts[0].positive_prompt
    assert "In-image layout notes" in prompts[0].positive_prompt
    assert str(prompts[0].reference_image_path) not in prompts[0].positive_prompt
    assert "unreadable text" in prompts[0].negative_prompt
    assert "speech bubble, text bubble" not in prompts[0].negative_prompt
