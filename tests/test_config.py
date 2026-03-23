from pathlib import Path

from termbase.testsupport import load_test_config


def test_load_sample_config() -> None:
    config = load_test_config("config/project.sample.json")

    assert config.term == "DNS"
    assert config.character_reference_root_dir.is_absolute()
    assert config.image_workflow_path is not None
    assert config.image_workflow_path.is_absolute()
    assert config.image_backend == "openai"
    assert config.openai_image_model == "gpt-image-1"
    assert config.gemini_base_url == "https://generativelanguage.googleapis.com/v1beta"
    assert config.gemini_image_model == "gemini-3.1-flash-image-preview"
    assert config.imagen_model == "imagen-3.0-generate-002"
    assert config.llm_model == "gpt-5.4"
    assert config.llm_temperature == 0.3
    assert config.comfyui_checkpoint_name == "sd_xl_base_1.0.safetensors"
    assert config.image_width == 832
    assert config.image_height == 1216
    assert "{term}" in config.opening_template
    assert "{term}" in config.ending_template
    assert str(config.output_dir).startswith("/Volumes/T7Shield/koichi-home/")
    assert config.voice_models.teacher
    assert config.voice_models.student
    assert config.google_application_credentials_path is not None
    assert config.google_application_credentials_path.name == "service-account.json"
    assert config.google_tts_language_code == "ja-JP"
    assert config.google_tts_audio_encoding == "mp3"
    assert config.google_tts_use_ssml is True
    assert config.google_tts_voice_tunings.teacher.speaking_rate == 1.04
    assert config.google_tts_voice_tunings.student.pitch_semitones == 2.6
    assert config.google_tts_voice_tunings.teacher.sentence_break_ms == 360
    assert config.google_tts_voice_tunings.student.question_pitch_delta_semitones == 0.8
    assert config.google_tts_section_speaking_rates.opening.teacher == 1.08
    assert "頼れる上司や先輩" in config.character_design_profiles.teacher
    assert "少しやんちゃで頼りない" in config.character_design_profiles.student


def test_load_legacy_catchphrase_config() -> None:
    config = load_test_config("tests/fixtures/legacy_catchphrase_config.json")

    assert "DNS" in config.opening_template
    assert "{term}" in config.ending_template
    assert config.character_design_profiles.teacher
    assert config.character_design_profiles.student
