from termbase.adapters.comfyui_client import populate_workflow_template


def test_populate_workflow_template_replaces_placeholders_recursively() -> None:
    workflow = {
        "3": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "__CHECKPOINT_NAME__"}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"text": "__POSITIVE_PROMPT__", "clip": ["3", 1]}},
        "6": {"class_type": "EmptyLatentImage", "inputs": {"width": "__WIDTH__", "height": "__HEIGHT__"}},
    }

    populated = populate_workflow_template(
        workflow,
        {
            "__CHECKPOINT_NAME__": "sd_xl_base_1.0.safetensors",
            "__POSITIVE_PROMPT__": "single-panel vertical illustration",
            "__WIDTH__": 832,
            "__HEIGHT__": 1216,
        },
    )

    assert populated["3"]["inputs"]["ckpt_name"] == "sd_xl_base_1.0.safetensors"
    assert populated["4"]["inputs"]["text"] == "single-panel vertical illustration"
    assert populated["6"]["inputs"]["width"] == 832
    assert populated["6"]["inputs"]["height"] == 1216