# ASR Studio 快速启动

## 本地 CPU / 开发环境

准备 Python 3.12、Node.js 22 或更高兼容版本、npm、ffmpeg；PDF 渲染需要 Poppler（`pdftoppm`）。Python 3.12 是部署基线，可选 ASR SDK 应按各自文档使用隔离环境。

在已下载并解压的 `asr-studio` 根目录执行：

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
npm --prefix frontend ci
npm --prefix frontend run build
TRANSCRIPT_PROFILE=local_cpu .venv/bin/python -m uvicorn api_server:app --host 127.0.0.1 --port 8000 --workers 1
```

访问 `http://127.0.0.1:8000`；健康检查为 `/api/health`，接口文档为 `/docs`。该方式直接由后端提供已构建前端。开发双进程入口为 `TRANSCRIPT_PROFILE=local_cpu ./start_web.sh`，参数见 `./start_web.sh --help`。

默认 YAML 的 profile 面向 GPU，因此无 GPU 时必须显式选择 `local_cpu`；网页保存的设置优先于环境默认。首次使用 Whisper 时会下载模型，可能需要访问模型托管服务；缓存位于 `~/.cache/asr-studio/`。运行依赖必须保持 `av==16.1.0`：Whisper 当前解码接口与 PyAV 19 不兼容，Docker 使用同一版本。

## 开始转录

1. 页面语言可切换简体中文、English、日本語；这只改变显示，不改变录音语言或已填写的表单。
2. 在「运行设置」确认 CPU profile、Whisper 候选和音频语言。既有默认仍为中文；日语选 `ja`，英语选 `en`，不确定时可对支持的模型选 `auto`。任务页可单独覆盖；旧任务使用原快照。可选 GPU 后端见 [模型说明](ASR_BACKENDS.md)。
3. 通过「单阶段运行」选择音频抽取或语音转录，上传材料后执行；纯转录无需 AI 校对 API。
4. 需要 OCR / AI 校对时，配置自己可用的兼容 Responses API 服务、API Key 和模型 ID。默认本地地址仅为示例，应用不会安装网关；模型 ID 需与服务实际支持的一致。日英正文保留原语言，不因界面语言而翻译。
5. 在任务详情下载产物，保留原始 ASR 文本和中间结果，人工复核最终稿。

三语入口：[简体中文](../README.md) · [English](../README.en.md) · [日本語](../README.ja.md)。批量与 CLI 示例见 [命令行与处理指南](CLI_GUIDE.md)。

运行数据在 `data/` 中；不要把材料、密钥、任务 JSON 或日志加入公开仓库。Web 设置保存在 `data/jobs/frontend-settings.json`，应视为凭据文件。

## Docker / GPU

见 [Docker 说明](DOCKER.md)。Compose 项目名为 `asr-studio`，服务仍为 `trans`，镜像为 `asr-studio:local`，模型卷为 `asr-studio_model-cache`。这是独立部署，不会读取另一项目的命名卷；旧缓存迁移须另行核对并备份。

```bash
docker compose config --quiet
docker compose build trans
docker compose up -d trans
```

需要 NVIDIA Container Toolkit 和 GPU。默认构建包含 Qwen；可用 `ASR_BACKENDS=whisper docker compose build trans` 只构建 Whisper 基础环境。容器里的 `127.0.0.1` 指容器自身，外部校对网关需配置可达地址。

## 开发检查

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest
npm --prefix frontend run build
```

发布前确认代码授权和项目许可证，并复查实际公开文件。`.gitignore` 只约束 Git 默认添加行为，不能阻止普通文件夹压缩工具带入本地文件；不要直接压缩整个开发目录。源码应排除 `.venv/`、`frontend/node_modules/`、运行数据、临时产物、截图和机器凭据。
