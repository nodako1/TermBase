from termbase.models import Storyboard


def test_storyboard_requires_sequential_scene_ids() -> None:
    payload = {
        "term": "DNS",
        "summary": "summary",
        "llm_prompt_log": {"system_prompt": "a", "user_prompt": "b"},
        "scenes": [
            {
                "scene_id": 1,
                "title": "導入",
                "speaker_role": "student",
                "primary_visual_role": "student",
                "expression": "confused",
                "narration": "分からない。",
                "speech_bubble_text": "分からない…",
                "subtitle": "分からない。",
                "duration_sec": 8,
                "visual_summary": "困っている生徒",
                "emotion_parameters": {"style": "困惑", "intensity": 0.6},
            },
            {
                "scene_id": 2,
                "title": "解説",
                "speaker_role": "teacher",
                "primary_visual_role": "teacher",
                "expression": "explaining",
                "narration": "先生が説明する。",
                "speech_bubble_text": "ここがポイントです。",
                "subtitle": "先生が説明する。",
                "duration_sec": 8,
                "visual_summary": "説明する先生",
                "emotion_parameters": {"style": "説明", "intensity": 0.5},
            },
        ],
    }

    storyboard = Storyboard.model_validate(payload)

    assert len(storyboard.scenes) == 2
