from __future__ import annotations

from html import escape
from pathlib import Path
import re

from termbase.adapters.google_cloud_tts import GoogleCloudTTSClient
from termbase.errors import AudioGenerationError
from termbase.models import AppConfig, GeneratedAudioAsset, Storyboard


def _audio_extension(audio_encoding: str) -> str:
    return "wav" if audio_encoding == "linear16" else "mp3"


def _format_pitch_semitones(pitch_semitones: float) -> str:
    if pitch_semitones > 0:
        return f"+{pitch_semitones:.1f}st"
    return f"{pitch_semitones:.1f}st"


def _insert_breaks(
    text: str,
    *,
    sentence_break_ms: int,
    question_break_ms: int,
    comma_break_ms: int,
) -> str:
    escaped = escape(text)
    escaped = re.sub(r"([。！!])", lambda match: f'{match.group(1)}<break time="{sentence_break_ms}ms"/>', escaped)
    escaped = re.sub(r"([？?])", lambda match: f'{match.group(1)}<break time="{question_break_ms}ms"/>', escaped)
    escaped = re.sub(r"([、，,])", lambda match: f'{match.group(1)}<break time="{comma_break_ms}ms"/>', escaped)
    return escaped


def _build_ssml(
    text: str,
    speaking_rate: float,
    pitch_semitones: float,
    *,
    sentence_break_ms: int = 300,
    question_break_ms: int = 500,
    comma_break_ms: int = 180,
) -> str:
    body = _insert_breaks(
        text,
        sentence_break_ms=sentence_break_ms,
        question_break_ms=question_break_ms,
        comma_break_ms=comma_break_ms,
    )
    return (
        "<speak>"
        f"<prosody rate=\"{speaking_rate:.1f}\" pitch=\"{_format_pitch_semitones(pitch_semitones)}\">"
        f"{body}"
        "</prosody>"
        "</speak>"
    )


def _resolve_scene_section(scene_index: int, scene_count: int) -> str | None:
    if scene_index < 2:
        return "opening"
    if scene_index >= max(scene_count - 2, 0):
        return "ending"
    return None


def _is_question_scene(scene) -> bool:
    text = f"{scene.narration} {scene.subtitle}"
    return any(marker in text for marker in ("?", "？", "どう", "なんで", "なぜ", "ですか"))


def _resolve_scene_voice(scene, config: AppConfig, scene_index: int, scene_count: int) -> tuple[float, float, int, int, int]:
    voice_tuning = getattr(config.google_tts_voice_tunings, scene.speaker_role)

    speaking_rate = voice_tuning.speaking_rate
    section = _resolve_scene_section(scene_index, scene_count)
    if section is not None:
        section_rates = getattr(config.google_tts_section_speaking_rates, section)
        override_rate = getattr(section_rates, scene.speaker_role)
        if override_rate is not None:
            speaking_rate = override_rate

    pitch_semitones = voice_tuning.pitch_semitones
    if scene.speaker_role == "student" and _is_question_scene(scene):
        pitch_semitones += voice_tuning.question_pitch_delta_semitones

    return (
        speaking_rate,
        pitch_semitones,
        voice_tuning.sentence_break_ms,
        voice_tuning.question_break_ms,
        voice_tuning.comma_break_ms,
    )


def generate_audio(
    config: AppConfig,
    storyboard: Storyboard,
    run_directory: Path,
    client: GoogleCloudTTSClient | None = None,
) -> list[GeneratedAudioAsset]:
    if config.voice_backend != "google-cloud-tts":
        raise AudioGenerationError(f"voice backend is not supported for audio generation: {config.voice_backend}")
    if not config.google_application_credentials_path:
        raise AudioGenerationError("google_application_credentials_path is required for audio generation")

    tts_client = client or GoogleCloudTTSClient(
        credentials_path=config.google_application_credentials_path,
        language_code=config.google_tts_language_code,
        audio_encoding=config.google_tts_audio_encoding,
    )

    audio_directory = run_directory / "audio"
    assets: list[GeneratedAudioAsset] = []
    extension = _audio_extension(config.google_tts_audio_encoding)

    for index, scene in enumerate(storyboard.scenes):
        voice_name = getattr(config.voice_models, scene.speaker_role)
        speaking_rate, pitch_semitones, sentence_break_ms, question_break_ms, comma_break_ms = _resolve_scene_voice(
            scene,
            config,
            index,
            len(storyboard.scenes),
        )
        output_path = audio_directory / f"scene_{scene.scene_id:02d}_{scene.speaker_role}.{extension}"
        synthesis_text = (
            _build_ssml(
                scene.narration,
                speaking_rate,
                pitch_semitones,
                sentence_break_ms=sentence_break_ms,
                question_break_ms=question_break_ms,
                comma_break_ms=comma_break_ms,
            )
            if config.google_tts_use_ssml
            else scene.narration
        )
        audio_bytes = tts_client.synthesize(
            synthesis_text,
            voice_name,
            speaking_rate=speaking_rate,
            pitch_semitones=pitch_semitones,
            use_ssml=config.google_tts_use_ssml,
        )
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(audio_bytes)
        except OSError as exc:
            raise AudioGenerationError(f"failed to write audio output: {exc}") from exc

        assets.append(
            GeneratedAudioAsset(
                scene_id=scene.scene_id,
                title=scene.title,
                speaker_role=scene.speaker_role,
                voice_name=voice_name,
                text=scene.narration,
                local_path=output_path,
                audio_encoding=config.google_tts_audio_encoding,
                speaking_rate=speaking_rate,
                pitch_semitones=pitch_semitones,
                sentence_break_ms=sentence_break_ms,
                question_break_ms=question_break_ms,
                comma_break_ms=comma_break_ms,
                synthesis_input_format="ssml" if config.google_tts_use_ssml else "text",
            )
        )

    return assets