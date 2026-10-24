# Claude Code 工作记录

## 2026-10-24：通用音视频转录与校对定位

本次工作使用 Claude Code 完成。用户确认保留 ASR Studio 品牌，清理内置专用名称与场景资料，并授权改写本地内容历史、保留真实作者和版权、单独留下协作提交；不推送远端。

### 结果与接口迁移

- 项目说明、默认提示词与标题改为通用音视频转录整理定位；默认不加载私人词库。
- 去除特定机构的分类特判。测试材料使用自拟短文、示例资料名称及合成任务标识，保留分句、弱匹配、中文路径、引用锁定和 OCR 清理覆盖。
- Web、API、CLI、批量清单与任务恢复中的参考型模式统一为 `reference`，不保留旧场景别名。`reference` 仍必须提供参考源；`conversation` 仍不接受参考源。
- 既有请求、手写清单和任务快照中的旧参考型模式值需手动改为 `reference`。原始材料、已生成结果和私人提示词不批量迁移。
- 界面使用“材料名称”“章节或部分”；`book_name` / `chapter` 字段及对应 CLI 参数保留，用途仍为 ASR 提示词。
- README 同步移除已不存在的 EPUB 导出能力说明。没有增加或重跑 ASR、OCR、AI 校对能力。

### 修改文件

- 说明与配置：`README.md`、`docs/ASR_BACKENDS.md`、`docs/PIPELINE_PLAN.md`、`config/settings.yaml`、`config/setting.yaml`、`config/default_prompts/final_cleanup.md`。
- 接口与运行入口：`api_server.py`、`scripts/08_run_job.py`、`scripts/09_run_batch_jobs.py`、`src/job_runner.py`、`src/classify_utils.py`、`src/schemas.py`、`src/web/models.py`、`src/web/tasks.py`。
- 前端：`frontend/src/api/client.ts`、`frontend/src/views/SingleJobView.vue`、`frontend/src/views/BatchJobView.vue`。
- 测试支持：`tests/helpers.py`、`tests/frontend_workbench_server.py`。
- 测试：`tests/test_align.py`、`tests/test_api_server.py`、`tests/test_classify.py`、`tests/test_cleanup_prompts.py`、`tests/test_export_markdown.py`、`tests/test_job_runner.py`、`tests/test_ocr_page_markers.py`、`tests/test_pdf_book_ocr_web.py`、`tests/test_prepare_reference.py`、`tests/test_refine.py`；新增 `tests/test_neutral_defaults.py`。
- 本地规则：同步已被忽略的 `AGENTS.md` 项目目标。既有 CodeStable 档案继续保持本地，不批量纳入公开仓库。

### 验证证据

- 修改前：`.venv/bin/python -m pytest`，662 项通过。
- 新增 6 项默认值与模式契约用例，先观察到 6 项预期失败，再实现修改。
- 最终：`.venv/bin/python -m pytest`，668 项通过。
- `npm --prefix frontend run build`：类型检查和生产构建通过；存在打包后单块超过 500 kB 的体积警告。
- 实际运行 `scripts/03_prepare_reference.py`，使用隔离配置提取自拟 TXT 材料：1 项成功，输出 `sample.txt`、`sample.json`；`success=true`，`extraction_method=direct_text_read`，无警告。
- 隔离 API 返回 `reference` / `conversation` 两种模式，并成功预览公开默认提示词。浏览器检查单任务模式来回切换、参考源显示条件、材料名称标签和批量默认模式；截图已实际查看。
- 根据 `docs/REVIEW_CHECKLIST.md` 自查范围、配置、接口与中间结构。已知旧名称、机构与原样例标识在受跟踪内容扫描中无匹配。
- 本地样例输出位于 `tmp/generalize-project-smoke/`，界面隔离数据位于 `tmp/generalize-project-web-data/`，截图为 `tmp/generalize-project-single-job.png`；这些本地产物不随源码发布。
- 没有真实录音输入，也没有调用 ASR、OCR 或外部模型；本次验证不包含模型推理质量验收。

### Git 与范围

清理后的初始内容提交为 `e1a343b`，保留原作者和原提交说明。本文件单独提交，并通过提交尾注 `Assisted-by: Claude Code` 标明本次工具协作，不将此前开发冒记为本次工作。

原始历史已在仓库外保存本地恢复备份，备份仍含原始内容，不应随清理后的项目发布。许可证、第三方声明及真实版权信息保留；私人材料、既有输出、凭据、部署与远端发布不在本轮修改范围。

## 2026-10-24：中英日界面与录音语言适配

本轮由 Claude Code 实现。用户要求增加日语、英语适配，重写中文 README，并新增英文、日文版本；确认采用界面语言与录音语言独立的方案。Codex、Gemini MCP 连接失败后，用户明确允许本轮不使用外部模型继续；没有把连接失败记录为外部评审通过。

### 结果与使用方式

- 页面语言选择器支持简体中文、English、日本語，默认中文，偏好保存在浏览器；切换不重建表单或修改音频语言。公共文案、状态、日期、Naive UI 内建语言与可访问名称同步切换。
- “运行设置”和各任务支持独立音频语言：`auto`、`zh`、`en`、`ja`。CLI 使用 `--asr-language`，YAML 仍为 `asr.language`，API 和批量清单使用可选 `asr_language`。
- 保留中文默认、指定配置及旧任务快照的继承方式；旧 Whisper 配置中的其他合法语言可以继续继承，不静默改成中文。批量条目可以覆盖批次语言。
- Whisper、Qwen3-ASR、Fun-ASR-Nano 接通本轮语言参数；Paraformer-zh 只接受中文。主、次 ASR 均校验能力，不支持的组合报错，不自动换模型。
- 请求语言与 SDK 实际报告语言分开记录。中文 Qwen 既有有界恢复继续只用于中文，不扩展到日英或自动检测。
- 公共提示词保留英语、日语及混合语段，标题与问答标签跟随正文；修复英文分句空格丢失与参考文本清洗误删英文开头。参考材料 OCR 语言不跟随音频语言自动覆盖。
- 三份 README 同构互链，首页收敛为安装、语言设置与任务入口；详细批量、逐阶段、OCR 和诊断操作移到 `docs/CLI_GUIDE.md`。已有私人提示词、自定义指令不会自动更新，若其中强制输出中文，使用日英材料前需自行调整或在新任务中恢复公共默认。

### 修改文件

- 文档：`README.md`、新增 `README.en.md`、`README.ja.md`、`docs/CLI_GUIDE.md`；更新 `docs/QUICKSTART.md`、`docs/ASR_BACKENDS.md`、`docs/PIPELINE_PLAN.md` 和本工作记录。
- 公共提示词：`config/default_prompts/classify_and_correct.md`、`config/default_prompts/conversation_cleanup.md`、`config/default_prompts/final_cleanup.md`。
- 配置与任务：`api_server.py`、`src/schemas.py`、`src/settings_overrides.py`、`src/job_runner.py`、`src/web/models.py`、`src/web/tasks.py`、`src/web/frontend_settings.py`。
- 转录与文本处理：`src/asr/registry.py`、`src/asr/worker.py`、`src/asr/qwen3_backend.py`、`src/asr/funasr_backend.py`、`src/asr/segmentation.py`、`src/asr_utils.py`、`src/align_utils.py`、`src/reference_utils.py`、`src/refine_utils.py`。
- CLI：`scripts/00_run_main_pipeline.py`、`scripts/02_transcribe.py`、`scripts/06_refine.py`、`scripts/08_run_job.py`、`scripts/09_run_batch_jobs.py`、`scripts/run_pipeline.py`、`scripts/probe_asr_backends.py`、`scripts/check_docker_gpu.py`。
- 前端新增：`frontend/src/i18n/index.ts`、`frontend/src/i18n/messages.ts`、`frontend/src/components/AsrLanguageSelector.vue`、`frontend/src/composables/asrLanguage.ts`、`frontend/tests/i18n.mjs`、`frontend/tests/radio-layout.mjs`。
- 前端入口与 API：`frontend/package.json`、`frontend/src/App.vue`、`frontend/src/api/client.ts`、`frontend/src/composables/useConfigOptions.ts`、`frontend/src/styles/main.css`。
- 前端页面：`SingleJobView.vue`、`BatchJobView.vue`、`JobListView.vue`、`StageRunnerView.vue`、`PDFBookOCRView.vue`、`SettingsView.vue`，均位于 `frontend/src/views/`。
- 公共组件：`AsrCandidateSelector.vue`、`BackendSelector.vue`、`FileBrowser.vue`、`JobArtifactsViewer.vue`、`JobStatusCard.vue`、`NavBar.vue`、`ProfileSelector.vue`、`RemoteDirectoryUpload.vue`、`RemoteFileUpload.vue`、`StageFileUpload.vue`，均位于 `frontend/src/components/`。
- Python 测试：新增 `tests/test_asr_languages.py`，更新 `tests/test_api_server.py`。设计和本地事项记录继续留在既有本地管理目录，不批量加入公开源码。

### 验证证据

- 项目虚拟环境全量测试：`.venv/bin/python -m pytest`，**737 passed / 33.58s**，包含 69 项新增公共语言用例及既有中文恢复回归。
- `npm --prefix frontend run test:i18n`：564 个消息键、三语占位符和响应切换、19 个 Vue 文件的 710 处源键引用、六页面三语实际 SFC 渲染、语言继承与七类请求序列化检查通过。
- `npm --prefix frontend run build`：类型检查与生产构建通过；仍有单块超过 500 kB 的体积警告。
- 隔离 HTTP/API 实测四种语言能力、中文配置默认、日语 Web 默认保存读回，以及公共英日保留原文提示；证据 `tmp/multilingual-http-summary.json`。
- 实际运行 `scripts/03_prepare_reference.py` 与 `scripts/07_export_markdown.py`，英日自拟 TXT 提取、Markdown/TXT 输出保留原文，输出 `tmp/multilingual-text-smoke/{en,ja}/final_dir/`。
- 独立 Chrome 实际检查同页连续切换三语、表单值保留、界面与音频语言独立、刷新持久化、六个主要页面、英文删除确认取消、日文设置和手机导航。
- 英文界面实际上传自拟英日 `final_markdown` JSON，调用已有导出阶段，下载 ZIP；只读检查 ZIP 中 Markdown/TXT 均完整包含英文和日文源句。证据 `tmp/multilingual-browser/summary.json`、`export-state.json`、`multilingual-export.zip`。这些输入是文本样例，不是 AI 校对结果。
- 三份 README 各 174 行，七组可执行示例一致；七份文档本地链接及锚点检查通过，CLI 日英批次示例通过生产清单校验器。
- 窄屏截图发现日文批量页第二行模式选项被裁切，定位为 Naive radio button group 固定一行高度；最小修改其自适应高度与标签换行。新增 `frontend/tests/radio-layout.mjs`、`test:radio-layout`：先观察到第3项被后续提示遮挡的预期失败，再验证中英日 390px 下 36 次裁切检查、容器包含、中心 hit-test 和实际点击全部通过；最终日英截图已实际查看，四模式完整显示。修复后重新执行本地化检查与生产构建，通过；保留既有体积警告。

### 验收范围与继续条件

本轮未执行真实英日录音推理、真实 PDF OCR、外部 AI 调用、付费服务或部署。SDK 实参和工程链路已经检查，录音识别精度仍需用获得授权的代表性短录音分别验收。隔离样例不访问用户真实任务；既有上游产物未回写。按 `docs/REVIEW_CHECKLIST.md` 检查批准范围、虚拟环境、真实运行和兼容结构。

本轮没有新增 Git 提交、改写历史或推送；本文件如实记录本轮协作，不将未发生的 Git 操作写成已完成。
