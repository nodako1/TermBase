from pathlib import Path

from termbase.services.character_reference_manager import validate_character_references
from termbase.services.scenario_engine import (
    _build_repair_prompt,
    _build_system_prompt,
    _build_user_prompt,
    _validate_storyboard_quality,
    build_storyboard_messages,
)
from termbase.testsupport import load_storyboard_fixture, load_test_config


def test_prompts_include_stability_constraints() -> None:
    config = load_test_config("config/project.json")
    references = validate_character_references(Path("assets/character_refs"))

    system_prompt = _build_system_prompt(config)
    user_prompt = _build_user_prompt(config, references)

    assert "JSON only" in system_prompt
    assert "opening hook, problem awareness, intuitive metaphor, step-by-step explanation, recap" in system_prompt
    assert "reliable Japanese female senior colleague or manager" in system_prompt
    assert "Student must appear as speaker in at least 3 scenes" in user_prompt
    assert "Total duration should be close" in user_prompt
    assert "Do not include any extra top-level keys" in user_prompt
    assert "speech_bubble_text is separate from narration" in user_prompt
    assert "opening_template" in user_prompt
    assert "ending_template" in user_prompt
    assert "The first 1 to 2 scenes must be a concise adaptation of the opening_template" in user_prompt
    assert "The final 1 to 2 scenes must be a concise adaptation of the ending_template" in user_prompt


def test_storyboard_quality_validation_accepts_stable_fixture() -> None:
    config = load_test_config("config/project.json")
    storyboard = load_storyboard_fixture()
    config.term = storyboard.term

    _validate_storyboard_quality(config, storyboard)


def test_repair_prompt_mentions_validation_failure_and_metaphor() -> None:
    config = load_test_config("config/project.json")
    repair_prompt = _build_repair_prompt(
        config,
        previous_payload={"summary": "x", "scenes": []},
        validation_error="storyboard must contain at least one explicit everyday metaphor cue",
    )

    assert "validation_error" in repair_prompt
    assert "たとえば" in repair_prompt
    assert "ending_template" in repair_prompt


def test_build_storyboard_messages_returns_system_and_user_messages() -> None:
    config = load_test_config("config/project.json")
    references = validate_character_references(Path("assets/character_refs"))

    messages = build_storyboard_messages(config, references)

    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert "Generate a storyboard" in messages[1]["content"]
