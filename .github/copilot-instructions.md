# Copilot Instructions for TermBase

## プロジェクト概要

TermBase は IT 用語を題材にした日本語ショート動画向け素材（ストーリーボード・画像・音声）を生成する Python 製 CLI ツールです。

## リポジトリ構成

```
src/termbase/        # メインパッケージ
  cli.py             # Typer ベースの CLI エントリーポイント
  config.py          # 設定ファイルの読み込みとバリデーション
  models.py          # Pydantic モデル定義（AppConfig, Scene, Storyboard など）
  errors.py          # カスタム例外クラス
  adapters/          # 外部サービスクライアント（LLM, 画像, 音声）
  services/          # ビジネスロジック（脚本生成, 画像生成, 音声生成）
  writers/           # 出力ファイルの書き込み処理
tests/               # pytest テストスイート
config/              # JSON 設定ファイルのサンプルとスキーマ
assets/              # フォントなどの静的リソース
```

## 言語・技術スタック

- **Python 3.12**（型アノテーション必須、`from __future__ import annotations` を各ファイル先頭に付ける）
- **Pydantic v2**：データモデルおよび設定バリデーション
- **Typer**：CLI フレームワーク
- **pytest**：テストフレームワーク
- 依存関係は `pyproject.toml` で管理

## コーディング規約

- すべてのファイルの先頭に `from __future__ import annotations` を記述する
- データモデルは `src/termbase/models.py` の Pydantic BaseModel として定義する
- 新しい例外は `src/termbase/errors.py` の `TermBaseError` を継承して追加する
- CLI コマンドは `src/termbase/cli.py` の `app` に `@app.command()` で追加する
- 外部 API クライアントは `src/termbase/adapters/` に配置する
- ビジネスロジックは `src/termbase/services/` に配置する
- コメントや docstring は日本語で記述してよい
- 出力先は `output/`、機密情報は `secrets/` に置き、どちらも commit しない

## セットアップ

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## テスト実行

```bash
.venv/bin/pytest
```

特定のテストファイルを指定する場合:

```bash
.venv/bin/pytest tests/test_scenario_engine.py tests/test_prompt_builder.py
```

## 主な CLI コマンド

```bash
# 設定ファイルの検証
.venv/bin/python -m termbase validate-config --config config/project.json

# ストーリーボードと画像プロンプトの生成
.venv/bin/python -m termbase generate-script --config config/project.json

# 設定から画像まで一括生成
.venv/bin/python -m termbase generate-images --config config/project.json

# 既存 run から画像だけ再生成
.venv/bin/python -m termbase generate-images-from-run --config config/project.json --run-dir output/run_YYYYMMDD_HHMMSS

# 音声を生成
.venv/bin/python -m termbase generate-audio --config config/project.json --run-dir output/run_YYYYMMDD_HHMMSS
```

## テスト作成のガイドライン

- テストファイルは `tests/test_<モジュール名>.py` の命名規則に従う
- テスト用フィクスチャは `tests/fixtures/` に配置する
- モックは `unittest.mock` または `pytest-mock` を使用する
- 外部 API 呼び出しはモックで置き換える
- `AppConfig` を必要とするテストは `src/termbase/testsupport.py` のヘルパーを活用する

## PR・Issue 運用

- PR には `.github/pull_request_template.md` を使う
- `output/`、`secrets/`、`.venv/` は commit しない
- Issue ラベル: `task` / `bug` / `enhancement` / `docs` / `prompt` / `voice`
