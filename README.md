# ASR Studio

[简体中文](README.md) · [English](README.en.md) · [日本語](README.ja.md)

**把音视频整理成可校对、可追溯的文稿。**

ASR Studio 是可自行部署的转录与人工校对工作台。上传录屏、讲座或访谈材料，选择转录模型，按需加入参考文本，导出 Markdown 和 TXT；原始转录与中间结果独立保留。

```text
音视频 → 语音转录 → 可选参考文本 / PDF OCR → AI 校对 → Markdown + TXT
```

本地 ASR 不需要校对 API；PDF AI OCR 和 AI 校对需要你自己的兼容服务与凭据。应用没有内置登录鉴权，只应在可信本机或受访问控制的网络运行。

## 可以做什么

- **三语界面**：简体中文、English、日本語，界面语言与音频语言独立设置。
- **多模型转录**：Whisper、Qwen3-ASR；还保留可选 Paraformer、Fun-ASR-Nano 接入，各模型能力和依赖不同。
- **两种整理方式**：有参考材料的校对，或无参考材料的对谈转录整理。
- **单任务与批量处理**：上传文件、目录配对、共享参考源或 YAML / JSON 清单。
- **独立 PDF OCR**：识别单本或目录中的 PDF，保留成功页检查点，重试缺失页，下载 TXT 或 ZIP。
- **可追溯结果**：查看任务状态、原始 ASR、参考文本、校对草稿与调用诊断，下载 Markdown / TXT。

## 快速启动

准备 Python **3.12**、Node.js **22**、npm 和 `ffmpeg`。处理 PDF 还需要 Poppler 的 `pdftoppm`。在项目根目录执行：

```bash
python3.12 -m venv ".venv"
".venv/bin/python" -m pip install -r "requirements.txt"
npm --prefix "frontend" ci
npm --prefix "frontend" run build
TRANSCRIPT_PROFILE=local_cpu ".venv/bin/python" -m uvicorn api_server:app \
  --host 127.0.0.1 --port 8000 --workers 1
```

打开 **http://127.0.0.1:8000**。接口文档在 `/docs`，健康检查在 `/api/health`。

- 无 GPU 时明确选择 `local_cpu`；默认 YAML 面向 GPU，网页已保存的默认设置也可能覆盖环境选择。
- 第一次转录可能下载模型。模型依赖已安装，不代表权重已缓存或 GPU 推理已验收。
- 只想转文字：打开“单阶段运行”，选择语音转录并上传音频，无需配置 AI 校对服务。
- 开发时使用 `TRANSCRIPT_PROFILE=local_cpu ./start_web.sh`，前端地址为 `http://127.0.0.1:5173`；`Ctrl+C` 停止前后端。

安装、缓存和运行环境细节见 [快速启动](docs/QUICKSTART.md)。

## 语言设置

### 界面语言

在页面语言选择器切换 **简体中文 / English / 日本語**。偏好保存在当前浏览器，默认简体中文。切换界面不会清空当前表单，也不会改变任务的音频语言。

### 音频语言

在“运行设置”保存默认音频语言，也可在任务中单独选择：

| 代码 | 用途 |
| --- | --- |
| `zh` | 中文，兼容既有默认配置 |
| `en` | 英语 |
| `ja` | 日语 |
| `auto` | 由支持的转录模型检测音频语言 |

已知录音语言时优先明确指定，尤其是短片段和混合语言材料。`auto` 是语种检测，不是翻译。英语、日语转录与校对保留原语言；中文讲话使用简体中文。界面语言不决定文稿语言。

Whisper 与 Qwen 的语言参数会传入各自引擎；其他候选按实际支持能力校验，不支持的组合会报错，不会静默换模型。双 ASR 的两个候选都需要支持所选语言。具体范围、安装方式和时间戳限制见 [ASR 模型说明](docs/ASR_BACKENDS.md)。

命令行配置仍使用已有 YAML 中的 `asr.language`，例如：

```yaml
asr:
  language: ja
```

只修改现有配置的这一项，不要用这个片段替换完整配置。省略任务覆盖时继承已有配置；旧任务保留自己的快照，不会因后来切换界面或默认语言而被改写。

公共默认提示词已适配原语言校对；已有私人提示词和任务自定义指令不会自动覆盖。如果其中要求统一输出中文，处理日英材料前需自行调整或在新任务中恢复公共默认指令。

音频语言不自动覆盖参考材料的 OCR 语言。使用 Tesseract 时，按材料设置 `reference.ocr_languages`，并安装对应语言包；日语为 `jpn`，英语为 `eng`。AI OCR 同样应保留源文，不承担翻译。

## 从录音得到整理稿

1. 在“运行设置”选择 ASR 模型、运行配置和音频语言。
2. 需要 AI 校对或 PDF AI OCR 时，配置兼容 **Responses API** 的 Base URL、客户端 API Key 和服务实际提供的模型 ID。应用不会替你部署网关。
3. 新建单任务，选择处理方式，上传材料并检查本次参数。
4. 完成后在“任务列表”预览中间结果，下载 Markdown / TXT；批量任务可下载成功子任务的 ZIP。
5. 人工复核专名、数字、否定条件、引用和低置信片段，再使用或发布文稿。

### 有参考材料

`reference` 是默认模式，必须提供 TXT、Markdown、PDF 或网页参考源。录音和参考文件不必同名。

```bash
".venv/bin/python" "scripts/08_run_job.py" \
  --video "/path/to/recording.mp4" \
  --reference "/path/to/reference.txt" \
  --output-dir "/path/to/output" \
  --content-type reference --asr-language ja --profile local_cpu
```

### 无参考对谈

`conversation` 不接受参考源。以下示例整理英语录音：

```bash
".venv/bin/python" "scripts/08_run_job.py" \
  --video "/path/to/interview.mp4" \
  --output-dir "/path/to/output" \
  --content-type conversation --asr-language en --profile local_cpu
```

已有请求和任务清单应使用 `reference` / `conversation`，不保留其他场景模式别名。`book_name` / `chapter` 字段及 `--book-name` / `--chapter` 参数仍可提供材料名称与章节或部分，参与本次 ASR 提示词；不内置私人词库。

批量清单、逐阶段处理、独立 PDF OCR、术语与诊断见 [命令行与处理指南](docs/CLI_GUIDE.md)。

## AI 服务与数据

默认 AI 后端 `codex_api` 连接 CPA（CLIProxyAPI）或其他兼容网关的标准 `/v1/responses`。名称沿用既有配置，不要求运行 codex-lb。Base URL 可填服务根地址或带 `/v1` 的地址，不要填完整 `/responses` 端点。

Web 用户在“运行设置”填写连接；脚本也可以使用：

```bash
export CODEX_LB_BASE_URL="https://api.example.com/v1"
export CODEX_LB_API_KEY="your-client-api-key"
```

这里的域名与 Key 是占位值，需要替换。模型 ID 必须与服务实际支持的一致。AI 校对和 PDF OCR 的快速模式独立、默认关闭，开启可能增加费用。

- 网页保存的连接和 Key 位于 `data/jobs/frontend-settings.json`，应视为凭据文件并限制访问。
- 上传文件位于 `data/uploads/`；每个任务的快照、中间结果和输出位于 `data/jobs/<job_id>/`。目录式流水线使用 `data/intermediate/` 与 `data/output/`。
- OCR / AI 校对会把相应图像、转录和参考文本发送给你配置的服务；先确认材料授权、隐私政策和费用。
- 日志和诊断可能包含模型响应及原文；不要公开运行数据、截图、环境文件或备份。

参阅 [安全与数据说明](SECURITY.md)。

## Docker 与 GPU

Docker 默认部署面向 NVIDIA GPU。先按宿主平台进行只读预检：

```bash
# 原生 Ubuntu + NVIDIA
bash "scripts/deploy_docker_linux.sh" --check

# WSL2 内原生 Docker Engine + NVIDIA
bash "scripts/deploy_docker_wsl2.sh" --check
```

检查通过后，由管理员按对应文档批准安装与部署。更新容器可能中断任务，`healthy` 不代表任务空闲。不要执行 `docker compose down -v` 清除模型缓存，也不要为解决权限问题递归改写已有资料属主。

- [Docker 部署、数据卷与 API 连接](docs/DOCKER.md)
- [原生 Ubuntu GPU 部署与验收](docs/DOCKER_LINUX.md)
- [WSL2 本地安装](docs/INSTALL_NEW_MACHINE.md)

## 开发与文档

```bash
".venv/bin/python" -m pip install -r "requirements-dev.txt"
".venv/bin/python" -m pytest
npm --prefix "frontend" run build
```

测试不等同于录音质量验收；模型、语言、音频和运行设备需要使用代表性材料人工检查。可选 ASR SDK 使用隔离 Python 环境，避免污染基础 Web / Whisper 环境。

| 想了解什么 | 阅读位置 |
| --- | --- |
| 安装与第一条任务 | [快速启动](docs/QUICKSTART.md) |
| 批量、阶段、OCR、排障 | [命令行与处理指南](docs/CLI_GUIDE.md) |
| 模型、语言、双 ASR 与时间戳 | [ASR 模型说明](docs/ASR_BACKENDS.md) |
| 流水线阶段与中间结构 | [阶段计划](docs/PIPELINE_PLAN.md) |
| 贡献与检查 | [贡献指南](CONTRIBUTING.md) |
| 工具协作历史 | [Claude Code 工作记录](docs/CLAUDE_CODE_WORKLOG.md) |

## 许可证

项目原创代码采用 [MIT License](LICENSE)。第三方代码、依赖、模型权重与输入材料仍适用各自授权，详见 [第三方依赖与授权说明](THIRD_PARTY_NOTICES.md)。
