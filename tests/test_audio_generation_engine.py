from pathlib import Path

from termbase.services.audio_generation_engine import _build_ssml, generate_audio
from termbase.testsupport import load_storyboard_fixture, load_test_config


class StubGoogleCloudTTSClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, float, float, bool]] = []

    def synthesize(
        self,
        text: str,
        voice_name: str,
        speaking_rate: float,
        pitch_semitones: float,
        use_ssml: bool,
    ) -> bytes:
        self.calls.append((text, voice_name, speaking_rate, pitch_semitones, use_ssml))
        return f"audio:{voice_name}:{text}".encode("utf-8")


def test_build_ssml_inserts_breaks_and_role_tuning() -> None:
    ssml = _build_ssml(
        "えっ、魔法の箱？それって、どういうメリット？",
        speaking_rate=1.0,
        pitch_semitones=1.5,
        sentence_break_ms=320,
        question_break_ms=470,
        comma_break_ms=160,
    )

    assert "<speak>" in ssml
    assert 'rate="1.0"' in ssml
    assert 'pitch="+1.5st"' in ssml
    assert '<break time="470ms"/>' in ssml
    assert '<break time="160ms"/>' in ssml


def test_generate_audio_writes_scene_audio_files(tmp_path: Path) -> None:
    config = load_test_config("config/project.json")
    storyboard = load_storyboard_fixture()
    storyboard.scenes[0].narration = "DNSって、名前だけで届くんですか？"
    storyboard.scenes[0].speech_bubble_text = "名前だけで届くんすか？"
    storyboard.scenes[0].subtitle = "DNSって、名前だけで届くんですか？"
    client = StubGoogleCloudTTSClient()

    assets = generate_audio(config, storyboard, tmp_path, client=client)

    assert len(assets) == len(storyboard.scenes)
    assert assets[0].local_path.exists()
    assert assets[0].voice_name == config.voice_models.student
    assert assets[0].synthesis_input_format == "ssml"
    assert assets[0].pitch_semitones == (
        config.google_tts_voice_tunings.student.pitch_semitones
        + config.google_tts_voice_tunings.student.question_pitch_delta_semitones
    )
    assert assets[0].speaking_rate == config.google_tts_section_speaking_rates.opening.student
    assert assets[0].question_break_ms == config.google_tts_voice_tunings.student.question_break_ms
    assert client.calls[0][1] == config.voice_models.student
    assert client.calls[0][2] == config.google_tts_section_speaking_rates.opening.student
    assert client.calls[0][3] == (
        config.google_tts_voice_tunings.student.pitch_semitones
        + config.google_tts_voice_tunings.student.question_pitch_delta_semitones
    )
    assert client.calls[0][4] is True
    assert "<speak>" in client.calls[0][0]