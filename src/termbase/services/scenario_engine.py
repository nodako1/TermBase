from __future__ import annotations

import json
from statistics import mean

from termbase.errors import ConfigValidationError, LLMRequestError
from termbase.models import AppConfig, CharacterReferenceSet, Storyboard
from termbase.services.llm_provider import create_json_llm_client


ALLOWED_EXPRESSIONS = (
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
)

OUTPUT_RULES_VERSION = "script-json-v4"


def _storyboard_response_schema(scene_count: int) -> dict:
    scene_schema = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "scene_id",
            "title",
            "speaker_role",
            "primary_visual_role",
            "expression",
            "narration",
            "speech_bubble_text",
            "subtitle",
            "duration_sec",
            "visual_summary",
            "emotion_parameters",
        ],
        "properties": {
            "scene_id": {"type": "integer", "minimum": 1},
            "title": {"type": "string", "minLength": 1, "maxLength": 80},
            "speaker_role": {"type": "string", "enum": ["teacher", "student"]},
            "primary_visual_role": {"type": "string", "enum": ["teacher", "student"]},
            "expression": {"type": "string", "enum": list(ALLOWED_EXPRESSIONS)},
            "narration": {"type": "string", "minLength": 1},
            "speech_bubble_text": {"type": "string", "minLength": 1, "maxLength": 40},
            "subtitle": {"type": "string", "minLength": 1},
            "duration_sec": {"type": "integer", "minimum": 3, "maximum": 30},
            "visual_summary": {"type": "string", "minLength": 1},
            "emotion_parameters": {
                "type": "object",
                "additionalProperties": False,
                "required": ["style", "intensity"],
                "properties": {
                    "style": {"type": "string", "minLength": 1, "maxLength": 40},
                    "intensity": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                },
            },
        },
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["summary", "scenes"],
        "properties": {
            "summary": {"type": "string", "minLength": 1},
            "scenes": {
                "type": "array",
                "minItems": scene_count,
                "maxItems": scene_count,
                "items": scene_schema,
            },
        },
    }


def build_storyboard_messages(config: AppConfig, references: CharacterReferenceSet) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": _build_system_prompt(config)},
        {"role": "user", "content": _build_user_prompt(config, references)},
    ]


def _build_system_prompt(config: AppConfig) -> str:
    return (
        "You are a screenplay generator for Japanese short-form educational videos about IT terminology. "
        "Your job is to produce a stable, structured, beginner-friendly storyboard in JSON only. "
        "Do not output markdown, explanations, comments, code fences, or any text outside the JSON object. "
        "The content must be correct enough for beginner education, concrete rather than abstract, and easy to visualize. "
        "There are always two roles: teacher and student. Teacher explains and corrects. Student asks, reacts, or confirms understanding. "
        "The dialogue must feel like a short lesson, not a monologue. "
        "The script must follow this arc: opening hook, problem awareness, intuitive metaphor, step-by-step explanation, recap, concise closing CTA. "
        "Avoid jargon stacking. When jargon is necessary, explain it immediately in plain Japanese. "
        "Every scene must include exactly these keys: scene_id, title, speaker_role, primary_visual_role, expression, narration, speech_bubble_text, subtitle, duration_sec, visual_summary, emotion_parameters. "
        "narration is the full spoken line used for voice generation and should carry the explanation clearly. "
        "speech_bubble_text is separate from narration and is only the short text shown inside one manga-style speech bubble in the image. "
        "speech_bubble_text must be brief, punchy, conversational, and visually readable at smartphone size. It must not simply copy the full narration. "
        "Teacher persona: a reliable Japanese female senior colleague or manager. She is calm, competent, supportive, and direct without sounding harsh or theatrical. Avoid old-fashioned macho phrasing or exaggerated hot-blooded speech. "
        "Student persona: a slightly cheeky but lovable junior colleague. Usually a bit unreliable and reactive, but once taught, they respond brightly and energetically with lines such as なるほど！ or それなら分かります！ "
        "emotion_parameters must include exactly style and intensity. intensity must be a number between 0.0 and 1.0. "
        "Use only the allowed role names and expression names provided by the user prompt. "
        "Keep each narration concise enough for one short-video scene. "
        "The opening scenes must naturally compress the provided opening template instead of copying it mechanically. "
        "The final scenes must naturally compress the provided ending template instead of copying it mechanically."
    )


def _build_user_prompt(config: AppConfig, references: CharacterReferenceSet) -> str:
    teacher_files = ", ".join(path.name for path in references.teacher.expressions.values())
    student_files = ", ".join(path.name for path in references.student.expressions.values())
    return f"""
Generate a storyboard for the IT term below.

term: {config.term}
opening_template: {config.opening_template}
ending_template: {config.ending_template}
tone: {config.tone}
target_duration_sec: {config.target_duration_sec}
scene_count: {config.scene_count}
language: Japanese
aspect_ratio: {config.image_aspect_ratio}
additional_instructions: {config.additional_instructions or 'none'}

teacher reference files: {teacher_files}
student reference files: {student_files}

Constraints:
- Output one JSON object with exactly two top-level keys: summary, scenes
- Do not include any extra top-level keys
- scenes must contain exactly {config.scene_count} items
- scene_id must start at 1 and be sequential without gaps
- Use expressions from this set only: {", ".join(ALLOWED_EXPRESSIONS)}
- speaker_role and primary_visual_role must be teacher or student
- narration is for spoken audio. It should explain the content fully enough for listeners.
- speech_bubble_text is separate from narration and is only for one manga-style speech bubble shown in the image.
- speech_bubble_text must stay short, ideally one brief line, usually around 4 to 20 Japanese characters, and must not copy the full narration verbatim.
- Student must appear as speaker in at least 3 scenes
- Teacher must appear as speaker in at least 4 scenes
- The first 1 to 2 scenes must be a concise adaptation of the opening_template and must mention {config.term}
- The first 3 scenes must clearly establish the learner's confusion or problem
- At least 1 scene must contain an everyday metaphor that maps to the IT term
- The middle scenes must explain the term step by step, not all at once
- The final 1 to 2 scenes must be a concise adaptation of the ending_template
- The final scenes must recap the meaning in plain Japanese and include a natural next-step or channel CTA
- subtitle should usually match narration exactly, unless a shorter subtitle is clearly better
- narration should generally stay within 25 to 70 Japanese characters per scene
- teacher wording should feel like a dependable female boss or senior colleague using natural modern Japanese
- student wording should feel like an energetic, slightly cheeky but lovable junior colleague
- visual_summary must describe what should be shown in one sentence and be image-friendly
- Avoid repeating the same title, same expression, or nearly identical narration in consecutive scenes
- teacher should usually use explaining or serious when delivering core explanations
- student should usually use confused, surprised, thinking, or happy depending on context
- Do not copy the full opening_template verbatim if it is too long; compress it into natural short-video wording
- Do not copy the full ending_template verbatim if it is too long; compress it into natural short-video wording
- Total duration should be close to {config.target_duration_sec} seconds, with at most 20 percent deviation

Required story structure:
1. Concise opening hook based on the opening_template
2. Beginner confusion or everyday problem
3. Teacher reframes the problem in plain Japanese
4. Everyday metaphor
5. Core explanation in small steps
6. Recap with learner understanding
7. Concise closing based on the ending_template

JSON output contract:
- summary: one short Japanese paragraph summarizing the whole script
- scenes: array of scene objects
- narration: full spoken Japanese line for audio
- speech_bubble_text: short Japanese line for in-image speech bubble only
- emotion_parameters.style: short Japanese label such as 困惑, 説明, 強調, 安心, 納得
- emotion_parameters.intensity: decimal number between 0.0 and 1.0
""".strip()


def _validate_storyboard_quality(config: AppConfig, storyboard: Storyboard) -> None:
    if len(storyboard.scenes) != config.scene_count:
        raise ConfigValidationError(
            f"LLM returned {len(storyboard.scenes)} scenes, expected {config.scene_count}"
        )

    durations = [scene.duration_sec for scene in storyboard.scenes]
    total_duration = sum(durations)
    allowed_deviation = max(10, int(config.target_duration_sec * 0.2))
    if abs(total_duration - config.target_duration_sec) > allowed_deviation:
        raise LLMRequestError(
            "total duration deviates too much from target_duration_sec: "
            f"target={config.target_duration_sec}, actual={total_duration}"
        )

    if min(durations) < 4 or max(durations) > 25:
        raise LLMRequestError("scene durations must stay between 4 and 25 seconds for script stability")

    teacher_speaking_scenes = sum(1 for scene in storyboard.scenes if scene.speaker_role == "teacher")
    student_speaking_scenes = sum(1 for scene in storyboard.scenes if scene.speaker_role == "student")
    if teacher_speaking_scenes < 4:
        raise LLMRequestError("teacher must speak in at least 4 scenes")
    if student_speaking_scenes < 3:
        raise LLMRequestError("student must speak in at least 3 scenes")

    opening_text = " ".join(scene.narration for scene in storyboard.scenes[:3])
    opening_window = " ".join(scene.narration for scene in storyboard.scenes[:2])
    if config.term not in opening_window:
        raise LLMRequestError("opening scenes must mention the target term")

    if not any(keyword in opening_text for keyword in ("わから", "困", "迷", "なんで", "どうして", "?", "？")):
        raise LLMRequestError("opening scenes must establish beginner confusion or a problem")

    if not any(keyword in opening_window for keyword in ("説明", "学", "ドキッ", "どうなる", "意味")):
        raise LLMRequestError("opening scenes must behave like a concise learning hook")

    all_text = " ".join(scene.narration for scene in storyboard.scenes)
    if not any(keyword in all_text for keyword in ("たとえば", "例える", "みたい", "たとえると")):
        raise LLMRequestError("storyboard must contain at least one explicit everyday metaphor cue")

    closing_window = " ".join(scene.narration for scene in storyboard.scenes[-2:])
    if config.term not in closing_window:
        raise LLMRequestError("closing scenes must mention the target term")

    if not any(keyword in closing_window for keyword in ("チャンネル", "登録", "深掘", "動画", "見て", "もっと")):
        raise LLMRequestError("closing scenes must contain a concise CTA based on ending_template")

    consecutive_titles = list(zip(storyboard.scenes, storyboard.scenes[1:]))
    if any(left.title == right.title for left, right in consecutive_titles):
        raise LLMRequestError("consecutive scenes must not reuse the same title")

    if any(left.narration == right.narration for left, right in consecutive_titles):
        raise LLMRequestError("consecutive scenes must not reuse identical narration")

    for scene in storyboard.scenes:
        bubble_text = scene.speech_bubble_text.strip()
        if len(bubble_text) > 30:
            raise LLMRequestError("speech_bubble_text must stay concise enough for one manga bubble")
        if bubble_text == scene.narration.strip():
            raise LLMRequestError("speech_bubble_text must not copy narration verbatim")

    average_duration = mean(durations)
    if average_duration < 5 or average_duration > 20:
        raise LLMRequestError("average scene duration is outside the expected range")


def _build_repair_prompt(config: AppConfig, previous_payload: dict, validation_error: str) -> str:
    return f"""
The previous storyboard JSON failed validation.

target_term: {config.term}
validation_error: {validation_error}

Rewrite the entire JSON object from scratch while preserving the useful parts.
You must fix the validation failure completely.

Important corrections:
- The first 3 scenes must explicitly establish beginner confusion or a problem using cues such as わからない, 困る, 迷う, なんで, どうして, ? or ？.
- The first 1 to 2 scenes must mention {config.term} and behave like a concise learning hook.
- Include at least one explicit everyday metaphor cue using phrases such as たとえば, 例えると, or みたいに.
- Each scene must include speech_bubble_text as a short manga-style line that does not copy narration verbatim.
- Keep the opening aligned with opening_template.
- Keep the ending aligned with ending_template.
- Return valid JSON only.
- Keep exactly {config.scene_count} scenes.

Previous JSON:
{json.dumps(previous_payload, ensure_ascii=False, indent=2)}
""".strip()


def _parse_storyboard_payload(config: AppConfig, system_prompt: str, user_prompt: str, payload: dict) -> Storyboard:
    try:
        storyboard = Storyboard.model_validate(
            {
                "term": config.term,
                "summary": payload["summary"],
                "scenes": payload["scenes"],
                "llm_prompt_log": {
                    "output_rules_version": OUTPUT_RULES_VERSION,
                    "system_prompt": system_prompt,
                    "user_prompt": user_prompt,
                },
            }
        )
    except Exception as exc:  # noqa: BLE001
        raise LLMRequestError(f"failed to validate storyboard from LLM: {exc}") from exc

    _validate_storyboard_quality(config, storyboard)
    return storyboard


def generate_storyboard(config: AppConfig, references: CharacterReferenceSet) -> Storyboard:
    client = create_json_llm_client(config)
    messages = build_storyboard_messages(config, references)
    system_prompt = messages[0]["content"]
    user_prompt = messages[1]["content"]
    schema = _storyboard_response_schema(config.scene_count)
    payload = client.generate_json_from_messages(messages, response_json_schema=schema)

    try:
        return _parse_storyboard_payload(config, system_prompt, user_prompt, payload)
    except LLMRequestError as exc:
        repair_prompt = _build_repair_prompt(config, payload, str(exc))
        repaired_payload = client.generate_json_from_messages(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
                {"role": "assistant", "content": json.dumps(payload, ensure_ascii=False)},
                {"role": "user", "content": repair_prompt},
            ],
            response_json_schema=schema,
        )
        return _parse_storyboard_payload(config, system_prompt, user_prompt, repaired_payload)