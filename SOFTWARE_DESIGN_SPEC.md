# ソフトウェア設計書

## 1. 文書情報
- 文書名: IT Terminology Manga-Explain Generator 設計書
- 版数: v0.4
- 更新日: 2026-03-20
- 状態: 更新中

## 2. プロジェクト概要
### 2.1 目的
IT用語を、キャラクターを用いた縦長漫画動画向けの素材として分かりやすく解説するため、9:16形式の脚本、画像、音声を自動生成する。

### 2.2 解決したい課題
- IT初学者にとって抽象的で理解しづらい用語を、例え話を中心に理解しやすくする
- 解説用コンテンツ制作の工数を下げる
- キャラクターや語り口の一貫性を保ちながら継続的に素材を生成する

### 2.3 想定ユーザー
- コンテンツ制作者
- IT教育用素材の作成者
- SNS向け縦長動画の企画・編集担当者

## 3. スコープ
### 3.1 MVPの対象範囲
- 入力されたIT用語に対して脚本を生成する
- シーンごとの画像生成プロンプトを生成する
- シーンごとの画像を生成する
- シーンごとの音声を生成する
- 画像、音声、メタデータをフォルダに出力する

### 3.2 MVPの対象外
- 最終動画の自動結合
- SNSへの自動投稿
- 複数ユーザー対応
- クラウド前提の大規模運用機能

## 4. 前提条件
- 実装言語は Python 3.12 とする
- 設定ファイル形式は JSON とする
- LLM の標準接続先は OpenAI 系 API とする
- OpenAI の運用標準モデルは gpt-4o に固定する
- 実行環境は macOS ローカル
- 操作形態は CLI
- AI接続は API 利用可
- 画像生成の第一候補は ComfyUI API
- 音声生成の第一候補は Style-BERT-VITS2 のローカル実行
- 画像アスペクト比は 9:16 を正式仕様とする
- 入力単位は単一用語のみとする
- 出力言語は日本語固定とする
- 既存作品キャラクターは使用しない
- 商用利用を前提とする
- 品質の最優先事項はキャラクターデザインの一貫性維持
- 登場人物は先生と生徒の二人構成とする
- 品質の次点はIT用語の説明精度と、画像内容の説明整合性

## 5. 成果物
- シーンごとの脚本
- シーンごとの画像ファイル
- シーンごとの音声ファイル
- 字幕用テキスト
- 各種生成条件を保持するメタデータ

## 6. 機能要件
### 6.1 入力管理
ユーザーは以下を入力できること。
- 対象用語
- 先生と生徒のキャラクター参照情報
- 決め台詞
- 解説トーン
- 任意の補足指示

### 6.2 脚本生成
システムは以下を満たす脚本を生成すること。
- 導入、解説、結びの三段構成であること
- IT初学者が理解できる難易度であること
- 例え話を含むこと
- 決め台詞を終盤に自然に含めること
- シーン単位に分割可能な粒度であること

### 6.3 シーン分割
システムは脚本を10から15程度のシーンに分割できること。
- 各シーンにナレーション文を持つこと
- 各シーンに画像生成用プロンプトを持つこと
- 各シーンに秒数見積もりを持つこと

### 6.4 画像生成
システムは各シーンごとに画像生成を実行できること。
- 先生と生徒のキャラクター参照情報を全シーンに反映すること
- シーン内容に応じた比喩図や小物を含められること
- 9:16 のアスペクト比で出力できること

### 6.5 音声生成
システムは各シーンごとに音声生成を実行できること。
- シーン本文を元に音声ファイルを出力すること
- 字幕用テキストを同時に保持すること
- 先生と生徒の固定話者をシーンごとに切り替え可能であること
- Style-BERT-VITS2 のローカル実行を標準経路として扱うこと
- 感情パラメータを原稿内容に応じて自動調整できること

### 6.6 出力管理
システムは生成物を再利用しやすい形式で保存すること。
- 画像出力
- 音声出力
- メタデータ出力
- 実行ログ出力

## 7. 非機能要件
### 7.1 品質
- キャラクターの顔、髪型、服装、雰囲気がシーン間で大きく崩れないこと
- 脚本内容と画像内容が矛盾しないこと
- 用語説明に重大な誤りがないこと

### 7.2 保守性
- モジュール単位で責務分離されていること
- AIプロバイダを差し替えやすいこと
- 生成パラメータを設定ファイル化できること

### 7.3 再現性
- 同一入力に対して生成条件を記録できること
- 実行日時、モデル、プロンプト、主要パラメータをメタデータに残すこと

### 7.4 性能
- MVPでは速度最適化より品質優先とする
- ただし1回の実行が極端に長時間化しないよう、シーン単位の再実行を可能にする

### 7.5 セキュリティ
- APIキーをファイルに直書きしないこと
- 機密情報は環境変数またはローカル設定ファイルで管理すること

### 7.6 権利・利用条件
- 既存作品のキャラクターに依拠する入力や生成を避けること
- 商用利用時に利用モデルと生成素材の利用条件を追跡できること
- 使用したモデルと素材条件をメタデータに残せること

## 8. 想定アーキテクチャ
```text
CLI
  -> Input Manager
  -> Scenario Engine
  -> Prompt Builder
  -> Image Generator Adapter
  -> Voice Generator Adapter
  -> Output Writer
  -> Metadata Logger
```

## 9. モジュール設計
### 9.1 CLI
責務:
- ユーザー入力の受け取り
- 実行モードの指定
- 設定ファイルの読み込み
- 実行結果の表示

想定コマンド例:
```bash
python -m termbase generate --config ./config/project.json
```

### 9.2 Input Manager
責務:
- CLI引数と設定ファイルを統合する
- 必須入力の妥当性を検証する
- 内部処理用の正規化済み入力オブジェクトを作る

入力項目案:
- term
- character_reference_root_dir
- opening_template
- ending_template
- tone
- target_duration_sec
- scene_count
- image_aspect_ratio
- output_dir

### 9.3 Scenario Engine
責務:
- 用語の解説方針を決める
- 三段構成の脚本を生成する
- シーン分割済みのナレーション文を出力する
- OpenAI 系 API 向けのシステムプロンプトとユーザープロンプトを組み立てる

入出力:
- 入力: 正規化済みユーザー入力
- 出力: scene 配列を含む脚本データ

### 9.4 Prompt Builder
責務:
- 先生と生徒の固定要素をプロンプト先頭に付与する
- 話者ロールと表情指定に応じて参照画像セットから適切な画像を選ぶ
- シーン本文から画像生成向けの視覚表現を抽出する
- 禁止事項やネガティブプロンプトを付与する

### 9.5 Image Generator Adapter
責務:
- 画像生成エンジンへの要求変換
- 画像ファイルの保存
- エラー時の再実行制御

候補:
- ComfyUI API を標準実装とする
- 必要に応じて Stable Diffusion 直実行アダプタを追加可能とする

### 9.6 Voice Generator Adapter
責務:
- 音声合成エンジンへの要求変換
- シーンごとの音声出力
- 字幕テキストの保存
- 先生と生徒の固定話者モデルを切り替える
- 原稿内容に応じて感情パラメータを調整する

候補:
- Style-BERT-VITS2 のローカル実行を標準実装とする
- 将来的に他エンジンを差し替え可能とする

### 9.7 Output Writer
責務:
- 出力フォルダ構成の生成
- 命名規則の統一
- 生成ファイルとメタデータの保存

## 9.9 Character Reference Manager
責務:
- 先生用と生徒用の参照画像ディレクトリを検証する
- 各ロールの必須ファイルの有無を確認する
- ロール名と表情名から参照画像パスを解決する
- 画像生成時に使用するロール別画像セットを返す

配置先:
- assets/character_refs/teacher/
- assets/character_refs/student/

運用ルール:
- 先生用10枚、生徒用10枚の計20枚を必須とする
- 背景透過PNGを必須とする
- 画像構図はバストアップで統一する
- 画像サイズは長辺1024px以上を推奨とする
- ファイル名は固定命名規則に従う

### 9.8 Metadata Logger
責務:
- 使用モデル
- 入力パラメータ
- 生成プロンプト
- 実行結果
- エラー情報
を保存する

## 10. データ設計
### 10.1 入力データモデル案
```json
{
  "term": "DNS",
  "character_reference_root_dir": "./assets/character_refs",
  "opening_template": "ねえ、{term}の意味を説明してって言われたら、少しドキッとしませんか？ このチャンネルではエンジニア1〜3年目で必要な知識を短く整理していきます。では、{term}を簡単に説明するとどうなるのでしょうか。",
  "ending_template": "{term}の説明、できるようになりましたか？ もっと深掘りしたい方はチャンネル登録をして、横向きの解説動画やほかのショート動画もぜひ見てみてください。",
  "tone": "熱血",
  "target_duration_sec": 150,
  "scene_count": 12,
  "image_aspect_ratio": "9:16",
  "output_dir": "./output",
  "llm_provider": "openai",
  "llm_model": "gpt-4o",
  "voice_models": {
    "teacher": "teacher_voice_model",
    "student": "student_voice_model"
  }
}
```

### 10.1.1 キャラクター参照画像仕様
必須枚数:
- 先生用10枚
- 生徒用10枚
- 合計20枚

必須形式:
- PNG
- 背景透過あり
- バストアップ
- 同一ロール内では同一キャラクター、同一衣装、同一基本画風で統一

ディレクトリ構成:
- assets/character_refs/teacher/
- assets/character_refs/student/

先生用必須ファイル名:
- teacher_01_neutral.png
- teacher_02_happy.png
- teacher_03_smile.png
- teacher_04_surprised.png
- teacher_05_confused.png
- teacher_06_explaining.png
- teacher_07_serious.png
- teacher_08_thinking.png
- teacher_09_sad.png
- teacher_10_angry.png

生徒用必須ファイル名:
- student_01_neutral.png
- student_02_happy.png
- student_03_smile.png
- student_04_surprised.png
- student_05_confused.png
- student_06_explaining.png
- student_07_serious.png
- student_08_thinking.png
- student_09_sad.png
- student_10_angry.png

表情採用理由:
- neutral: 基本状態
- happy: 成功や肯定
- smile: 柔らかい導入や締め
- surprised: 意外性のある説明
- confused: 問題提起
- explaining: 解説の中心
- serious: 重要ポイントの強調
- thinking: 比喩導入や整理
- sad: 失敗例や困りごと
- angry: 強い注意喚起

運用補足:
- シーン生成では先生は explaining と serious を中心に使い、生徒は confused と surprised を中心に使う
- 話者と画像上の主役ロールをシーンごとに記録する
- 追加表情を将来拡張する場合でも、上記10枚を最小必須セットとする

### 10.2 シーンデータモデル案
```json
{
  "scene_id": 1,
  "title": "導入",
  "speaker_role": "student",
  "primary_visual_role": "student",
  "expression": "confused",
  "narration": "Webサイト名を入れたのに、どこへアクセスすればいいか分からない。",
  "image_prompt": "...",
  "negative_prompt": "...",
  "emotion_parameters": {
    "style": "困惑",
    "intensity": 0.72
  },
  "duration_sec": 12,
  "subtitle": "Webサイト名を入れたのに、どこへアクセスすればいいか分からない。",
  "image_file": "images/001.png",
  "audio_file": "audios/001.wav"
}
```

### 10.3 メタデータ案
```json
{
  "run_id": "20260320-120000",
  "term": "DNS",
  "models": {
    "llm": "gpt-4o",
    "image": "comfyui-api",
    "voice": "style-bert-vits2"
  },
  "settings": {
    "scene_count": 12,
    "aspect_ratio": "9:16"
  },
  "character_references": {
    "root_directory": "./assets/character_refs",
    "roles": {
      "teacher": {
        "directory": "./assets/character_refs/teacher",
        "required_count": 10
      },
      "student": {
        "directory": "./assets/character_refs/student",
        "required_count": 10
      }
    }
  },
  "voice_models": {
    "teacher": "teacher_voice_model",
    "student": "student_voice_model"
  },
  "scenes": []
}
```

### 10.4 設定ファイル仕様
設定ファイルは JSON とし、MVPでは単一の project.json を読み込む。

スキーマファイル:
- config/project.schema.json

必須キー:
- term
- character_reference_root_dir
- opening_template
- ending_template
- tone
- target_duration_sec
- scene_count
- image_aspect_ratio
- output_dir
- llm_provider
- llm_model
- voice_models

任意キー:
- openai_base_url
- image_backend
- image_workflow_path
- voice_backend
- retry_count
- additional_instructions

## 11. 出力フォルダ構成
```text
assets/
  character_refs/
    teacher/
      teacher_01_neutral.png
      teacher_02_happy.png
      teacher_03_smile.png
      teacher_04_surprised.png
      teacher_05_confused.png
      teacher_06_explaining.png
      teacher_07_serious.png
      teacher_08_thinking.png
      teacher_09_sad.png
      teacher_10_angry.png
    student/
      student_01_neutral.png
      student_02_happy.png
      student_03_smile.png
      student_04_surprised.png
      student_05_confused.png
      student_06_explaining.png
      student_07_serious.png
      student_08_thinking.png
      student_09_sad.png
      student_10_angry.png
config/
  project.json
output/
  run_YYYYMMDD_HHMMSS/
    images/
      001.png
    audios/
      001.wav
    scripts/
      metadata.json
      storyboard.json
    logs/
      run.log
```

## 12. 処理フロー
1. CLIで JSON 設定ファイルを受け取る
2. 設定値と先生用・生徒用の参照画像ディレクトリを検証する
3. OpenAI 系 API で脚本とシーン構成を生成する
4. 各シーンの話者ロール、主役ロール、必要な表情を決定する
5. 各シーンの画像生成プロンプトと感情パラメータを構築する
6. ComfyUI API で各シーン画像を生成する
7. Style-BERT-VITS2 で先生・生徒の固定話者を使い、各シーン音声を生成する
8. メタデータとログを保存する
9. 実行結果を一覧表示する

## 13. 品質保証方針
### 13.1 受け入れ観点
- 同一キャラクターとして視認できるか
- 用語説明が初学者に伝わるか
- シーン順が自然か
- 決め台詞が不自然でないか
- 出力ファイルが欠損なく揃うか

### 13.2 テスト方針
- 入力検証の単体テスト
- 先生用・生徒用の参照画像20枚セットの検証テスト
- ファイル命名規則の検証テスト
- シーンデータ構造の整合性テスト
- 話者ロールと感情パラメータの整合性テスト
- 出力ファイル命名規則のテスト
- 外部APIアダプタの結合テスト
- 実サンプル用語での手動評価

## 14. リスクと対策
### 14.1 キャラ崩れ
対策:
- 参照画像を必須化する
- 先生用・生徒用に表情別の固定ファイル名で参照画像セットを運用する
- 共通プロンプト断片を固定化する
- 必要に応じて ControlNet や reference 系機能を採用する

### 14.2 説明品質のばらつき
対策:
- 脚本生成テンプレートを固定化する
- 用語説明の禁止事項と必須要素を定義する
- レビュー用メタデータを残す

### 14.3 API依存
対策:
- アダプタ層でプロバイダ差し替え可能にする
- API失敗時の再試行方針を持つ

## 15. 未確定事項
- Style-BERT-VITS2 の先生用・生徒用の具体的なモデル名
- 感情パラメータのマッピング規則の詳細値

## 16. 実装の推奨方針
### 16.1 推奨技術スタック
- Python 3.12
- CLI ライブラリは Typer
- データモデルは Pydantic
- HTTP クライアントは httpx
- テストは pytest

### 16.2 実装開始時の最小ディレクトリ構成案
```text
src/
  termbase/
    cli.py
    config.py
    models.py
    services/
      scenario_engine.py
      prompt_builder.py
      character_reference_manager.py
    adapters/
      openai_llm.py
      comfyui_image.py
      style_bert_vits2_voice.py
    writers/
      output_writer.py
      metadata_logger.py
tests/
  test_config.py
  test_character_reference_manager.py
  test_models.py
```

## 17. 次に確定すべき内容
- MVP後の拡張計画
- Style-BERT-VITS2 の先生用・生徒用のモデル名
- 感情パラメータの詳細マッピング表

## 18. CLI詳細仕様
### 18.1 コマンド一覧
MVPで提供するコマンドは以下の3種類とする。

1. generate
設定ファイルを読み込み、脚本、画像、音声、メタデータを生成する。

2. validate-config
設定ファイルが JSON Schema と業務ルールを満たすか検証する。

3. validate-assets
先生用・生徒用の参照画像ディレクトリの必須ファイルと形式を検証する。

### 18.2 コマンド例
```bash
python -m termbase generate --config ./config/project.json
python -m termbase validate-config --config ./config/project.json
python -m termbase validate-assets --character-root ./assets/character_refs
```

### 18.3 generate のオプション
- --config: 設定ファイルパス。必須
- --output-dir: 出力先の上書き指定。任意
- --scene-start: 途中シーンから再実行する開始番号。任意
- --scene-end: 再実行の終了シーン番号。任意
- --skip-images: 画像生成をスキップする。任意
- --skip-audio: 音声生成をスキップする。任意
- --dry-run: 外部生成を行わず、脚本とプロンプト構築のみ行う。任意

### 18.4 終了コード
- 0: 正常終了
- 1: 想定外エラー
- 2: 設定値エラー
- 3: 参照画像エラー
- 4: OpenAI API 呼び出しエラー
- 5: ComfyUI API 呼び出しエラー
- 6: Style-BERT-VITS2 呼び出しエラー
- 7: 出力書き込みエラー

### 18.5 標準出力方針
- 実行開始時に run_id を表示する
- 各フェーズ開始時に phase 名を表示する
- シーン単位の進捗は scene 番号と結果を表示する
- 異常終了時は原因カテゴリと再実行対象を表示する

## 19. JSON Schema詳細
### 19.1 スキーマ適用方針
- 構文検証は JSON Schema で行う
- 業務ルール検証は Input Manager と Character Reference Manager で行う
- JSON Schema では存在、型、列挙値、数値範囲を保証する

### 19.2 業務ルールで検証する項目
- character_reference_root_dir が実在すること
- 先生用10枚と生徒用10枚が固定名で揃っていること
- scene_count が 10 から 15 の範囲であること
- target_duration_sec が scene_count と比較して極端に短すぎないこと
- image_workflow_path を指定した場合、実ファイルが存在すること
- voice_models.teacher と voice_models.student が指定されていること

### 19.3 設定値の標準値
- llm_provider: openai
- llm_model: gpt-4o
- image_backend: comfyui
- voice_backend: style-bert-vits2
- retry_count: 2
- image_aspect_ratio: 9:16

## 20. モジュールI/O仕様
### 20.1 Config Loader
入力:
- config_path: Path

出力:
- AppConfig

失敗条件:
- JSON 構文エラー
- Schema 不一致
- 必須キー欠落

### 20.2 Character Reference Manager
入力:
- character_reference_root_dir: Path

出力:
- CharacterReferenceSet

主なフィールド:
- base_dir
- teacher_expressions
- student_expressions
- primary_teacher_image
- primary_student_image
- validation_summary

失敗条件:
- 先生用または生徒用の必須10ファイルの不足
- PNG以外の拡張子
- 背景透過前提に反する画像

### 20.3 Scenario Engine
入力:
- AppConfig
- CharacterReferenceSet

出力:
- Storyboard

Storyboard の主な内容:
- term
- summary
- scenes
- llm_prompt_log

失敗条件:
- OpenAI API エラー
- 期待 JSON 形式での応答失敗
- scene_count 不整合

### 20.4 Prompt Builder
入力:
- Storyboard
- CharacterReferenceSet

出力:
- PromptBundle の配列

PromptBundle の主な内容:
- scene_id
- speaker_role
- primary_visual_role
- expression_name
- reference_image_path
- positive_prompt
- negative_prompt
- composition_notes

### 20.5 Image Generator Adapter
入力:
- PromptBundle
- AppConfig

出力:
- ImageArtifact

ImageArtifact の主な内容:
- scene_id
- file_path
- width
- height
- generation_seed
- backend_response

### 20.6 Voice Generator Adapter
入力:
- Scene
- AppConfig

出力:
- AudioArtifact

AudioArtifact の主な内容:
- scene_id
- speaker_role
- file_path
- duration_ms
- subtitle
- emotion_parameters
- backend_response

### 20.7 Output Writer
入力:
- AppConfig
- Storyboard
- ImageArtifact の配列
- AudioArtifact の配列

出力:
- OutputManifest

OutputManifest の主な内容:
- run_id
- output_root
- images_dir
- audios_dir
- scripts_dir
- logs_dir

### 20.8 Metadata Logger
入力:
- AppConfig
- Storyboard
- PromptBundle の配列
- ImageArtifact の配列
- AudioArtifact の配列
- 実行ログ要約

出力:
- metadata.json
- storyboard.json

## 21. フェーズ別エラーハンドリング方針
### 21.1 基本方針
- 品質優先のため、MVPでは不完全な成果物を黙って成功扱いしない
- 失敗時は即座に中断し、失敗フェーズと対象シーンを明示する
- 途中まで成功した成果物は削除せず残し、再実行に利用できるようにする

### 21.2 再試行方針
- 設定値エラーと参照画像エラーは再試行しない
- OpenAI API、ComfyUI API、Style-BERT-VITS2 の一時エラーは最大2回まで再試行する
- 再試行間隔は 2 秒、4 秒の指数バックオフとする

### 21.3 フェーズ別ルール
設定読み込みフェーズ:
- 失敗時は終了コード 2 で終了する

参照画像検証フェーズ:
- 失敗時は不足ファイル名一覧を表示し、終了コード 3 で終了する

脚本生成フェーズ:
- OpenAI 応答が JSON として解釈できない場合は1回だけ再整形要求を行う
- 再整形後も不正なら終了コード 4 で終了する

画像生成フェーズ:
- シーン単位で再試行する
- retry_count を超えたシーンが1つでもあれば終了コード 5 で終了する

音声生成フェーズ:
- シーン単位で再試行する
- retry_count を超えたシーンが1つでもあれば終了コード 6 で終了する

メタデータ保存フェーズ:
- 保存失敗時は終了コード 7 で終了する
- ただし一時ファイルが残っている場合はその場所を表示する

### 21.4 ログ出力方針
- logs/run.log に時刻、phase、scene_id、level、message を1行単位で出力する
- metadata.json に最終ステータスと失敗理由を保持する
- 外部APIの生レスポンスは全文保存せず、必要最小限の要約のみを残す

## 22. 受け入れ基準
### 22.1 自動受け入れ基準
- validate-config が正常終了すること
- validate-assets が正常終了すること
- generate 実行後に images、audios、scripts、logs が作成されること
- storyboard.json の scene 数が設定値と一致すること
- 全 scene に speaker_role、expression、narration、subtitle、image_prompt、audio_file、image_file が存在すること
- metadata.json に models、settings、character_references、voice_models、scenes が存在すること

### 22.2 品質受け入れ基準
- 10 から 15 シーン以内で導入、解説、結びが成立していること
- 決め台詞が最終3シーン以内に含まれること
- 各シーン画像が 9:16 で出力されること
- 先生と生徒の見た目がそれぞれ一貫していること
- 説明の流れに沿って表情が不自然でないこと
- 同一人物として視認困難なレベルのキャラ崩れが主要シーンで発生しないこと

### 22.3 手動レビュー基準
- IT用語の説明に重大な誤りがない
- 例え話が用語理解に寄与している
- 初学者が読んで意味を追える日本語になっている
- 先生と生徒の役割分担が自然である
- 画像内の小物や構図がナレーションと矛盾しない
- 音声読み上げで不自然な読みやアクセント崩れが許容範囲内である
- 感情パラメータが原稿の温度感と大きく乖離していない

## 23. 手動レビュー工程
### 23.1 レビュータイミング
- 初回MVPでは generate 完了後にまとめてレビューする
- 将来拡張では脚本生成後レビューの中間停止を追加候補とする

### 23.2 レビュー対象ファイル
- scripts/storyboard.json
- scripts/metadata.json
- images/*.png
- audios/*.wav

### 23.3 レビュー結果の扱い
- 脚本修正が必要な場合は additional_instructions を更新して再生成する
- 特定シーンのみ差し替える場合は --scene-start と --scene-end を使う
- キャラ崩れが多い場合は参照画像セットの見直しを優先する