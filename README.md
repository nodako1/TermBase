# TermBase

TermBase は、IT 用語を題材にした日本語ショート動画向け素材を生成する Python 製 CLI ツールです。

現在は次の素材をまとめて作れます。

- ストーリーボード JSON
- シーンごとの画像プロンプト
- 画像
- 音声

## できること

たとえば `HTTP / HTTPS` のような用語を入力すると、次の流れでショート動画用の素材を作れます。

1. 先生役と生徒役の会話ベースでストーリーボードを生成
2. 各シーンの画像生成プロンプトを生成
3. 縦動画向けの画像を生成
4. 各シーンの音声を生成

## 必要なもの

- Python 3.12
- Gemini 系生成を使う場合の Google Gemini API キー
- 音声生成を使う場合の Google Cloud Text-to-Speech 認証情報

## ローカルセットアップ

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

## 主なコマンド

設定ファイルの検証:

```bash
.venv/bin/python -m termbase validate-config --config config/project.json
```

ストーリーボードと画像プロンプトの生成:

```bash
.venv/bin/python -m termbase generate-script --config config/project.json
```

設定から画像までまとめて生成:

```bash
.venv/bin/python -m termbase generate-images --config config/project.json
```

既存 run から画像だけ再生成:

```bash
.venv/bin/python -m termbase generate-images-from-run --config config/project.json --run-dir output/run_YYYYMMDD_HHMMSS
```

既存 run に対して音声を生成:

```bash
.venv/bin/python -m termbase generate-audio --config config/project.json --run-dir output/run_YYYYMMDD_HHMMSS
```

テスト実行:

```bash
.venv/bin/pytest
```

## 具体的な生成例

`config/project.json` に `HTTP / HTTPS` を設定している場合の一例です。

1. ストーリーボードと画像プロンプトを生成します。

```bash
.venv/bin/python -m termbase generate-script --config config/project.json
```

出力例:

```text
run_id: 20260322_064759
storyboard: output/run_20260322_064759/scripts/storyboard.json
image_prompts: output/run_20260322_064759/scripts/image_prompts.json
```

2. その run から画像を生成します。

```bash
.venv/bin/python -m termbase generate-images-from-run --config config/project.json --run-dir output/run_20260322_064759
```

3. 画像生成済み run に音声を追加します。

```bash
.venv/bin/python -m termbase generate-audio --config config/project.json --run-dir output/run_20260322_064827
```

生成物の例:

- ストーリーボード: `output/run_20260322_064759/scripts/storyboard.json`
- 画像プロンプト: `output/run_20260322_064827/scripts/image_prompts.json`
- 画像 manifest: `output/run_20260322_064827/images/image_generation.json`
- 音声 manifest: `output/run_20260322_064827/audio/audio_generation.json`

この構成では `narration` は音声用の説明文、`speech_bubble_text` は画像内の吹き出し用短文として分離されています。

## Codespaces

このリポジトリには `.devcontainer` 設定が入っています。

Codespaces 起動時には次を自動で行います。

- `.venv` の作成
- `pip install -e .` の実行
- Python 拡張向けの基本設定

Codespaces で最初に確認するとよいコマンド:

```bash
python --version
.venv/bin/python -m termbase validate-config --config config/project.json
.venv/bin/pytest tests/test_scenario_engine.py tests/test_prompt_builder.py
```

## GitHub Mobile からの運用

GitHub Mobile からは、Issue を入口にする運用が一番扱いやすいです。

おすすめの流れ:

1. GitHub Mobile でこの repo を開く
2. Issue テンプレから依頼を作る
3. 目的、対象ファイル、完了条件を書く
4. ブラウザで Codespaces を開く
5. 実装して push する
6. GitHub Mobile で差分や PR を確認する

向いている依頼例:

- 吹き出しの文言をさらに短くしたい
- 別の IT 用語テンプレを追加したい
- 先生と生徒の音声チューニングを調整したい
- 画像プロンプトの回帰テストを追加したい

## Issue ラベル運用

この repo では次のラベル運用を想定しています。

- `task`: 通常の作業依頼
- `bug`: 不具合修正
- `enhancement`: 機能改善・新機能
- `docs`: README や手順書の更新
- `prompt`: プロンプトや表現調整
- `voice`: 音声チューニング関連

Issue テンプレには代表ラベルをあらかじめ設定しています。

## 注意事項

- `secrets/` は機密情報置き場なので commit しません
- `output/` は生成物なので commit しません
- `.venv/` はローカル環境なので commit しません
