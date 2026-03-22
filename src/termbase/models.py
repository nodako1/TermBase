from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

from pydantic import AliasChoices, BaseModel, Field, field_validator, model_validator


RoleName = Literal["teacher", "student"]
OverlayPlacement = Literal["top-left", "top-right", "upper-center", "left-side", "right-side", "bottom-panel"]
GraphType = Literal["flowchart", "comparison-chart", "mapping-diagram", "sequence-diagram"]
ExpressionName = Literal[
    "neutral",
    "happy",
    "smile",
    "surprised",
    "confused",
    "explaining",
    "serious",
    "thinking",
    "sad",
    "angry",
]


class VoiceModels(BaseModel):
    teacher: str = Field(min_length=1, max_length=80)
    student: str = Field(min_length=1, max_length=80)


class GoogleTTSVoiceTuning(BaseModel):
    speaking_rate: float = Field(default=1.0, ge=0.25, le=4.0)
    pitch_semitones: float = Field(default=0.0, ge=-20.0, le=20.0)
    sentence_break_ms: int = Field(default=300, ge=0, le=5000)
    question_break_ms: int = Field(default=500, ge=0, le=5000)
    comma_break_ms: int = Field(default=180, ge=0, le=5000)
    question_pitch_delta_semitones: float = Field(default=0.0, ge=-20.0, le=20.0)


class GoogleTTSVoiceTunings(BaseModel):
    teacher: GoogleTTSVoiceTuning
    student: GoogleTTSVoiceTuning


class GoogleTTSSectionSpeakingRate(BaseModel):
    teacher: Optional[float] = Field(default=None, ge=0.25, le=4.0)
    student: Optional[float] = Field(default=None, ge=0.25, le=4.0)


class GoogleTTSSectionSpeakingRates(BaseModel):
    opening: GoogleTTSSectionSpeakingRate = Field(default_factory=GoogleTTSSectionSpeakingRate)
    ending: GoogleTTSSectionSpeakingRate = Field(default_factory=GoogleTTSSectionSpeakingRate)


class CharacterDesignProfile(BaseModel):
    teacher: str = Field(min_length=1, max_length=500)
    student: str = Field(min_length=1, max_length=500)


class AppConfig(BaseModel):
    term: str = Field(min_length=1, max_length=80)
    character_reference_root_dir: Path
    opening_template: str = Field(
        min_length=1,
        max_length=800,
        validation_alias=AliasChoices("opening_template", "catchphrase"),
    )
    ending_template: str = Field(min_length=1, max_length=500)
    tone: str = Field(min_length=1, max_length=40)
    target_duration_sec: int = Field(ge=60, le=300)
    scene_count: int = Field(ge=10, le=15)
    image_aspect_ratio: Literal["9:16"] = "9:16"
    output_dir: Path
    llm_provider: Literal["openai", "gemini"] = "openai"
    llm_model: str = Field(default="gpt-5.4", min_length=1, max_length=80)
    llm_temperature: float = Field(default=0.3, ge=0.0, le=1.0)
    openai_base_url: str = "https://api.openai.com/v1"
    image_prompt_use_llm: bool = False
    image_backend: Literal["comfyui", "openai", "gemini", "imagen"] = "openai"
    openai_image_model: str = Field(default="gpt-image-1", min_length=1, max_length=80)
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    gemini_image_model: str = Field(default="gemini-3.1-flash-image-preview", min_length=1, max_length=120)
    imagen_model: str = Field(default="imagen-3.0-generate-002", min_length=1, max_length=120)
    comfyui_base_url: str = "http://127.0.0.1:8188"
    image_workflow_path: Optional[Path] = None
    comfyui_checkpoint_name: str = Field(default="sd_xl_base_1.0.safetensors", min_length=1, max_length=200)
    comfyui_steps: int = Field(default=20, ge=1, le=100)
    comfyui_cfg_scale: float = Field(default=6.5, ge=0.0, le=30.0)
    comfyui_timeout_sec: float = Field(default=600.0, gt=0.0, le=3600.0)
    comfyui_poll_interval_sec: float = Field(default=2.0, gt=0.0, le=60.0)
    image_width: int = Field(default=832, ge=256, le=2048)
    image_height: int = Field(default=1216, ge=256, le=4096)
    voice_backend: Literal["style-bert-vits2", "google-cloud-tts"] = "style-bert-vits2"
    voice_models: VoiceModels
    google_application_credentials_path: Optional[Path] = None
    google_tts_language_code: str = Field(default="ja-JP", min_length=2, max_length=20)
    google_tts_audio_encoding: Literal["mp3", "linear16"] = "mp3"
    google_tts_speaking_rate: float = Field(default=1.0, ge=0.25, le=4.0)
    google_tts_use_ssml: bool = True
    google_tts_voice_tunings: GoogleTTSVoiceTunings = Field(
        default_factory=lambda: GoogleTTSVoiceTunings(
            teacher=GoogleTTSVoiceTuning(
                speaking_rate=1.1,
                pitch_semitones=0.0,
                sentence_break_ms=340,
                question_break_ms=520,
                comma_break_ms=190,
                question_pitch_delta_semitones=0.0,
            ),
            student=GoogleTTSVoiceTuning(
                speaking_rate=1.0,
                pitch_semitones=1.5,
                sentence_break_ms=260,
                question_break_ms=430,
                comma_break_ms=150,
                question_pitch_delta_semitones=0.4,
            ),
        )
    )
    google_tts_section_speaking_rates: GoogleTTSSectionSpeakingRates = Field(
        default_factory=lambda: GoogleTTSSectionSpeakingRates(
            opening=GoogleTTSSectionSpeakingRate(teacher=1.15, student=1.05),
            ending=GoogleTTSSectionSpeakingRate(teacher=1.0, student=0.95),
        )
    )
    overlay_font_path: Optional[Path] = None
    character_design_profiles: CharacterDesignProfile
    retry_count: int = Field(default=2, ge=0, le=5)
    additional_instructions: str = Field(default="", max_length=2000)

    @field_validator(
        "character_reference_root_dir",
        "output_dir",
        "image_workflow_path",
        "google_application_credentials_path",
        "overlay_font_path",
        mode="before",
    )
    @classmethod
    def _path_from_str(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, Path):
            return value
        if isinstance(value, str):
            return Path(value)
        return value


class CharacterRoleReferences(BaseModel):
    role: RoleName
    directory: Path
    expressions: dict[ExpressionName, Path]


class CharacterReferenceSet(BaseModel):
    root_directory: Path
    teacher: CharacterRoleReferences
    student: CharacterRoleReferences

    def get_path(self, role: RoleName, expression: ExpressionName) -> Path:
        reference = self.teacher if role == "teacher" else self.student
        return reference.expressions[expression]


class EmotionParameters(BaseModel):
    style: str = Field(min_length=1, max_length=40)
    intensity: float = Field(ge=0.0, le=1.0)


class Scene(BaseModel):
    scene_id: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=80)
    speaker_role: RoleName
    primary_visual_role: RoleName
    expression: ExpressionName
    narration: str = Field(min_length=1)
    speech_bubble_text: str = Field(min_length=1, max_length=40)
    subtitle: str = Field(min_length=1)
    duration_sec: int = Field(ge=3, le=30)
    visual_summary: str = Field(min_length=1)
    emotion_parameters: EmotionParameters


class SpeechBubblePlan(BaseModel):
    text: str = Field(min_length=1, max_length=80)
    placement: OverlayPlacement
    style: str = Field(min_length=1, max_length=40)


class GraphOverlayPlan(BaseModel):
    graph_type: GraphType
    placement: OverlayPlacement
    instruction: str = Field(min_length=1, max_length=300)
    source_excerpt: str = Field(min_length=1, max_length=120)


class ImagePrompt(BaseModel):
    scene_id: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=80)
    speaker_role: RoleName
    primary_visual_role: RoleName
    expression: ExpressionName
    reference_image_path: Path
    supporting_reference_image_path: Path
    visual_summary: str = Field(min_length=1)
    composition_notes: str = Field(min_length=1)
    speech_bubble: SpeechBubblePlan
    graph_overlay: Optional[GraphOverlayPlan] = None
    overlay_layout_notes: str = Field(min_length=1)
    filename_prefix: str = Field(min_length=1, max_length=120)
    seed: int = Field(ge=0, le=4294967295)
    width: int = Field(ge=256, le=2048)
    height: int = Field(ge=256, le=4096)
    positive_prompt: str = Field(min_length=1)
    negative_prompt: str = Field(min_length=1)


class Storyboard(BaseModel):
    term: str
    summary: str = Field(min_length=1)
    scenes: list[Scene]
    llm_prompt_log: dict[str, str]

    @model_validator(mode="after")
    def _validate_scene_order(self) -> "Storyboard":
        expected_ids = list(range(1, len(self.scenes) + 1))
        actual_ids = [scene.scene_id for scene in self.scenes]
        if actual_ids != expected_ids:
            raise ValueError("scene_id must be sequential starting from 1")
        return self


class ScriptGenerationResult(BaseModel):
    run_id: str
    run_directory: Path
    storyboard_path: Path
    metadata_path: Path
    image_prompts_path: Path
    storyboard: Storyboard


class GeneratedImageAsset(BaseModel):
    scene_id: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=80)
    prompt_id: str = Field(min_length=1)
    filename_prefix: str = Field(min_length=1, max_length=120)
    local_path: Path
    reference_image_paths: list[Path] = Field(default_factory=list)
    positive_prompt: str = Field(min_length=1)
    negative_prompt: str = Field(min_length=1)
    seed: int = Field(ge=0, le=4294967295)
    width: int = Field(ge=256, le=2048)
    height: int = Field(ge=256, le=4096)
    remote_filename: str = Field(min_length=1)
    remote_subfolder: str = ""
    remote_type: str = Field(default="output", min_length=1)


class ImageGenerationResult(BaseModel):
    run_directory: Path
    images_directory: Path
    manifest_path: Path
    assets: list[GeneratedImageAsset]


class OverlayCompositeAsset(BaseModel):
    scene_id: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=80)
    base_image_path: Path
    output_path: Path
    speech_bubble_text: str = Field(min_length=1, max_length=80)
    graph_type: Optional[GraphType] = None


class OverlayCompositeResult(BaseModel):
    run_directory: Path
    output_directory: Path
    manifest_path: Path
    assets: list[OverlayCompositeAsset]


class GeneratedAudioAsset(BaseModel):
    scene_id: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=80)
    speaker_role: RoleName
    voice_name: str = Field(min_length=1, max_length=80)
    text: str = Field(min_length=1)
    local_path: Path
    audio_encoding: Literal["mp3", "linear16"]
    speaking_rate: float = Field(ge=0.25, le=4.0)
    pitch_semitones: float = Field(ge=-20.0, le=20.0)
    sentence_break_ms: int = Field(ge=0, le=5000)
    question_break_ms: int = Field(ge=0, le=5000)
    comma_break_ms: int = Field(ge=0, le=5000)
    synthesis_input_format: Literal["text", "ssml"]


class AudioGenerationResult(BaseModel):
    run_directory: Path
    audio_directory: Path
    manifest_path: Path
    assets: list[GeneratedAudioAsset]
