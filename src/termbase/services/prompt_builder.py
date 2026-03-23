from __future__ import annotations

from hashlib import sha256
import json
import re

from termbase.errors import LLMRequestError, TermBaseError
from termbase.models import AppConfig, CharacterReferenceSet, GraphOverlayPlan, ImagePrompt, RoleName, SpeechBubblePlan, Storyboard
from termbase.services.llm_provider import create_json_llm_client


PROMPT_STRATEGY_VERSION = "image-prompt-v5"

NEGATIVE_PROMPT = (
    "low quality, blurry, muddy colors, noisy shading, overexposed, underexposed, weak composition, flat lighting, "
    "deformed anatomy, broken hands, extra fingers, duplicated body parts, cropped head, tiny subject, cluttered frame, "
    "multiple panels, manga page layout, split screen, collage, too many props, unreadable text, typo-ridden Japanese text, "
    "misplaced speech bubble, malformed graph, floating UI, watermark, logo, photorealistic, 3d render, inconsistent hairstyle, inconsistent outfit"
)

STYLE_REQUIREMENTS = (
    "Premium manga-inspired educational key visual, single-panel vertical composition, crisp line art, polished cel shading, "
    "clear smartphone readability, strong focal hierarchy, expressive face acting, stable anatomy, intentional negative space, and clean background separation."
)

IN_IMAGE_TEXT_POLICY = (
    "Render the speech bubble and any chart directly into the final illustration. Japanese text must be short, large, high-contrast, and legible on a smartphone."
)


def _prompt_planner_schema(scene_count: int) -> dict:
    speech_bubble_schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["text", "placement", "style"],
        "properties": {
            "text": {"type": "string", "minLength": 1, "maxLength": 80},
            "placement": {
                "type": "string",
                "enum": ["top-left", "top-right", "upper-center", "left-side", "right-side", "bottom-panel"],
            },
            "style": {"type": "string", "minLength": 1, "maxLength": 40},
        },
    }
    graph_overlay_schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["graph_type", "placement", "instruction", "source_excerpt"],
        "properties": {
            "graph_type": {
                "type": "string",
                "enum": ["flowchart", "comparison-chart", "mapping-diagram", "sequence-diagram"],
            },
            "placement": {
                "type": "string",
                "enum": ["top-left", "top-right", "upper-center", "left-side", "right-side", "bottom-panel"],
            },
            "instruction": {"type": "string", "minLength": 1, "maxLength": 300},
            "source_excerpt": {"type": "string", "minLength": 1, "maxLength": 120},
        },
    }
    scene_plan_schema = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "scene_id",
            "composition_notes",
            "speech_bubble",
            "graph_overlay",
            "overlay_layout_notes",
            "positive_prompt",
            "negative_prompt",
        ],
        "properties": {
            "scene_id": {"type": "integer", "minimum": 1},
            "composition_notes": {"type": "string", "minLength": 1},
            "speech_bubble": speech_bubble_schema,
            "graph_overlay": {"anyOf": [graph_overlay_schema, {"type": "null"}]},
            "overlay_layout_notes": {"type": "string", "minLength": 1},
            "positive_prompt": {"type": "string", "minLength": 1},
            "negative_prompt": {"type": "string", "minLength": 1},
        },
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["scene_plans"],
        "properties": {
            "scene_plans": {
                "type": "array",
                "minItems": scene_count,
                "maxItems": scene_count,
                "items": scene_plan_schema,
            }
        },
    }


def _trim_overlay_text(text: str, max_length: int = 30, strip_terminal_punctuation: bool = True) -> str:
    normalized = re.sub(r"\s+", " ", text).strip()
    if strip_terminal_punctuation:
        normalized = normalized.rstrip("。!?！？")
    if len(normalized) <= max_length:
        return normalized
    return normalized[: max_length - 3].rstrip() + "..."


def _supporting_role(primary_visual_role: RoleName) -> RoleName:
    return "student" if primary_visual_role == "teacher" else "teacher"


def _build_speech_bubble(scene) -> SpeechBubblePlan:
    placement = "top-left" if scene.primary_visual_role == "teacher" else "top-right"
    return SpeechBubblePlan(
        text=_trim_overlay_text(scene.speech_bubble_text, max_length=24, strip_terminal_punctuation=False),
        placement=placement,
        style="rounded-manga-bubble",
    )


def _build_graph_overlay(scene) -> GraphOverlayPlan | None:
    combined = f"{scene.title} {scene.narration} {scene.visual_summary}"
    placement = "bottom-panel"

    if any(keyword in combined for keyword in ("まず", "次", "そのあと", "流れ", "問い合わせ", "返", "接続", "順番")):
        return GraphOverlayPlan(
            graph_type="flowchart",
            placement=placement,
            instruction="Draw a simple Japanese-labeled flowchart at the bottom panel with large readable labels and clear arrows.",
            source_excerpt=_trim_overlay_text(scene.narration, max_length=36),
        )

    if any(keyword in combined for keyword in ("変換", "結びつけ", "ドメイン", "IPアドレス", "住所", "名前")):
        return GraphOverlayPlan(
            graph_type="mapping-diagram",
            placement=placement,
            instruction="Draw a large readable mapping diagram at the bottom panel showing name-to-address correspondence in Japanese.",
            source_excerpt=_trim_overlay_text(scene.narration, max_length=36),
        )

    if any(keyword in combined for keyword in ("たとえば", "例える", "みたい", "電話帳", "人は", "機械は", "対比", "一方")):
        return GraphOverlayPlan(
            graph_type="comparison-chart",
            placement=placement,
            instruction="Draw a two-column Japanese comparison chart at the bottom panel with large readable labels.",
            source_excerpt=_trim_overlay_text(scene.narration, max_length=36),
        )

    return None


def _build_overlay_layout_notes(speech_bubble: SpeechBubblePlan, graph_overlay: GraphOverlayPlan | None) -> str:
    notes = [
        f"Render one speech bubble directly in the image at {speech_bubble.placement}.",
        IN_IMAGE_TEXT_POLICY,
    ]
    if graph_overlay is not None:
        notes.insert(1, f"Render one {graph_overlay.graph_type} directly in the image at {graph_overlay.placement}.")
    return " ".join(notes)


def _build_composition_notes(storyboard: Storyboard, scene_index: int, primary_visual_role: RoleName) -> str:
    if scene_index == 0:
        return f"Opening shot led by {primary_visual_role}. Use a clear bust or medium shot with immediate hook clarity and strong gaze direction."
    if scene_index == len(storyboard.scenes) - 1:
        return f"Closing shot led by {primary_visual_role}. Use a confident bust or medium shot that communicates wrap-up and CTA at first glance."
    return f"Single-panel explanation shot led by {primary_visual_role}. Prioritize one clear teaching idea with simple visual hierarchy."


def _build_character_consistency_rules(primary_visual_role: RoleName, support_role: RoleName, expression: str) -> str:
    return (
        "Character consistency requirements: "
        f"Use the provided primary reference image as the exact identity anchor for the main {primary_visual_role}. "
        "Preserve the same face shape, hairstyle, hair color, eye shape, outfit design, and silhouette. "
        f"Match the requested expression as {expression}. "
        f"Use the provided {support_role} reference only as a secondary design reference if that role appears."
    )


def _build_character_design_notes(config: AppConfig, primary_visual_role: RoleName, support_role: RoleName) -> str:
    primary_design = getattr(config.character_design_profiles, primary_visual_role)
    support_design = getattr(config.character_design_profiles, support_role)
    return (
        f"Primary {primary_visual_role} design profile: {primary_design}\n"
        f"Supporting {support_role} design profile: {support_design}"
    )


def _build_speech_bubble_render_instruction(speech_bubble: SpeechBubblePlan) -> str:
    return (
        "Render exactly one Japanese speech bubble directly in the final image. "
        f"Bubble placement: {speech_bubble.placement}. "
        f"Bubble style: {speech_bubble.style}. "
        f"Bubble text must be exactly: 「{speech_bubble.text}」."
    )


def _build_graph_render_instruction(graph_overlay: GraphOverlayPlan | None) -> str:
    if graph_overlay is None:
        return "Do not add a graph or chart to this image."
    return (
        f"Render exactly one {graph_overlay.graph_type} directly in the final image at {graph_overlay.placement}. "
        f"{graph_overlay.instruction} Source meaning: {graph_overlay.source_excerpt}."
    )


def _build_default_positive_prompt(scene, composition_notes: str, config: AppConfig) -> str:
    support_role = _supporting_role(scene.primary_visual_role)
    speech_bubble = _build_speech_bubble(scene)
    graph_overlay = _build_graph_overlay(scene)
    overlay_layout_notes = _build_overlay_layout_notes(speech_bubble, graph_overlay)
    return (
        f"Prompt strategy: {PROMPT_STRATEGY_VERSION}.\n"
        f"Style requirements: {STYLE_REQUIREMENTS}\n"
        f"Scene goal: main role is {scene.primary_visual_role}; speaker role is {scene.speaker_role}.\n"
        f"Emotion target: {scene.emotion_parameters.style}. Expression target: {scene.expression}.\n"
        f"Scene summary: {scene.visual_summary}\n"
        f"Composition requirements: {composition_notes}\n"
        f"Narration context: {scene.narration}\n"
        f"Speech bubble rendering instruction: {_build_speech_bubble_render_instruction(speech_bubble)}\n"
        f"Graph rendering instruction: {_build_graph_render_instruction(graph_overlay)}\n"
        f"In-image layout notes: {overlay_layout_notes}\n"
        f"Character design notes: {_build_character_design_notes(config, scene.primary_visual_role, support_role)}\n"
        f"Character consistency: {_build_character_consistency_rules(scene.primary_visual_role, support_role, scene.expression)}\n"
        "Quality requirements: clean medium shot or bust shot, strong focal point, readable pose, clean hands, clear silhouette, readable overlays, and premium composition."
    )


def _build_seed(term: str, scene_id: int) -> int:
    digest = sha256(f"{term}:{scene_id}".encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big")


def _build_filename_prefix(scene_id: int, primary_visual_role: RoleName) -> str:
    return f"scene_{scene_id:02d}_{primary_visual_role}"


def _build_backend_hint(config: AppConfig) -> str:
    if config.image_backend == "imagen":
        return (
            "Target backend is Imagen. Write the positive_prompt in English only. "
            "Do not rely on file paths. Preserve character identity through explicit design cues, recurring outfit details, and scene-level continuity."
        )
    return (
        "Target backend can receive reference PNGs. Write the positive_prompt in English, but assume teacher and student reference images will be supplied as identity anchors when supported."
    )


def _build_prompt_planner_messages(config: AppConfig, storyboard: Storyboard) -> list[dict[str, str]]:
    scene_briefs: list[dict[str, object]] = []
    for index, scene in enumerate(storyboard.scenes):
        speech_bubble = _build_speech_bubble(scene)
        graph_overlay = _build_graph_overlay(scene)
        scene_briefs.append(
            {
                "scene_id": scene.scene_id,
                "title": scene.title,
                "speaker_role": scene.speaker_role,
                "primary_visual_role": scene.primary_visual_role,
                "expression": scene.expression,
                "narration": scene.narration,
                "speech_bubble_text": scene.speech_bubble_text,
                "subtitle": scene.subtitle,
                "visual_summary": scene.visual_summary,
                "default_composition_notes": _build_composition_notes(storyboard, index, scene.primary_visual_role),
                "default_speech_bubble": speech_bubble.model_dump(mode="json"),
                "default_graph_overlay": graph_overlay.model_dump(mode="json") if graph_overlay is not None else None,
            }
        )

    system_prompt = (
        "You are a senior visual prompt designer for premium Japanese educational short-video stills. "
        "Output JSON only. For each scene, create a production-ready English image prompt optimized for one polished vertical illustration. "
        "Keep the scene visually simple, readable on a smartphone, and faithful to the script. "
        "Treat narration as audio-only context and speech_bubble_text as the only source for in-image speech bubble wording. "
        "Preserve exact Japanese speech bubble text. If a graph is useful, keep it minimal and readable. "
        "Do not mention file paths, JSON, or meta commentary inside positive_prompt."
    )
    user_prompt = json.dumps(
        {
            "prompt_strategy_version": PROMPT_STRATEGY_VERSION,
            "backend_hint": _build_backend_hint(config),
            "style_requirements": STYLE_REQUIREMENTS,
            "in_image_text_policy": IN_IMAGE_TEXT_POLICY,
            "teacher_design_profile": config.character_design_profiles.teacher,
            "student_design_profile": config.character_design_profiles.student,
            "global_negative_prompt": NEGATIVE_PROMPT,
            "scenes": scene_briefs,
            "requirements": [
                "positive_prompt must be English and optimized for a premium single-panel vertical illustration",
                "positive_prompt must explicitly state shot type, framing, focal hierarchy, lighting, expression, and in-image text integration",
                "narration is longer spoken dialogue for audio and must not be mistaken for in-image text",
                "speech_bubble.text must preserve the exact Japanese speech_bubble_text wording or a trimmed equivalent already provided",
                "graph_overlay should be null when a graph would add clutter",
                "negative_prompt can refine the global negative prompt but must remain compatible with it"
            ],
        },
        ensure_ascii=False,
        indent=2,
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def _generate_llm_scene_plans(config: AppConfig, storyboard: Storyboard) -> dict[int, dict[str, object]]:
    client = create_json_llm_client(config)
    schema = _prompt_planner_schema(len(storyboard.scenes))
    payload = client.generate_json_from_messages(_build_prompt_planner_messages(config, storyboard), response_json_schema=schema)

    scene_plans = payload.get("scene_plans")
    if not isinstance(scene_plans, list):
        raise LLMRequestError("image prompt planner response did not contain scene_plans")

    plan_by_scene_id: dict[int, dict[str, object]] = {}
    for scene_plan in scene_plans:
        if not isinstance(scene_plan, dict):
            raise LLMRequestError("image prompt planner response contained a non-object scene plan")
        scene_id = scene_plan.get("scene_id")
        if not isinstance(scene_id, int):
            raise LLMRequestError("image prompt planner response contained an invalid scene_id")
        plan_by_scene_id[scene_id] = scene_plan

    expected_scene_ids = {scene.scene_id for scene in storyboard.scenes}
    if set(plan_by_scene_id) != expected_scene_ids:
        raise LLMRequestError("image prompt planner did not return a plan for every scene")
    return plan_by_scene_id


def build_image_prompts(
    config: AppConfig,
    storyboard: Storyboard,
    references: CharacterReferenceSet,
) -> list[ImagePrompt]:
    llm_scene_plans: dict[int, dict[str, object]] = {}
    if config.image_prompt_use_llm:
        try:
            llm_scene_plans = _generate_llm_scene_plans(config, storyboard)
        except (LLMRequestError, TermBaseError):
            llm_scene_plans = {}
    prompts: list[ImagePrompt] = []

    for index, scene in enumerate(storyboard.scenes):
        support_role = _supporting_role(scene.primary_visual_role)
        reference_image_path = references.get_path(scene.primary_visual_role, scene.expression)
        supporting_reference_image_path = references.get_path(support_role, "neutral")
        fallback_speech_bubble = _build_speech_bubble(scene)
        fallback_graph_overlay = _build_graph_overlay(scene)
        fallback_composition_notes = _build_composition_notes(storyboard, index, scene.primary_visual_role)
        fallback_overlay_layout_notes = _build_overlay_layout_notes(fallback_speech_bubble, fallback_graph_overlay)
        fallback_positive_prompt = _build_default_positive_prompt(scene, fallback_composition_notes, config)

        scene_plan = llm_scene_plans.get(scene.scene_id)
        if scene_plan is not None:
            speech_bubble = SpeechBubblePlan.model_validate(scene_plan["speech_bubble"])
            graph_overlay_payload = scene_plan.get("graph_overlay")
            graph_overlay = GraphOverlayPlan.model_validate(graph_overlay_payload) if graph_overlay_payload else None
            composition_notes = str(scene_plan["composition_notes"])
            overlay_layout_notes = str(scene_plan["overlay_layout_notes"])
            positive_prompt = str(scene_plan["positive_prompt"])
            negative_prompt = str(scene_plan["negative_prompt"])
        else:
            speech_bubble = fallback_speech_bubble
            graph_overlay = fallback_graph_overlay
            composition_notes = fallback_composition_notes
            overlay_layout_notes = fallback_overlay_layout_notes
            positive_prompt = fallback_positive_prompt
            negative_prompt = NEGATIVE_PROMPT

        prompts.append(
            ImagePrompt(
                scene_id=scene.scene_id,
                title=scene.title,
                speaker_role=scene.speaker_role,
                primary_visual_role=scene.primary_visual_role,
                expression=scene.expression,
                reference_image_path=reference_image_path,
                supporting_reference_image_path=supporting_reference_image_path,
                visual_summary=scene.visual_summary,
                composition_notes=composition_notes,
                speech_bubble=speech_bubble,
                graph_overlay=graph_overlay,
                overlay_layout_notes=overlay_layout_notes,
                filename_prefix=_build_filename_prefix(scene.scene_id, scene.primary_visual_role),
                seed=_build_seed(config.term, scene.scene_id),
                width=config.image_width,
                height=config.image_height,
                positive_prompt=positive_prompt,
                negative_prompt=negative_prompt,
            )
        )

    return prompts