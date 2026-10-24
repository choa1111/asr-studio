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
