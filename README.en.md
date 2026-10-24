# ASR Studio

[简体中文](README.md) · [English](README.en.md) · [日本語](README.ja.md)

**Turn recordings into readable, reviewable transcripts without losing the source evidence.**

ASR Studio is a self-hosted transcription and proofreading workbench. Upload a lecture, screen recording, or interview, choose a speech model, optionally add reference material, and export Markdown and plain text. Original transcripts and intermediate results are kept separately.

```text
Audio/video → Transcription → Optional reference text / PDF OCR → AI proofreading → Markdown + TXT
```

Local ASR does not need a proofreading API. AI PDF OCR and AI proofreading require your own compatible service and credentials. There is no built-in authentication: run the application on a trusted local machine or behind access controls.

## What you can do

- **Use three interface languages:** Simplified Chinese, English, and Japanese, independently of the recording language.
- **Choose a speech model:** Whisper and Qwen3-ASR, with optional Paraformer and Fun-ASR-Nano integrations. Capabilities and dependencies vary by model.
- **Work with or without references:** proofread against reference material, or clean up a conversation using the recording alone.
- **Process individual or batch jobs:** upload files, match directories, share a reference, or use a YAML / JSON manifest.
- **Run standalone PDF OCR:** process a PDF or a directory, retain completed-page checkpoints, retry missing pages, and download TXT or ZIP files.
- **Inspect the evidence:** review task status, original ASR, reference text, draft manuscripts, and request diagnostics before downloading Markdown / TXT.

## Quick start

Install Python **3.12**, Node.js **22**, npm, and `ffmpeg`. PDF processing also needs Poppler's `pdftoppm`. From the project root:

```bash
python3.12 -m venv ".venv"
".venv/bin/python" -m pip install -r "requirements.txt"
npm --prefix "frontend" ci
npm --prefix "frontend" run build
TRANSCRIPT_PROFILE=local_cpu ".venv/bin/python" -m uvicorn api_server:app \
  --host 127.0.0.1 --port 8000 --workers 1
```

Open **http://127.0.0.1:8000**. API documentation is at `/docs`; the health endpoint is `/api/health`.

- Select `local_cpu` explicitly when no GPU is available. The default YAML targets a GPU, and saved Web settings can override environment defaults.
- The first transcription may download model weights. Installed dependencies do not prove that weights are cached or GPU inference works.
- For transcription only, open the stage runner, select transcription, and upload audio. No AI proofreading service is required.
- For development, use `TRANSCRIPT_PROFILE=local_cpu ./start_web.sh`; the frontend runs at `http://127.0.0.1:5173`. Press `Ctrl+C` to stop both processes.

See the [setup guide](docs/QUICKSTART.md) for installation, caching, and environment details. Detailed guides currently linked from this README are in Chinese.

## Language settings

### Interface language

Use the language selector to switch between **简体中文 / English / 日本語**. Your preference is saved in the current browser; Simplified Chinese is the default. Switching the interface keeps form entries and does not change the recording language.

### Recording language

Save a default in Settings or choose a language for an individual task:

| Code | Meaning |
| --- | --- |
| `zh` | Chinese; preserves the existing default |
| `en` | English |
| `ja` | Japanese |
| `auto` | Ask a supported speech model to identify the language |

Prefer an explicit language when you know it, especially for short or mixed-language recordings. `auto` means language detection, not translation. English and Japanese transcripts retain their original language; Chinese speech is written in Simplified Chinese. The interface language does not determine the manuscript language.

Whisper and Qwen receive the selected language through their engine-specific parameters. Other candidates are checked against their supported capabilities: unsupported combinations fail explicitly instead of silently switching models. Both candidates in a dual-ASR task must support the selected language. See [ASR models](docs/ASR_BACKENDS.md) for capabilities, installation, and timestamp limits.

CLI configuration continues to use `asr.language` in the existing YAML:

```yaml
asr:
  language: ja
```

Change this field in your existing configuration; this snippet is not a complete settings file. Omitting a task override preserves configuration inheritance. Existing tasks retain their snapshots; changing the interface or later defaults does not rewrite them.

Public default prompts preserve the source language. Existing private prompts and task-specific instructions are not overwritten. If yours require Chinese-only output, adjust them before processing English or Japanese material, or restore the public defaults in a new task.

The recording language does not automatically replace the reference OCR language. For Tesseract, configure `reference.ocr_languages` for the material and install the corresponding language packs: `jpn` for Japanese and `eng` for English. AI OCR should also preserve the source language rather than translate it.

## From a recording to a manuscript

1. In Settings, choose the ASR model, runtime profile, and recording language.
2. If you need AI proofreading or AI PDF OCR, configure a **Responses API**-compatible Base URL, client API key, and model IDs actually offered by your service. The application does not deploy the gateway for you.
3. Create a job, choose the processing mode, upload the material, and check the task settings.
4. In the job list, inspect intermediate results and download Markdown / TXT. Batch jobs offer a ZIP of successful items.
5. Review names, numbers, negation, conditions, quotations, and uncertain passages before using or publishing the manuscript.

### With reference material

`reference` is the default mode and requires a TXT, Markdown, PDF, or web reference. The recording and reference do not need matching filenames.

```bash
".venv/bin/python" "scripts/08_run_job.py" \
  --video "/path/to/recording.mp4" \
  --reference "/path/to/reference.txt" \
  --output-dir "/path/to/output" \
  --content-type reference --asr-language ja --profile local_cpu
```

### Conversation without a reference

`conversation` does not accept a reference. This example processes an English recording:

```bash
".venv/bin/python" "scripts/08_run_job.py" \
  --video "/path/to/interview.mp4" \
  --output-dir "/path/to/output" \
  --content-type conversation --asr-language en --profile local_cpu
```

Requests and manifests must use `reference` / `conversation`; other legacy scenario aliases are not accepted. The `book_name` / `chapter` fields and `--book-name` / `--chapter` options still accept an optional material title and section, used in the ASR prompt. No private glossary is bundled.

See the [CLI and processing guide](docs/CLI_GUIDE.md) for batches, individual stages, standalone PDF OCR, terminology, and diagnostics.

## AI services and your data

The default AI backend, `codex_api`, connects to the standard `/v1/responses` endpoint of CPA (CLIProxyAPI) or another compatible gateway. The legacy configuration name does not require a codex-lb deployment. Enter a service root or a Base URL ending in `/v1`, not a full `/responses` endpoint.

Web users configure the connection in Settings. Scripts can also use:

```bash
export CODEX_LB_BASE_URL="https://api.example.com/v1"
export CODEX_LB_API_KEY="your-client-api-key"
```

The domain and key above are placeholders. Replace them with your own connection details and use model IDs supported by that service. AI proofreading and PDF OCR have separate fast-mode settings, both off by default; enabling them may increase charges.

- Saved connection details and keys are stored in `data/jobs/frontend-settings.json`. Treat it as a credentials file and restrict access.
- Uploads live in `data/uploads/`; task snapshots, intermediate files, and results live in `data/jobs/<job_id>/`. Directory-based stages use `data/intermediate/` and `data/output/`.
- OCR and AI proofreading send the relevant images, transcripts, and references to your configured service. Check material permissions, privacy policies, and costs first.
- Logs and diagnostics may include model responses and source text. Do not publish runtime data, screenshots, environment files, or backups.

Read the [security and data notes](SECURITY.md).

## Docker and GPU deployment

The default Docker deployment targets NVIDIA GPUs. Start with the read-only check for your host:

```bash
# Native Ubuntu with NVIDIA
bash "scripts/deploy_docker_linux.sh" --check

# Native Docker Engine inside WSL2 with NVIDIA
bash "scripts/deploy_docker_wsl2.sh" --check
```

An administrator should review the check and authorize installation and deployment using the corresponding guide. Updating a container can interrupt tasks; a healthy service is not necessarily idle. Do not remove the model cache with `docker compose down -v`, or recursively change ownership of existing material to work around permissions.

- [Docker deployment, volumes, and API connections](docs/DOCKER.md)
- [Native Ubuntu GPU deployment and acceptance checks](docs/DOCKER_LINUX.md)
- [Local WSL2 installation](docs/INSTALL_NEW_MACHINE.md)

## Development and documentation

```bash
".venv/bin/python" -m pip install -r "requirements-dev.txt"
".venv/bin/python" -m pytest
npm --prefix "frontend" run build
```

Passing tests does not establish transcription quality. Review representative recordings for your model, language, and hardware. Optional ASR SDKs run in an isolated Python environment to avoid disturbing the base Web / Whisper environment.

| What you need | Where to read |
| --- | --- |
| Installation and a first task | [Quick start](docs/QUICKSTART.md) |
| Batches, stages, OCR, troubleshooting | [CLI and processing guide](docs/CLI_GUIDE.md) |
| Models, languages, dual ASR, timestamps | [ASR models](docs/ASR_BACKENDS.md) |
| Pipeline stages and intermediate formats | [Pipeline plan](docs/PIPELINE_PLAN.md) |
| Contributing and checks | [Contributing](CONTRIBUTING.md) |
| Tool-assisted work history | [Claude Code work log](docs/CLAUDE_CODE_WORKLOG.md) |

## License

Original project code is available under the [MIT License](LICENSE). Third-party code, dependencies, model weights, and input material retain their own licenses. See [third-party notices](THIRD_PARTY_NOTICES.md).
