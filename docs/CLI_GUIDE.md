# 命令行与处理指南

从现成音频得到原始转录、批量整理多份录屏，或只识别 PDF，都可以使用项目已有脚本。命令在项目根目录执行，Python 始终使用 `.venv/bin/python`。首次安装见 [快速启动](QUICKSTART.md)，界面及语言设置见 [README](../README.md)。

## 选对任务模式与配置

- `reference`：默认模式，必须提供本地 TXT / Markdown / PDF 或网页参考源。
- `conversation`：无参考对谈整理，不接受参考源；主链不经过参考文本提取。
- `--config` 指定完整 YAML；默认读取 `config/settings.yaml`，旧的 `config/setting.yaml` 不是默认入口。
- profile 优先级为 `--profile` > `TRANSCRIPT_PROFILE` > YAML 的 `runtime.profile`。Web 新任务还会使用已保存的 Web 默认值；旧任务重试沿用快照。
- 没有 GPU 时使用 `local_cpu`；更高精度 CPU 为 `local_cpu_high_accuracy`。GPU 可选 `wsl2_gpu`、`wsl2_gpu_high_accuracy`、`wsl2_gpu_max_accuracy`，名称沿用历史配置，也可用于满足依赖的原生 Linux。
- 音频语言使用 `--asr-language zh|en|ja|auto`，省略时继承配置。已知语种尽量明确指定；模型不支持该语种时会报错，不自动切换候选。

`book_name` / `chapter` 及对应 CLI 参数保留，表示材料名称与章节或部分，用于构造 ASR 术语提示，不决定最终输出文件名。任务对外复制的文件名使用输入录屏标题；中间工作区使用统一的 `source` basename。

## 单任务：参考材料与无参考对谈

日语录屏结合参考材料校对：

```bash
".venv/bin/python" "scripts/08_run_job.py" \
  --video "/path/to/recording.mp4" \
  --reference "/path/to/reference.txt" \
  --output-dir "/path/to/output" \
  --content-type reference --asr-language ja --profile local_cpu
```

英语对谈，不提供参考源：

```bash
".venv/bin/python" "scripts/08_run_job.py" \
  --video "/path/to/interview.mp4" \
  --output-dir "/path/to/output" \
  --content-type conversation --asr-language en --profile local_cpu
```

每次运行创建独立的 `data/jobs/<job_id>/`，保存输入副本、生成配置、原始 ASR、参考文本、校对结果与日志。最终 Markdown 和 TXT 会额外复制到 `--output-dir`。不要直接覆盖旧任务的上游文件来模拟新任务。

### 显式附加术语

```bash
".venv/bin/python" "scripts/08_run_job.py" \
  --video "/path/to/recording.mp4" \
  --reference "/path/to/reference.txt" \
  --output-dir "/path/to/output" \
  --book-name "示例材料" --chapter "第一部分" \
  --glossary-file "/path/to/terms.txt" \
  --asr-language zh --profile local_cpu
```

术语文件每行一个词条。默认不加载内置私人词库；中文术语不一定适合日英录音，先检查本次实际提示词。不同引擎对术语的支持与长度限制见 [ASR 说明](ASR_BACKENDS.md)。

### 选择 ASR 与 AI 后端

`--asr-candidate` 选择转录模型；`--backend` / `--model` 属于后续 AI 校对，不是 ASR 模型参数。

```bash
".venv/bin/python" "scripts/08_run_job.py" \
  --video "/path/to/recording.mp4" \
  --reference "/path/to/reference.txt" \
  --output-dir "/path/to/output" \
  --asr-candidate whisper-existing --asr-language en \
  --backend codex_api --profile local_cpu
```

可用 AI 后端为 `codex_api`、`codex_cli`、`agy`、`both`。默认 API 后端要求可用的 Responses API 服务与模型 ID；CLI 后端需自行安装、登录。`both` 仅表示旧的 `codex_cli + agy`，不是两个 ASR，也不包括 `codex_api`；双 AI 结果需人工选择，不会自动选定最终稿。

`--model`、`--reasoning-effort`、`--ocr-model`、`--ocr-reasoning-effort` 可覆盖本次模型参数。使用前运行相应脚本的 `--help`，并核对服务实际支持的 ID。

### 可选双 ASR

```bash
".venv/bin/python" "scripts/08_run_job.py" \
  --video "/path/to/recording.mp4" \
  --reference "/path/to/reference.txt" \
  --output-dir "/path/to/output" \
  --asr-candidate whisper-existing \
  --secondary-asr-candidate qwen3-asr-0.6b \
  --asr-language ja --profile wsl2_gpu_high_accuracy
```

主、辅候选必须不同且均支持所选语言。两次转录串行执行并分别保留；只有同源配对完整时才允许联合校对。默认仍是单 ASR；额外模型会增加耗时及校对输入费用。完整规则见 [双 ASR 联合校对](ASR_BACKENDS.md#双-asr-联合校对可选)。

## 批量任务

### 清单：逐条指定资料与语言

创建自己的 `jobs.yaml`，例如：

```yaml
jobs:
  - video: /data/videos/session-01.mp4
    reference: /data/reference/session-01.txt
    output_dir: /data/output
    content_type: reference
    asr_language: ja
    book_name: 示例材料
    chapter: 第一部分

  - video: /data/videos/interview-02.mp4
    output_dir: /data/output
    content_type: conversation
    asr_language: en
```

```bash
".venv/bin/python" "scripts/09_run_batch_jobs.py" \
  --manifest "/path/to/jobs.yaml" \
  --remote-concurrency 2 --profile local_cpu
```

条目省略语言时继承批次的语言覆盖或原配置。不要把界面 locale 写入 `asr_language`；这里使用 `zh`、`en`、`ja`、`auto`，不是 `zh-CN`。

### 目录自动配对

录屏和参考资料按 basename 配对，例如 `session-01.mp4` 对应 `session-01.txt`。每份录屏可以使用不同格式的参考文件。

```bash
".venv/bin/python" "scripts/09_run_batch_jobs.py" \
  --videos-dir "/data/videos" \
  --reference-dir "/data/reference" \
  --output-dir "/data/output" \
  --asr-language ja --profile local_cpu
```

### 共享参考材料

```bash
".venv/bin/python" "scripts/09_run_batch_jobs.py" \
  --videos-dir "/data/videos" \
  --shared-reference "/data/reference/shared.txt" \
  --output-dir "/data/output" \
  --asr-language en --profile local_cpu
```

共享参考也可以是公开网页 URL。无参考对谈目录使用 `--content-type conversation`，不提供参考目录或共享参考。

ASR 与音频抽取按现有本地资源规则执行；远程阶段并发由 `--remote-concurrency` 控制。批次状态、清单和摘要保存到 `data/jobs/batches/<batch_id>/`。退出码 `0` 表示全部成功，`2` 表示部分失败，`1` 表示全部失败或入口参数无效；请检查失败子任务而不是仅重跑整批。

## 只运行某个阶段

目录式阶段处理的是当前配置绑定的数据目录，不要误用真实资料目录进行验证。Web 另有隔离的上传文件阶段入口，见页面说明。

| 阶段 | 脚本 | 统一入口的阶段名 |
| --- | --- | --- |
| 音频抽取 | `scripts/01_extract_audio.py` | `extract-audio` |
| 语音转录 | `scripts/02_transcribe.py` | `transcribe` |
| 参考文本提取 | `scripts/03_prepare_reference.py` | `prepare-reference` |
| 块级对齐（辅助） | `scripts/04_align.py` | `align` |
| 候选分类（辅助） | `scripts/05_classify.py` | `classify` |
| AI 校对 | `scripts/06_refine.py` | `refine` |
| Markdown / TXT 导出 | `scripts/07_export_markdown.py` | `export-markdown` |

先将英语音频放入配置的 `audio_dir`，再只运行转录：

```bash
".venv/bin/python" "scripts/02_transcribe.py" \
  --asr-language en --profile local_cpu
```

其他阶段可通过统一入口运行：

```bash
".venv/bin/python" "scripts/run_pipeline.py" --stage prepare-reference
".venv/bin/python" "scripts/run_pipeline.py" --stage export-markdown
```

当前参考型主链为音频抽取 → 转录 → 参考文本提取 → 校对 → 导出；`align` / `classify` 是辅助调试，不是成稿必经阶段。`scripts/00_run_main_pipeline.py` 用于当前配置目录的整链处理。保留任务的中间 JSON / TXT，便于定位问题。

英文和日文正文由转录/校对保留原语言。候选分类依赖可配置规则，不应把中文默认关键词当作日英分类质量已验收的证明。

## 独立 PDF OCR 与文本整合

独立 OCR 不要求录屏，也不读取流水线的参考目录：

```bash
".venv/bin/python" "scripts/10_ocr_pdf_books.py" \
  "/path/to/books" --output-dir "/path/to/ocr-text"
```

目录会递归扫描 PDF，并保留子目录结构；默认输出为 `output/pdf/ocr/`。需要 `pdftoppm`、可用的 OCR API 与模型。完整 TXT 只在所有页面成功后发布。Web 独立 OCR 保留逐页检查点，可以重试不足页面，并下载完整文件或 TXT ZIP。删除项目需确认，运行中禁止删除；保留上传 PDF。当前不导出 EPUB。

AI OCR 保留材料原语言。使用 Tesseract 回退时，按材料设置 `reference.ocr_languages` 并安装相应语言包；不要把音频语言与参考文本语言强行绑定。

逐页 OCR 合并会加入独立的物理页边界标记：

```text
----- OCR_PAGE_BREAK: 1 -> 2 -----
```

页边界不是自然段边界。校对输入保留标记用于衔接，最终原稿不显示标记；原参考 TXT 不回改。普通书籍横线、正文数字和不完整标记不会当作页边界删除。

已有普通 TXT 片段可以离线整合：

```bash
".venv/bin/python" "scripts/11_integrate_ocr_txt.py" \
  "/path/to/text-parts" --output "/path/to/integrated.txt"
```

片段按自然文件名顺序排列，不覆盖源文件。该工具不知道 PDF 页码，不生成物理页标记，也不等同于从 OCR 页检查点重建整本资料。缺页检查点重建可能触发 OCR 请求，不能当作必然离线操作。

## 定位错误与保护证据

- **转录无法启动**：检查候选依赖、设备、模型缓存、语言支持范围及 profile。不要在报错后静默换模型冒充原任务成功。
- **短语音或混合语言误识别**：优先明确指定语种，检查原始 ASR 与实际语言 metadata；自动检测可能误判。
- **PDF 缺页**：查看失败页码，独立 OCR 优先重试缺失页，保留已成功页的检查点。
- **校对失败**：核对 API 地址、客户端 Key、模型 ID 和服务错误；`/api/health` 正常不表示远端 API 可用。
- **任务已中断**：检查状态与原产物后重试；网页刷新或容器重启不保证自动续跑业务任务。更换模型组合应新建任务。

阶段 6 汇总诊断位于目录式 `data/output/logs/refine/diagnostics.json`，或任务内 `data/jobs/<job_id>/output/logs/refine/diagnostics.json`。汇总会列出每次尝试的诊断目录，记录脱敏请求摘要、传输指标、SSE、提取正文、解析和最终校验原因。请求摘要不保存 API Key、Authorization 或提示词正文，但完整模型响应可能含敏感原文；这些目录不应公开。

日志不自动截断或清理历史诊断，长任务需预留磁盘并制定备份策略。最终稿仍需人工终审；程序成功、时间戳有效和文字准确是不同的检查。安全与部署要求分别见 [SECURITY.md](../SECURITY.md) 和 [Docker 说明](DOCKER.md)。
