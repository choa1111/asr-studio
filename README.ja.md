# ASR Studio

[简体中文](README.md) · [English](README.en.md) · [日本語](README.ja.md)

**音声や動画を、原文を確認しながら校正できる原稿へ。**

ASR Studio は、セルフホスト型の文字起こし・校正ワークベンチです。講義、画面録画、インタビューなどをアップロードし、音声認識モデルを選択します。必要に応じて参照資料を追加し、Markdown と TXT で書き出せます。元の認識結果と中間ファイルは、それぞれ独立して保存されます。

```text
音声・動画 → 文字起こし → 任意の参照テキスト・PDF OCR → AI 校正 → Markdown + TXT
```

ローカルの音声認識だけなら、校正 API は不要です。PDF の AI OCR と AI 校正には、ご自身の互換サービスと認証情報が必要です。ログイン認証は内蔵していないため、信頼できるローカル環境、またはアクセス制御されたネットワークで使用してください。

## 主な機能

- **3 言語のインターフェース**：簡体字中国語、英語、日本語。画面の言語と音声の言語は別々に設定できます。
- **複数の音声認識モデル**：Whisper、Qwen3-ASR に加え、Paraformer、Fun-ASR-Nano の追加連携も用意しています。対応機能や依存パッケージはモデルごとに異なります。
- **2 つの処理モード**：参照資料を使う校正と、参照資料を使わない対話の文字起こし・整理。
- **単一・一括処理**：ファイルのアップロード、ディレクトリの自動対応付け、共通の参照資料、YAML / JSON のタスク一覧に対応。
- **独立した PDF OCR**：PDF 1 冊またはディレクトリを処理し、完了したページを保存。不足ページだけを再試行して、TXT または ZIP をダウンロードできます。
- **処理過程の確認**：タスク状態、元の認識結果、参照テキスト、校正原稿、リクエスト診断を確認し、Markdown / TXT を取得できます。

## クイックスタート

Python **3.12**、Node.js **22**、npm、`ffmpeg` を用意してください。PDF を処理する場合は、Poppler の `pdftoppm` も必要です。プロジェクトのルートディレクトリで実行します。

```bash
python3.12 -m venv ".venv"
".venv/bin/python" -m pip install -r "requirements.txt"
npm --prefix "frontend" ci
npm --prefix "frontend" run build
TRANSCRIPT_PROFILE=local_cpu ".venv/bin/python" -m uvicorn api_server:app \
  --host 127.0.0.1 --port 8000 --workers 1
```

**http://127.0.0.1:8000** を開きます。API ドキュメントは `/docs`、ヘルスチェックは `/api/health` です。

- GPU がない場合は、明示的に `local_cpu` を選択してください。標準 YAML は GPU 向けです。Web 画面で保存した設定が環境変数の既定値より優先される場合もあります。
- 初回の文字起こしでは、モデルの重みをダウンロードすることがあります。依存パッケージのインストールだけでは、モデルのキャッシュや GPU 推論の動作までは確認できません。
- 文字起こしだけを行う場合は、ステージ実行画面で文字起こしを選び、音声をアップロードします。AI 校正サービスの設定は不要です。
- 開発時は `TRANSCRIPT_PROFILE=local_cpu ./start_web.sh` を使用できます。フロントエンドは `http://127.0.0.1:5173`、終了は `Ctrl+C` です。

環境構築やキャッシュの詳細は [起動ガイド](docs/QUICKSTART.md) を参照してください。この README からリンクする詳細ガイドは、現在は中国語で提供しています。

## 言語の設定

### 画面の言語

言語選択から **简体中文 / English / 日本語** を切り替えられます。設定は現在のブラウザに保存され、既定値は簡体字中国語です。言語を切り替えても、入力中のフォームや音声の言語設定は変わりません。

### 音声の言語

設定画面で既定の音声言語を保存するか、タスクごとに指定します。

| コード | 意味 |
| --- | --- |
| `zh` | 中国語。従来の既定値を維持 |
| `en` | 英語 |
| `ja` | 日本語 |
| `auto` | 対応する音声認識モデルで言語を自動判定 |

言語が分かっている場合は、特に短い音声や複数言語が混在する資料では、明示的な指定を推奨します。`auto` は言語の判定であり、翻訳ではありません。日本語・英語の文字起こしと校正は元の言語を維持し、中国語の発話は簡体字で出力します。画面の言語が原稿の言語を決めることはありません。

Whisper と Qwen には、選択した言語を各エンジンの形式で渡します。ほかの候補は実際の対応範囲を検査し、非対応の組み合わせではエラーを表示します。別のモデルへ自動的に切り替えることはありません。デュアル ASR では、両方のモデルが選択した言語に対応している必要があります。対応範囲、インストール、タイムスタンプの制限は [ASR モデルの説明](docs/ASR_BACKENDS.md) を参照してください。

CLI 用の言語設定は、従来どおり YAML の `asr.language` を使います。

```yaml
asr:
  language: ja
```

既存の設定ファイルの該当項目だけを変更してください。この例は設定ファイル全体ではありません。タスク側で省略した場合は既存の設定を継承します。過去のタスクは保存済みのスナップショットを使い、その後の画面言語や既定値の変更では書き換えられません。

公開の標準プロンプトは元の言語を保持します。既存の個人用プロンプトやタスク固有の指示は、自動的には上書きしません。中国語のみの出力を指定している場合は、日本語・英語の資料を処理する前に修正するか、新しいタスクで公開の標準指示に戻してください。

音声言語の変更によって、参照資料の OCR 言語が自動的に上書きされることはありません。Tesseract を使う場合は、資料に合わせて `reference.ocr_languages` を設定し、対応する言語パックをインストールしてください。日本語は `jpn`、英語は `eng` です。AI OCR も、翻訳せずに資料の元の言語を保持します。

## 録音から原稿を作る

1. 設定画面で ASR モデル、実行プロファイル、音声の言語を選びます。
2. AI 校正または PDF の AI OCR が必要な場合は、**Responses API** 互換の Base URL、クライアント API キー、サービスが実際に提供するモデル ID を設定します。アプリケーションがゲートウェイを構築することはありません。
3. 新しいタスクで処理モードを選び、資料をアップロードし、今回の設定を確認します。
4. タスク一覧で中間結果を確認し、Markdown / TXT をダウンロードします。一括処理では、成功したタスクの ZIP も取得できます。
5. 固有名詞、数値、否定、条件、引用、不確かな箇所を人手で確認してから、原稿を利用・公開してください。

### 参照資料を使う場合

既定の `reference` モードでは、TXT、Markdown、PDF、または Web ページの参照元が必要です。録音と参照資料のファイル名をそろえる必要はありません。

```bash
".venv/bin/python" "scripts/08_run_job.py" \
  --video "/path/to/recording.mp4" \
  --reference "/path/to/reference.txt" \
  --output-dir "/path/to/output" \
  --content-type reference --asr-language ja --profile local_cpu
```

### 参照資料のない対話の場合

`conversation` モードには、参照元を指定できません。次の例では英語の録音を処理します。

```bash
".venv/bin/python" "scripts/08_run_job.py" \
  --video "/path/to/interview.mp4" \
  --output-dir "/path/to/output" \
  --content-type conversation --asr-language en --profile local_cpu
```

リクエストとタスク一覧には `reference` / `conversation` を使ってください。それ以外の旧シナリオ名は受け付けません。`book_name` / `chapter` フィールドと `--book-name` / `--chapter` オプションは維持しており、任意の資料名や章・節を ASR のヒントとして渡せます。個人用の用語集は同梱していません。

一括処理、ステージ単位の実行、独立 PDF OCR、用語集、診断の詳細は [CLI・処理ガイド](docs/CLI_GUIDE.md) を参照してください。

## AI サービスとデータ

標準の AI バックエンド `codex_api` は、CPA（CLIProxyAPI）などの互換ゲートウェイの標準 `/v1/responses` エンドポイントに接続します。設定名は従来のものを維持していますが、codex-lb の導入は必須ではありません。Base URL にはサービスのルート、または `/v1` までの URL を指定します。完全な `/responses` エンドポイントは指定しないでください。

Web では設定画面から接続を保存します。スクリプトでは次の環境変数も使用できます。

```bash
export CODEX_LB_BASE_URL="https://api.example.com/v1"
export CODEX_LB_API_KEY="your-client-api-key"
```

上記のドメインとキーは例です。ご自身の接続情報に置き換え、サービスが対応しているモデル ID を指定してください。AI 校正と PDF OCR の高速モードは別々に設定し、どちらも既定では無効です。有効化すると料金が増える場合があります。

- 接続情報と API キーは `data/jobs/frontend-settings.json` に保存されます。認証情報を含むファイルとして扱い、アクセスを制限してください。
- アップロードは `data/uploads/`、タスクの設定・中間結果・出力は `data/jobs/<job_id>/` に保存します。ディレクトリ単位のステージは `data/intermediate/` と `data/output/` を使います。
- OCR と AI 校正では、対象の画像、文字起こし、参照テキストを設定先のサービスへ送信します。事前に資料の利用権限、プライバシーポリシー、費用を確認してください。
- ログや診断には、モデルの応答や原文が含まれることがあります。実行データ、スクリーンショット、環境設定、バックアップを公開しないでください。

[セキュリティとデータの説明](SECURITY.md) も確認してください。

## Docker・GPU 環境

標準の Docker 構成は NVIDIA GPU 向けです。まず、ホスト環境に合った読み取り専用チェックを実行します。

```bash
# ネイティブ Ubuntu + NVIDIA
bash "scripts/deploy_docker_linux.sh" --check

# WSL2 内のネイティブ Docker Engine + NVIDIA
bash "scripts/deploy_docker_wsl2.sh" --check
```

結果を確認したうえで、管理者が各ガイドに従ってインストールとデプロイを承認してください。コンテナの更新で実行中のタスクが中断される場合があります。`healthy` は、タスクが実行されていないことを意味しません。`docker compose down -v` でモデルキャッシュを削除したり、権限問題への対処として既存資料の所有者を再帰的に変更したりしないでください。

- [Docker のデプロイ、データボリューム、API 接続](docs/DOCKER.md)
- [ネイティブ Ubuntu の GPU デプロイと動作確認](docs/DOCKER_LINUX.md)
- [WSL2 のローカルインストール](docs/INSTALL_NEW_MACHINE.md)

## 開発・ドキュメント

```bash
".venv/bin/python" -m pip install -r "requirements-dev.txt"
".venv/bin/python" -m pytest
npm --prefix "frontend" run build
```

テストの成功だけでは、文字起こしの品質を保証できません。使用するモデル、言語、音声、機器に合った代表的な録音を人手で確認してください。追加 ASR SDK は、基本の Web / Whisper 環境を変更しないよう、独立した Python 環境で実行します。

| 確認したい内容 | 参照先 |
| --- | --- |
| インストールと最初のタスク | [クイックスタート](docs/QUICKSTART.md) |
| 一括処理、ステージ、OCR、トラブル対応 | [CLI・処理ガイド](docs/CLI_GUIDE.md) |
| モデル、言語、デュアル ASR、タイムスタンプ | [ASR モデルの説明](docs/ASR_BACKENDS.md) |
| 処理ステージと中間形式 | [パイプライン計画](docs/PIPELINE_PLAN.md) |
| コントリビューションと確認手順 | [貢献ガイド](CONTRIBUTING.md) |
| 開発ツールを用いた作業の履歴 | [Claude Code 作業記録](docs/CLAUDE_CODE_WORKLOG.md) |

## ライセンス

プロジェクト独自のコードには [MIT License](LICENSE) を適用しています。第三者のコード、依存パッケージ、モデルの重み、入力資料には、それぞれのライセンスが適用されます。[第三者ライセンスの説明](THIRD_PARTY_NOTICES.md) を参照してください。
