# TermBase

TermBase is a Python CLI project for generating Japanese short-form educational assets about IT terminology.

Current pipeline:

- Generate storyboard JSON
- Generate per-scene image prompts
- Generate images
- Generate audio

## Requirements

- Python 3.12
- Google Gemini API key for Gemini-backed generation
- Google Cloud Text-to-Speech credentials for audio generation

## Local Setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

## Main Commands

Validate config:

```bash
.venv/bin/python -m termbase validate-config --config config/project.json
```

Generate storyboard and image prompts:

```bash
.venv/bin/python -m termbase generate-script --config config/project.json
```

Generate images from config:

```bash
.venv/bin/python -m termbase generate-images --config config/project.json
```

Generate images from an existing run:

```bash
.venv/bin/python -m termbase generate-images-from-run --config config/project.json --run-dir output/run_YYYYMMDD_HHMMSS
```

Generate audio for an existing run:

```bash
.venv/bin/python -m termbase generate-audio --config config/project.json --run-dir output/run_YYYYMMDD_HHMMSS
```

Run tests:

```bash
.venv/bin/pytest
```

## Codespaces

This repository includes a `.devcontainer` configuration.

When Codespaces starts, it will:

- create `.venv`
- install the package with `pip install -e .`
- configure Python extension defaults

Recommended first checks in Codespaces:

```bash
python --version
.venv/bin/python -m termbase validate-config --config config/project.json
.venv/bin/pytest tests/test_scenario_engine.py tests/test_prompt_builder.py
```

## GitHub Mobile Workflow

The easiest way to manage work from GitHub Mobile is to use Issues.

Recommended flow:

1. Open this repository in GitHub Mobile.
2. Create an Issue using the task template.
3. Write the goal, affected files, and acceptance criteria.
4. Open Codespaces from GitHub in a browser.
5. Implement and push changes.
6. Review the result from GitHub Mobile.

Good issue examples:

- Shorten manga speech bubble text further
- Add another IT term preset
- Improve teacher and student voice tuning
- Add image prompt regression tests

## Notes

- `secrets/` is intentionally ignored and must not be committed.
- `output/` is generated output and is ignored.
- `.venv/` is local environment state and is ignored.
