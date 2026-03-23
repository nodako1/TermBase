import json
from pathlib import Path

from termbase.models import AppConfig, CharacterDesignProfile, GeneratedImageAsset, Storyboard, VoiceModels
from termbase.writers.output_writer import write_image_outputs, write_script_outputs


def test_write_image_outputs_updates_metadata_status(tmp_path: Path) -> None:
    run_directory = tmp_path / "run_20260321_000000"
    scripts_directory = run_directory / "scripts"
    scripts_directory.mkdir(parents=True)
    metadata_path = scripts_directory / "metadata.json"
    metadata_path.write_text(json.dumps({"status": "script_generated"}), encoding="utf-8")

    asset_path = run_directory / "images" / "scene_01_teacher.png"
    asset = GeneratedImageAsset(
        scene_id=1,
        title="導入",
        prompt_id="openai-1",
        filename_prefix="scene_01_teacher",
        local_path=asset_path,
        reference_image_paths=[Path("/tmp/teacher.png"), Path("/tmp/student.png")],
        positive_prompt="positive",
        negative_prompt="negative",
        seed=1,
        width=1024,
        height=1536,
        remote_filename="scene_01_teacher.png",
        remote_type="openai",
    )

    result = write_image_outputs(run_directory, [asset])

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert result.manifest_path.exists()
    assert metadata["status"] == "image_generated"
    assert metadata["image_generation"]["count"] == 1
    assert metadata["image_generation"]["manifest_path"] == str(result.manifest_path)


def test_write_script_outputs_keeps_latest_five_runs(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True)
    for run_name in [
        "run_20260321_100000",
        "run_20260321_100100",
        "run_20260321_100200",
        "run_20260321_100300",
        "run_20260321_100400",
        "run_20260321_100500",
    ]:
        (output_dir / run_name / "scripts").mkdir(parents=True)

    config = AppConfig(
        term="DNS",
        character_reference_root_dir=tmp_path / "assets",
        opening_template="{term}の導入",
        ending_template="{term}の締め",
        tone="熱血",
        target_duration_sec=120,
        scene_count=10,
        output_dir=output_dir,
        voice_models=VoiceModels(teacher="teacher", student="student"),
        character_design_profiles=CharacterDesignProfile(teacher="teacher design", student="student design"),
    )
    storyboard = Storyboard.model_validate(
        {
            "term": "DNS",
            "summary": "summary",
            "llm_prompt_log": {"system_prompt": "stub", "user_prompt": "stub"},
            "scenes": [
                {
                    "scene_id": scene_id,
                    "title": f"scene {scene_id}",
                    "speaker_role": "teacher",
                    "primary_visual_role": "teacher",
                    "expression": "explaining",
                    "narration": "narration",
                    "subtitle": "subtitle",
                    "duration_sec": 10,
                    "visual_summary": "visual",
                    "emotion_parameters": {"style": "説明", "intensity": 0.5},
                }
                for scene_id in range(1, 11)
            ],
        }
    )

    result = write_script_outputs(config, storyboard, [])

    remaining_runs = sorted(path.name for path in output_dir.iterdir() if path.is_dir() and path.name.startswith("run_"))
    assert result.run_directory.exists()
    assert len(remaining_runs) == 5
    assert "run_20260321_100000" not in remaining_runs
    assert result.run_directory.name in remaining_runs